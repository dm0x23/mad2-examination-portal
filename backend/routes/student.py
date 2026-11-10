from datetime import datetime, timezone
from flask import Blueprint, g, jsonify, request

try:
    from backend.database import db
    from backend.models import (
        User,
        Course,
        Examination,
        ExaminationRubric,
        ExaminationSlot,
        Booking,
        Evaluation,
    )
    from backend.utils.auth_middleware import role_required
except ImportError:
    from database import db
    from models import (
        User,
        Course,
        Examination,
        ExaminationRubric,
        ExaminationSlot,
        Booking,
        Evaluation,
    )
    from utils.auth_middleware import role_required

student_bp = Blueprint("student", __name__, url_prefix="/api/student")


def utc_now():
    return datetime.now(timezone.utc)


def is_booking_open(exam: Examination) -> bool:

    if exam.status == "Booking Open":
        return True
    if exam.status in ("Cancelled", "Completed", "Booking Closed"):
        return False

    now = datetime.now()
    if exam.slot_booking_start_date and exam.slot_booking_end_date:
        start = exam.slot_booking_start_date.replace(tzinfo=None)
        end = exam.slot_booking_end_date.replace(tzinfo=None)
        return start <= now <= end

    return False


def format_booking_payload(booking: Booking) -> dict:
    slot = booking.slot
    exam = slot.examination if slot else None
    course = exam.course if exam else None
    examiner = slot.examiner if slot else None
    examiner_profile = examiner.examiner_profile if examiner else None

    can_cancel = False
    if booking.status == "Booked" and exam:
        if exam.status == "Booking Open":
            can_cancel = True
        elif exam.slot_booking_end_date:
            now = datetime.now()
            deadline = exam.slot_booking_end_date.replace(tzinfo=None)
            can_cancel = now <= deadline

    return {
        "booking_id": booking.id,
        "booking_date": booking.booking_date.isoformat() if booking.booking_date else None,
        "status": booking.status,
        "can_cancel": can_cancel,
        "slot": {
            "id": slot.id if slot else None,
            "date": slot.date.isoformat() if slot and slot.date else None,
            "start_time": slot.start_time.strftime("%H:%M") if slot and slot.start_time else None,
            "end_time": slot.end_time.strftime("%H:%M") if slot and slot.end_time else None,
            "meeting_link": slot.meeting_link if slot else None,
            "status": slot.status if slot else None,
        } if slot else None,
        "examiner": {
            "id": examiner.id if examiner else None,
            "name": examiner_profile.name if examiner_profile else (examiner.email if examiner else "N/A"),
            "email": examiner.email if examiner else "N/A",
            "department": examiner_profile.department if examiner_profile else "N/A",
        } if examiner else None,
        "examination": {
            "id": exam.id if exam else None,
            "name": exam.name if exam else "N/A",
            "type": exam.type if exam else "N/A",
            "status": exam.status if exam else "N/A",
            "slot_booking_end_date": exam.slot_booking_end_date.isoformat() if exam and exam.slot_booking_end_date else None,
        } if exam else None,
        "course": {
            "id": course.id if course else None,
            "code": course.code if course else "N/A",
            "name": course.name if course else "N/A",
        } if course else None,
        "rubrics": [r.to_dict() for r in exam.rubrics] if exam and exam.rubrics else [],
        "evaluation": booking.evaluation.to_dict() if booking.evaluation else None,
        "has_evaluation": booking.evaluation is not None,
    }


@student_bp.route("/dashboard", methods=["GET"])
@role_required("Student")
def get_student_dashboard():
    student_id = g.current_user.id

    all_bookings = (
        Booking.query.filter_by(student_id=student_id)
        .order_by(Booking.booking_date.desc())
        .all()
    )

    formatted_bookings = [format_booking_payload(b) for b in all_bookings]

    upcoming_bookings = [b for b in formatted_bookings if b["status"] == "Booked"]
    results_list = [b for b in formatted_bookings if b["has_evaluation"]]

    active_booked_exam_ids = {
        b["examination"]["id"]
        for b in upcoming_bookings
        if b["examination"] and b["examination"]["id"]
    }

    active_exams = (
        Examination.query.filter(Examination.status != "Cancelled")
        .order_by(Examination.id.desc())
        .all()
    )

    open_examinations = []
    for ex in active_exams:
        if is_booking_open(ex):
            available_slots_count = ExaminationSlot.query.filter(
                ExaminationSlot.examination_id == ex.id,
                ExaminationSlot.available_seats > 0,
                ExaminationSlot.status != "Cancelled",
            ).count()

            open_examinations.append(
                {
                    "id": ex.id,
                    "name": ex.name,
                    "type": ex.type,
                    "course_id": ex.course_id,
                    "course_code": ex.course.code if ex.course else None,
                    "course_name": ex.course.name if ex.course else None,
                    "slot_booking_start_date": ex.slot_booking_start_date.isoformat() if ex.slot_booking_start_date else None,
                    "slot_booking_end_date": ex.slot_booking_end_date.isoformat() if ex.slot_booking_end_date else None,
                    "status": ex.status,
                    "is_booking_open": True,
                    "available_slots_count": available_slots_count,
                    "has_active_booking": ex.id in active_booked_exam_ids,
                }
            )

    return (
        jsonify(
            {
                "student": g.current_user.to_dict(),
                "metrics": {
                    "active_bookings_count": len(upcoming_bookings),
                    "completed_exams_count": sum(1 for b in formatted_bookings if b["status"] == "Completed"),
                    "available_exams_count": len(open_examinations),
                    "total_evaluations_count": len(results_list),
                },
                "open_examinations": open_examinations,
                "upcoming_bookings": upcoming_bookings,
                "booking_history": formatted_bookings,
                "results": results_list,
            }
        ),
        200,
    )


@student_bp.route("/examinations", methods=["GET"])
@role_required("Student")
def list_available_examinations():

    student_id = g.current_user.id
    active_booked_exam_ids = {
        b.slot.examination_id
        for b in Booking.query.filter_by(student_id=student_id, status="Booked").all()
        if b.slot
    }

    all_exams = (
        Examination.query.filter(Examination.status != "Cancelled")
        .order_by(Examination.id.desc())
        .all()
    )

    results = []
    for ex in all_exams:
        open_status = is_booking_open(ex)
        if open_status:
            avail_slots = ExaminationSlot.query.filter(
                ExaminationSlot.examination_id == ex.id,
                ExaminationSlot.available_seats > 0,
                ExaminationSlot.status != "Cancelled",
            ).count()

            results.append(
                {
                    "id": ex.id,
                    "name": ex.name,
                    "type": ex.type,
                    "course_id": ex.course_id,
                    "course_code": ex.course.code if ex.course else None,
                    "course_name": ex.course.name if ex.course else None,
                    "slot_booking_start_date": ex.slot_booking_start_date.isoformat() if ex.slot_booking_start_date else None,
                    "slot_booking_end_date": ex.slot_booking_end_date.isoformat() if ex.slot_booking_end_date else None,
                    "status": ex.status,
                    "is_booking_open": True,
                    "available_slots_count": avail_slots,
                    "has_active_booking": ex.id in active_booked_exam_ids,
                    "rubrics": [r.to_dict() for r in ex.rubrics],
                }
            )

    return jsonify({"examinations": results, "total": len(results)}), 200


@student_bp.route("/examinations/<int:exam_id>/slots", methods=["GET"])
@role_required("Student")
def list_examination_slots(exam_id):

    exam = Examination.query.get(exam_id)
    if not exam:
        return jsonify({"error": "Not Found", "message": "Examination not found."}), 404

    slots = (
        ExaminationSlot.query.filter(
            ExaminationSlot.examination_id == exam.id,
            ExaminationSlot.available_seats > 0,
            ExaminationSlot.status != "Cancelled",
        )
        .order_by(ExaminationSlot.date.asc(), ExaminationSlot.start_time.asc())
        .all()
    )

    results = []
    for s in slots:
        examiner = s.examiner
        profile = examiner.examiner_profile if examiner else None
        results.append(
            {
                "id": s.id,
                "examination_id": s.examination_id,
                "examination_name": exam.name,
                "course_code": exam.course.code if exam.course else None,
                "date": s.date.isoformat() if s.date else None,
                "start_time": s.start_time.strftime("%H:%M") if s.start_time else None,
                "end_time": s.end_time.strftime("%H:%M") if s.end_time else None,
                "max_capacity": s.max_capacity,
                "available_seats": s.available_seats,
                "status": s.status,
                "meeting_link": s.meeting_link,
                "examiner_id": s.examiner_id,
                "examiner_name": profile.name if profile else (examiner.email if examiner else "N/A"),
                "examiner_email": examiner.email if examiner else "N/A",
                "examiner_department": profile.department if profile else "N/A",
            }
        )

    return (
        jsonify(
            {
                "examination_id": exam.id,
                "examination_name": exam.name,
                "course_code": exam.course.code if exam.course else None,
                "is_booking_open": is_booking_open(exam),
                "slots": results,
                "total_available_slots": len(results),
            }
        ),
        200,
    )


@student_bp.route("/bookings", methods=["POST"])
@role_required("Student")
def book_slot():

    student_id = g.current_user.id
    data = request.get_json(silent=True) or {}
    slot_id = data.get("slot_id")

    if not slot_id:
        return jsonify({"error": "Bad Request", "message": "slot_id is required."}), 400

    slot = ExaminationSlot.query.get(slot_id)
    if not slot:
        return jsonify({"error": "Not Found", "message": "Examination slot not found."}), 404

    exam = slot.examination
    if not exam:
        return jsonify({"error": "Not Found", "message": "Parent examination not found."}), 404

    if not is_booking_open(exam):
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": (
                        f"Student booking is currently closed for '{exam.name}'. "
                        f"Booking window: {exam.slot_booking_start_date} to {exam.slot_booking_end_date} "
                        f"(Status: {exam.status})."
                    ),
                }
            ),
            400,
        )

    existing_active_booking = (
        Booking.query.join(ExaminationSlot)
        .filter(
            Booking.student_id == student_id,
            Booking.status == "Booked",
            ExaminationSlot.examination_id == exam.id,
        )
        .first()
    )

    if existing_active_booking:
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": (
                        f"You already have an active booking (Slot #{existing_active_booking.slot_id}) "
                        f"for '{exam.name}'. You may only reserve one slot per examination. "
                        "Please cancel your existing booking first if you wish to choose another slot."
                    ),
                }
            ),
            400,
        )

    if slot.available_seats <= 0 or slot.status in ("Full", "Cancelled", "Completed"):
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": "This examination slot is full or unavailable.",
                }
            ),
            400,
        )

    slot.available_seats = max(0, slot.available_seats - 1)
    if slot.available_seats == 0:
        slot.status = "Full"

    new_booking = Booking(
        student_id=student_id,
        slot_id=slot.id,
        status="Booked",
        booking_date=utc_now(),
    )
    db.session.add(new_booking)
    db.session.commit()

    return (
        jsonify(
            {
                "message": (
                    f"Successfully reserved slot on {slot.date} "
                    f"({slot.start_time.strftime('%H:%M')} - {slot.end_time.strftime('%H:%M')}) "
                    f"for examination '{exam.name}'."
                ),
                "booking": format_booking_payload(new_booking),
            }
        ),
        201,
    )


@student_bp.route("/bookings/<int:booking_id>/cancel", methods=["POST"])
@role_required("Student")
def cancel_booking(booking_id):
    """
    POST /api/student/bookings/<id>/cancel
    Ensure the booking belongs to the authenticated student and has status 'Booked'.
    Verify cancellation is made before the booking deadline (slot_booking_end_date).
    Update booking.status = 'Cancelled'.
    Increment slot.available_seats by 1.
    If slot.status == 'Full', restore it to 'Available'.
    Commit and return HTTP 200.
    """
    student_id = g.current_user.id
    booking = Booking.query.get(booking_id)

    if not booking:
        return jsonify({"error": "Not Found", "message": "Booking not found."}), 404

    if booking.student_id != student_id:
        return (
            jsonify(
                {
                    "error": "Forbidden",
                    "message": "You can only cancel your own bookings.",
                }
            ),
            403,
        )

    if booking.status != "Booked":
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": f"Cannot cancel booking with current status '{booking.status}'.",
                }
            ),
            400,
        )

    slot = booking.slot
    exam = slot.examination if slot else None

    if exam and exam.slot_booking_end_date and exam.status != "Booking Open":
        now = datetime.now()
        deadline = exam.slot_booking_end_date.replace(tzinfo=None)
        if now > deadline:
            return (
                jsonify(
                    {
                        "error": "Bad Request",
                        "message": (
                            f"Cancellation deadline ({exam.slot_booking_end_date.strftime('%Y-%m-%d %H:%M')}) "
                            "has passed. You can no longer cancel this reservation."
                        ),
                    }
                ),
                400,
            )

    booking.status = "Cancelled"

    if slot:
        slot.available_seats = min(slot.max_capacity, slot.available_seats + 1)
        if slot.status == "Full" and slot.available_seats > 0:
            slot.status = "Available"

    db.session.commit()

    return (
        jsonify(
            {
                "message": f"Booking #{booking.id} cancelled successfully. The reserved seat has been released.",
                "booking": format_booking_payload(booking),
            }
        ),
        200,
    )



@student_bp.route("/examinations/search", methods=["GET"])
@role_required("Student")
def search_examinations():
    """
    GET /api/student/examinations/search?q=...
    Search examinations by name, course code, or type.
    """
    search_text = (request.args.get("q") or request.args.get("query") or "").strip()
    if not search_text:
        return list_available_examinations()

    student_id = g.current_user.id
    pattern = f"%{search_text}%"

    active_booked_exam_ids = {
        b.slot.examination_id
        for b in Booking.query.filter_by(student_id=student_id, status="Booked").all()
        if b.slot
    }

    matching_exams = (
        Examination.query.join(Course)
        .filter(
            Examination.status != "Cancelled",
            (
                Examination.name.ilike(pattern)
                | Course.code.ilike(pattern)
                | Course.name.ilike(pattern)
                | Examination.type.ilike(pattern)
            ),
        )
        .order_by(Examination.id.desc())
        .all()
    )

    results = []
    for ex in matching_exams:
        avail_slots = ExaminationSlot.query.filter(
            ExaminationSlot.examination_id == ex.id,
            ExaminationSlot.available_seats > 0,
            ExaminationSlot.status != "Cancelled",
        ).count()

        results.append(
            {
                "id": ex.id,
                "name": ex.name,
                "type": ex.type,
                "course_id": ex.course_id,
                "course_code": ex.course.code if ex.course else None,
                "course_name": ex.course.name if ex.course else None,
                "slot_booking_start_date": ex.slot_booking_start_date.isoformat() if ex.slot_booking_start_date else None,
                "slot_booking_end_date": ex.slot_booking_end_date.isoformat() if ex.slot_booking_end_date else None,
                "status": ex.status,
                "is_booking_open": is_booking_open(ex),
                "available_slots_count": avail_slots,
                "has_active_booking": ex.id in active_booked_exam_ids,
            }
        )

    return jsonify({"query": search_text, "examinations": results, "total": len(results)}), 200


# ---------------------------------------------------------------------------
# 6. Student Examination Booking History & Results (Milestone 6)
# ---------------------------------------------------------------------------


@student_bp.route("/history", methods=["GET"])
@role_required("Student")
def get_student_history():
    """
    GET /api/student/history
    Student can view only their own booking records, examination attempts,
    published marks, and rubric feedback.
    """
    student_id = g.current_user.id
    bookings = (
        Booking.query.filter_by(student_id=student_id)
        .order_by(Booking.booking_date.desc())
        .all()
    )

    formatted = [format_booking_payload(b) for b in bookings]
    completed = [b for b in formatted if b["status"] == "Completed" or b["has_evaluation"]]
    cancelled = [b for b in formatted if b["status"] == "Cancelled"]
    upcoming = [b for b in formatted if b["status"] == "Booked"]

    return (
        jsonify(
            {
                "student": g.current_user.to_dict(),
                "metrics": {
                    "total_bookings": len(formatted),
                    "completed": len(completed),
                    "cancelled": len(cancelled),
                    "upcoming": len(upcoming),
                },
                "bookings": formatted,
                "completed_evaluations": completed,
            }
        ),
        200,
    )


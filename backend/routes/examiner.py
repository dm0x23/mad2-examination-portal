from datetime import datetime, date, time, timezone
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

examiner_bp = Blueprint("examiner", __name__, url_prefix="/api/examiner")


def utc_now():
    return datetime.now(timezone.utc)


def parse_date(d_val):
    if not d_val:
        return None
    if isinstance(d_val, date) and not isinstance(d_val, datetime):
        return d_val
    d_str = str(d_val).strip()[:10]
    return datetime.strptime(d_str, "%Y-%m-%d").date()


def parse_time(t_val):
    if not t_val:
        return None
    if isinstance(t_val, time):
        return t_val
    t_str = str(t_val).strip()
    if len(t_str) == 5:
        return datetime.strptime(t_str, "%H:%M").time()
    return datetime.strptime(t_str[:8], "%H:%M:%S").time()


def is_slot_creation_open(exam: Examination) -> bool:
    """
    Check if slot creation is currently open:
    1. If status is explicitly 'Slot Creation Open', allow creation.
    2. If within slot_creation_start_date and slot_creation_end_date, and not cancelled/closed.
    """
    if exam.status == "Slot Creation Open":
        return True
    if exam.status in ("Cancelled", "Completed", "Slot Creation Closed"):
        return False

    now = datetime.now()
    if exam.slot_creation_start_date and exam.slot_creation_end_date:
        start = exam.slot_creation_start_date.replace(tzinfo=None)
        end = exam.slot_creation_end_date.replace(tzinfo=None)
        return start <= now <= end

    return False


# ---------------------------------------------------------------------------
# 1. Examiner Dashboard Metrics
# ---------------------------------------------------------------------------


@examiner_bp.route("/dashboard", methods=["GET"])
@role_required("Examiner")
def get_dashboard_metrics():
    """
    GET /api/examiner/dashboard
    Fetch the logged-in examiner's assigned examinations.
    Return counts for: created examination slots, total booked students,
    and pending student evaluations.
    """
    examiner_id = g.current_user.id

    # Created slots
    slots = (
        ExaminationSlot.query.filter_by(examiner_id=examiner_id)
        .order_by(ExaminationSlot.date.desc(), ExaminationSlot.start_time.asc())
        .all()
    )
    total_slots = len(slots)

    # Bookings on examiner slots
    slot_ids = [s.id for s in slots]
    if slot_ids:
        all_bookings = (
            Booking.query.filter(Booking.slot_id.in_(slot_ids))
            .order_by(Booking.booking_date.desc())
            .all()
        )
    else:
        all_bookings = []

    total_booked_students = len(all_bookings)
    pending_evaluations = sum(1 for b in all_bookings if b.status != "Completed" and not b.evaluation)
    completed_evaluations = sum(1 for b in all_bookings if b.status == "Completed" or b.evaluation)

    # Active examinations
    active_exams = (
        Examination.query.filter(Examination.status != "Cancelled")
        .order_by(Examination.id.desc())
        .all()
    )

    exams_data = []
    for ex in active_exams:
        d = ex.to_dict(include_rubrics=True)
        d["slot_creation_open"] = is_slot_creation_open(ex)
        d["my_slots_count"] = sum(1 for s in slots if s.examination_id == ex.id)
        exams_data.append(d)

    return (
        jsonify(
            {
                "examiner": g.current_user.to_dict(),
                "metrics": {
                    "assigned_examinations_count": len(active_exams),
                    "total_slots": total_slots,
                    "booked_students": total_booked_students,
                    "pending_evaluations": pending_evaluations,
                    "completed_evaluations": completed_evaluations,
                },
                "examinations": exams_data,
            }
        ),
        200,
    )


# ---------------------------------------------------------------------------
# 2. Assigned Examinations
# ---------------------------------------------------------------------------


@examiner_bp.route("/examinations", methods=["GET"])
@role_required("Examiner")
def list_assigned_examinations():
    """
    GET /api/examiner/examinations
    List all active examinations where this examiner is eligible or assigned to create slots.
    Include examination timelines: slot_creation_start_date, slot_creation_end_date,
    slot_booking_start_date, and status.
    """
    examiner_id = g.current_user.id
    exams = (
        Examination.query.filter(Examination.status != "Cancelled")
        .order_by(Examination.id.desc())
        .all()
    )

    results = []
    for ex in exams:
        item = ex.to_dict(include_rubrics=True)
        item["slot_creation_open"] = is_slot_creation_open(ex)
        my_slots = [s for s in ex.slots if s.examiner_id == examiner_id]
        item["my_slots_count"] = len(my_slots)
        item["total_rubric_max_marks"] = sum(r.max_marks for r in ex.rubrics) if ex.rubrics else 0
        results.append(item)

    return jsonify({"examinations": results}), 200


# ---------------------------------------------------------------------------
# 3. Slot Creation
# ---------------------------------------------------------------------------


@examiner_bp.route("/slots", methods=["POST"])
@role_required("Examiner")
def create_slot():
    """
    POST /api/examiner/slots
    Accepts: examination_id, date, start_time, end_time, max_capacity, meeting_link (optional).
    Timeline Validation Rule: Verify that the current date/time falls within the
    examination's slot creation window (slot_creation_start_date to slot_creation_end_date).
    Reject with HTTP 400 if slot creation is closed.
    Sets available_seats = max_capacity and status = 'Available' upon creation.
    """
    data = request.get_json(silent=True) or {}
    examination_id = data.get("examination_id")
    meeting_link = (data.get("meeting_link") or "").strip()

    if not examination_id:
        return (
            jsonify({"error": "Bad Request", "message": "examination_id is required."}),
            400,
        )

    exam = Examination.query.get(examination_id)
    if not exam:
        return (
            jsonify({"error": "Not Found", "message": "Examination not found."}),
            404,
        )

    # Timeline Validation Rule
    if not is_slot_creation_open(exam):
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": (
                        f"Slot creation is closed for '{exam.name}'. "
                        f"Slot creation window: {exam.slot_creation_start_date} to "
                        f"{exam.slot_creation_end_date} (Status: {exam.status})."
                    ),
                }
            ),
            400,
        )

    # Date & Time parsing
    try:
        slot_date = parse_date(data.get("date"))
        start_time = parse_time(data.get("start_time"))
        end_time = parse_time(data.get("end_time"))
        max_capacity = int(data.get("max_capacity", 1))
    except (ValueError, TypeError) as exc:
        return jsonify({"error": "Bad Request", "message": f"Invalid format: {exc}"}), 400

    if not slot_date or not start_time or not end_time:
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": "date, start_time, and end_time are required.",
                }
            ),
            400,
        )

    if start_time >= end_time:
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": "start_time must be strictly before end_time.",
                }
            ),
            400,
        )

    if max_capacity < 1:
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": "max_capacity must be at least 1.",
                }
            ),
            400,
        )

    # Check for schedule overlap for this examiner
    examiner_id = g.current_user.id
    overlapping_slot = ExaminationSlot.query.filter(
        ExaminationSlot.examiner_id == examiner_id,
        ExaminationSlot.date == slot_date,
        ExaminationSlot.status != "Cancelled",
        ExaminationSlot.start_time < end_time,
        ExaminationSlot.end_time > start_time,
    ).first()

    if overlapping_slot:
        return (
            jsonify(
                {
                    "error": "Conflict",
                    "message": (
                        f"You already have an active slot (#{overlapping_slot.id}) scheduled on "
                        f"{slot_date} from {overlapping_slot.start_time.strftime('%H:%M')} to "
                        f"{overlapping_slot.end_time.strftime('%H:%M')}."
                    ),
                }
            ),
            409,
        )

    new_slot = ExaminationSlot(
        examination_id=exam.id,
        examiner_id=examiner_id,
        date=slot_date,
        start_time=start_time,
        end_time=end_time,
        max_capacity=max_capacity,
        available_seats=max_capacity,
        status="Available",
        meeting_link=meeting_link or None,
    )
    db.session.add(new_slot)
    db.session.commit()

    return (
        jsonify(
            {
                "message": "Examination slot created successfully.",
                "slot": new_slot.to_dict(),
            }
        ),
        201,
    )


# ---------------------------------------------------------------------------
# 4. Slot Modification & Deletion
# ---------------------------------------------------------------------------


@examiner_bp.route("/slots", methods=["GET"])
@role_required("Examiner")
def list_my_slots():
    """GET /api/examiner/slots: List all slots created by logged-in examiner."""
    examiner_id = g.current_user.id
    slots = (
        ExaminationSlot.query.filter_by(examiner_id=examiner_id)
        .order_by(ExaminationSlot.date.desc(), ExaminationSlot.start_time.asc())
        .all()
    )
    return jsonify({"slots": [s.to_dict() for s in slots]}), 200


@examiner_bp.route("/slots/<int:slot_id>", methods=["PUT"])
@role_required("Examiner")
def update_slot(slot_id):
    """
    PUT /api/examiner/slots/<id>: Update slot details (date, time, capacity, meeting_link).
    Safety Validation Rule: Slot editing is ONLY permitted if no student has booked the slot yet,
    or before the student booking window opens. If bookings exist, reject with HTTP 400.
    """
    examiner_id = g.current_user.id
    slot = ExaminationSlot.query.get(slot_id)
    if not slot:
        return jsonify({"error": "Not Found", "message": "Slot not found."}), 404

    if slot.examiner_id != examiner_id:
        return (
            jsonify(
                {
                    "error": "Forbidden",
                    "message": "You can only edit slots created by your account.",
                }
            ),
            403,
        )

    # Safety Validation Rule
    if slot.bookings and len(slot.bookings) > 0:
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": (
                        f"Cannot modify slot #{slot.id} because {len(slot.bookings)} "
                        "student(s) have already booked it."
                    ),
                }
            ),
            400,
        )

    data = request.get_json(silent=True) or {}

    try:
        if "date" in data:
            slot.date = parse_date(data["date"])
        if "start_time" in data:
            slot.start_time = parse_time(data["start_time"])
        if "end_time" in data:
            slot.end_time = parse_time(data["end_time"])
        if "max_capacity" in data:
            cap = int(data["max_capacity"])
            if cap < 1:
                return jsonify({"error": "Bad Request", "message": "Capacity must be >= 1"}), 400
            slot.max_capacity = cap
            slot.available_seats = cap
        if "meeting_link" in data:
            slot.meeting_link = (data.get("meeting_link") or "").strip() or None
        if "status" in data:
            slot.status = data["status"].strip()
    except Exception as exc:
        return jsonify({"error": "Bad Request", "message": str(exc)}), 400

    if slot.start_time >= slot.end_time:
        return (
            jsonify({"error": "Bad Request", "message": "start_time must be before end_time."}),
            400,
        )

    db.session.commit()

    return (
        jsonify(
            {
                "message": "Slot updated successfully.",
                "slot": slot.to_dict(),
            }
        ),
        200,
    )


@examiner_bp.route("/slots/<int:slot_id>", methods=["DELETE"])
@role_required("Examiner")
def delete_slot(slot_id):
    """
    DELETE /api/examiner/slots/<id>: Remove an examination slot.
    Safety Validation Rule: Slot deletion is ONLY permitted if no student has booked the slot yet.
    If bookings exist, reject with HTTP 400.
    """
    examiner_id = g.current_user.id
    slot = ExaminationSlot.query.get(slot_id)
    if not slot:
        return jsonify({"error": "Not Found", "message": "Slot not found."}), 404

    if slot.examiner_id != examiner_id:
        return (
            jsonify(
                {
                    "error": "Forbidden",
                    "message": "You can only delete slots created by your account.",
                }
            ),
            403,
        )

    # Safety Validation Rule
    if slot.bookings and len(slot.bookings) > 0:
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": (
                        f"Cannot delete slot #{slot.id} because {len(slot.bookings)} "
                        "student(s) have already booked it."
                    ),
                }
            ),
            400,
        )

    db.session.delete(slot)
    db.session.commit()

    return (
        jsonify({"message": f"Slot #{slot_id} removed successfully."}),
        200,
    )


# ---------------------------------------------------------------------------
# 5. View Booked Students
# ---------------------------------------------------------------------------


@examiner_bp.route("/bookings", methods=["GET"])
@examiner_bp.route("/slots/<int:slot_id>/students", methods=["GET"])
@role_required("Examiner")
def list_booked_students(slot_id=None):
    """
    GET /api/examiner/bookings
    GET /api/examiner/slots/<id>/students
    List all students booked for the examiner's slots with their booking status.
    Include student profile details (Name, Email, Student ID).
    """
    examiner_id = g.current_user.id

    query = Booking.query.join(ExaminationSlot).filter(
        ExaminationSlot.examiner_id == examiner_id
    )

    if slot_id is not None:
        query = query.filter(Booking.slot_id == slot_id)

    # Optional status filter
    status_filter = request.args.get("status")
    if status_filter:
        query = query.filter(Booking.status.ilike(status_filter.strip()))

    bookings = query.order_by(Booking.booking_date.desc()).all()

    results = []
    for b in bookings:
        student = b.student
        slot = b.slot
        exam = slot.examination if slot else None
        evaluation = b.evaluation

        student_name = (
            student.email.split("@")[0].replace(".", " ").title()
            if student and student.email
            else "Student"
        )

        results.append(
            {
                "booking_id": b.id,
                "booking_date": b.booking_date.isoformat() if b.booking_date else None,
                "status": b.status,
                "student_id": b.student_id,
                "student_email": student.email if student else None,
                "student_name": student_name,
                "slot_id": b.slot_id,
                "slot_date": slot.date.isoformat() if slot and slot.date else None,
                "slot_start_time": (
                    slot.start_time.strftime("%H:%M") if slot and slot.start_time else None
                ),
                "slot_end_time": (
                    slot.end_time.strftime("%H:%M") if slot and slot.end_time else None
                ),
                "meeting_link": slot.meeting_link if slot else None,
                "examination_id": exam.id if exam else None,
                "examination_name": exam.name if exam else None,
                "examination_type": exam.type if exam else None,
                "course_code": exam.course.code if exam and exam.course else None,
                "course_name": exam.course.name if exam and exam.course else None,
                "rubrics": [r.to_dict() for r in exam.rubrics] if exam and exam.rubrics else [],
                "has_evaluation": evaluation is not None,
                "evaluation": evaluation.to_dict() if evaluation else None,
            }
        )

    return jsonify({"bookings": results, "total": len(results)}), 200


# ---------------------------------------------------------------------------
# 6. Student Evaluation & Grading
# ---------------------------------------------------------------------------


@examiner_bp.route("/evaluations", methods=["POST"])
@role_required("Examiner")
def evaluate_student():
    """
    POST /api/examiner/evaluations
    Accepts: booking_id, marks_obtained (or marks), remarks.
    Verify that the slot belongs to this examiner.
    Fetch the predefined rubrics for the examination to ensure marks do not exceed max_marks.
    Create/Update the Evaluation record, update the booking status to 'Completed',
    and record the evaluation date.
    """
    data = request.get_json(silent=True) or {}
    booking_id = data.get("booking_id")
    raw_marks = data.get("marks_obtained")
    if raw_marks is None:
        raw_marks = data.get("marks")
    remarks = (data.get("remarks") or "").strip()

    if not booking_id:
        return (
            jsonify({"error": "Bad Request", "message": "booking_id is required."}),
            400,
        )

    booking = Booking.query.get(booking_id)
    if not booking:
        return jsonify({"error": "Not Found", "message": "Booking not found."}), 404

    # Verify slot belongs to this examiner
    examiner_id = g.current_user.id
    if not booking.slot or booking.slot.examiner_id != examiner_id:
        return (
            jsonify(
                {
                    "error": "Forbidden",
                    "message": "You can only evaluate students assigned to your slots.",
                }
            ),
            403,
        )

    # Validate marks
    try:
        marks_obtained = float(raw_marks)
    except (ValueError, TypeError):
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": "marks_obtained must be a valid positive number.",
                }
            ),
            400,
        )

    if marks_obtained < 0:
        return (
            jsonify({"error": "Bad Request", "message": "Marks cannot be negative."}),
            400,
        )

    # Predefined rubrics check
    exam = booking.slot.examination
    if exam and exam.rubrics and len(exam.rubrics) > 0:
        max_total_marks = sum(r.max_marks for r in exam.rubrics)
        if marks_obtained > max_total_marks:
            return (
                jsonify(
                    {
                        "error": "Bad Request",
                        "message": (
                            f"Marks ({marks_obtained}) exceed maximum allowed total marks "
                            f"({max_total_marks}) for examination '{exam.name}' based on defined rubrics."
                        ),
                        "max_allowed_marks": max_total_marks,
                    }
                ),
                400,
            )

    # Create or update evaluation
    evaluation = Evaluation.query.filter_by(booking_id=booking.id).first()
    if evaluation:
        evaluation.total_marks = marks_obtained
        evaluation.remarks = remarks
        evaluation.evaluation_date = utc_now()
    else:
        evaluation = Evaluation(
            booking_id=booking.id,
            examiner_id=examiner_id,
            student_id=booking.student_id,
            total_marks=marks_obtained,
            remarks=remarks,
            evaluation_date=utc_now(),
        )
        db.session.add(evaluation)

    # Mark booking completed
    booking.status = "Completed"
    db.session.commit()

    return (
        jsonify(
            {
                "message": "Student evaluation recorded successfully.",
                "booking_id": booking.id,
                "status": booking.status,
                "evaluation": evaluation.to_dict(),
            }
        ),
        200,
    )


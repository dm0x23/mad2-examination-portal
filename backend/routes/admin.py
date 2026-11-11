import os
from datetime import datetime, date, time
from flask import Blueprint, jsonify, request, send_from_directory
from werkzeug.security import generate_password_hash

try:
    from backend.config import Config
    from backend.database import db
    from backend.models import (
        User,
        ExaminerProfile,
        Course,
        Examination,
        ExaminationRubric,
        ExaminationSlot,
        Booking,
        Evaluation,
    )
    from backend.utils.auth_middleware import role_required
    from backend.tasks.jobs import generate_monthly_admin_report
except ImportError:
    from config import Config
    from database import db
    from models import (
        User,
        ExaminerProfile,
        Course,
        Examination,
        ExaminationRubric,
        ExaminationSlot,
        Booking,
        Evaluation,
    )
    from utils.auth_middleware import role_required
    from tasks.jobs import generate_monthly_admin_report

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


def parse_datetime(dt_val):
    if not dt_val:
        return None
    if isinstance(dt_val, datetime):
        return dt_val
    dt_str = str(dt_val).strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(dt_str)
    except Exception:
        for fmt in (
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
        ):
            try:
                return datetime.strptime(dt_str, fmt)
            except ValueError:
                pass
        raise ValueError(f"Invalid datetime format: {dt_val}")


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


@admin_bp.route("/stats", methods=["GET"])
@role_required("Admin")
def get_system_stats():
    """
    GET /api/admin/stats
    Return total counts for: courses, examinations, examiners,
    registered students, examination slots, and bookings.
    """
    total_courses = Course.query.count()
    total_examinations = Examination.query.count()
    total_examiners = User.query.filter_by(role="Examiner").count()
    total_students = User.query.filter_by(role="Student").count()
    total_slots = ExaminationSlot.query.count()
    total_bookings = Booking.query.count()

    return (
        jsonify(
            {
                "total_courses": total_courses,
                "total_examinations": total_examinations,
                "total_examiners": total_examiners,
                "total_students": total_students,
                "total_slots": total_slots,
                "total_bookings": total_bookings,
            }
        ),
        200,
    )




@admin_bp.route("/courses", methods=["GET"])
@role_required("Admin")
def list_courses():
    """GET /api/admin/courses: List all courses."""
    courses = Course.query.order_by(Course.code.asc()).all()
    return jsonify({"courses": [c.to_dict() for c in courses]}), 200


@admin_bp.route("/courses", methods=["POST"])
@role_required("Admin")
def create_course():
    """POST /api/admin/courses: Create a course (code, name, description)."""
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip().upper()
    name = (data.get("name") or "").strip()
    description = (data.get("description") or "").strip()
    status = (data.get("status") or "Active").strip()

    if not code or not name:
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": "Course code and course name are required.",
                }
            ),
            400,
        )

    if Course.query.filter_by(code=code).first():
        return (
            jsonify(
                {
                    "error": "Conflict",
                    "message": f"Course with code '{code}' already exists.",
                }
            ),
            409,
        )

    course = Course(
        code=code,
        name=name,
        description=description,
        status=status,
    )
    db.session.add(course)
    db.session.commit()

    return (
        jsonify(
            {
                "message": "Course created successfully.",
                "course": course.to_dict(),
            }
        ),
        201,
    )


@admin_bp.route("/courses/<int:course_id>", methods=["PUT"])
@role_required("Admin")
def update_course(course_id):
    """PUT /api/admin/courses/<id>: Update course details."""
    course = Course.query.get(course_id)
    if not course:
        return jsonify({"error": "Not Found", "message": "Course not found."}), 404

    data = request.get_json(silent=True) or {}
    if "code" in data:
        new_code = (data.get("code") or "").strip().upper()
        if not new_code:
            return (
                jsonify({"error": "Bad Request", "message": "Course code cannot be empty."}),
                400,
            )
        if new_code != course.code:
            existing = Course.query.filter_by(code=new_code).first()
            if existing:
                return (
                    jsonify(
                        {
                            "error": "Conflict",
                            "message": f"Course code '{new_code}' is already in use.",
                        }
                    ),
                    409,
                )
            course.code = new_code

    if "name" in data:
        new_name = (data.get("name") or "").strip()
        if not new_name:
            return (
                jsonify({"error": "Bad Request", "message": "Course name cannot be empty."}),
                400,
            )
        course.name = new_name

    if "description" in data:
        course.description = data.get("description", "").strip()

    if "status" in data:
        course.status = data.get("status", "Active").strip()

    db.session.commit()

    return (
        jsonify(
            {
                "message": "Course updated successfully.",
                "course": course.to_dict(),
            }
        ),
        200,
    )


@admin_bp.route("/courses/<int:course_id>", methods=["DELETE"])
@role_required("Admin")
def delete_course(course_id):
    """
    DELETE /api/admin/courses/<id>: Delete course
    (ensure safe handling if examinations exist).
    """
    course = Course.query.get(course_id)
    if not course:
        return jsonify({"error": "Not Found", "message": "Course not found."}), 404

    if course.examinations and len(course.examinations) > 0:
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": (
                        f"Cannot delete course '{course.code}' because it has "
                        f"{len(course.examinations)} associated examination(s). "
                        "Please remove or reassign examinations first."
                    ),
                }
            ),
            400,
        )

    db.session.delete(course)
    db.session.commit()

    return (
        jsonify(
            {
                "message": f"Course '{course.code}' deleted successfully.",
            }
        ),
        200,
    )


# ---------------------------------------------------------------------------
# 3. Examination & Rubric Management
# ---------------------------------------------------------------------------


@admin_bp.route("/examinations", methods=["GET"])
@role_required("Admin")
def list_examinations():
    """GET /api/admin/examinations: List all examinations with associated course info."""
    exams = Examination.query.order_by(Examination.id.desc()).all()
    return (
        jsonify({"examinations": [e.to_dict(include_rubrics=True) for e in exams]}),
        200,
    )


@admin_bp.route("/examinations", methods=["POST"])
@role_required("Admin")
def create_examination():
    """
    POST /api/admin/examinations: Create an examination
    (course_id, name, type, timelines: slot_creation_start_date,
    slot_creation_end_date, slot_booking_start_date, slot_booking_end_date, status).
    """
    data = request.get_json(silent=True) or {}
    course_id = data.get("course_id")
    name = (data.get("name") or "").strip()
    exam_type = (data.get("type") or "Viva").strip()
    status = (data.get("status") or "Scheduled").strip()

    if not course_id or not name:
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": "Course ID and Examination name are required.",
                }
            ),
            400,
        )

    course = Course.query.get(course_id)
    if not course:
        return jsonify({"error": "Not Found", "message": "Associated course not found."}), 404

    try:
        sc_start = parse_datetime(data.get("slot_creation_start_date"))
        sc_end = parse_datetime(data.get("slot_creation_end_date"))
        sb_start = parse_datetime(data.get("slot_booking_start_date"))
        sb_end = parse_datetime(data.get("slot_booking_end_date"))
    except ValueError as val_err:
        return jsonify({"error": "Bad Request", "message": str(val_err)}), 400

    if not all([sc_start, sc_end, sb_start, sb_end]):
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": "All four timeline dates are required.",
                }
            ),
            400,
        )

    if sc_start > sc_end:
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": "Slot creation start date must be before or equal to end date.",
                }
            ),
            400,
        )

    if sb_start > sb_end:
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": "Slot booking start date must be before or equal to end date.",
                }
            ),
            400,
        )

    examination = Examination(
        course_id=course.id,
        name=name,
        type=exam_type,
        slot_creation_start_date=sc_start,
        slot_creation_end_date=sc_end,
        slot_booking_start_date=sb_start,
        slot_booking_end_date=sb_end,
        status=status,
    )
    db.session.add(examination)
    db.session.commit()

    return (
        jsonify(
            {
                "message": "Examination created successfully.",
                "examination": examination.to_dict(),
            }
        ),
        201,
    )


@admin_bp.route("/examinations/<int:exam_id>", methods=["PUT"])
@role_required("Admin")
def update_examination(exam_id):
    """
    PUT /api/admin/examinations/<id>: Update examination details or change status
    (e.g., manually opening/closing slot creation or student booking).
    """
    exam = Examination.query.get(exam_id)
    if not exam:
        return (
            jsonify({"error": "Not Found", "message": "Examination not found."}),
            404,
        )

    data = request.get_json(silent=True) or {}

    if "name" in data:
        val = (data.get("name") or "").strip()
        if not val:
            return jsonify({"error": "Bad Request", "message": "Name cannot be empty."}), 400
        exam.name = val

    if "type" in data:
        exam.type = (data.get("type") or "Viva").strip()

    if "status" in data:
        exam.status = (data.get("status") or "Scheduled").strip()

    if "course_id" in data:
        course = Course.query.get(data.get("course_id"))
        if not course:
            return jsonify({"error": "Not Found", "message": "Target course not found."}), 404
        exam.course_id = course.id

    try:
        if "slot_creation_start_date" in data:
            exam.slot_creation_start_date = parse_datetime(data["slot_creation_start_date"])
        if "slot_creation_end_date" in data:
            exam.slot_creation_end_date = parse_datetime(data["slot_creation_end_date"])
        if "slot_booking_start_date" in data:
            exam.slot_booking_start_date = parse_datetime(data["slot_booking_start_date"])
        if "slot_booking_end_date" in data:
            exam.slot_booking_end_date = parse_datetime(data["slot_booking_end_date"])
    except ValueError as val_err:
        return jsonify({"error": "Bad Request", "message": str(val_err)}), 400

    db.session.commit()

    return (
        jsonify(
            {
                "message": "Examination updated successfully.",
                "examination": exam.to_dict(),
            }
        ),
        200,
    )


@admin_bp.route("/examinations/<int:exam_id>", methods=["DELETE"])
@role_required("Admin")
def delete_examination(exam_id):
    """DELETE /api/admin/examinations/<id>: Remove examination."""
    exam = Examination.query.get(exam_id)
    if not exam:
        return (
            jsonify({"error": "Not Found", "message": "Examination not found."}),
            404,
        )

    active_bookings_count = (
        Booking.query.join(ExaminationSlot)
        .filter(ExaminationSlot.examination_id == exam.id)
        .count()
    )
    if active_bookings_count > 0:
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": (
                        f"Cannot delete examination '{exam.name}' because it has "
                        f"{active_bookings_count} student booking(s). Please cancel "
                        "or reschedule student bookings before deleting."
                    ),
                }
            ),
            400,
        )

    db.session.delete(exam)
    db.session.commit()

    return (
        jsonify({"message": f"Examination '{exam.name}' removed successfully."}),
        200,
    )


@admin_bp.route("/examinations/<int:exam_id>/rubrics", methods=["GET"])
@role_required("Admin")
def get_examination_rubrics(exam_id):
    """GET /api/admin/examinations/<id>/rubrics: Fetch rubrics for an exam."""
    exam = Examination.query.get(exam_id)
    if not exam:
        return (
            jsonify({"error": "Not Found", "message": "Examination not found."}),
            404,
        )

    return jsonify({"rubrics": [r.to_dict() for r in exam.rubrics]}), 200


@admin_bp.route("/examinations/<int:exam_id>/rubrics", methods=["POST"])
@role_required("Admin")
def add_examination_rubric(exam_id):
    """
    POST /api/admin/examinations/<id>/rubrics: Add evaluation rubrics
    (criterion_name, max_marks, weightage).
    """
    exam = Examination.query.get(exam_id)
    if not exam:
        return (
            jsonify({"error": "Not Found", "message": "Examination not found."}),
            404,
        )

    data = request.get_json(silent=True) or {}
    criterion_name = (data.get("criterion_name") or "").strip()
    try:
        max_marks = float(data.get("max_marks", 0))
        weightage = float(data.get("weightage", 0))
    except (ValueError, TypeError):
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": "Max marks and weightage must be valid numbers.",
                }
            ),
            400,
        )

    if not criterion_name:
        return (
            jsonify({"error": "Bad Request", "message": "Criterion name is required."}),
            400,
        )
    if max_marks <= 0:
        return (
            jsonify({"error": "Bad Request", "message": "Max marks must be greater than 0."}),
            400,
        )

    rubric = ExaminationRubric(
        examination_id=exam.id,
        criterion_name=criterion_name,
        max_marks=max_marks,
        weightage=weightage,
    )
    db.session.add(rubric)
    db.session.commit()

    return (
        jsonify(
            {
                "message": "Evaluation rubric added successfully.",
                "rubric": rubric.to_dict(),
            }
        ),
        201,
    )


@admin_bp.route("/rubrics/<int:rubric_id>", methods=["DELETE"])
@admin_bp.route("/examinations/<int:exam_id>/rubrics/<int:rubric_id>", methods=["DELETE"])
@role_required("Admin")
def delete_examination_rubric(rubric_id, exam_id=None):
    """Delete an examination rubric."""
    rubric = ExaminationRubric.query.get(rubric_id)
    if not rubric:
        return jsonify({"error": "Not Found", "message": "Rubric not found."}), 404

    db.session.delete(rubric)
    db.session.commit()
    return jsonify({"message": "Rubric deleted successfully."}), 200


# ---------------------------------------------------------------------------
# 4. Examiner Provisioning & Management
# ---------------------------------------------------------------------------


@admin_bp.route("/examiners", methods=["GET"])
@role_required("Admin")
def list_examiners():
    """
    GET /api/admin/examiners: List all examiners with profile details
    (name, department, contact, status).
    """
    examiners = (
        User.query.filter_by(role="Examiner")
        .order_by(User.id.desc())
        .all()
    )

    result = []
    for u in examiners:
        profile = u.examiner_profile
        result.append(
            {
                "id": u.id,
                "email": u.email,
                "active": u.active,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "name": profile.name if profile else "N/A",
                "department": profile.department if profile else "N/A",
                "contact": profile.contact if profile else "N/A",
                "status": profile.status if profile else ("Active" if u.active else "Deactivated"),
                "profile": profile.to_dict() if profile else None,
            }
        )

    return jsonify({"examiners": result}), 200


@admin_bp.route("/examiners", methods=["POST"])
@role_required("Admin")
def provision_examiner():
    """
    POST /api/admin/examiners: Create a new Examiner.
    Programmatically create a User record (role 'Examiner', hashed temporary password)
    and a corresponding ExaminerProfile.
    """
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    name = (data.get("name") or "").strip()
    department = (data.get("department") or "").strip()
    contact = (data.get("contact") or "").strip()
    temporary_password = data.get("temporary_password") or "Examiner@123"

    if not email or not name or not department:
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": "Email, name, and department are required to provision an examiner.",
                }
            ),
            400,
        )

    if User.query.filter_by(email=email).first():
        return (
            jsonify(
                {
                    "error": "Conflict",
                    "message": f"A user with email '{email}' already exists.",
                }
            ),
            409,
        )

    new_examiner_user = User(
        email=email,
        password_hash=generate_password_hash(temporary_password),
        role="Examiner",
        active=True,
    )
    db.session.add(new_examiner_user)
    db.session.flush()

    examiner_profile = ExaminerProfile(
        user_id=new_examiner_user.id,
        name=name,
        department=department,
        contact=contact,
        status="Active",
    )
    db.session.add(examiner_profile)
    db.session.commit()

    return (
        jsonify(
            {
                "message": "Examiner provisioned successfully.",
                "examiner": new_examiner_user.to_dict(),
                "temporary_password": temporary_password,
            }
        ),
        201,
    )


@admin_bp.route("/examiners/<int:examiner_id>/status", methods=["PUT"])
@role_required("Admin")
def update_examiner_status(examiner_id):
    """
    PUT /api/admin/examiners/<id>/status: Approve, activate, or deactivate an examiner.
    Supports either User.id or ExaminerProfile.id.
    """
    user = User.query.filter_by(id=examiner_id, role="Examiner").first()
    if not user:
        profile = ExaminerProfile.query.get(examiner_id)
        if profile:
            user = profile.user

    if not user:
        return (
            jsonify({"error": "Not Found", "message": "Examiner account not found."}),
            404,
        )

    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    new_active = data.get("active")

    if new_status:
        clean_status = str(new_status).strip()
        if user.examiner_profile:
            user.examiner_profile.status = clean_status
        if clean_status.lower() in ("deactivated", "inactive", "suspended"):
            user.active = False
        elif clean_status.lower() in ("active", "approved"):
            user.active = True

    if new_active is not None:
        user.active = bool(new_active)
        if not user.active and user.examiner_profile:
            user.examiner_profile.status = "Deactivated"
        elif user.active and user.examiner_profile and user.examiner_profile.status == "Deactivated":
            user.examiner_profile.status = "Active"

    db.session.commit()

    return (
        jsonify(
            {
                "message": "Examiner status updated successfully.",
                "examiner": user.to_dict(),
            }
        ),
        200,
    )


# ---------------------------------------------------------------------------
# 5. Slot Supervision & Exceptional Reassignments
# ---------------------------------------------------------------------------


@admin_bp.route("/slots", methods=["GET"])
@role_required("Admin")
def list_slots():
    """
    GET /api/admin/slots: View all examination slots created across the platform.
    Optional query params: examination_id, examiner_id, date.
    """
    query = ExaminationSlot.query

    exam_id = request.args.get("examination_id")
    if exam_id:
        query = query.filter_by(examination_id=exam_id)

    examiner_id = request.args.get("examiner_id")
    if examiner_id:
        query = query.filter_by(examiner_id=examiner_id)

    date_filter = request.args.get("date")
    if date_filter:
        try:
            d_val = parse_date(date_filter)
            query = query.filter_by(date=d_val)
        except Exception:
            pass

    slots = query.order_by(ExaminationSlot.date.desc(), ExaminationSlot.start_time.asc()).all()
    return jsonify({"slots": [s.to_dict() for s in slots]}), 200


@admin_bp.route("/slots/<int:slot_id>/reassign-examiner", methods=["PUT"])
@role_required("Admin")
def reassign_examiner(slot_id):
    """
    PUT /api/admin/slots/<id>/reassign-examiner: Reassign a slot to a different examiner
    in exceptional situations.
    """
    slot = ExaminationSlot.query.get(slot_id)
    if not slot:
        return jsonify({"error": "Not Found", "message": "Examination slot not found."}), 404

    data = request.get_json(silent=True) or {}
    new_examiner_id = data.get("examiner_id")
    if not new_examiner_id:
        return (
            jsonify({"error": "Bad Request", "message": "Target examiner_id is required."}),
            400,
        )

    new_examiner = User.query.filter_by(id=new_examiner_id, role="Examiner").first()
    if not new_examiner:
        return (
            jsonify(
                {
                    "error": "Not Found",
                    "message": f"Target Examiner with user ID {new_examiner_id} not found.",
                }
            ),
            404,
        )

    if not new_examiner.active:
        return (
            jsonify(
                {
                    "error": "Forbidden",
                    "message": "Cannot reassign to an inactive or deactivated examiner.",
                }
            ),
            403,
        )

    old_examiner_id = slot.examiner_id
    slot.examiner_id = new_examiner.id
    db.session.commit()

    return (
        jsonify(
            {
                "message": (
                    f"Slot #{slot.id} successfully reassigned from Examiner #{old_examiner_id} "
                    f"to Examiner #{new_examiner.id} ({new_examiner.email})."
                ),
                "slot": slot.to_dict(),
            }
        ),
        200,
    )


@admin_bp.route("/bookings/<int:booking_id>/reschedule", methods=["PUT"])
@role_required("Admin")
def reschedule_booking(booking_id):
    """
    PUT /api/admin/bookings/<id>/reschedule: Reschedule a student's booking
    to another available slot.
    """
    booking = Booking.query.get(booking_id)
    if not booking:
        return jsonify({"error": "Not Found", "message": "Booking not found."}), 404

    data = request.get_json(silent=True) or {}
    new_slot_id = data.get("new_slot_id")
    if not new_slot_id:
        return (
            jsonify({"error": "Bad Request", "message": "new_slot_id is required."}),
            400,
        )

    if booking.slot_id == int(new_slot_id):
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": "Student is already booked in this exact slot.",
                }
            ),
            400,
        )

    new_slot = ExaminationSlot.query.get(new_slot_id)
    if not new_slot:
        return (
            jsonify({"error": "Not Found", "message": "Target slot not found."}),
            404,
        )

    old_slot = booking.slot

    # Validate slot compatibility
    if old_slot and new_slot.examination_id != old_slot.examination_id:
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": "Cannot reschedule booking to a slot belonging to a different examination.",
                }
            ),
            400,
        )

    if new_slot.available_seats <= 0:
        return (
            jsonify(
                {
                    "error": "Conflict",
                    "message": "Target examination slot has no available seats remaining.",
                }
            ),
            409,
        )

    if new_slot.status.lower() in ("cancelled", "completed"):
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": f"Cannot reschedule to a slot with status '{new_slot.status}'.",
                }
            ),
            400,
        )

    # Adjust seats on old slot if present
    if old_slot:
        old_slot.available_seats = min(old_slot.max_capacity, old_slot.available_seats + 1)
        if old_slot.status == "Full" and old_slot.available_seats > 0:
            old_slot.status = "Available"

    # Adjust seats on new slot
    new_slot.available_seats = max(0, new_slot.available_seats - 1)
    if new_slot.available_seats == 0:
        new_slot.status = "Full"

    # Reassign booking
    booking.slot_id = new_slot.id
    booking.status = "Booked"
    db.session.commit()

    return (
        jsonify(
            {
                "message": (
                    f"Booking #{booking.id} successfully rescheduled to slot #{new_slot.id} "
                    f"({new_slot.date} {new_slot.start_time.strftime('%H:%M')})."
                ),
                "booking": booking.to_dict(),
            }
        ),
        200,
    )


# ---------------------------------------------------------------------------
# 6. Search & Records
# ---------------------------------------------------------------------------


@admin_bp.route("/search", methods=["GET"])
@role_required("Admin")
def global_search():
    """
    GET /api/admin/search?query=...&type=...: Global search for students,
    examiners, examinations, or bookings by name, code, or ID.
    """
    search_query = (request.args.get("query") or "").strip()
    search_type = (request.args.get("type") or "all").strip().lower()

    if not search_query:
        return (
            jsonify(
                {
                    "query": "",
                    "type": search_type,
                    "students": [],
                    "examiners": [],
                    "examinations": [],
                    "courses": [],
                    "bookings": [],
                }
            ),
            200,
        )

    pattern = f"%{search_query}%"
    results = {
        "query": search_query,
        "type": search_type,
        "students": [],
        "examiners": [],
        "examinations": [],
        "courses": [],
        "bookings": [],
    }

    # Students search
    if search_type in ("all", "students", "student"):
        students = (
            User.query.filter(
                User.role == "Student",
                (
                    User.email.ilike(pattern)
                    | User.id.cast(db.String).ilike(pattern)
                ),
            )
            .limit(25)
            .all()
        )
        results["students"] = [s.to_dict() for s in students]

    # Examiners search
    if search_type in ("all", "examiners", "examiner"):
        examiners = (
            User.query.outerjoin(ExaminerProfile)
            .filter(
                User.role == "Examiner",
                (
                    User.email.ilike(pattern)
                    | ExaminerProfile.name.ilike(pattern)
                    | ExaminerProfile.department.ilike(pattern)
                    | User.id.cast(db.String).ilike(pattern)
                ),
            )
            .limit(25)
            .all()
        )
        results["examiners"] = [
            {
                "id": u.id,
                "email": u.email,
                "active": u.active,
                "name": u.examiner_profile.name if u.examiner_profile else "N/A",
                "department": u.examiner_profile.department if u.examiner_profile else "N/A",
                "contact": u.examiner_profile.contact if u.examiner_profile else "N/A",
                "status": u.examiner_profile.status if u.examiner_profile else ("Active" if u.active else "Deactivated"),
            }
            for u in examiners
        ]

    # Courses search
    if search_type in ("all", "courses", "course"):
        courses = (
            Course.query.filter(
                Course.code.ilike(pattern)
                | Course.name.ilike(pattern)
                | Course.description.ilike(pattern)
            )
            .limit(25)
            .all()
        )
        results["courses"] = [c.to_dict() for c in courses]

    # Examinations search
    if search_type in ("all", "examinations", "examination", "exams"):
        exams = (
            Examination.query.join(Course)
            .filter(
                Examination.name.ilike(pattern)
                | Examination.type.ilike(pattern)
                | Course.code.ilike(pattern)
                | Course.name.ilike(pattern)
            )
            .limit(25)
            .all()
        )
        results["examinations"] = [e.to_dict() for e in exams]

    # Bookings search
    if search_type in ("all", "bookings", "booking"):
        bookings = (
            Booking.query.join(User)
            .filter(
                User.email.ilike(pattern)
                | Booking.id.cast(db.String).ilike(pattern)
                | Booking.status.ilike(pattern)
            )
            .limit(25)
            .all()
        )
        results["bookings"] = [b.to_dict() for b in bookings]

    return jsonify(results), 200


@admin_bp.route("/history", methods=["GET"])
@admin_bp.route("/records/history", methods=["GET"])
@role_required("Admin")
def get_records_history():
    """
    GET /api/admin/history
    GET /api/admin/records/history
    Admin can query and filter the global history of all examinations, bookings,
    evaluations, and student records across all courses and examiners.
    Supports query parameters: status, course_id, examination_id, examiner_id, student_id, query/search.
    """
    query = Booking.query.join(ExaminationSlot).join(Examination)

    status_filter = request.args.get("status")
    if status_filter and status_filter.lower() != "all":
        query = query.filter(Booking.status.ilike(status_filter.strip()))

    course_id = request.args.get("course_id")
    if course_id:
        query = query.filter(Examination.course_id == int(course_id))

    exam_id = request.args.get("examination_id")
    if exam_id:
        query = query.filter(Examination.id == int(exam_id))

    examiner_id = request.args.get("examiner_id")
    if examiner_id:
        query = query.filter(ExaminationSlot.examiner_id == int(examiner_id))

    student_id = request.args.get("student_id")
    if student_id:
        query = query.filter(Booking.student_id == int(student_id))

    search_term = (request.args.get("query") or request.args.get("search") or "").strip()
    if search_term:
        pattern = f"%{search_term}%"
        query = query.join(User, Booking.student_id == User.id).filter(
            User.email.ilike(pattern)
            | Examination.name.ilike(pattern)
            | Booking.status.ilike(pattern)
            | Booking.id.cast(db.String).ilike(pattern)
        )

    bookings = query.order_by(Booking.booking_date.desc()).all()
    exams = Examination.query.order_by(Examination.id.desc()).all()

    formatted_bookings = [b.to_dict() for b in bookings]

    total_b = len(formatted_bookings)
    completed_b = sum(1 for b in formatted_bookings if b["status"] == "Completed")
    cancelled_b = sum(1 for b in formatted_bookings if b["status"] == "Cancelled")
    active_b = sum(1 for b in formatted_bookings if b["status"] == "Booked")
    total_evals = sum(1 for b in formatted_bookings if b.get("has_evaluation"))

    return (
        jsonify(
            {
                "summary": {
                    "total_bookings": total_b,
                    "completed_bookings": completed_b,
                    "cancelled_bookings": cancelled_b,
                    "active_bookings": active_b,
                    "total_evaluations": total_evals,
                    "total_examinations": len(exams),
                },
                "examinations": [e.to_dict(include_rubrics=True) for e in exams],
                "bookings": formatted_bookings,
                "total_examinations": len(exams),
                "total_bookings": total_b,
            }
        ),
        200,
    )




@admin_bp.route("/reports", methods=["GET"])
@role_required("Admin")
def list_monthly_reports():

    os.makedirs(Config.REPORTS_FOLDER, exist_ok=True)
    report_files = []

    try:
        for fname in os.listdir(Config.REPORTS_FOLDER):
            if fname.endswith(".html"):
                full_path = os.path.join(Config.REPORTS_FOLDER, fname)
                stat = os.stat(full_path)
                report_files.append(
                    {
                        "filename": fname,
                        "file_size": stat.st_size,
                        "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "view_url": f"/api/admin/reports/{fname}",
                    }
                )
    except Exception as exc:
        return jsonify({"error": "Failed to read reports directory", "message": str(exc)}), 500

    report_files.sort(key=lambda x: x["created_at"], reverse=True)
    return jsonify({"reports": report_files, "total": len(report_files)}), 200


@admin_bp.route("/reports/generate", methods=["POST"])
@role_required("Admin")
def trigger_monthly_report():

    data = request.get_json(silent=True) or {}
    year = data.get("year")
    month = data.get("month")

    try:
        result = generate_monthly_admin_report(year=year, month=month)
        return (
            jsonify(
                {
                    "message": "Monthly report generated successfully.",
                    "report": result,
                }
            ),
            201,
        )
    except Exception as exc:
        return (
            jsonify(
                {
                    "error": "Report Generation Failed",
                    "message": str(exc),
                }
            ),
            500,
        )


@admin_bp.route("/reports/<filename>", methods=["GET"])
@role_required("Admin")
def view_monthly_report(filename: str):

    if ".." in filename or "/" in filename or "\\" in filename:
        return jsonify({"error": "Forbidden", "message": "Invalid file request."}), 400

    if not filename.endswith(".html"):
        return jsonify({"error": "Bad Request", "message": "Only HTML report files can be viewed."}), 400

    file_path = os.path.join(Config.REPORTS_FOLDER, filename)
    if not os.path.isfile(file_path):
        return jsonify({"error": "Not Found", "message": "Report file not found."}), 404

    return send_from_directory(
        Config.REPORTS_FOLDER,
        filename,
        mimetype="text/html",
    )


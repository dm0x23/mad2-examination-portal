import json
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash

try:
    from backend.database import db
except ImportError:
    from database import db


def utc_now():
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)

    examiner_profile = db.relationship(
        "ExaminerProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    examiner_slots = db.relationship(
        "ExaminationSlot",
        back_populates="examiner",
        foreign_keys="ExaminationSlot.examiner_id",
        cascade="all, delete-orphan",
    )
    student_bookings = db.relationship(
        "Booking",
        back_populates="student",
        foreign_keys="Booking.student_id",
        cascade="all, delete-orphan",
    )
    evaluations_given = db.relationship(
        "Evaluation",
        back_populates="examiner",
        foreign_keys="Evaluation.examiner_id",
    )
    evaluations_received = db.relationship(
        "Evaluation",
        back_populates="student",
        foreign_keys="Evaluation.student_id",
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        data = {
            "id": self.id,
            "email": self.email,
            "role": self.role,
            "active": self.active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if self.role == "Examiner" and self.examiner_profile:
            data["examiner_profile"] = self.examiner_profile.to_dict()
        return data

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role})>"


class ExaminerProfile(db.Model):
    __tablename__ = "examiner_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    name = db.Column(db.String(150), nullable=False)
    department = db.Column(db.String(150), nullable=False)
    contact = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(50), default="Pending", nullable=False)

    user = db.relationship("User", back_populates="examiner_profile")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "department": self.department,
            "contact": self.contact,
            "status": self.status,
        }

    def __repr__(self) -> str:
        return f"<ExaminerProfile {self.name} (user_id={self.user_id})>"


class Course(db.Model):
    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default="Active", nullable=False)

    examinations = db.relationship(
        "Examination",
        back_populates="course",
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "examinations_count": len(self.examinations) if self.examinations else 0,
        }

    def __repr__(self) -> str:
        return f"<Course {self.code}: {self.name}>"


class Examination(db.Model):
    __tablename__ = "examinations"

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(
        db.Integer,
        db.ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(50), nullable=False)  
    slot_creation_start_date = db.Column(db.DateTime, nullable=False)
    slot_creation_end_date = db.Column(db.DateTime, nullable=False)
    slot_booking_start_date = db.Column(db.DateTime, nullable=False)
    slot_booking_end_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(50), default="Scheduled", nullable=False)

    course = db.relationship("Course", back_populates="examinations")
    rubrics = db.relationship(
        "ExaminationRubric",
        back_populates="examination",
        cascade="all, delete-orphan",
    )
    slots = db.relationship(
        "ExaminationSlot",
        back_populates="examination",
        cascade="all, delete-orphan",
    )

    def to_dict(self, include_rubrics: bool = True) -> dict:
        data = {
            "id": self.id,
            "course_id": self.course_id,
            "course_code": self.course.code if self.course else None,
            "course_name": self.course.name if self.course else None,
            "name": self.name,
            "type": self.type,
            "slot_creation_start_date": (
                self.slot_creation_start_date.isoformat()
                if self.slot_creation_start_date
                else None
            ),
            "slot_creation_end_date": (
                self.slot_creation_end_date.isoformat()
                if self.slot_creation_end_date
                else None
            ),
            "slot_booking_start_date": (
                self.slot_booking_start_date.isoformat()
                if self.slot_booking_start_date
                else None
            ),
            "slot_booking_end_date": (
                self.slot_booking_end_date.isoformat()
                if self.slot_booking_end_date
                else None
            ),
            "status": self.status,
            "slots_count": len(self.slots) if self.slots else 0,
            "rubrics_count": len(self.rubrics) if self.rubrics else 0,
        }
        if include_rubrics and self.rubrics:
            data["rubrics"] = [r.to_dict() for r in self.rubrics]
        else:
            data["rubrics"] = []
        return data

    def __repr__(self) -> str:
        return f"<Examination {self.name} ({self.type})>"


class ExaminationRubric(db.Model):
    __tablename__ = "examination_rubrics"

    id = db.Column(db.Integer, primary_key=True)
    examination_id = db.Column(
        db.Integer,
        db.ForeignKey("examinations.id", ondelete="CASCADE"),
        nullable=False,
    )
    criterion_name = db.Column(db.String(150), nullable=False)
    max_marks = db.Column(db.Float, nullable=False)
    weightage = db.Column(db.Float, nullable=False)

    examination = db.relationship("Examination", back_populates="rubrics")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "examination_id": self.examination_id,
            "criterion_name": self.criterion_name,
            "max_marks": self.max_marks,
            "weightage": self.weightage,
        }

    def __repr__(self) -> str:
        return f"<ExaminationRubric {self.criterion_name} (max={self.max_marks})>"


class ExaminationSlot(db.Model):
    __tablename__ = "examination_slots"

    id = db.Column(db.Integer, primary_key=True)
    examination_id = db.Column(
        db.Integer,
        db.ForeignKey("examinations.id", ondelete="CASCADE"),
        nullable=False,
    )
    examiner_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    max_capacity = db.Column(db.Integer, default=1, nullable=False)
    available_seats = db.Column(db.Integer, default=1, nullable=False)
    status = db.Column(db.String(50), default="Available", nullable=False)
    meeting_link = db.Column(db.String(500), nullable=True)

    examination = db.relationship("Examination", back_populates="slots")
    examiner = db.relationship(
        "User",
        back_populates="examiner_slots",
        foreign_keys=[examiner_id],
    )
    bookings = db.relationship(
        "Booking",
        back_populates="slot",
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> dict:
        examiner_profile = self.examiner.examiner_profile if self.examiner else None
        return {
            "id": self.id,
            "examination_id": self.examination_id,
            "examination_name": self.examination.name if self.examination else None,
            "examination_type": self.examination.type if self.examination else None,
            "course_code": (
                self.examination.course.code
                if self.examination and self.examination.course
                else None
            ),
            "course_name": (
                self.examination.course.name
                if self.examination and self.examination.course
                else None
            ),
            "examiner_id": self.examiner_id,
            "examiner_email": self.examiner.email if self.examiner else None,
            "examiner_name": (
                examiner_profile.name if examiner_profile else (self.examiner.email if self.examiner else None)
            ),
            "examiner_department": (
                examiner_profile.department if examiner_profile else None
            ),
            "date": self.date.isoformat() if self.date else None,
            "start_time": (
                self.start_time.strftime("%H:%M")
                if self.start_time
                else None
            ),
            "end_time": (
                self.end_time.strftime("%H:%M")
                if self.end_time
                else None
            ),
            "max_capacity": self.max_capacity,
            "available_seats": self.available_seats,
            "status": self.status,
            "meeting_link": self.meeting_link,
            "bookings_count": len(self.bookings) if self.bookings else 0,
        }

    def __repr__(self) -> str:
        return f"<ExaminationSlot id={self.id} date={self.date} {self.start_time}-{self.end_time}>"


class Booking(db.Model):
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    slot_id = db.Column(
        db.Integer,
        db.ForeignKey("examination_slots.id", ondelete="CASCADE"),
        nullable=False,
    )
    booking_date = db.Column(db.DateTime, default=utc_now, nullable=False)
    status = db.Column(
        db.String(50), default="Booked", nullable=False
    )  

    student = db.relationship(
        "User",
        back_populates="student_bookings",
        foreign_keys=[student_id],
    )
    slot = db.relationship("ExaminationSlot", back_populates="bookings")
    evaluation = db.relationship(
        "Evaluation",
        back_populates="booking",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "student_id": self.student_id,
            "student_email": self.student.email if self.student else None,
            "slot_id": self.slot_id,
            "booking_date": (
                self.booking_date.isoformat() if self.booking_date else None
            ),
            "status": self.status,
            "slot": self.slot.to_dict() if self.slot else None,
            "has_evaluation": self.evaluation is not None,
            "evaluation": self.evaluation.to_dict() if self.evaluation else None,
        }

    def __repr__(self) -> str:
        return f"<Booking id={self.id} student={self.student_id} slot={self.slot_id} ({self.status})>"


class Evaluation(db.Model):
    __tablename__ = "evaluations"

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(
        db.Integer,
        db.ForeignKey("bookings.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    examiner_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    student_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    total_marks = db.Column(db.Float, nullable=False)
    remarks = db.Column(db.Text, nullable=True)
    rubric_breakdown = db.Column(db.Text, nullable=True)
    evaluation_date = db.Column(db.DateTime, default=utc_now, nullable=False)

    booking = db.relationship("Booking", back_populates="evaluation")
    examiner = db.relationship(
        "User",
        back_populates="evaluations_given",
        foreign_keys=[examiner_id],
    )
    student = db.relationship(
        "User",
        back_populates="evaluations_received",
        foreign_keys=[student_id],
    )

    def to_dict(self) -> dict:
        parsed_breakdown = None
        if self.rubric_breakdown:
            try:
                parsed_breakdown = json.loads(self.rubric_breakdown)
            except Exception:
                parsed_breakdown = self.rubric_breakdown

        return {
            "id": self.id,
            "booking_id": self.booking_id,
            "examiner_id": self.examiner_id,
            "examiner_email": self.examiner.email if self.examiner else None,
            "examiner_name": (
                self.examiner.examiner_profile.name
                if self.examiner and self.examiner.examiner_profile
                else (self.examiner.email if self.examiner else None)
            ),
            "student_id": self.student_id,
            "student_email": self.student.email if self.student else None,
            "total_marks": self.total_marks,
            "remarks": self.remarks,
            "rubric_breakdown": parsed_breakdown,
            "evaluation_date": (
                self.evaluation_date.isoformat() if self.evaluation_date else None
            ),
        }

    def __repr__(self) -> str:
        return f"<Evaluation id={self.id} booking={self.booking_id} marks={self.total_marks}>"


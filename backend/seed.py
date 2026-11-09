import os
from werkzeug.security import generate_password_hash

try:
    from backend.database import db
    from backend.models import User, Course, ExaminerProfile
except ImportError:
    from database import db
    from models import User, Course, ExaminerProfile

ADMIN_EMAIL = "admin@portal.com"
ADMIN_DEFAULT_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Admin@123")


def seed_database(app=None):
    if app is not None:
        with app.app_context():
            _create_tables_and_seed()
    else:
        _create_tables_and_seed()

def _create_tables_and_seed():
    db.create_all()

    existing_admin = User.query.filter(
        (User.email == ADMIN_EMAIL) | (User.role == "Admin")
    ).first()

    if not existing_admin:
        admin_user = User(
            email=ADMIN_EMAIL,
            password_hash=generate_password_hash(ADMIN_DEFAULT_PASSWORD),
            role="Admin",
            active=True,
        )
        db.session.add(admin_user)
        db.session.commit()
        print(f"[SEED] Created initial Admin user: {ADMIN_EMAIL}")
    else:
        print(f"[SEED] Admin user already exists ({existing_admin.email}). Skipping.")

    # Seed initial demo student if not present
    demo_student = User.query.filter_by(email="student@portal.com").first()
    if not demo_student:
        demo_student = User(
            email="student@portal.com",
            password_hash=generate_password_hash("Student@123"),
            role="Student",
            active=True,
        )
        db.session.add(demo_student)
        db.session.commit()
        print("[SEED] Created demo student user: student@portal.com (Password: Student@123)")

    if Course.query.count() == 0:
        c1 = Course(
            code="CS101",
            name="Introduction to Programming",
            description="Foundational Python and software problem solving.",
            status="Active",
        )
        c2 = Course(
            code="MAD202",
            name="Modern Application Development II",
            description="Full-stack web application development with Flask & Vue.",
            status="Active",
        )
        db.session.add_all([c1, c2])
        db.session.commit()
        print("[SEED] Seeded initial sample courses (CS101, MAD202).")


if __name__ == "__main__":
    try:
        from backend.app import create_app
    except ImportError:
        from app import create_app

    flask_app = create_app(seed_on_init=False)
    seed_database(flask_app)

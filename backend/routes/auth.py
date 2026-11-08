from flask import Blueprint, g, jsonify, request
from werkzeug.security import generate_password_hash

try:
    from backend.database import db
    from backend.models import User
    from backend.utils.auth_middleware import generate_jwt_token, role_required
except ImportError:
    from database import db
    from models import User
    from utils.auth_middleware import generate_jwt_token, role_required

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")
rbac_test_bp = Blueprint("rbac_test", __name__, url_prefix="/api")


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    name = (data.get("name") or "").strip()
    requested_role = data.get("role", "Student")

    if requested_role != "Student":
        return (
            jsonify(
                {
                    "error": "Forbidden",
                    "message": "Self-registration is strictly restricted to Students only.",
                }
            ),
            403,
        )

    if not email or not password or not name:
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": "Name, email, and password are required.",
                }
            ),
            400,
        )

    if len(password) < 6:
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": "Password must be at least 6 characters long.",
                }
            ),
            400,
        )

    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return (
            jsonify(
                {
                    "error": "Conflict",
                    "message": "An account with this email already exists.",
                }
            ),
            409,
        )

    new_user = User(
        email=email,
        password_hash=generate_password_hash(password),
        role="Student",
        active=True,
    )
    db.session.add(new_user)
    db.session.commit()

    token = generate_jwt_token(new_user)
    user_payload = new_user.to_dict()
    user_payload["name"] = name

    return (
        jsonify(
            {
                "message": "Student registered successfully.",
                "access_token": token,
                "token": token,
                "user": user_payload,
            }
        ),
        201,
    )


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": "Email and password are required.",
                }
            ),
            400,
        )

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return (
            jsonify(
                {
                    "error": "Unauthorized",
                    "message": "Invalid email or password.",
                }
            ),
            401,
        )

    if not user.active:
        return (
            jsonify(
                {
                    "error": "Forbidden",
                    "message": "Your account has been deactivated. Please contact the Administrator.",
                }
            ),
            403,
        )

    token = generate_jwt_token(user)

    return (
        jsonify(
            {
                "message": "Login successful.",
                "access_token": token,
                "token": token,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "role": user.role,
                    "active": user.active,
                },
            }
        ),
        200,
    )


@auth_bp.route("/me", methods=["GET"])
@role_required("Admin", "Examiner", "Student")
def get_current_user_profile():
    user = g.current_user
    return (
        jsonify(
            {
                "user": user.to_dict(),
            }
        ),
        200,
    )


@rbac_test_bp.route("/admin/ping", methods=["GET"])
@role_required("Admin")
def admin_ping():
    return (
        jsonify(
            {
                "status": "ok",
                "message": "pong from Admin endpoint",
                "role": g.current_user.role,
                "user_id": g.current_user.id,
                "email": g.current_user.email,
            }
        ),
        200,
    )


@rbac_test_bp.route("/examiner/ping", methods=["GET"])
@role_required("Examiner")
def examiner_ping():
    return (
        jsonify(
            {
                "status": "ok",
                "message": "pong from Examiner endpoint",
                "role": g.current_user.role,
                "user_id": g.current_user.id,
                "email": g.current_user.email,
            }
        ),
        200,
    )


@rbac_test_bp.route("/student/ping", methods=["GET"])
@role_required("Student")
def student_ping():
    return (
        jsonify(
            {
                "status": "ok",
                "message": "pong from Student endpoint",
                "role": g.current_user.role,
                "user_id": g.current_user.id,
                "email": g.current_user.email,
            }
        ),
        200,
    )


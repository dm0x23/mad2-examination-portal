from datetime import datetime, timezone
from functools import wraps
import jwt
from flask import current_app, g, jsonify, request

try:
    from backend.models import User
except ImportError:
    from models import User


def generate_jwt_token(user: User) -> str:

    now = datetime.now(timezone.utc)
    expires_delta = current_app.config.get("JWT_ACCESS_TOKEN_EXPIRES")
    exp = now + expires_delta if expires_delta else now

    payload = {
        "sub": str(user.id),
        "user_id": user.id,
        "email": user.email,
        "role": user.role,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    secret = current_app.config["JWT_SECRET_KEY"]
    algorithm = current_app.config.get("JWT_ALGORITHM", "HS256")
    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_jwt_token(token: str) -> dict:

    secret = current_app.config["JWT_SECRET_KEY"]
    algorithm = current_app.config.get("JWT_ALGORITHM", "HS256")
    return jwt.decode(token, secret, algorithms=[algorithm])


def _extract_bearer_token() -> tuple[str | None, str | None]:

    auth_header = request.headers.get("Authorization", "").strip()
    if not auth_header:
        return None, "Missing Authorization header"

    parts = auth_header.split(None, 1)
    if parts[0].lower() != "bearer":
        return None, "Invalid Authorization header format. Expected 'Bearer <token>'"

    if len(parts) < 2 or not parts[1].strip():
        return (
            None,
            "Bearer token is empty. Ensure your token variable (e.g. $ADMIN_TOKEN) is set.",
        )

    token = parts[1].strip().strip('"').strip("'")
    return token, None


def role_required(*allowed_roles: str):

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            token, error = _extract_bearer_token()
            if error:
                return jsonify({"error": "Unauthorized", "message": error}), 401

            try:
                payload = decode_jwt_token(token)
            except jwt.ExpiredSignatureError:
                return (
                    jsonify({"error": "Unauthorized", "message": "Token has expired"}),
                    401,
                )
            except jwt.InvalidTokenError:
                return (
                    jsonify({"error": "Unauthorized", "message": "Invalid token"}),
                    401,
                )

            user_id = payload.get("user_id") or payload.get("sub")
            token_role = payload.get("role")

            if not user_id or not token_role:
                return (
                    jsonify(
                        {
                            "error": "Unauthorized",
                            "message": "Malformed token payload",
                        }
                    ),
                    401,
                )

            user = User.query.get(int(user_id))
            if not user:
                return (
                    jsonify({"error": "Unauthorized", "message": "User not found"}),
                    401,
                )

            if not user.active:
                return (
                    jsonify(
                        {
                            "error": "Forbidden",
                            "message": "User account is deactivated",
                        }
                    ),
                    403,
                )

            if allowed_roles and token_role not in allowed_roles:
                return (
                    jsonify(
                        {
                            "error": "Forbidden",
                            "message": f"Access denied. Required role(s): {', '.join(allowed_roles)}",
                        }
                    ),
                    403,
                )

            g.current_user = user
            g.jwt_payload = payload
            return fn(*args, **kwargs)

        return wrapper

    return decorator


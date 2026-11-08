from flask import Flask, jsonify
from sqlalchemy import text

try:
    from backend.config import Config
    from backend.database import db
    from backend import models  # noqa: F401 - ensure models are registered with SQLAlchemy
    from backend.seed import seed_database
except ImportError:
    from config import Config
    from database import db
    import models  # noqa: F401 - ensure models are registered with SQLAlchemy
    from seed import seed_database


def create_app(config_class=Config, seed_on_init=True):
    """Flask application factory."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    if seed_on_init:
        seed_database(app)

    @app.route("/health", methods=["GET"])
    def health_check():
        """Health check endpoint that queries the SQLite database to verify connection."""
        try:
            db.session.execute(text("SELECT 1"))
            admin_exists = (
                models.User.query.filter_by(role="Admin").first() is not None
            )
            return (
                jsonify(
                    {
                        "status": "healthy",
                        "database": "connected",
                        "admin_seeded": admin_exists,
                    }
                ),
                200,
            )
        except Exception as exc:
            return (
                jsonify(
                    {
                        "status": "unhealthy",
                        "database": "disconnected",
                        "error": str(exc),
                    }
                ),
                500,
            )

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

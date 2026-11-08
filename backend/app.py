from flask import Flask, jsonify
from flask_cors import CORS
from sqlalchemy import text

try:
    from backend.config import Config
    from backend.database import db
    from backend import models 
    from backend.seed import seed_database
    from backend.routes.auth import auth_bp, rbac_test_bp
except ImportError:
    from config import Config
    from database import db
    import models 
    from seed import seed_database
    from routes.auth import auth_bp, rbac_test_bp


def create_app(config_class=Config, seed_on_init=True):
    app = Flask(__name__)
    app.config.from_object(config_class)

    CORS(
        app,
        resources={r"/api/*": {"origins": "*"}},
        supports_credentials=True,
    )

    db.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(rbac_test_bp)

    if seed_on_init:
        seed_database(app)

    @app.route("/health", methods=["GET"])
    def health_check():
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

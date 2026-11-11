import os
import sys

# Ensure parent directory is in sys.path so 'import backend' works seamlessly whether running
# from the repository root (python backend/app.py) or inside the backend folder (python app.py)
CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from flask import Flask, jsonify
from flask_cors import CORS
from sqlalchemy import text

try:
    from backend.config import Config
    from backend.database import db
    from backend import models 
    from backend.seed import seed_database
    from backend.routes.auth import auth_bp, rbac_test_bp
    from backend.routes.admin import admin_bp
    from backend.routes.examiner import examiner_bp
    from backend.routes.student import student_bp
    from backend.extensions import cache
except ImportError:
    from config import Config
    from database import db
    import models 
    from seed import seed_database
    from routes.auth import auth_bp, rbac_test_bp
    from routes.admin import admin_bp
    from routes.examiner import examiner_bp
    from routes.student import student_bp
    from extensions import cache


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
    app.register_blueprint(admin_bp)
    app.register_blueprint(examiner_bp)
    app.register_blueprint(student_bp)

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

    @app.route("/api/examinations/<int:exam_id>/rubrics", methods=["GET"])
    @cache.cached("rubrics_exam_{exam_id}", timeout=getattr(Config, "CACHE_RUBRICS_TIMEOUT", 300))
    def get_examination_rubrics_public(exam_id):
        """
        GET /api/examinations/<id>/rubrics
        Public / shared endpoint returning rubrics for an examination.
        Cached in Redis with key 'rubrics_exam_<id>' for 300s.
        """
        exam = models.Examination.query.get(exam_id)
        if not exam:
            return jsonify({"error": "Not Found", "message": "Examination not found."}), 404
        return jsonify({"rubrics": [r.to_dict() for r in exam.rubrics], "examination_id": exam.id}), 200

    @app.route("/api/examinations", methods=["GET"])
    @cache.cached("available_examinations_list", timeout=getattr(Config, "CACHE_CATALOGUE_TIMEOUT", 120))
    def get_public_catalogue_examinations():
        """
        GET /api/examinations
        Public examination catalogue listing.
        Cached in Redis with key 'available_examinations_list' for 120s.
        """
        all_exams = (
            models.Examination.query.filter(models.Examination.status != "Cancelled")
            .order_by(models.Examination.id.desc())
            .all()
        )
        results = []
        for ex in all_exams:
            avail_slots = models.ExaminationSlot.query.filter(
                models.ExaminationSlot.examination_id == ex.id,
                models.ExaminationSlot.available_seats > 0,
                models.ExaminationSlot.status != "Cancelled",
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
                    "available_slots_count": avail_slots,
                    "rubrics": [r.to_dict() for r in ex.rubrics],
                }
            )
        return jsonify({"examinations": results, "total": len(results)}), 200

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

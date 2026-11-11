import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Base configuration for Examination Management Portal V2."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(BASE_DIR, 'portal.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", SECRET_KEY)
    JWT_ALGORITHM = "HS256"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"

    # Celery & Redis Configuration (Milestone 7)
    CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
    CELERY_TIMEZONE = os.environ.get("CELERY_TIMEZONE", "Asia/Kolkata")

    # Static Exports & Reports
    EXPORTS_FOLDER = os.path.join(BASE_DIR, "static", "exports")
    REPORTS_FOLDER = os.path.join(BASE_DIR, "static", "reports")
    LOGS_FOLDER = os.path.join(BASE_DIR, "logs")

    # Redis Caching Configuration (Milestone 8)
    CACHE_TYPE = "RedisCache"
    CACHE_REDIS_URL = os.environ.get("CACHE_REDIS_URL", "redis://localhost:6379/2")
    CACHE_DEFAULT_TIMEOUT = 300
    CACHE_RUBRICS_TIMEOUT = 300  # 5 minutes
    CACHE_CATALOGUE_TIMEOUT = 120  # 2 minutes




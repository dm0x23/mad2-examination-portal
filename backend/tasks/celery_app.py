import os
import uuid
from datetime import datetime

try:
    from celery import Celery, Task
    from celery.schedules import crontab
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    Celery = None
    Task = object
    crontab = None

try:
    from backend.config import Config
except ImportError:
    from config import Config



class MockAsyncResult:

    def __init__(self, task_id, status="SUCCESS", result=None):
        self.id = task_id
        self.status = status
        self.result = result
        self.info = result

    def ready(self):
        return True

    def successful(self):
        return self.status == "SUCCESS"

    def failed(self):
        return self.status == "FAILURE"


_local_task_results = {}


class MockTask:
    def __init__(self, task_id):
        self.id = task_id
        self.request = type("Request", (), {"id": task_id})()

    def update_state(self, state="PROGRESS", meta=None):
        pass


class MockCeleryApp:

    def __init__(self, name="portal_mock_celery"):
        self.name = name
        self.conf = {}

    def task(self, *args, **kwargs):
        is_bound = kwargs.get("bind", False)

        def decorator(fn):
            def delay(*call_args, **call_kwargs):
                task_id = str(uuid.uuid4())
                try:
                    if is_bound:
                        mock_task = MockTask(task_id)
                        res = fn(mock_task, *call_args, **call_kwargs)
                    else:
                        res = fn(*call_args, **call_kwargs)
                    _local_task_results[task_id] = {
                        "status": "SUCCESS",
                        "result": res,
                    }
                    return MockAsyncResult(task_id, "SUCCESS", res)
                except Exception as exc:
                    _local_task_results[task_id] = {
                        "status": "FAILURE",
                        "result": str(exc),
                    }
                    return MockAsyncResult(task_id, "FAILURE", str(exc))

            fn.delay = delay
            fn.apply_async = lambda args=(), kwargs={}: delay(*args, **kwargs)
            return fn

        return decorator

    def AsyncResult(self, task_id):
        if task_id in _local_task_results:
            info = _local_task_results[task_id]
            return MockAsyncResult(task_id, info["status"], info["result"])
        return MockAsyncResult(task_id, "SUCCESS", None)



def make_celery(flask_app=None):
    """
    Initializes and configures the Celery application with Flask context support.
    Uses Redis as message broker (redis://localhost:6379/0) and result backend (redis://localhost:6379/1).
    """
    if not CELERY_AVAILABLE:
        print("[CELERY] Running with in-memory task runner (Celery library not detected).")
        return MockCeleryApp("portal_tasks")

    broker_url = getattr(Config, "CELERY_BROKER_URL", "redis://localhost:6379/0")
    result_backend = getattr(Config, "CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

    celery_instance = Celery(
        "portal_tasks",
        broker=broker_url,
        backend=result_backend,
        include=["backend.tasks.jobs"],
    )

    celery_instance.conf.update(
        timezone=getattr(Config, "CELERY_TIMEZONE", "Asia/Kolkata"),
        enable_utc=True,
        task_track_started=True,
        result_extended=True,
        broker_connection_retry_on_startup=True,
        beat_schedule={
            "daily-exam-reminders": {
                "task": "backend.tasks.jobs.send_daily_exam_reminders",
                "schedule": crontab(hour=7, minute=0),
            },
            "monthly-admin-report": {
                "task": "backend.tasks.jobs.generate_monthly_admin_report",
                "schedule": crontab(hour=0, minute=0, day_of_month=1),
            },
        },
    )

    if flask_app is not None:
        class FlaskContextTask(Task):
            abstract = True

            def __call__(self, *args, **kwargs):
                with flask_app.app_context():
                    return self.run(*args, **kwargs)

        celery_instance.Task = FlaskContextTask

    return celery_instance


def get_celery_task_result(task_id: str):

    if CELERY_AVAILABLE and celery_app and hasattr(celery_app, "AsyncResult"):
        try:
            return celery_app.AsyncResult(task_id)
        except Exception:
            pass
    if task_id in _local_task_results:
        item = _local_task_results[task_id]
        return MockAsyncResult(task_id, item["status"], item["result"])
    return MockAsyncResult(task_id, "PENDING", None)


flask_app_instance = None
try:
    from backend.app import app as flask_app_instance
except Exception:
    pass

celery_app = make_celery(flask_app_instance)

try:
    import backend.tasks.jobs  
except ImportError:
    try:
        import tasks.jobs  
    except ImportError:
        pass

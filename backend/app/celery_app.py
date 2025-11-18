# backend/app/celery_app.py
import os
from celery import Celery

REDIS = os.getenv("REDIS_URL", "redis://redis:6379/0")
celery = Celery(__name__, broker=REDIS, backend=REDIS, include=["app.tasks"])
celery.conf.beat_schedule = {
    "verify-every-5-min": {
        "task": "app.tasks.verify_offers_task",
        "schedule": 100.0,
    }
}

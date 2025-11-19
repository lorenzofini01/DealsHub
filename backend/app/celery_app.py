# backend/app/celery_app.py
import os
from celery import Celery

REDIS = os.getenv("REDIS_URL", "redis://redis:6379/0")
celery = Celery(__name__, broker=REDIS, backend=REDIS, include=["app.tasks", "app.tasks_v2"])

celery.conf.beat_schedule = {
    "verify-every-5-min": {
        "task": "app.tasks.verify_offers_task_v2",  # Usa nuovo task
        "schedule": 300.0,  # Ogni 5 minuti
    }
}

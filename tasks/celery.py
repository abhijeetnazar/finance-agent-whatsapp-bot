import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery(
    "tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["tasks.scheduled_tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Celery Beat schedule for checking dynamic subscriptions
celery_app.conf.beat_schedule = {
    "process-dynamic-subscriptions": {
        "task": "tasks.scheduled_tasks.process_dynamic_subscriptions",
        "schedule": 60.0,  # Run every minute to check for due reminders
    },
}

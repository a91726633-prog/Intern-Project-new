import json
from datetime import datetime, timezone

import redis
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import ProgressEvent, ProgressEventType, ProcessingJob


def redis_client() -> redis.Redis:
    return redis.Redis.from_url(get_settings().redis_url, decode_responses=True)


def progress_channel(job_id: str) -> str:
    return f"jobs:{job_id}:progress"


def publish_progress(
    db: Session,
    job: ProcessingJob,
    event_type: ProgressEventType,
    message: str,
    progress_percent: int,
) -> None:
    job.progress_percent = progress_percent
    event = ProgressEvent(
        job_id=job.id,
        event_type=event_type,
        message=message,
        progress_percent=progress_percent,
        attempt_number=job.attempt_count,
    )
    db.add(event)
    db.flush()

    payload = {
        "id": event.id,
        "job_id": job.id,
        "event_type": event_type.value,
        "message": message,
        "progress_percent": progress_percent,
        "attempt_number": job.attempt_count,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    redis_client().publish(progress_channel(job.id), json.dumps(payload))

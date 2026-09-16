import time
from pathlib import Path

from celery import Celery
from sqlalchemy.orm import joinedload

from app.config import get_settings
from app.database import SessionLocal
from app.document_processor import extract_fields, read_document_text
from app.models import ExtractedResult, JobStatus, ProcessingJob, ProgressEventType
from app.progress import publish_progress

settings = get_settings()

celery_app = Celery(
    "document_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.conf.update(task_track_started=True, worker_prefetch_multiplier=1)


@celery_app.task(name="process_document", bind=True, autoretry_for=(OSError,), retry_backoff=True, max_retries=3)
def process_document(self, job_id: str) -> None:
    db = SessionLocal()
    try:
        job = (
            db.query(ProcessingJob)
            .options(joinedload(ProcessingJob.document), joinedload(ProcessingJob.result))
            .filter(ProcessingJob.id == job_id)
            .one()
        )
        if job.status in {JobStatus.completed, JobStatus.finalized}:
            return

        job.status = JobStatus.processing
        job.error_message = None
        job.attempt_count += 1
        publish_progress(db, job, ProgressEventType.job_started, "Background worker started the job.", 10)
        db.commit()

        time.sleep(0.4)
        publish_progress(db, job, ProgressEventType.document_parsing_started, "Document parsing started.", 30)
        db.commit()

        file_path = Path(settings.upload_dir) / job.document.stored_filename
        parsed_text = read_document_text(file_path)
        time.sleep(0.4)
        publish_progress(db, job, ProgressEventType.document_parsing_completed, "Document parsing completed.", 55)
        db.commit()

        time.sleep(0.4)
        publish_progress(db, job, ProgressEventType.field_extraction_started, "Structured field extraction started.", 70)
        db.commit()

        extracted = extract_fields(job.document, parsed_text)
        if job.result is None:
            job.result = ExtractedResult(job_id=job.id, extracted_json=extracted)
        else:
            job.result.extracted_json = extracted
            job.result.reviewed_json = None
            job.result.finalized_json = None

        publish_progress(db, job, ProgressEventType.field_extraction_completed, "Structured fields are ready for review.", 90)
        db.commit()

        job.status = JobStatus.completed
        publish_progress(db, job, ProgressEventType.job_completed, "Job completed successfully.", 100)
        db.commit()
    except Exception as exc:
        db.rollback()
        job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).one_or_none()
        if job is not None:
            job.status = JobStatus.failed
            job.error_message = str(exc)
            publish_progress(db, job, ProgressEventType.job_failed, "Job failed and can be retried.", job.progress_percent)
            db.commit()
        raise
    finally:
        db.close()

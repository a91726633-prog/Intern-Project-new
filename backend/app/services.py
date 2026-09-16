from __future__ import annotations

import csv
import io
import uuid
from pathlib import Path
from typing import Iterable, Optional

from fastapi import HTTPException, UploadFile
from sqlalchemy import asc, desc, or_
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.models import Document, ExtractedResult, JobStatus, ProcessingJob, ProgressEventType
from app.progress import publish_progress
from app.worker import process_document


def create_jobs(db: Session, files: Iterable[UploadFile]) -> list[ProcessingJob]:
    settings = get_settings()
    jobs: list[ProcessingJob] = []

    for upload in files:
        suffix = Path(upload.filename or "document").suffix
        stored_filename = f"{uuid.uuid4()}{suffix}"
        target = settings.upload_dir / stored_filename
        content = upload.file.read()
        target.write_bytes(content)

        document = Document(
            original_filename=upload.filename or stored_filename,
            stored_filename=stored_filename,
            content_type=upload.content_type or "application/octet-stream",
            size_bytes=len(content),
        )
        job = ProcessingJob(document=document, status=JobStatus.queued, progress_percent=0)
        db.add(job)
        db.flush()
        publish_progress(db, job, ProgressEventType.job_queued, "Document received and job queued.", 0)
        jobs.append(job)

    db.commit()
    for job in jobs:
        process_document.delay(job.id)
    return jobs


def list_jobs(db: Session, status: Optional[JobStatus], search: Optional[str], sort: str) -> list[ProcessingJob]:
    query = db.query(ProcessingJob).options(joinedload(ProcessingJob.document))
    if status is not None:
        query = query.filter(ProcessingJob.status == status)
    if search:
        like = f"%{search}%"
        query = query.join(ProcessingJob.document).filter(or_(Document.original_filename.ilike(like), ProcessingJob.id.ilike(like)))
    order = asc(ProcessingJob.created_at) if sort == "oldest" else desc(ProcessingJob.created_at)
    return query.order_by(order).all()


def get_job_or_404(db: Session, job_id: str) -> ProcessingJob:
    job = (
        db.query(ProcessingJob)
        .options(
            joinedload(ProcessingJob.document),
            joinedload(ProcessingJob.result),
            joinedload(ProcessingJob.events),
        )
        .filter(ProcessingJob.id == job_id)
        .one_or_none()
    )
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    job.events.sort(key=lambda event: event.created_at)
    return job


def retry_job(db: Session, job_id: str) -> ProcessingJob:
    job = get_job_or_404(db, job_id)
    if job.status != JobStatus.failed:
        raise HTTPException(status_code=409, detail="Only failed jobs can be retried")
    job.status = JobStatus.queued
    job.progress_percent = 0
    job.error_message = None
    publish_progress(db, job, ProgressEventType.job_queued, "Failed job queued for retry.", 0)
    db.commit()
    process_document.delay(job.id)
    return get_job_or_404(db, job_id)


def update_review(db: Session, job_id: str, reviewed_json: dict) -> ProcessingJob:
    job = get_job_or_404(db, job_id)
    if job.result is None:
        raise HTTPException(status_code=409, detail="Job has no extracted result yet")
    job.result.reviewed_json = reviewed_json
    db.commit()
    return get_job_or_404(db, job_id)


def finalize_job(db: Session, job_id: str) -> ProcessingJob:
    job = get_job_or_404(db, job_id)
    if job.result is None:
        raise HTTPException(status_code=409, detail="Job has no result to finalize")
    job.result.finalized_json = job.result.reviewed_json or job.result.extracted_json
    job.status = JobStatus.finalized
    db.commit()
    return get_job_or_404(db, job_id)


def export_job(db: Session, job_id: str, export_format: str) -> tuple[str, str, str]:
    job = get_job_or_404(db, job_id)
    if job.result is None or job.result.finalized_json is None:
        raise HTTPException(status_code=409, detail="Finalize the result before exporting")

    data = job.result.finalized_json
    if export_format == "json":
        import json

        return "application/json", f"{job.document.original_filename}.json", json.dumps(data, indent=2)
    if export_format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["field", "value"])
        for key, value in data.items():
            writer.writerow([key, value if isinstance(value, str) else str(value)])
        return "text/csv", f"{job.document.original_filename}.csv", output.getvalue()

    raise HTTPException(status_code=400, detail="format must be json or csv")

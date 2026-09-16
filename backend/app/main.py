from __future__ import annotations

import json
from typing import Optional
from fastapi import Depends, FastAPI, File, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db, init_db
from app.models import JobStatus
from app.progress import progress_channel, redis_client
from app.schemas import JobListItem, JobRead, ReviewUpdate, UploadResponse
from app.services import create_jobs, export_job, finalize_job, get_job_or_404, list_jobs, retry_job, update_review

settings = get_settings()
app = FastAPI(title="Async Document Processing Workflow")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/documents", response_model=UploadResponse, status_code=201)
def upload_documents(files: list[UploadFile] = File(...), db: Session = Depends(get_db)) -> UploadResponse:
    jobs = create_jobs(db, files)
    return UploadResponse(jobs=jobs)


@app.get("/api/jobs", response_model=list[JobListItem])
def jobs(
    status: Optional[JobStatus] = None,
    search: Optional[str] = None,
    sort: str = Query("newest", pattern="^(newest|oldest)$"),
    db: Session = Depends(get_db),
) -> list[JobListItem]:
    return list_jobs(db, status=status, search=search, sort=sort)


@app.get("/api/jobs/{job_id}", response_model=JobRead)
def job_detail(job_id: str, db: Session = Depends(get_db)) -> JobRead:
    return get_job_or_404(db, job_id)


@app.post("/api/jobs/{job_id}/retry", response_model=JobRead)
def retry(job_id: str, db: Session = Depends(get_db)) -> JobRead:
    return retry_job(db, job_id)


@app.patch("/api/jobs/{job_id}/review", response_model=JobRead)
def review(job_id: str, payload: ReviewUpdate, db: Session = Depends(get_db)) -> JobRead:
    return update_review(db, job_id, payload.reviewed_json)


@app.post("/api/jobs/{job_id}/finalize", response_model=JobRead)
def finalize(job_id: str, db: Session = Depends(get_db)) -> JobRead:
    return finalize_job(db, job_id)


@app.get("/api/jobs/{job_id}/export")
def export(job_id: str, format: str = "json", db: Session = Depends(get_db)) -> Response:
    media_type, filename, body = export_job(db, job_id, format)
    return Response(
        content=body,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/jobs/{job_id}/events")
async def job_events(job_id: str, db: Session = Depends(get_db)) -> StreamingResponse:
    get_job_or_404(db, job_id)

    def stream():
        client = redis_client()
        pubsub = client.pubsub()
        pubsub.subscribe(progress_channel(job_id))
        try:
            yield "event: connected\ndata: {}\n\n"
            for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                payload = json.loads(message["data"])
                yield f"event: progress\ndata: {json.dumps(payload)}\n\n"
                if payload.get("event_type") in {"job_completed", "job_failed"}:
                    break
        finally:
            pubsub.close()

    return StreamingResponse(stream(), media_type="text/event-stream")

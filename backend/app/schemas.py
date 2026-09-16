from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.models import JobStatus, ProgressEventType


class DocumentRead(BaseModel):
    id: str
    original_filename: str
    content_type: str
    size_bytes: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ProgressEventRead(BaseModel):
    id: str
    event_type: ProgressEventType
    message: str
    progress_percent: int
    attempt_number: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ExtractedResultRead(BaseModel):
    extracted_json: dict[str, Any]
    reviewed_json: Optional[dict[str, Any]] = None
    finalized_json: Optional[dict[str, Any]] = None

    model_config = {"from_attributes": True}


class JobRead(BaseModel):
    id: str
    status: JobStatus
    progress_percent: int
    error_message: Optional[str]
    attempt_count: int
    created_at: datetime
    updated_at: datetime
    document: DocumentRead
    result: Optional[ExtractedResultRead] = None
    events: list[ProgressEventRead] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class JobListItem(BaseModel):
    id: str
    status: JobStatus
    progress_percent: int
    error_message: Optional[str]
    attempt_count: int
    created_at: datetime
    updated_at: datetime
    document: DocumentRead

    model_config = {"from_attributes": True}


class UploadResponse(BaseModel):
    jobs: list[JobListItem]


class ReviewUpdate(BaseModel):
    reviewed_json: dict[str, Any]


class ExportFormat(BaseModel):
    format: str = "json"

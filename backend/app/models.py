from __future__ import annotations

from datetime import datetime
from enum import Enum as PythonEnum
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class JobStatus(str, PythonEnum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    finalized = "finalized"


class ProgressEventType(str, PythonEnum):
    job_queued = "job_queued"
    job_started = "job_started"
    document_parsing_started = "document_parsing_started"
    document_parsing_completed = "document_parsing_completed"
    field_extraction_started = "field_extraction_started"
    field_extraction_completed = "field_extraction_completed"
    job_completed = "job_completed"
    job_failed = "job_failed"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    job: Mapped["ProcessingJob"] = relationship(back_populates="document", cascade="all, delete-orphan")


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[JobStatus] = mapped_column(SqlEnum(JobStatus), default=JobStatus.queued, nullable=False)
    progress_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    document: Mapped[Document] = relationship(back_populates="job")
    events: Mapped[list["ProgressEvent"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    result: Mapped[Optional["ExtractedResult"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class ProgressEvent(Base):
    __tablename__ = "progress_events"
    __table_args__ = (UniqueConstraint("job_id", "event_type", "attempt_number", name="uq_job_event_attempt"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    job_id: Mapped[str] = mapped_column(ForeignKey("processing_jobs.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[ProgressEventType] = mapped_column(SqlEnum(ProgressEventType), nullable=False)
    message: Mapped[str] = mapped_column(String(255), nullable=False)
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    job: Mapped[ProcessingJob] = relationship(back_populates="events")


class ExtractedResult(Base):
    __tablename__ = "extracted_results"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    job_id: Mapped[str] = mapped_column(ForeignKey("processing_jobs.id", ondelete="CASCADE"), nullable=False, unique=True)
    extracted_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    reviewed_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    finalized_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    job: Mapped[ProcessingJob] = relationship(back_populates="result")

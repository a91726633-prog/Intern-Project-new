import re
from pathlib import Path
from typing import Protocol


class DocumentLike(Protocol):
    original_filename: str
    content_type: str
    size_bytes: int


def read_document_text(path: Path) -> str:
    if path.suffix.lower() in {".txt", ".md", ".csv", ".json"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    return (
        "Mock parsed document content. This project focuses on asynchronous system design, "
        "progress tracking, review workflow, and export behavior rather than OCR quality."
    )


def extract_fields(document: DocumentLike, parsed_text: str) -> dict:
    words = re.findall(r"[A-Za-z][A-Za-z0-9_-]+", parsed_text.lower())
    keywords = sorted({word for word in words if len(word) > 5})[:8]
    summary_source = " ".join(parsed_text.split())
    summary = summary_source[:240] + ("..." if len(summary_source) > 240 else "")

    extension = Path(document.original_filename).suffix.lower().lstrip(".") or "unknown"
    return {
        "title": Path(document.original_filename).stem.replace("_", " ").replace("-", " ").title(),
        "category": extension.upper(),
        "summary": summary or "No readable text was found; metadata-only extraction was generated.",
        "extracted_keywords": keywords or ["document", "processing", "review"],
        "status": "ready_for_review",
        "metadata": {
            "filename": document.original_filename,
            "file_type": document.content_type,
            "size_bytes": document.size_bytes,
        },
    }

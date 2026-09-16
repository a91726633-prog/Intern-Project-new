from pathlib import Path
from types import SimpleNamespace

from app.document_processor import extract_fields, read_document_text


def test_read_document_text_reads_text_file(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.txt"
    file_path.write_text("Async workflow progress tracking", encoding="utf-8")

    assert read_document_text(file_path) == "Async workflow progress tracking"


def test_read_document_text_mocks_binary_file(tmp_path: Path) -> None:
    file_path = tmp_path / "scan.pdf"
    file_path.write_bytes(b"%PDF-1.4")

    assert "Mock parsed document content" in read_document_text(file_path)


def test_extract_fields_generates_reviewable_structure() -> None:
    document = SimpleNamespace(
        original_filename="invoice_alpha.txt",
        content_type="text/plain",
        size_bytes=128,
    )

    result = extract_fields(document, "Invoice Alpha includes compliance automation and document review.")

    assert result["title"] == "Invoice Alpha"
    assert result["category"] == "TXT"
    assert result["status"] == "ready_for_review"
    assert result["metadata"]["filename"] == "invoice_alpha.txt"
    assert "document" in result["extracted_keywords"]

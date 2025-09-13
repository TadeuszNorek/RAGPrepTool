import os
from typing import Any, Dict, Tuple, Optional

import pytest

from src.document_processor.processors.pdf_processor import PDFProcessor
from src.document_processor.config import ConverterConfig


def test_supported_extensions_and_can_process_flags():
    assert PDFProcessor.get_supported_extensions() == [".pdf"]
    assert PDFProcessor.can_process("file.pdf") is True
    # Temp/Office-like files starting with '~' should be ignored by base logic
    assert PDFProcessor.can_process("~$temp.pdf") is False


@pytest.fixture
def processor() -> PDFProcessor:
    return PDFProcessor(ConverterConfig())


def test_process_success_updates_images_and_cleans_temp(processor: PDFProcessor, tmp_path, monkeypatch):
    input_pdf = tmp_path / "doc.pdf"
    input_pdf.write_bytes(b"%PDF-1.4\n%fake")
    output_dir = tmp_path / "out"
    media_dir = tmp_path / "out" / "media"

    # Fake extraction result
    md_before = "See ![one](PLACEHOLDER1) and ![two](PLACEHOLDER2)"
    raw_images = {
        "PLACEHOLDER1": {"bytes": b"img1", "filename_suggestion": "one.png"},
        "PLACEHOLDER2": {"bytes": b"img2", "filename_suggestion": "two.jpg"},
    }
    meta = {"source_filename": "doc.pdf", "parser": "pdf_pymupdf4llm"}

    def fake_extract(self, file_path: str, temp_dir: str):
        # ensure temp dir exists as processor would create it before calling
        assert os.path.exists(temp_dir)
        return md_before, raw_images, meta

    monkeypatch.setattr(PDFProcessor, "_extract_pdf_content", fake_extract)

    # Stub ImageProcessor inside module to avoid PIL work
    class FakeIP:
        def __init__(self, cfg: Dict[str, Any]):
            self.cfg = cfg

        def process_pdf_images(self, raw: Dict[str, Any], mdir: str) -> Dict[str, Any]:
            return {
                "PLACEHOLDER1": {"action": "relink", "new_path": "media/p1.png"},
                "PLACEHOLDER2": {"action": "embed", "data": "data:image/png;base64,abc"},
            }

        def update_markdown_with_processed_images(self, md: str, info: Dict[str, Any]) -> str:
            return (
                md.replace("(PLACEHOLDER1)", "(media/p1.png)")
                .replace("(PLACEHOLDER2)", "(data:image/png;base64,abc)")
            )

    monkeypatch.setattr(
        "src.document_processor.processors.pdf_processor.ImageProcessor",
        FakeIP,
    )

    content, result_meta = processor.process(
        os.fspath(input_pdf), os.fspath(output_dir), os.fspath(media_dir)
    )

    assert content is not None
    assert "(media/p1.png)" in content
    assert "(data:image/png;base64,abc)" in content
    assert result_meta["parser"] == "pdf_pymupdf4llm"

    # Temp directory should be cleaned
    temp_dir = output_dir / "pdf_pymupdf_temp_raw_images"
    assert not temp_dir.exists()


def test_process_failure_when_extraction_returns_empty(processor: PDFProcessor, tmp_path, monkeypatch):
    input_pdf = tmp_path / "empty.pdf"
    input_pdf.write_bytes(b"%PDF-1.4\n%fake")
    output_dir = tmp_path / "out"
    media_dir = tmp_path / "out" / "media"

    def fake_extract(self, file_path: str, temp_dir: str):
        return None, {}, {"source_filename": "empty.pdf", "parser": "pdf_pymupdf4llm"}

    monkeypatch.setattr(PDFProcessor, "_extract_pdf_content", fake_extract)

    content, meta = processor.process(
        os.fspath(input_pdf), os.fspath(output_dir), os.fspath(media_dir)
    )

    assert content is None
    assert "Failed to extract PDF content" in meta.get("error", "")

    temp_dir = output_dir / "pdf_pymupdf_temp_raw_images"
    assert not temp_dir.exists()


def test_process_exception_bubbles_as_error_and_cleans(processor: PDFProcessor, tmp_path, monkeypatch):
    input_pdf = tmp_path / "boom.pdf"
    input_pdf.write_bytes(b"%PDF-1.4\n%fake")
    output_dir = tmp_path / "out"
    media_dir = tmp_path / "out" / "media"

    def boom(self, file_path: str, temp_dir: str):
        raise RuntimeError("explode")

    monkeypatch.setattr(PDFProcessor, "_extract_pdf_content", boom)

    content, meta = processor.process(
        os.fspath(input_pdf), os.fspath(output_dir), os.fspath(media_dir)
    )

    assert content is None
    assert "explode" in meta.get("error", "")

    temp_dir = output_dir / "pdf_pymupdf_temp_raw_images"
    assert not temp_dir.exists()


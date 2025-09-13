import os
from typing import Any, Dict, Tuple, Optional

import pytest

from src.document_processor.rag_converter import RAGConverter


class FakeProcessor:
    def __init__(self, cfg):
        self.cfg = cfg

    def process(self, file_path: str, output_dir: str, media_dir: str) -> Tuple[Optional[str], Dict[str, Any]]:
        return "CONTENT", {"parser": "fake", "source_filename": os.path.basename(file_path)}


def test_process_file_and_package_success(tmp_path, monkeypatch):
    conv = RAGConverter({})

    # Factory returns our fake processor
    monkeypatch.setattr(
        "src.document_processor.processors.processor_factory.DocumentProcessorFactory.create_processor",
        lambda path, cfg: FakeProcessor(cfg),
    )

    called = {"save": 0, "zip": 0, "cleanup": 0}

    def fake_save(meta, path):
        called["save"] += 1
        return True

    def fake_cleanup(output_dir):
        called["cleanup"] += 1

    def fake_zip(zip_fp, md_fp, arcname, metadata_fp=None, media_folder=None):
        called["zip"] += 1
        # Check arguments look sane
        assert os.path.exists(md_fp)
        return True

    monkeypatch.setattr("src.document_processor.utils.file_utils.FileUtils.save_metadata", fake_save)
    monkeypatch.setattr(
        "src.document_processor.utils.file_utils.FileUtils.cleanup_nested_media_folders", lambda parent: None
    )
    monkeypatch.setattr("src.document_processor.utils.file_utils.FileUtils.create_zip_package", fake_zip)

    file_path = tmp_path / "file.txt"
    file_path.write_text("hello", encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    temp = out / "temp"
    temp.mkdir()
    media = temp / "media"
    media.mkdir()

    ok = conv.process_file_and_package(
        os.fspath(file_path), os.fspath(temp), os.fspath(media), "doc.md", os.fspath(out / "doc.zip")
    )
    assert ok is True
    assert called["save"] == 1 and called["zip"] == 1


def test_process_file_and_package_processor_failure(tmp_path, monkeypatch):
    conv = RAGConverter({})

    class BadProcessor:
        def __init__(self, cfg):
            pass

        def process(self, a, b, c):
            return None, {"parser": "bad"}

    monkeypatch.setattr(
        "src.document_processor.processors.processor_factory.DocumentProcessorFactory.create_processor",
        lambda path, cfg: BadProcessor(cfg),
    )

    file_path = tmp_path / "file.txt"
    file_path.write_text("hello", encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    temp = out / "temp"
    temp.mkdir()
    media = temp / "media"
    media.mkdir()

    ok = conv.process_file_and_package(
        os.fspath(file_path), os.fspath(temp), os.fspath(media), "doc.md", os.fspath(out / "doc.zip")
    )
    assert ok is False


def test_find_supported_files_mix(tmp_path, monkeypatch):
    conv = RAGConverter({})

    # Map of supported extensions
    monkeypatch.setattr(
        "src.document_processor.processors.processor_factory.DocumentProcessorFactory.get_all_supported_extensions",
        lambda: {".txt": object},
    )
    monkeypatch.setattr(
        "src.document_processor.utils.pandoc_utils.PandocUtils.check_installed_locally",
        lambda: True,
    )
    monkeypatch.setattr(
        "src.document_processor.utils.pandoc_utils.PandocUtils.is_supported_format",
        lambda p: p.endswith(".docx"),
    )

    # Create files
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    (tmp_path / "b.docx").write_text("x", encoding="utf-8")
    (tmp_path / "c.bin").write_text("x", encoding="utf-8")

    files = conv._find_supported_files(os.fspath(tmp_path))
    names = {os.path.basename(p) for p in files}
    assert names == {"a.txt", "b.docx"}


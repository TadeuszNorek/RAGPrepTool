import os
from typing import Any, Dict, Optional

import pytest

from src.document_processor.processors.pandoc_processor import PandocProcessor
from src.document_processor.config import ConverterConfig


def test_supported_extensions_list_is_nonempty_and_reasonable():
    exts = PandocProcessor.get_supported_extensions()
    # A few common ones should be present
    for ext in [".docx", ".html", ".rtf", ".odt"]:
        assert ext in exts


@pytest.fixture
def processor() -> PandocProcessor:
    # Enable TOC to verify options propagation
    return PandocProcessor(ConverterConfig({"pandoc_toc": True}))


def test_process_success_reads_generated_md_and_extracts_title(processor: PandocProcessor, tmp_path, monkeypatch):
    input_file = tmp_path / "source.docx"
    input_file.write_bytes(b"fake")
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    media_dir = output_dir / "media"

    observed_options: Dict[str, Any] = {}

    def fake_convert_file(inp: str, out_dir: str, md_name: str, options: Optional[Dict[str, Any]] = None) -> str:
        # Capture options used by processor
        if options is not None:
            observed_options.update(options)
        md_path = os.path.join(out_dir, md_name)
        content = """---
title: My Document
---

# Heading

Body text.
"""
        os.makedirs(out_dir, exist_ok=True)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(content)
        return md_path

    # Patch convert_file directly on the imported PandocUtils symbol within the module
    monkeypatch.setattr(
        "src.document_processor.processors.pandoc_processor.PandocUtils.convert_file",
        fake_convert_file,
    )

    content, meta = processor.process(os.fspath(input_file), os.fspath(output_dir), os.fspath(media_dir))

    assert content is not None
    assert "# Heading" in content
    assert meta["parser"] == "pandoc"
    # Title extracted from YAML
    assert meta.get("title") == "My Document"
    # Options propagated
    assert observed_options.get("toc") is True
    assert observed_options.get("standalone") is True
    assert observed_options.get("images") == "separate"


def test_process_failure_when_convert_returns_none(processor: PandocProcessor, tmp_path, monkeypatch):
    input_file = tmp_path / "source.docx"
    input_file.write_bytes(b"fake")
    output_dir = tmp_path / "out"
    media_dir = output_dir / "media"

    def fake_convert_file(inp: str, out_dir: str, md_name: str, options: Optional[Dict[str, Any]] = None):
        return None

    monkeypatch.setattr(
        "src.document_processor.processors.pandoc_processor.PandocUtils.convert_file",
        fake_convert_file,
    )

    content, meta = processor.process(os.fspath(input_file), os.fspath(output_dir), os.fspath(media_dir))
    assert content is None
    assert "Pandoc conversion failed" in meta.get("error", "")


def test_process_reads_md_without_title_without_setting_title(processor: PandocProcessor, tmp_path, monkeypatch):
    input_file = tmp_path / "note.html"
    input_file.write_text("<p>hello</p>", encoding="utf-8")
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    media_dir = output_dir / "media"

    def fake_convert_file(inp: str, out_dir: str, md_name: str, options: Optional[Dict[str, Any]] = None) -> str:
        md_path = os.path.join(out_dir, md_name)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("Just content without YAML header")
        return md_path

    monkeypatch.setattr(
        "src.document_processor.processors.pandoc_processor.PandocUtils.convert_file",
        fake_convert_file,
    )

    content, meta = processor.process(os.fspath(input_file), os.fspath(output_dir), os.fspath(media_dir))
    assert content is not None
    assert "Just content" in content
    assert "title" not in meta

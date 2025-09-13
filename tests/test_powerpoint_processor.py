import os
import hashlib
import re
from typing import Any, List

import pytest

from src.document_processor.processors.powerpoint_processor import PowerPointProcessor
from src.document_processor.config import ConverterConfig


def test_supported_extensions_and_can_process_flags():
    assert set(PowerPointProcessor.get_supported_extensions()) == {".pptx", ".ppt"}
    assert PowerPointProcessor.can_process("deck.pptx") is True
    assert PowerPointProcessor.can_process("slides.ppt") is True
    assert PowerPointProcessor.can_process("~$temp.pptx") is False


@pytest.fixture
def processor() -> PowerPointProcessor:
    return PowerPointProcessor(ConverterConfig())


def test_process_pptx_basic_text_images_and_notes(processor: PowerPointProcessor, tmp_path, monkeypatch):
    # Fake python-pptx API
    class FakeParagraph:
        def __init__(self, text: str, level: int = 0):
            self.text = text
            self.level = level

    class FakeShapeTitle:
        def __init__(self, text: str, name: str = "Title 1"):
            self.text = text
            self.is_title = True
            self.name = name

    class FakeShapeText:
        def __init__(self, text: str, paragraphs: List[FakeParagraph]):
            self.text = text
            self.is_title = False
            self.paragraphs = paragraphs

    class FakeImage:
        def __init__(self, blob: bytes):
            self.blob = blob

    class FakePicture:
        def __init__(self, blob: bytes, alt_text: str = "Picture"):
            self.shape_type = 13  # placeholder, will be compared to MSO_SHAPE_TYPE.PICTURE
            self.image = FakeImage(blob)
            self.alt_text = alt_text
            self.name = "Picture 1"

    class FakeNotesFrame:
        def __init__(self, text: str):
            self.text = text

    class FakeNotes:
        def __init__(self, text: str):
            self.notes_text_frame = FakeNotesFrame(text)

    class FakeSlide:
        def __init__(self, shapes: List[Any], notes: str):
            self.shapes = shapes
            self.has_notes_slide = True
            self.notes_slide = FakeNotes(notes)

    class FakeCoreProps:
        def __init__(self, title: str):
            self.title = title

    class FakePresentation:
        def __init__(self, path: str):
            self.slides = [
                FakeSlide(
                    [
                        FakeShapeTitle("Intro"),
                        FakeShapeText(
                            "Bullet block",
                            [
                                FakeParagraph("First", 0),
                                FakeParagraph("Second", 1),
                            ],
                        ),
                        FakePicture(b"\x89PNG\r\n\x1A\nABC"),
                    ],
                    notes="Remember to demo",
                )
            ]
            self.core_properties = FakeCoreProps("Deck Title")

    class FakeMSO:
        PICTURE = 13

    # Install fake pptx modules so in-function import succeeds
    import types, sys
    m_pptx = types.ModuleType("pptx")
    m_enum = types.ModuleType("pptx.enum")
    m_shapes = types.ModuleType("pptx.enum.shapes")
    m_shapes.MSO_SHAPE_TYPE = FakeMSO
    m_pptx.Presentation = FakePresentation
    sys.modules["pptx"] = m_pptx
    sys.modules["pptx.enum"] = m_enum
    sys.modules["pptx.enum.shapes"] = m_shapes

    input_path = tmp_path / "slides.pptx"
    input_path.write_bytes(b"fake")
    out_dir = tmp_path / "out"
    media_dir = out_dir / "media"

    content, meta = processor.process(os.fspath(input_path), os.fspath(out_dir), os.fspath(media_dir))

    # Assertions: metadata
    assert meta["parser"] == "pptx_parser"
    assert meta["slide_count"] == 1
    assert meta["title"] == "Deck Title"
    assert meta["image_count"] == 1

    # Assertions: content structure
    assert content is not None
    assert content.startswith("# Deck Title\n")
    assert "## Intro\n" in content
    # Bullet rendering (levels)
    assert "* First" in content
    assert re.search(r"^\s*- Second", content, flags=re.MULTILINE)
    # Slide notes
    assert "> **Slide Notes:** Remember to demo" in content

    # Image saved and referenced
    # Compute expected prefix for filename: ppt_img_0_<md5 12 chars>.png
    img_bytes = b"\x89PNG\r\n\x1A\nABC"
    h = hashlib.md5(img_bytes).hexdigest()[:12]
    expected_name = f"ppt_img_0_{h}.png"
    assert (media_dir / expected_name).exists()
    assert f"(media/{expected_name})" in content


def test_process_ppt_adds_notice_and_processes(processor: PowerPointProcessor, tmp_path, monkeypatch):
    # Reuse simple fake with one slide and no image
    class FakeShapeTitle:
        def __init__(self, text: str):
            self.text = text
            self.is_title = True

    class FakeSlide:
        def __init__(self):
            self.shapes = [FakeShapeTitle("Old Format Slide")]
            self.has_notes_slide = False

    class FakeCoreProps:
        def __init__(self):
            self.title = "Old Deck"

    class FakePresentation:
        def __init__(self, path: str):
            self.slides = [FakeSlide()]
            self.core_properties = FakeCoreProps()

    class FakeMSO:
        PICTURE = 13

    import types, sys
    m_pptx = types.ModuleType("pptx")
    m_enum = types.ModuleType("pptx.enum")
    m_shapes = types.ModuleType("pptx.enum.shapes")
    m_shapes.MSO_SHAPE_TYPE = FakeMSO
    m_pptx.Presentation = FakePresentation
    sys.modules["pptx"] = m_pptx
    sys.modules["pptx.enum"] = m_enum
    sys.modules["pptx.enum.shapes"] = m_shapes

    input_path = tmp_path / "old.ppt"
    input_path.write_bytes(b"fake")
    out_dir = tmp_path / "out"
    media_dir = out_dir / "media"

    content, meta = processor.process(os.fspath(input_path), os.fspath(out_dir), os.fspath(media_dir))
    assert content is not None
    assert content.lstrip().startswith("# PPT Format Notice")
    assert meta["title"] == "Old Deck"

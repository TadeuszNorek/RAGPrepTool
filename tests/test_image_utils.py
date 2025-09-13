import os
import io
import base64
from typing import Dict, Any

import pytest
from PIL import Image

from src.document_processor.utils.image_utils import ImageProcessor


def make_image_bytes(mode: str = "RGBA", size=(16, 16), color=(255, 0, 0, 255)) -> bytes:
    img = Image.new(mode, size, color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_process_image_jpeg_conversion_and_rgb():
    cfg: Dict[str, Any] = {}
    ip = ImageProcessor(cfg)
    png_rgba = make_image_bytes("RGBA")

    result = ip.process_image(png_rgba, filename_suggestion="photo.jpg")

    assert result["action"] == "save"
    assert result["format"] == "JPEG"
    # JPEG bytes should exist and be non-empty
    assert isinstance(result["bytes"], (bytes, bytearray)) and len(result["bytes"]) > 0


def test_process_image_excludes_decorative_small_images():
    cfg = {"exclude_decorative": True, "decorative_threshold_px": 100}
    ip = ImageProcessor(cfg)

    tiny = make_image_bytes(size=(10, 10))
    result = ip.process_image(tiny, filename_suggestion="tiny.png")
    assert result["action"] == "remove"


def test_process_image_embeds_small_images_when_configured():
    # Set a large threshold to guarantee embedding of our tiny image
    cfg = {"embed_small_images": True, "small_image_threshold_kb": 1024}
    ip = ImageProcessor(cfg)

    tiny = make_image_bytes(size=(8, 8))
    result = ip.process_image(tiny, filename_suggestion="icon.png")

    assert result["action"] in ("embed", "save")
    if result["action"] == "embed":
        assert result.get("data_uri", "").startswith("data:image/")


def test_process_pdf_images_saves_and_relinks(tmp_path):
    cfg: Dict[str, Any] = {}
    ip = ImageProcessor(cfg)
    media_dir = tmp_path / "media"

    raw = {
        "PH1": {"bytes": make_image_bytes(), "filename_suggestion": "one.png"},
        "PH2": {"bytes": make_image_bytes(), "filename_suggestion": "two.dat"},  # forces png
    }

    info = ip.process_pdf_images(raw, os.fspath(media_dir))

    assert set(info.keys()) == {"PH1", "PH2"}
    for ph, rec in info.items():
        assert rec["action"] == "relink"
        rel = rec["new_path"]
        assert rel.startswith("media/")
        assert (media_dir / os.path.basename(rel)).exists()


def test_update_markdown_with_processed_images_variants():
    cfg: Dict[str, Any] = {}
    ip = ImageProcessor(cfg)
    md = "Look ![A](P1) and ![B](P2 \"t\") and ![C](P3)"
    info = {
        "P1": {"action": "relink", "new_path": "media/a.png"},
        "P2": {"action": "embed", "data": "data:image/png;base64,xxx"},
        "P3": {"action": "remove"},
    }
    out = ip.update_markdown_with_processed_images(md, info)
    assert "(media/a.png)" in out
    assert "(data:image/png;base64,xxx \"t\")" in out
    assert "(P3)" not in out


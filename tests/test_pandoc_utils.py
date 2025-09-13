import os
from typing import Optional, Dict, Any

import pytest

from src.document_processor.utils.pandoc_utils import PandocUtils


def test_check_installed_locally_true_and_false(monkeypatch):
    # Reset cache
    PandocUtils._pandoc_installed = None

    class FakePP:
        @staticmethod
        def get_pandoc_version():
            return "3.1"

    monkeypatch.setattr("pypandoc.get_pandoc_version", FakePP.get_pandoc_version)
    assert PandocUtils.check_installed_locally() is True

    # Force failure path
    PandocUtils._pandoc_installed = None

    def boom():
        raise RuntimeError("not found")

    monkeypatch.setattr("pypandoc.get_pandoc_version", boom)
    assert PandocUtils.check_installed_locally() is False


def test_is_supported_format_depends_on_check(monkeypatch):
    monkeypatch.setattr(PandocUtils, "_pandoc_installed", True)
    assert PandocUtils.is_supported_format("doc.odt") is True
    assert PandocUtils.is_supported_format("file.unknown") is False

    monkeypatch.setattr(PandocUtils, "_pandoc_installed", False)
    assert PandocUtils.is_supported_format("doc.odt") is False


def test_fix_md_media_paths(tmp_path):
    p = tmp_path / "doc.md"
    p.write_text("media/media/img.png", encoding="utf-8")
    PandocUtils.fix_md_media_paths(os.fspath(p))
    assert p.read_text(encoding="utf-8") == "media/img.png"


def test_convert_file_creates_md_and_passes_options(tmp_path, monkeypatch):
    input_file = tmp_path / "in.html"
    input_file.write_text("<p>x</p>", encoding="utf-8")
    out_dir = tmp_path / "out"
    md_name = "out.md"

    captured: Dict[str, Any] = {}

    def fake_convert_file(inp, fmt, outputfile=None, extra_args=None, cworkdir=None):
        # Capture arguments passed by PandocUtils
        captured["outputfile"] = outputfile
        captured["extra_args"] = extra_args or []
        captured["cworkdir"] = cworkdir
        # Create output file
        os.makedirs(os.path.dirname(outputfile), exist_ok=True)
        with open(outputfile, "w", encoding="utf-8") as f:
            f.write("content")

    monkeypatch.setattr("pypandoc.convert_file", fake_convert_file)
    # Avoid actual HTML predownload path
    monkeypatch.setattr(PandocUtils, "_predownload_external_images", lambda a, b, options=None: os.fspath(input_file))

    md_path = PandocUtils.convert_file(
        os.fspath(input_file), os.fspath(out_dir), md_name, options={"images": "separate", "toc": True, "standalone": True}
    )

    assert md_path == os.path.join(os.fspath(out_dir), md_name)
    args = captured["extra_args"]
    assert any(arg.startswith("--extract-media=") for arg in args)
    assert "--toc" in args and "--standalone" in args


def test_convert_file_returns_none_if_missing_output(tmp_path, monkeypatch):
    input_file = tmp_path / "in.html"
    input_file.write_text("<p>x</p>", encoding="utf-8")
    out_dir = tmp_path / "out"
    md_name = "out.md"

    def fake_convert_file(inp, fmt, outputfile=None, extra_args=None, cworkdir=None):
        # Do not create the output file to simulate error
        return None

    monkeypatch.setattr("pypandoc.convert_file", fake_convert_file)
    monkeypatch.setattr(PandocUtils, "_predownload_external_images", lambda a, b, options=None: os.fspath(input_file))

    md_path = PandocUtils.convert_file(os.fspath(input_file), os.fspath(out_dir), md_name)
    assert md_path is None


def test_convert_file_cleans_modified_html(tmp_path, monkeypatch):
    input_file = tmp_path / "in.html"
    input_file.write_text("<img src='http://x/y.png'>", encoding="utf-8")
    out_dir = tmp_path / "out"
    md_name = "out.md"

    # Create a fake modified HTML file that predownload step should return
    modified_html = out_dir / "in.html.modified.html"
    modified_html.parent.mkdir(exist_ok=True)
    modified_html.write_text("modified", encoding="utf-8")

    def fake_convert_file(inp, fmt, outputfile=None, extra_args=None, cworkdir=None):
        with open(outputfile, "w", encoding="utf-8") as f:
            f.write("ok")

    monkeypatch.setattr("pypandoc.convert_file", fake_convert_file)
    monkeypatch.setattr(PandocUtils, "_predownload_external_images", lambda a, b, options=None: os.fspath(modified_html))

    md_path = PandocUtils.convert_file(os.fspath(input_file), os.fspath(out_dir), md_name)
    assert md_path is not None
    assert not modified_html.exists()  # cleaned up


def test_predownload_external_images_download_and_update(tmp_path, monkeypatch):
    html = tmp_path / "page.html"
    html.write_text("""
    <html><body>
    <img src="http://example.com/a.jpg">
    <p>Text</p>
    <img src="http://example.com/a.jpg">
    <img src="http://example.com/b.png">
    </body></html>
    """, encoding="utf-8")
    media_dir = tmp_path / "out" / "media"

    def fake_download(urls, mdir, max_workers=5, timeout=90):
        return {
            "http://example.com/a.jpg": "media/a_local.jpg",
            "http://example.com/b.png": "media/b_local.png",
        }

    monkeypatch.setattr(PandocUtils, "_download_images_parallel", fake_download)

    out = PandocUtils._predownload_external_images(os.fspath(html), os.fspath(media_dir), options={"limit_image_download": True, "image_download_timeout": 1})
    assert out.endswith(".modified.html")
    text = open(out, encoding="utf-8").read()
    assert text.count("media/a_local.jpg") == 2
    assert "media/b_local.png" in text


def test_predownload_external_images_no_external_returns_input(tmp_path):
    html = tmp_path / "page.html"
    html.write_text("<img src='/local.png'>", encoding="utf-8")
    media_dir = tmp_path / "out" / "media"
    out = PandocUtils._predownload_external_images(os.fspath(html), os.fspath(media_dir), options={})
    assert out == os.fspath(html)


def test_predownload_external_images_missing_input_returns_input(tmp_path):
    missing = tmp_path / "missing.html"
    out = PandocUtils._predownload_external_images(os.fspath(missing), os.fspath(tmp_path / "media"), options={})
    assert out == os.fspath(missing)


def test_predownload_external_images_write_error_returns_input(tmp_path, monkeypatch):
    html = tmp_path / "page.html"
    html.write_text("<img src='http://x/a.jpg'>", encoding="utf-8")
    media_dir = tmp_path / "out" / "media"

    monkeypatch.setattr(PandocUtils, "_download_images_parallel", lambda urls, m, max_workers=5, timeout=90: {"http://x/a.jpg": "media/a.jpg"})

    import builtins
    real_open = builtins.open

    def fake_open(path, mode="r", *args, **kwargs):
        if isinstance(path, str) and path.endswith(".modified.html") and "w" in mode:
            raise OSError("write error")
        return real_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", fake_open)
    out = PandocUtils._predownload_external_images(os.fspath(html), os.fspath(media_dir), options={})
    assert out == os.fspath(html)


def test_predownload_external_images_sets_flags_and_status(tmp_path, monkeypatch):
    html = tmp_path / "page.html"
    html.write_text("<img src='http://x/a.jpg'><img src='http://x/b.jpg'>", encoding="utf-8")
    media_dir = tmp_path / "out" / "media"

    monkeypatch.setattr(PandocUtils, "_download_images_parallel", lambda urls, m, max_workers=5, timeout=90: {u: "media/x.jpg" for u in urls})
    PandocUtils.last_file_had_external_images = False
    PandocUtils.last_file_external_image_count = 0

    messages = []
    PandocUtils.status_callback = lambda msg: messages.append(msg)

    PandocUtils._predownload_external_images(os.fspath(html), os.fspath(media_dir), options={"limit_image_download": True, "image_download_timeout": 1})
    assert PandocUtils.last_file_had_external_images is True
    assert PandocUtils.last_file_external_image_count == 2
    assert any("2 external image(s)" in m for m in messages)

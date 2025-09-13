import os
import json
import shutil
import zipfile
import time
from typing import Optional

import pytest

from src.document_processor.utils.file_utils import (
    FileUtils,
    TempDirectory,
    safe_remove_directory,
)


def write_text(path: os.PathLike, text: str) -> None:
    path = os.fspath(path)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def test_save_metadata_success(tmp_path):
    metadata = {"author": "Test Author", "title": "Test Title"}
    filepath = tmp_path / "metadata.json"

    success = FileUtils.save_metadata(metadata, os.fspath(filepath))
    assert success is True
    assert filepath.exists()

    with open(filepath, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded == metadata


def test_save_metadata_failure_when_parent_missing(tmp_path):
    target = tmp_path / "missing" / "metadata.json"
    metadata = {"author": "X", "title": "Y"}

    ok = FileUtils.save_metadata(metadata, os.fspath(target))

    assert ok is False
    assert not target.exists()


def test_safe_remove_directory_removes_existing_dir(tmp_path):
    dir_to_remove = tmp_path / "dir_to_remove"
    dir_to_remove.mkdir()
    assert dir_to_remove.exists()

    result = safe_remove_directory(os.fspath(dir_to_remove))

    assert result is True
    assert not dir_to_remove.exists()


def test_safe_remove_directory_nonexistent_returns_true(tmp_path):
    non_existent_dir = tmp_path / "non_existent"
    assert not non_existent_dir.exists()
    result = safe_remove_directory(os.fspath(non_existent_dir))
    assert result is True


def test_safe_remove_directory_retries_permissionerror(tmp_path, monkeypatch):
    dir_to_remove = tmp_path / "to_remove"
    dir_to_remove.mkdir()

    orig_rmtree = shutil.rmtree
    calls = {"i": 0}

    def flaky_rmtree(path: str):
        if calls["i"] == 0:
            calls["i"] += 1
            raise PermissionError("Locked for a moment")
        return orig_rmtree(path)

    monkeypatch.setattr(shutil, "rmtree", flaky_rmtree)
    monkeypatch.setattr(time, "sleep", lambda s: None)

    result = safe_remove_directory(os.fspath(dir_to_remove))

    assert result is True
    assert not dir_to_remove.exists()


def test_temp_directory_context_manager_auto_remove_true(tmp_path):
    temp_path = tmp_path / "temp_auto_remove"
    with TempDirectory(os.fspath(temp_path), auto_remove=True) as path:
        assert os.path.exists(path)
    assert not temp_path.exists()


def test_temp_directory_context_manager_auto_remove_false(tmp_path):
    temp_path = tmp_path / "temp_no_remove"
    with TempDirectory(os.fspath(temp_path), auto_remove=False) as path:
        assert os.path.exists(path)
    assert temp_path.exists()


def test_cleanup_nested_media_folders_basic(tmp_path):
    # Setup nested structure
    nested_media_dir = tmp_path / "media" / "media"
    nested_media_dir.mkdir(parents=True)

    # Unique file in nested dir
    write_text(nested_media_dir / "test_image.jpg", "dummy image")

    # Duplicate file in parent media dir and nested dir
    write_text(tmp_path / "media" / "existing_image.jpg", "dummy image")
    write_text(nested_media_dir / "existing_image.jpg", "dummy image")

    FileUtils.cleanup_nested_media_folders(os.fspath(tmp_path))

    # Assert file moved and duplicate handled
    assert (tmp_path / "media" / "test_image.jpg").exists()
    assert not nested_media_dir.exists()
    assert (tmp_path / "media" / "existing_image.jpg").exists()


def test_cleanup_nested_media_folders_with_subdir(tmp_path):
    output_dir = tmp_path
    nested_media_dir = output_dir / "media" / "media"
    subdir = nested_media_dir / "subdir"
    subdir.mkdir(parents=True)
    write_text(subdir / "file.txt", "content")

    FileUtils.cleanup_nested_media_folders(os.fspath(output_dir))

    moved_file = output_dir / "media" / "subdir" / "file.txt"
    assert moved_file.exists()
    assert not nested_media_dir.exists()


def test_create_zip_package_full(tmp_path):
    md_path = tmp_path / "test.md"
    write_text(md_path, "# Hello World")

    media_dir = tmp_path / "media"
    media_dir.mkdir()
    write_text(media_dir / "image.jpg", "dummy image")

    metadata_path = tmp_path / "metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump({"key": "value"}, f)

    zip_path = tmp_path / "package.zip"

    success = FileUtils.create_zip_package(
        zip_filepath=os.fspath(zip_path),
        markdown_filepath=os.fspath(md_path),
        markdown_arcname="document.md",
        media_folder=os.fspath(media_dir),
        metadata_filepath=os.fspath(metadata_path),
    )

    assert success is True
    assert zip_path.exists()

    with zipfile.ZipFile(os.fspath(zip_path), "r") as zf:
        names = zf.namelist()
        assert "document.md" in names
        assert "metadata.json" in names
        assert "media/image.jpg" in names


def test_create_zip_package_missing_markdown(tmp_path):
    zip_path = tmp_path / "package.zip"

    success = FileUtils.create_zip_package(
        zip_filepath=os.fspath(zip_path),
        markdown_filepath="non_existent.md",
        markdown_arcname="document.md",
    )

    assert success is False
    assert not zip_path.exists()


def test_create_zip_package_without_metadata(tmp_path):
    md_path = tmp_path / "doc.md"
    write_text(md_path, "# Title")
    zip_path = tmp_path / "pkg.zip"

    ok = FileUtils.create_zip_package(
        zip_filepath=os.fspath(zip_path),
        markdown_filepath=os.fspath(md_path),
        markdown_arcname="document.md",
    )

    assert ok is True
    with zipfile.ZipFile(os.fspath(zip_path), "r") as zf:
        names = zf.namelist()
        assert "document.md" in names
        assert "metadata.json" not in names


@pytest.mark.parametrize("variant", ["none", "empty"], ids=["no-media", "empty-media-dir"])
def test_create_zip_package_without_or_empty_media(tmp_path, variant: str):
    md_path = tmp_path / "doc.md"
    write_text(md_path, "# Title")
    zip_path = tmp_path / "pkg.zip"

    media_folder: Optional[str]
    if variant == "none":
        media_folder = None
    else:
        media_dir = tmp_path / "media"
        media_dir.mkdir()
        media_folder = os.fspath(media_dir)

    ok = FileUtils.create_zip_package(
        zip_filepath=os.fspath(zip_path),
        markdown_filepath=os.fspath(md_path),
        markdown_arcname="document.md",
        media_folder=media_folder,
    )

    assert ok is True
    with zipfile.ZipFile(os.fspath(zip_path), "r") as zf:
        names = zf.namelist()
        assert not any(n.startswith("media/") for n in names)


def test_create_zip_package_error_during_zipping(tmp_path, monkeypatch):
    md_path = tmp_path / "doc.md"
    write_text(md_path, "# Title")
    metadata_path = tmp_path / "metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump({"k": "v"}, f)
    zip_path = tmp_path / "pkg.zip"

    orig_write = zipfile.ZipFile.write
    calls = {"i": 0}

    def flaky_write(self, filename, arcname=None, compress_type=None):
        calls["i"] += 1
        if calls["i"] == 2:
            raise RuntimeError("Simulated write failure")
        return orig_write(self, filename, arcname=arcname, compress_type=compress_type)

    monkeypatch.setattr(zipfile.ZipFile, "write", flaky_write)

    ok = FileUtils.create_zip_package(
        zip_filepath=os.fspath(zip_path),
        markdown_filepath=os.fspath(md_path),
        markdown_arcname="document.md",
        metadata_filepath=os.fspath(metadata_path),
    )

    assert ok is False
    assert not zip_path.exists()


def test_create_zip_package_overwrites_existing_zip(tmp_path):
    existing_zip = tmp_path / "pkg.zip"
    with zipfile.ZipFile(os.fspath(existing_zip), "w", zipfile.ZIP_DEFLATED) as zf:
        tmp_file = tmp_path / "old.txt"
        write_text(tmp_file, "old")
        zf.write(os.fspath(tmp_file), arcname="old.txt")

    md_path = tmp_path / "doc.md"
    write_text(md_path, "# Title")

    ok = FileUtils.create_zip_package(
        zip_filepath=os.fspath(existing_zip),
        markdown_filepath=os.fspath(md_path),
        markdown_arcname="document.md",
    )

    assert ok is True
    with zipfile.ZipFile(os.fspath(existing_zip), "r") as zf:
        names = set(zf.namelist())
        assert "document.md" in names
        assert "old.txt" not in names

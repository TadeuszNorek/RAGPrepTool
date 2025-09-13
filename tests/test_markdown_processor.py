
import pytest
from unittest.mock import MagicMock

from src.document_processor.processors.markdown_processor import MarkdownProcessor
from src.document_processor.config import ConverterConfig

@pytest.fixture
def mock_config():
    """Fixture for a mock ConverterConfig."""
    return MagicMock(spec=ConverterConfig)

@pytest.fixture
def processor(mock_config):
    """Fixture for a MarkdownProcessor instance."""
    return MarkdownProcessor(mock_config)

def test_process_markdown_with_local_image(processor, tmp_path):
    """Test processing a markdown file with a simple local image."""
    # Arrange
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    media_dir = output_dir / "media"
    # media_dir is created by the processor

    md_path = src_dir / "test.md"
    img_path = src_dir / "image.png"
    
    md_content = "Hello world!\n\n![An image](./image.png)"
    md_path.write_text(md_content, encoding='utf-8')
    img_path.touch() # Create a dummy image file

    # Act
    processed_content, _ = processor.process(str(md_path), str(output_dir), str(media_dir))

    # Assert
    dest_img_path = media_dir / "image.png"
    assert dest_img_path.exists()
    
    expected_content = "Hello world!\n\n![An image](media/image.png)"
    assert processed_content == expected_content

def test_process_markdown_with_nested_image(processor, tmp_path):
    """Test processing markdown with an image in a subfolder."""
    # Arrange
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    img_subdir = src_dir / "images"
    img_subdir.mkdir()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    media_dir = output_dir / "media"

    md_path = src_dir / "test.md"
    img_path = img_subdir / "pic.jpg"
    
    md_content = "![A nested image](images/pic.jpg)"
    md_path.write_text(md_content, encoding='utf-8')
    img_path.touch()

    # Act
    processed_content, _ = processor.process(str(md_path), str(output_dir), str(media_dir))

    # Assert
    dest_img_path = media_dir / "images_pic.jpg"
    assert dest_img_path.exists()
    
    expected_content = "![A nested image](media/images_pic.jpg)"
    assert processed_content == expected_content

def test_ignores_remote_and_absolute_images(processor, tmp_path):
    """Test that remote (http) and absolute paths are ignored."""
    # Arrange
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    media_dir = output_dir / "media"

    md_path = src_dir / "test.md"
    md_content = (
        "![Remote](https://example.com/image.png)\n"
        "![Absolute](/images/pic.jpg)\n"
        "![Data URI](data:image/png;base64,iVBORw0KGgo=...)"
    )
    md_path.write_text(md_content, encoding='utf-8')

    # Act
    processed_content, _ = processor.process(str(md_path), str(output_dir), str(media_dir))

    # Assert
    # The media dir is created unconditionally, so we check if it's empty
    assert not any(media_dir.iterdir())
    assert processed_content == md_content # Content should be unchanged


def test_handles_missing_local_image(processor, tmp_path, caplog):
    """Test that a missing local image is handled gracefully."""
    # Arrange
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    media_dir = output_dir / "media"

    md_path = src_dir / "test.md"
    md_content = "![Missing](./not_found.png)"
    md_path.write_text(md_content, encoding='utf-8')

    # Act
    processed_content, _ = processor.process(str(md_path), str(output_dir), str(media_dir))

    # Assert
    assert not (media_dir / "not_found.png").exists()
    assert processed_content == md_content # Content should be unchanged
    assert "Local image not found" in caplog.text

def test_updates_html_img_tags(processor, tmp_path):
    """Test that standard HTML <img> tags are also updated."""
    # Arrange
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    media_dir = output_dir / "media"

    md_path = src_dir / "test.md"
    img_path = src_dir / "photo.gif"
    
    md_content = 'Check this out: <img src="./photo.gif" alt="A photo">'
    md_path.write_text(md_content, encoding='utf-8')
    img_path.touch()

    # Act
    processed_content, _ = processor.process(str(md_path), str(output_dir), str(media_dir))

    # Assert
    dest_img_path = media_dir / "photo.gif"
    assert dest_img_path.exists()
    
    expected_content = 'Check this out: <img src="media/photo.gif" alt="A photo">'
    assert processed_content == expected_content


def test_updates_html_img_tags_single_quotes_and_case(processor, tmp_path):
    """HTML <IMG SRC='...'> with single quotes and different cases should be updated."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    media_dir = output_dir / "media"

    md_path = src_dir / "test.md"
    img_path = src_dir / "asset.PNG"

    md_content = "Check: <IMG SRC='./asset.PNG' ALT='X'>"
    md_path.write_text(md_content, encoding='utf-8')
    img_path.touch()

    processed_content, _ = processor.process(str(md_path), str(output_dir), str(media_dir))

    assert (media_dir / "asset.PNG").exists()
    assert "<IMG SRC='media/asset.PNG' ALT='X'>" in processed_content

def test_process_markdown_with_parent_dir_image(processor, tmp_path):
    """Images referenced via ../ should be flattened into media/ without parent segments."""
    # Arrange
    src_dir = tmp_path / "src"
    assets_dir = tmp_path / "assets"
    src_dir.mkdir()
    assets_dir.mkdir()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    media_dir = output_dir / "media"

    md_path = src_dir / "test.md"
    img_path = assets_dir / "logo.png"

    md_content = "![Logo](../assets/logo.png)"
    md_path.write_text(md_content, encoding="utf-8")
    img_path.touch()

    # Act
    processed_content, _ = processor.process(str(md_path), str(output_dir), str(media_dir))

    # Assert: '../assets/logo.png' -> 'media/assets_logo.png'
    dest_img_path = media_dir / "assets_logo.png"
    assert dest_img_path.exists()
    expected_content = "![Logo](media/assets_logo.png)"
    assert processed_content == expected_content


def test_process_markdown_image_without_extension_defaults_png(processor, tmp_path):
    """Images without extension should be copied as .png and link updated accordingly."""
    # Arrange
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    media_dir = output_dir / "media"

    md_path = src_dir / "test.md"
    img_path = src_dir / "diagram"  # no extension

    md_content = "![Diagram](./diagram)"
    md_path.write_text(md_content, encoding="utf-8")
    img_path.touch()

    # Act
    processed_content, _ = processor.process(str(md_path), str(output_dir), str(media_dir))

    # Assert: './diagram' -> 'media/diagram.png'
    dest_img_path = media_dir / "diagram.png"
    assert dest_img_path.exists()
    expected_content = "![Diagram](media/diagram.png)"
    assert processed_content == expected_content


def test_process_markdown_preserves_title_in_link(processor, tmp_path):
    """Markdown image titles should be preserved when updating the link path."""
    # Arrange
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    media_dir = output_dir / "media"

    md_path = src_dir / "test.md"
    img_path = src_dir / "chart.png"

    md_content = '![Chart](./chart.png "Quarterly Results")'
    md_path.write_text(md_content, encoding="utf-8")
    img_path.touch()

    # Act
    processed_content, _ = processor.process(str(md_path), str(output_dir), str(media_dir))

    # Assert: title remains
    dest_img_path = media_dir / "chart.png"
    assert dest_img_path.exists()
    expected_content = '![Chart](media/chart.png "Quarterly Results")'
    assert processed_content == expected_content

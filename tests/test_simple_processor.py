
import pytest
import json
from unittest.mock import MagicMock

from src.document_processor.processors.simple_processor import SimpleProcessor
from src.document_processor.config import ConverterConfig

@pytest.fixture
def mock_config():
    """Fixture for a mock ConverterConfig."""
    return MagicMock(spec=ConverterConfig)

@pytest.fixture
def processor(mock_config):
    """Fixture for a SimpleProcessor instance."""
    return SimpleProcessor(mock_config)

def test_process_txt_file(processor, tmp_path):
    """Test processing a simple .txt file."""
    # Arrange
    file_path = tmp_path / "test.txt"
    content = "This is a simple text file."
    file_path.write_text(content, encoding='utf-8')

    # Act
    processed_content, metadata = processor.process(str(file_path), str(tmp_path), str(tmp_path))

    # Assert
    assert processed_content == content
    assert metadata["parser"] == "txt_simple"
    assert metadata["source_filename"] == "test.txt"

def test_process_valid_json_file(processor, tmp_path):
    """Test processing a valid .json file."""
    # Arrange
    file_path = tmp_path / "data.json"
    data = {"key": "value", "number": 123}
    file_path.write_text(json.dumps(data), encoding='utf-8')

    # Act
    processed_content, metadata = processor.process(str(file_path), str(tmp_path), str(tmp_path))

    # Assert
    expected_content = f"```json\n{json.dumps(data, indent=2)}\n```"
    assert processed_content == expected_content
    assert metadata["parser"] == "json_simple"

def test_process_invalid_json_file(processor, tmp_path):
    """Test processing an invalid .json file."""
    # Arrange
    file_path = tmp_path / "invalid.json"
    invalid_content = '{"key": "value",}' # trailing comma
    file_path.write_text(invalid_content, encoding='utf-8')

    # Act
    processed_content, metadata = processor.process(str(file_path), str(tmp_path), str(tmp_path))

    # Assert
    expected_content = f"```\n{invalid_content}\n```"
    assert processed_content == expected_content
    assert metadata["parser"] == "json_simple"
    assert "error" in metadata

@pytest.mark.parametrize(
    "extension, language",
    [
        (".py", "py"),
        (".js", "js"),
        (".java", "java"),
        (".cs", "cs"),
        (".c", "c"),
        (".cpp", "cpp"),
        (".go", "go"),
        (".rb", "rb"),
        (".php", "php"),
        (".rs", "rs"),
        (".kt", "kt"),
        (".swift", "swift"),
    ],
)
def test_process_code_files(processor, tmp_path, extension, language):
    """Test processing various code files."""
    # Arrange
    file_path = tmp_path / f"code{extension}"
    content = f"print('Hello, {language}')"
    file_path.write_text(content, encoding='utf-8')

    # Act
    processed_content, metadata = processor.process(str(file_path), str(tmp_path), str(tmp_path))

    # Assert
    expected_content = f"```{language}\n{content}\n```"
    assert processed_content == expected_content
    assert metadata["parser"] == "code_simple"
    assert metadata["language"] == language

def test_process_unknown_extension_falls_back_to_txt(processor, tmp_path):
    """Test that an unknown file extension is treated as plain text."""
    # Arrange
    file_path = tmp_path / "document.unknown"
    content = "Some content in an unknown file type."
    file_path.write_text(content, encoding='utf-8')

    # Act
    processed_content, metadata = processor.process(str(file_path), str(tmp_path), str(tmp_path))

    # Assert
    assert processed_content == content
    assert metadata["parser"] == "txt_simple"


def test_process_empty_txt_file(processor, tmp_path):
    """Empty .txt should result in empty content and txt parser metadata."""
    file_path = tmp_path / "empty.txt"
    file_path.write_text("", encoding="utf-8")

    processed_content, metadata = processor.process(str(file_path), str(tmp_path), str(tmp_path))

    assert processed_content == ""
    assert metadata["parser"] == "txt_simple"


def test_process_empty_json_file_invalid_fallback(processor, tmp_path):
    """Empty .json is invalid JSON and should use error handler fenced block."""
    file_path = tmp_path / "empty.json"
    file_path.write_text("", encoding="utf-8")

    processed_content, metadata = processor.process(str(file_path), str(tmp_path), str(tmp_path))

    assert processed_content == "```\n\n```"
    assert metadata["parser"] == "json_simple"
    assert "error" in metadata

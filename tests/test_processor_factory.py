
import pytest
from unittest.mock import MagicMock, patch
from typing import Any

from src.document_processor.processors.processor_factory import DocumentProcessorFactory
from src.document_processor.processors.base_processor import BaseDocumentProcessor
from src.document_processor.processors.pdf_processor import PDFProcessor
from src.document_processor.processors.pandoc_processor import PandocProcessor
from src.document_processor.processors.simple_processor import SimpleProcessor
from src.document_processor.processors.markdown_processor import MarkdownProcessor
from src.document_processor.config import ConverterConfig

# Mock ConverterConfig
@pytest.fixture
def mock_config():
    """Fixture for a mock ConverterConfig."""
    return MagicMock(spec=ConverterConfig)

# A dummy processor for testing registration
class DummyProcessor(BaseDocumentProcessor):
    @classmethod
    def get_supported_extensions(cls) -> list[str]:
        return [".dummy"]
    def process(self, file_path: str, output_dir: str, media_dir: str) -> tuple[str | None, dict[str, Any]]:
        return "dummy content", {"source": file_path}

def test_get_all_supported_extensions(monkeypatch):
    """Test if all supported extensions are collected correctly."""
    # Arrange: Create mock processors with known extensions
    class MockPDF(BaseDocumentProcessor):
        @classmethod
        def get_supported_extensions(cls) -> list[str]:
            return ['.pdf']
        def process(self, file_path: str, output_dir: str, media_dir: str) -> tuple[str | None, dict[str, Any]]:
            return None, {}

    class MockMD(BaseDocumentProcessor):
        @classmethod
        def get_supported_extensions(cls) -> list[str]:
            return ['.md', '.markdown']
        def process(self, file_path: str, output_dir: str, media_dir: str) -> tuple[str | None, dict[str, Any]]:
            return None, {}
    
    monkeypatch.setattr(DocumentProcessorFactory, '_processor_classes', [MockPDF, MockMD])

    # Act
    extensions = DocumentProcessorFactory.get_all_supported_extensions()

    # Assert
    assert extensions == {
        '.pdf': MockPDF,
        '.md': MockMD,
        '.markdown': MockMD
    }
    assert len(extensions) == 3

@pytest.mark.parametrize("file_path, pandoc_supported, expected", [
    ("document.pdf", False, True),  # Directly supported
    ("document.docx", True, True),   # Pandoc supported (directly)
    ("document.ipynb", True, True),  # Pandoc supported (indirectly)
    ("document.txt", False, True),  # Supported by SimpleProcessor
    ("archive.zip", False, False), # Unsupported by any default processor
])
@patch('src.document_processor.utils.pandoc_utils.PandocUtils.is_supported_format')
def test_can_process(mock_is_supported_format, file_path, pandoc_supported, expected):
    """Test the can_process method with various file types."""
    # Arrange
    mock_is_supported_format.return_value = pandoc_supported
    
    # Act
    result = DocumentProcessorFactory.can_process(file_path)

    # Assert
    assert result == expected

def test_create_processor_returns_correct_processor(mock_config):
    """Test if the factory creates the correct processor for a given file type."""
    # PDF
    processor_pdf = DocumentProcessorFactory.create_processor("test.pdf", mock_config)
    assert isinstance(processor_pdf, PDFProcessor)

    # Simple text file
    processor_simple = DocumentProcessorFactory.create_processor("test.txt", mock_config)
    assert isinstance(processor_simple, SimpleProcessor)

def test_create_processor_for_direct_pandoc_file(mock_config):
    """Test if PandocProcessor is created for a directly supported file like .docx."""
    # Arrange: .docx is in PandocProcessor.get_supported_extensions()
    # Act
    processor = DocumentProcessorFactory.create_processor("document.docx", mock_config)
    # Assert
    assert isinstance(processor, PandocProcessor)

@patch('src.document_processor.utils.pandoc_utils.PandocUtils.is_supported_format')
def test_create_processor_for_indirect_pandoc_file(mock_is_supported_format, mock_config):
    """Test if PandocProcessor is created for a file supported via PandocUtils."""
    # Arrange
    # .ipynb is not in any get_supported_extensions list, so this check will be triggered
    mock_is_supported_format.return_value = True
    
    # Act
    processor = DocumentProcessorFactory.create_processor("notebook.ipynb", mock_config)

    # Assert
    assert isinstance(processor, PandocProcessor)
    mock_is_supported_format.assert_called_with("notebook.ipynb")

@patch('src.document_processor.utils.pandoc_utils.PandocUtils.is_supported_format')
def test_create_processor_defaults_to_simple(mock_is_supported_format, mock_config):
    """Test if SimpleProcessor is returned for unsupported, non-pandoc files."""
    # Arrange
    mock_is_supported_format.return_value = False
    
    # Act
    # Assuming .xyz is not supported by any processor
    processor = DocumentProcessorFactory.create_processor("file.xyz", mock_config)

    # Assert
    assert isinstance(processor, SimpleProcessor)


def test_create_processor_for_markdown_file(mock_config):
    """Markdown files should be handled by MarkdownProcessor (not Pandoc)."""
    processor = DocumentProcessorFactory.create_processor("notes.md", mock_config)
    assert isinstance(processor, MarkdownProcessor)


def test_register_and_create_processor(monkeypatch, mock_config):
    """Test registering a new processor via public API and then creating it."""
    # Arrange: isolate registry per test using a copy
    original = list(DocumentProcessorFactory._processor_classes)
    monkeypatch.setattr(DocumentProcessorFactory, "_processor_classes", original.copy())

    # Act: register and inspect
    DocumentProcessorFactory.register_processor(DummyProcessor)
    extensions = DocumentProcessorFactory.get_all_supported_extensions()

    # Assert: recognition and creation
    assert ".dummy" in extensions
    assert extensions[".dummy"] == DummyProcessor
    processor = DocumentProcessorFactory.create_processor("example.dummy", mock_config)
    assert isinstance(processor, DummyProcessor)

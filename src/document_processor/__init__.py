#!filepath document_processor/__init__.py
from .utils.pandoc_utils import PandocUtils
from .rag_converter import RAGConverter
from .config import ConverterConfig

# Expose PANDOC_INSTALLED as a module-level variable for UI compatibility
PANDOC_INSTALLED = PandocUtils.check_installed_locally()

# Expose the function with the same name for UI compatibility
def pandoc_is_supported_format_locally(file_path):
    return PandocUtils.is_supported_format(file_path)

__all__ = ['RAGConverter', 'ConverterConfig', 'PANDOC_INSTALLED', 'pandoc_is_supported_format_locally']
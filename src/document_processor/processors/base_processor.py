#!filepath document_processor/processors/base_processor.py
import os
import logging
from typing import List, Tuple, Dict, Any, Type, Callable, Optional
from ..config import ConverterConfig

logger = logging.getLogger(__name__)

class BaseDocumentProcessor:
    """Base class for document processors"""
    
    def __init__(self, config: 'ConverterConfig') -> None:
        """
        Initialize document processor with configuration
        
        Args:
            config: Configuration object or dictionary
        """
        self.config: 'ConverterConfig' = config
    
    @classmethod
    def get_supported_extensions(cls) -> List[str]:
        """
        Get the file extensions supported by this processor.
        Override in subclasses to specify supported extensions.
        
        Returns:
            list: List of supported file extensions (e.g., ['.pdf', '.txt'])
        """
        return []
    
    @classmethod
    def can_process(cls, file_path: str) -> bool:
        """
        Check if this processor can handle the given file.
        
        Args:
            file_path (str): Path to the file to check
            
        Returns:
            bool: True if this processor can handle the file, False otherwise
        """
        # Check if it's a common temp file
        if cls._is_common_temp_file(cls, file_path):
            return False
        
        ext = os.path.splitext(file_path)[1].lower()
        return ext in cls.get_supported_extensions()
    
    @classmethod
    def _is_common_temp_file(cls, file_path: str) -> bool:
        """Check for common temporary file patterns"""
        filename = os.path.basename(file_path)
        
        # Microsoft Office temporary files (Excel, Word, PowerPoint)
        if filename.startswith('~$'):
            logger.debug(f"Skipping Microsoft Office temp file: {filename}")
            return True
        
        # Other common temporary files
        if filename.startswith('.~') or filename.endswith('.tmp'):
            logger.debug(f"Skipping temporary file: {filename}")
            return True
        
        # Backup files
        if filename.endswith('.bak'):
            logger.debug(f"Skipping backup file: {filename}")
            return True
        
        # System files
        if filename.lower() in ['thumbs.db', 'desktop.ini', '.ds_store']:
            logger.debug(f"Skipping system file: {filename}")
            return True
        
        return False
        
    def process(self, file_path: str, output_dir: str, media_dir: str) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Process document and return markdown content and metadata
        
        Args:
            file_path (str): Path to source file
            output_dir (str): Directory for temporary outputs
            media_dir (str): Directory for media files
            
        Returns:
            tuple: (markdown_content, metadata_dict)
        """
        raise NotImplementedError("Subclasses must implement the process method")
        
    def _safe_operation(self, operation_func: Callable, error_message: str, *args: Any, **kwargs: Any) -> Any:
        """
        Safely execute an operation with standardized error handling
        
        Args:
            operation_func (callable): Function to execute
            error_message (str): Error message prefix
            *args, **kwargs: Arguments to pass to the function
            
        Returns:
            Result of operation_func or None on error
        """
        try:
            return operation_func(*args, **kwargs)
        except Exception as e:
            logger.error(f"{error_message}: {e}", exc_info=True)
            return None
            
    def get_metadata_base(self, file_path: str, parser_name: str) -> Dict[str, Any]:
        """
        Generate base metadata for a document
        
        Args:
            file_path (str): Path to source file
            parser_name (str): Name of the parser
            
        Returns:
            dict: Base metadata
        """
        return {
            "source_filename": os.path.basename(file_path),
            "parser": parser_name
        }
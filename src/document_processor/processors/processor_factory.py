#!filepath document_processor/processors/processor_factory.py
import os
from typing import List, Dict, Type, Optional, Any
from .base_processor import BaseDocumentProcessor
from ..config import ConverterConfig
from .pdf_processor import PDFProcessor
from .markdown_processor import MarkdownProcessor
from .simple_processor import SimpleProcessor
from .pandoc_processor import PandocProcessor
from .powerpoint_processor import PowerPointProcessor
from .excel_csv_processor import ExcelCsvProcessor
from ..utils.pandoc_utils import PandocUtils

class DocumentProcessorFactory:
    """Factory for creating document processors based on file type"""
    
    # Registry of processor classes
    _processor_classes: List[Type[BaseDocumentProcessor]] = [
        PDFProcessor,
        MarkdownProcessor,
        PowerPointProcessor,
        ExcelCsvProcessor,
        SimpleProcessor,
        PandocProcessor
    ]
    
    @classmethod
    def get_all_supported_extensions(cls) -> Dict[str, Type[BaseDocumentProcessor]]:
        """
        Collect all supported extensions from registered processors
        
        Returns:
            dict: Dictionary mapping extensions to processor classes
        """
        extensions_map = {}
        
        # Collect extensions from each processor
        for processor_class in cls._processor_classes:
            for ext in processor_class.get_supported_extensions():
                extensions_map[ext] = processor_class
    
        return extensions_map
    
    @classmethod
    def can_process(cls, file_path: str) -> bool:
        """
        Check if this factory can create a processor for the given file
        
        Args:
            file_path (str): Path to document file
            
        Returns:
            bool: True if a processor can handle this file, False otherwise
        """
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        # Get map of all extensions to processor classes
        extensions_map = cls.get_all_supported_extensions()
        
        # Check if there's a processor for this extension
        if ext in extensions_map:
            return True
        
        # Special case for Pandoc-supported formats
        if PandocUtils.is_supported_format(file_path):
            return True
            
        return False
        
    @classmethod
    def create_processor(cls, file_path: str, config: ConverterConfig) -> BaseDocumentProcessor:
        """
        Create appropriate document processor based on file extension
        
        Args:
            file_path (str): Path to document file
            config: Configuration object or dictionary
            
        Returns:
            BaseDocumentProcessor: Appropriate processor instance
        """
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        # Get map of all extensions to processor classes
        extensions_map = cls.get_all_supported_extensions()
        
        # Check if there's a processor for this extension
        if ext in extensions_map:
            return extensions_map[ext](config)
        
        # Special case for Pandoc-supported formats
        if PandocUtils.is_supported_format(file_path):
            return PandocProcessor(config)
        
        # Default to simple processor if no specific processor is available
        return SimpleProcessor(config)
        
    @classmethod
    def register_processor(cls, processor_class: Type[BaseDocumentProcessor]) -> None:
        """
        Register a new processor class with the factory
        
        Args:
            processor_class: A BaseDocumentProcessor subclass to register
        """
        if processor_class not in cls._processor_classes:
            cls._processor_classes.append(processor_class)
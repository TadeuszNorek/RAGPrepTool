#!filepath document_processor/processors/simple_processor.py
import os
import json
import logging
from .base_processor import BaseDocumentProcessor

logger = logging.getLogger(__name__)

class SimpleProcessor(BaseDocumentProcessor):
    """
    Processor for simple file types (text, code, JSON)
    Uses a single implementation for processing similar file types
    """
    
    @classmethod
    def get_supported_extensions(cls):
        """Return the file extensions supported by this processor"""
        return list(cls.FILE_TYPES.keys())
    
    # File type configurations
    FILE_TYPES = {
        # Plain text
        ".txt": {
            "parser_name": "txt_simple",
            "formatter": lambda content: content,  # No special formatting
        },
        
        # JSON files
        ".json": {
            "parser_name": "json_simple",
            "formatter": lambda content: f"```json\n{json.dumps(json.loads(content), indent=2)}\n```",
            "error_handler": lambda content: f"```\n{content}\n```"  # For invalid JSON
        },
        
        # Code files with language-specific highlighting
        **{ext: {
            "parser_name": "code_simple",
            "formatter": lambda content, ext=ext: f"```{ext.lstrip('.')}\n{content}\n```",
            "metadata_extra": lambda ext=ext: {"language": ext.lstrip('.')}
        } for ext in [".py", ".js", ".java", ".cs", ".c", ".cpp", ".go", ".rb", ".php", ".rs", ".kt", ".swift"]}
    }
    
    def process(self, file_path, output_dir, media_dir):
        """
        Process simple file types using a unified approach
        
        Args:
            file_path (str): Path to the file
            output_dir (str): Directory for temporary files
            media_dir (str): Directory for media files
            
        Returns:
            tuple: (content, metadata_dict)
        """
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        # Get file type configuration
        if ext not in self.FILE_TYPES:
            logger.warning(f"No configuration for file type {ext}, using default text handler")
            file_type = self.FILE_TYPES[".txt"]  # Fallback to text handler
        else:
            file_type = self.FILE_TYPES[ext]
        
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Create base metadata
            metadata = self.get_metadata_base(file_path, file_type["parser_name"])
            
            # Add extra metadata if specified
            if "metadata_extra" in file_type:
                metadata.update(file_type["metadata_extra"]())
            
            # Format content according to file type
            try:
                formatted_content = file_type["formatter"](content)
            except Exception as e:
                logger.warning(f"Error formatting {file_path}: {e}")
                if "error_handler" in file_type:
                    formatted_content = file_type["error_handler"](content)
                    metadata["error"] = str(e)
                else:
                    # Default error handling - return plain text
                    formatted_content = content
                    metadata["error"] = str(e)
            
            return formatted_content, metadata
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}", exc_info=True)
            return None, {
                "error": str(e),
                **self.get_metadata_base(file_path, file_type["parser_name"])
            }
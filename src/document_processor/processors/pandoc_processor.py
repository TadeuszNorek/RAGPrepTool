#!filepath document_processor/processors/pandoc_processor.py
import os
import re
import logging
from typing import List, Tuple, Dict, Any, Optional
from .base_processor import BaseDocumentProcessor
from ..utils.pandoc_utils import PandocUtils

logger = logging.getLogger(__name__)

class PandocProcessor(BaseDocumentProcessor):
    """Processor for documents that can be converted via Pandoc"""
    
    @classmethod
    def get_supported_extensions(cls) -> List[str]:
        """Return the file extensions supported by this processor"""
        # Pandoc handles many formats, but we'll list the most common ones
        # For a complete list, PandocUtils.is_supported_format() should be used
        return [
            ".docx", ".doc", ".rtf", ".odt", ".epub", 
            ".html", ".htm", ".org", ".tex", ".wiki"
        ]
    
    def process(self, file_path: str, output_dir: str, media_dir: str) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Process document using Pandoc
        
        Args:
            file_path (str): Path to document
            output_dir (str): Directory for temporary files
            media_dir (str): Directory for media files
            
        Returns:
            tuple: (markdown_content, metadata_dict)
        """
        logger.info(f"Processing with Pandoc: {os.path.basename(file_path)}")
        
        # Prepare output filename
        basename = os.path.splitext(os.path.basename(file_path))[0]
        md_filename = f"{basename}.md"
        
        # Configure Pandoc options
        pandoc_options = {
            "images": "separate",
            "standalone": True,
            "toc": self.config.get("pandoc_toc", False),
            # Pass through image download timeout settings
            "limit_image_download": self.config.get("limit_image_download", False),
            "image_download_timeout": self.config.get("image_download_timeout", 120)
        }
        
        try:
            # Convert file using Pandoc
            converted_md_path = PandocUtils.convert_file(
                file_path, 
                output_dir, 
                md_filename, 
                options=pandoc_options
            )
            
            if not converted_md_path:
                return None, {
                    "error": "Pandoc conversion failed (MD not generated)",
                    **self.get_metadata_base(file_path, "pandoc")
                }
            
            # Read converted markdown
            with open(converted_md_path, 'r', encoding='utf-8', errors='ignore') as f:
                md_content = f.read()
                
            # Extract metadata from markdown content
            metadata = self.get_metadata_base(file_path, "pandoc")
            
            # Try to extract title from YAML frontmatter if present
            match = re.search(r"^---\s*\ntitle:\s*(.*?)\n", md_content, re.MULTILINE | re.DOTALL)
            if match:
                metadata['title'] = match.group(1).strip()
                
            logger.info(f"Pandoc conversion successful for {file_path}")
            
            return md_content, metadata
            
        except Exception as e:
            logger.error(f"Error in Pandoc conversion of {file_path}: {e}", exc_info=True)
            return None, {
                "error": str(e),
                **self.get_metadata_base(file_path, "pandoc")
            }
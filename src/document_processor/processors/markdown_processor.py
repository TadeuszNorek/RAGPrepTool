#!filepath document_processor/processors/markdown_processor.py
import os
import re
import shutil
import logging
from typing import List, Tuple, Dict, Any, Optional
from .base_processor import BaseDocumentProcessor

logger = logging.getLogger(__name__)

class MarkdownProcessor(BaseDocumentProcessor):
    """Processor for Markdown documents"""
    
    @classmethod
    def get_supported_extensions(cls) -> List[str]:
        """Return the file extensions supported by this processor"""
        return [".md", ".markdown"]
    
    def process(self, file_path: str, output_dir: str, media_dir: str) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Process Markdown document, handling local images
        
        Args:
            file_path (str): Path to Markdown file
            output_dir (str): Directory for temporary files
            media_dir (str): Directory for media files
            
        Returns:
            tuple: (markdown_content, metadata_dict)
        """
        logger.info(f"Processing Markdown file: {os.path.basename(file_path)}")
        
        try:
            # Read markdown content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                md_content = f.read()
                
            # Create base metadata
            metadata = self.get_metadata_base(file_path, "md_custom")
            
            # Handle local images
            md_content = self._process_local_images(file_path, md_content, media_dir)
            
            return md_content, metadata
            
        except Exception as e:
            logger.error(f"Error processing Markdown file {file_path}: {e}", exc_info=True)
            return None, {"error": str(e), **self.get_metadata_base(file_path, "md_custom")}
            
    def _process_local_images(self, file_path: str, md_content: str, media_dir: str) -> str:
        """
        Process local images referenced in markdown file
        
        Args:
            file_path (str): Path to markdown file
            md_content (str): Markdown content
            media_dir (str): Directory for media files
            
        Returns:
            str: Updated markdown content with fixed image references
        """
        os.makedirs(media_dir, exist_ok=True)
        updated_links = {}
        
        # Find all image references in markdown
        for match in re.finditer(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s*\"([^\"]*)\")?\)", md_content):
            img_path = match.group(2)
            
            # Skip external and absolute paths
            if img_path.startswith(('http://', 'https://', 'data:')) or os.path.isabs(img_path):
                continue
                
            # Calculate absolute path relative to markdown file
            abs_img_path = os.path.normpath(os.path.join(os.path.dirname(file_path), img_path))
            
            # Check if image exists
            if os.path.exists(abs_img_path) and os.path.isfile(abs_img_path):
                # Create a flattened filename to avoid path issues
                flat_img_name = img_path.replace("../", "").replace("./", "").replace(os.sep, "_")
                name, ext = os.path.splitext(flat_img_name)
                if not ext:
                    flat_img_name += ".png"
                    
                # Copy image to media directory
                dest_path = os.path.join(media_dir, flat_img_name)
                try:
                    shutil.copy(abs_img_path, dest_path)
                    # Create new reference path
                    new_link = os.path.join("media", flat_img_name).replace("\\", "/")
                    updated_links[img_path] = new_link
                    logger.info(f"Copied local image '{img_path}' to media folder, new link: '{new_link}'")
                except Exception as e:
                    logger.error(f"Failed to copy image {abs_img_path}: {e}")
            else:
                logger.warning(f"Local image not found: {abs_img_path}")
                
        # Update markdown with new image references
        if updated_links:
            for orig_link, new_link in sorted(updated_links.items(), key=lambda x: len(x[0]), reverse=True):
                # Replace in markdown image syntax
                escaped_orig = re.escape(orig_link)
                md_content = re.sub(
                    r"!\[([^\]]*)\]\(" + escaped_orig + r"(\s*\"(?:[^\"]*)\")?\)",
                    r"![\1](" + new_link + r"\2)",
                    md_content
                )
                
                # Also replace in HTML img tags
                img_tag_pattern = re.compile(
                    r"(<img\s+[^>]*?src\s*=\s*)(['\"])" + escaped_orig + r"\2([^>]*?>)", 
                    re.IGNORECASE
                )
                md_content = img_tag_pattern.sub(r"\1\2" + new_link + r"\2\3", md_content)
                
        return md_content
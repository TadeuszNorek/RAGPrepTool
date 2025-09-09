#!filepath document_processor/processors/pdf_processor.py
import os
import fitz
import pymupdf4llm
import gc
import logging
import shutil
import time
from typing import List, Tuple, Dict, Any, Optional
from .base_processor import BaseDocumentProcessor
from ..utils.image_utils import ImageProcessor

logger = logging.getLogger(__name__)

class PDFProcessor(BaseDocumentProcessor):
    """Processor for PDF documents"""
    
    @classmethod
    def get_supported_extensions(cls) -> List[str]:
        """Return the file extensions supported by this processor"""
        return [".pdf"]
    
    @classmethod
    def can_process(cls, file_path: str) -> bool:
        """PDF specific filtering"""
        if not super().can_process(file_path):
            return False
        
        # PDF-specific checks
        # if os.path.getsize(file_path) > 500_000_000:  # Skip huge PDFs
        #     logger.debug(f"Skipping large PDF: {os.path.basename(file_path)}")
        #     return False
        
        return True
    
    def process(self, file_path: str, output_dir: str, media_dir: str) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Process PDF document and convert to markdown
        
        Args:
            file_path (str): Path to PDF file
            output_dir (str): Directory for temporary files
            media_dir (str): Directory for media files
            
        Returns:
            tuple: (markdown_content, metadata_dict)
        """
        logger.info(f"Processing PDF: {os.path.basename(file_path)}")
        
        # Create temporary directory for raw extracted images
        temp_images_dir = os.path.join(output_dir, "pdf_pymupdf_temp_raw_images")
        os.makedirs(temp_images_dir, exist_ok=True)
        
        try:
            # Extract content and metadata from PDF
            md_content, raw_images, metadata = self._extract_pdf_content(file_path, temp_images_dir)
            
            if not md_content:
                return None, {"error": "Failed to extract PDF content", **self.get_metadata_base(file_path, "pdf_pymupdf4llm")}
            
            # Process extracted images and update markdown
            image_processor = ImageProcessor(self.config.to_dict())
            processed_images_info = image_processor.process_pdf_images(raw_images, media_dir)
            md_content = image_processor.update_markdown_with_processed_images(md_content, processed_images_info)
            
            return md_content, metadata
            
        except Exception as e:
            logger.error(f"Error processing PDF {file_path}: {e}", exc_info=True)
            return None, {"error": str(e), **self.get_metadata_base(file_path, "pdf_pymupdf4llm")}
        finally:
            # Clean up temporary files
            self._cleanup_temp_files(temp_images_dir)
    
    def _extract_pdf_content(self, file_path: str, temp_images_dir: str) -> Tuple[Optional[str], Dict[str, Any], Dict[str, Any]]:
        """
        Extract content and metadata from PDF file
        
        Args:
            file_path (str): Path to PDF file
            temp_images_dir (str): Directory for temporarily extracted images
            
        Returns:
            tuple: (markdown_content, raw_images_dict, metadata_dict)
        """
        raw_images = {}
        
        try:
            doc: Any = fitz.open(file_path)
            try:
                # Extract metadata
                metadata = {k: str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v 
                           for k, v in doc.metadata.items()}
                metadata.update(self.get_metadata_base(file_path, "pdf_pymupdf4llm"))
                
                # Convert to markdown
                md_content = pymupdf4llm.to_markdown(
                    doc, 
                    write_images=True, 
                    embed_images=False,
                    image_path=temp_images_dir
                )
            finally:
                doc.close()
            
            # Collect extracted images
            if os.path.exists(temp_images_dir):
                for img_filename in os.listdir(temp_images_dir):
                    img_path = os.path.join(temp_images_dir, img_filename)
                    try:
                        with open(img_path, "rb") as f:
                            img_bytes = f.read()
                        
                        placeholder_id = img_path.replace("\\", "/")
                        raw_images[placeholder_id] = {
                            'bytes': img_bytes, 
                            'filename_suggestion': img_filename
                        }
                    except Exception as e:
                        logger.warning(f"Could not read raw PDF image {img_path}: {e}")
            
            # Apply minor text fixes
            if md_content:
                md_content = md_content.replace(' \" **;**', '"**;**')
            
            return md_content, raw_images, metadata
            
        except Exception as e:
            logger.error(f"Failed to extract content from PDF {file_path}: {e}", exc_info=True)
            return None, {}, {"error": str(e), **self.get_metadata_base(file_path, "pdf_pymupdf4llm")}
    
    def _cleanup_temp_files(self, directory: str) -> None:
        """
        Clean up temporary files safely
        
        Args:
            directory (str): Directory to clean up
        """
        if not os.path.exists(directory):
            return
        
        # Force garbage collection to release file handles
        gc.collect()
        
        # Try multiple times with delays
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                # Small delay to allow resources to be released
                if attempt > 0:
                    time.sleep(1)
                    
                shutil.rmtree(directory)
                logger.info(f"Removed temporary directory: {directory}")
                break
            except PermissionError:
                if attempt == max_attempts - 1:
                    logger.warning(f"Could not remove temporary directory after {max_attempts} attempts: {directory}")
            except Exception as e:
                logger.warning(f"Error removing temporary directory {directory}: {e}")
                break

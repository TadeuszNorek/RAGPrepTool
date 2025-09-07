#!filepath document_processor/rag_converter.py
import os
import shutil
import logging
import re
import gc
import time
from typing import Callable, Optional, List, Union, Dict, Any
from .config import ConverterConfig
from .processors.processor_factory import DocumentProcessorFactory
from .utils.file_utils import FileUtils, TempDirectory, safe_remove_directory
from .utils.pandoc_utils import PandocUtils

logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class RAGConverter:
    """Main converter class for document processing and packaging"""
    
    def __init__(self, config: Union[Dict[str, Any], ConverterConfig], 
                 status_callback: Optional[Callable[[str], None]] = None, 
                 progress_callback: Optional[Callable[[float], None]] = None) -> None:
        """
        Initialize the RAG converter
        
        Args:
            config (dict or ConverterConfig): Configuration for conversion
            status_callback (callable, optional): Function to call with status updates
            progress_callback (callable, optional): Function to call with progress updates
        """
        self.config = config if isinstance(config, ConverterConfig) else ConverterConfig(config)
        self.status_callback = status_callback
        self.progress_callback = progress_callback
        
        # Pass our status callback to PandocUtils so it can update the UI directly when external images are found
        PandocUtils.status_callback = status_callback
        
        logger.info(f"RAGConverter initialized. Pandoc available: {PandocUtils.check_installed_locally()}")
    
    def _update_status(self, message: str) -> None:
        """Update status via callback if available"""
        if self.status_callback:
            self.status_callback(message)
    
    def _update_progress(self, value: float) -> None:
        """Update progress via callback if available"""
        if self.progress_callback:
            self.progress_callback(value)
    
    def process_file_and_package(self, file_path: str, temp_extraction_dir: str, 
                               common_media_dir: str, md_filename_in_zip: str, 
                               zip_filepath_abs: str) -> bool:
        """
        Process a single file and package results into a ZIP
        
        Args:
            file_path (str): Path to source file
            temp_extraction_dir (str): Directory for temporary extraction
            common_media_dir (str): Directory for media files
            md_filename_in_zip (str): Name of markdown file in ZIP
            zip_filepath_abs (str): Path for output ZIP file
            
        Returns:
            bool: True if processing and packaging succeeded
        """
        original_filename = os.path.basename(file_path)
        
        # Get appropriate processor for the file type
        processor = DocumentProcessorFactory.create_processor(file_path, self.config)
        
        # Process the file
        md_content, doc_metadata = processor.process(file_path, temp_extraction_dir, common_media_dir)
        
        if md_content is None:
            self._update_status(f"Failed to process {original_filename}.")
            return False
        
        # Write markdown content to file
        md_filepath_abs = os.path.join(temp_extraction_dir, md_filename_in_zip)
        try:
            with open(md_filepath_abs, "w", encoding="utf-8") as f:
                f.write(md_content)
        except Exception as e:
            logger.error(f"Failed to write MD file {md_filepath_abs}: {e}", exc_info=True)
            return False
        
        # Write metadata to file
        metadata_filepath_abs = os.path.join(temp_extraction_dir, "metadata.json")
        FileUtils.save_metadata(doc_metadata, metadata_filepath_abs)
        
        # Clean up directory structure before packaging
        media_parent_dir = os.path.dirname(common_media_dir)
        FileUtils.cleanup_nested_media_folders(media_parent_dir)
        
        # Create the ZIP package
        return FileUtils.create_zip_package(
            zip_filepath_abs,
            md_filepath_abs, 
            md_filename_in_zip,
            metadata_filepath_abs,
            common_media_dir
        )

    def process_folder(self, input_folder_path: str, output_base_path: str, output_filename_suffix: str = "") -> None:
        """
        Process all supported files in a folder
        
        Args:
            input_folder_path (str): Path to input folder containing documents
            output_base_path (str): Path for output files
            output_filename_suffix (str, optional): Suffix for output filenames
        """
        logger.info(f"process_folder started. Input: {input_folder_path}, Output: {output_base_path}, Suffix: '{output_filename_suffix}'")
        
        # Find all supported files
        files_to_process = self._find_supported_files(input_folder_path)
        
        if not files_to_process:
            self._update_status("No supported files found.")
            return
        
        self._update_status(f"Found {len(files_to_process)} supported files.")
        os.makedirs(output_base_path, exist_ok=True)
        
        # Process each file
        total_files = len(files_to_process)
        for i, file_path in enumerate(files_to_process):
            original_filename = os.path.basename(file_path)
            self._update_status(f"Starting {original_filename} ({i+1}/{total_files})...")
            
            # Reset external image flags before processing
            PandocUtils.last_file_had_external_images = False
            PandocUtils.last_file_external_image_count = 0
            
            # Generate output paths
            base_name_no_ext = os.path.splitext(original_filename)[0]
            zip_name_base = f"{base_name_no_ext}_{output_filename_suffix}" if output_filename_suffix else base_name_no_ext
            md_filename_in_zip = f"{zip_name_base}.md"
            temp_dir_path = os.path.join(output_base_path, f"{zip_name_base}_temp")
            zip_filepath_abs = os.path.join(output_base_path, f"{zip_name_base}.zip")
            
            # Create temporary directory
            with TempDirectory(temp_dir_path, auto_remove=False) as temp_dir:
                # Create media directory
                common_media_dir = os.path.join(temp_dir, "media") 
                os.makedirs(common_media_dir, exist_ok=True) 
                
                # Process file and create ZIP
                success = self.process_file_and_package(
                    file_path, 
                    temp_dir, 
                    common_media_dir, 
                    md_filename_in_zip, 
                    zip_filepath_abs
                )
                
                if success:
                    self._update_status(f"Successfully processed {original_filename}")
                else:
                    self._update_status(f"Failed to process {original_filename}")
                
            # Clean up temporary directory
            safe_remove_directory(temp_dir_path)
            
            # Update progress
            self._update_progress((i + 1) / total_files * 100)
          # Final cleanup of any remaining temporary directories
        self._cleanup_remaining_temp_dirs(output_base_path)
        self._update_status("Batch processing complete.")
    
    def _find_supported_files(self, folder_path: str) -> List[str]:
        """Find all supported files in folder"""
        files_to_process = []
        
        # Get all supported extensions from registered processors
        supported_exts = DocumentProcessorFactory.get_all_supported_extensions()
        
        # Add Pandoc-supported formats if available
        pandoc_available = PandocUtils.check_installed_locally()
        
        for f_name in os.listdir(folder_path):
            f_path = os.path.join(folder_path, f_name)
            if not os.path.isfile(f_path):
                continue
                
            ext = os.path.splitext(f_name)[1].lower()
            
            # Check if extension is directly supported
            if ext in supported_exts:
                files_to_process.append(f_path)
                logger.info(f"Found supported file: {f_name} (processor: {supported_exts[ext].__name__})")
            # Check if Pandoc supports it
            elif pandoc_available and PandocUtils.is_supported_format(f_path):
                files_to_process.append(f_path)
                logger.info(f"Found Pandoc-supported file: {f_name}")
            else:
                logger.info(f"Skipping unsupported file: {f_name} (ext: {ext})")
        
        return files_to_process
    
    def _cleanup_remaining_temp_dirs(self, output_path: str) -> None:
        """Clean up any remaining temporary directories"""
        try:
            temp_dirs = [
                os.path.join(output_path, d) for d in os.listdir(output_path) 
                if d.endswith("_temp") and os.path.isdir(os.path.join(output_path, d))
            ]
            
            for temp_dir in temp_dirs:
                safe_remove_directory(temp_dir)
                
        except Exception as e:
            logger.warning(f"Error during final cleanup: {e}")
    
    def cleanup_temp_files(self, directory: str) -> None:
        """Clean up temporary files at application shutdown"""
        gc.collect()  # Force garbage collection
        
        # Give processes time to release file handles
        time.sleep(2)
        
        safe_remove_directory(directory)
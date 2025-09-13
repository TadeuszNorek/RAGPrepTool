import os
import shutil
import gc
import time
import logging
import json
from typing import Dict, Any, Optional, Type

logger = logging.getLogger(__name__) 

def safe_remove_directory(directory: str, max_attempts: int = 3, delay: int = 1) -> bool:
    """
    Safely remove a directory with multiple attempts
    
    Args:
        directory (str): Directory path to remove
        max_attempts (int): Maximum number of removal attempts
        delay (int): Seconds to wait between attempts
        
    Returns:
        bool: True if directory was removed or didn't exist, False otherwise
    """
    if not os.path.exists(directory):
        return True
        
    gc.collect()  # Force garbage collection to release file handles
    
    for attempt in range(max_attempts):
        try:
            if attempt > 0:
                time.sleep(delay)
            shutil.rmtree(directory)
            logger.info(f"Successfully removed directory: {directory}")
            return True
        except PermissionError:
            logger.info(f"Permission error removing {directory}, attempt {attempt+1}/{max_attempts}")
            continue
        except Exception as e:
            logger.error(f"Error removing directory {directory}: {e}")
            return False
    
    logger.warning(f"Could not remove directory after {max_attempts} attempts: {directory}")
    return False

class TempDirectory:
    """Context manager for temporary directory handling"""
    
    def __init__(self, path: str, auto_remove: bool = True) -> None:
        """
        Initialize temporary directory manager
        
        Args:
            path (str): Directory path
            auto_remove (bool): Whether to automatically remove the directory on exit
        """
        self.path = path
        self.auto_remove = auto_remove
    
    def __enter__(self) -> str:
        """Create the directory and return its path"""
        os.makedirs(self.path, exist_ok=True)
        return self.path
    
    def __exit__(self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[Any]) -> None:
        """Clean up directory if auto_remove is True"""
        if self.auto_remove:
            safe_remove_directory(self.path)

class FileUtils:
    """Utility class for file operations"""
    
    @staticmethod
    def cleanup_nested_media_folders(output_dir: str) -> None:
        """
        Clean up directory structure by handling nested media folders
        
        Args:
            output_dir (str): Parent directory containing media folder
        """
        media_dir = os.path.join(output_dir, "media")
        if not (os.path.exists(media_dir) and os.path.isdir(media_dir)):
            return
            
        nested_media = os.path.join(media_dir, "media")
        if not (os.path.exists(nested_media) and os.path.isdir(nested_media)):
            return
            
        logger.info(f"Found nested media folder, reorganizing: {nested_media}")
        
        # Track files we've already moved
        existing_files = set(os.listdir(media_dir))
        
        # Move files from nested media to parent media
        for filename in os.listdir(nested_media):
            src_path = os.path.join(nested_media, filename)
            
            # Skip files that already exist in parent media folder
            if filename in existing_files:
                logger.info(f"Skipping duplicate file: {filename}")
                try:
                    os.remove(src_path)  # Remove duplicate in nested folder
                except Exception as e:
                    logger.warning(f"Failed to remove duplicate {src_path}: {e}")
                continue
            
            # Move unique files
            dest_path = os.path.join(media_dir, filename)
            try:
                shutil.move(src_path, dest_path)
                existing_files.add(filename)  # Track that we've moved this file
            except Exception as e:
                logger.warning(f"Failed to move {src_path}: {e}")
        
        # Remove the now-empty nested media folder
        try:
            if os.path.exists(nested_media) and not os.listdir(nested_media):
                os.rmdir(nested_media)
                logger.info("Removed empty nested media folder")
        except Exception as e:
            logger.warning(f"Failed to remove nested media folder: {e}")
    
    @staticmethod
    def save_metadata(metadata: Dict[str, Any], filepath: str) -> bool:
        """Save metadata to JSON file"""
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=4)
            return True
        except Exception as e:
            logger.error(f"Failed to write metadata to {filepath}: {e}")
            return False
    
    @staticmethod
    def create_zip_package(zip_filepath: str, markdown_filepath: str, markdown_arcname: str, 
                         metadata_filepath: Optional[str] = None, media_folder: Optional[str] = None) -> bool:
        """
        Create a ZIP package with markdown, metadata, and media files
        
        Args:
            zip_filepath (str): Output ZIP file path
            markdown_filepath (str): Path to markdown file to include
            markdown_arcname (str): Name of markdown file within ZIP
            metadata_filepath (str, optional): Path to metadata file
            media_folder (str, optional): Path to media folder
            
        Returns:
            bool: True if packaging was successful, False otherwise
        """
        import zipfile
        
        # First, check if the essential markdown file exists.
        if not (os.path.exists(markdown_filepath) and os.path.getsize(markdown_filepath) > 0):
            logger.error(f"Markdown file {markdown_filepath} is missing or empty. ZIP package will not be created.")
            return False

        logger.info(f"Creating ZIP package: {zip_filepath}")
        try:
            with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
                # Add markdown file
                zf.write(markdown_filepath, arcname=markdown_arcname)
                
                # Add metadata if available
                if metadata_filepath and os.path.exists(metadata_filepath):
                    zf.write(metadata_filepath, arcname="metadata.json")
                
                # Add media files if available
                media_count = 0
                if media_folder and os.path.exists(media_folder) and os.path.isdir(media_folder):
                    logger.info(f"Adding media from: {media_folder}")
                    for root, _, files in os.walk(media_folder):
                        for file in files:
                            full_path = os.path.join(root, file)
                            rel_path = os.path.join("media", os.path.relpath(full_path, media_folder))
                            zf.write(full_path, arcname=rel_path.replace("\\", "/"))
                            media_count += 1
                    
                    if media_count > 0:
                        logger.info(f"Added {media_count} media files to zip")
            
            logger.info(f"ZIP package created successfully: {zip_filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to create ZIP package: {e}", exc_info=True)
            # If something fails during zipping, ensure the partial zip is removed
            if os.path.exists(zip_filepath):
                os.remove(zip_filepath)
            return False

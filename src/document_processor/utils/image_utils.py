#!filepath document_processor/utils/image_utils.py
import os
import io
import base64
import re
import logging
from typing import Dict, Any, Optional
from PIL import Image, UnidentifiedImageError

logger = logging.getLogger(__name__)

class ImageProcessor:
    """Utility class for processing and managing images"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the image processor with config
        
        Args:
            config: Configuration object or dict with image processing settings
        """
        self.config = config
    
    def process_image(self, image_bytes: bytes, filename_suggestion: Optional[str] = None) -> Dict[str, Any]:
        """
        Process an image according to configuration
        
        Args:
            image_bytes (bytes): Raw image data
            filename_suggestion (str, optional): Suggested filename
            
        Returns:
            dict: Processing results including:
                - action: What to do with the image ("save", "embed", "remove")
                - bytes: Processed image bytes (if applicable)
                - format: Image format (if applicable)
                - data_uri: Base64 data URI (if embedded)
        """
        result = {
            "action": "save",
            "bytes": image_bytes,
            "format": "PNG"
        }
        
        try:
            img = Image.open(io.BytesIO(image_bytes))
            
            # Determine format for saving
            if filename_suggestion:
                ext = os.path.splitext(filename_suggestion)[1].lower()
                save_format = "JPEG" if ext in [".jpg", ".jpeg"] else "PNG"
            else:
                save_format = "PNG"
                
            # Ensure RGB mode for JPEGs
            if save_format == "JPEG" and img.mode != "RGB":
                img = img.convert("RGB")
            
            result["format"] = save_format
            
            # Check if image is decorative (too small)
            if self.config.get("exclude_decorative") and self.config.get("decorative_threshold_px", 0) > 0:
                threshold = self.config.get("decorative_threshold_px")
                if img.width < threshold and img.height < threshold:
                    logger.info(f"Excluding decorative image: {filename_suggestion or 'unnamed'}")
                    result["action"] = "remove"
                    return result
            
            # Resize if needed
            if self.config.get("apply_max_res") and self.config.get("max_image_res_px", 0) > 0:
                max_dim = self.config.get("max_image_res_px")
                if img.width > max_dim or img.height > max_dim:
                    img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
                    logger.info(f"Resized image to max dimension {max_dim}px")
            
            # Save processed image to bytes
            output = io.BytesIO()
            img.save(output, format=save_format)
            result["bytes"] = output.getvalue()
            
            # Check if image should be embedded
            if self.config.get("embed_small_images") and self.config.get("small_image_threshold_kb", 0) > 0:
                threshold_bytes = self.config.get("small_image_threshold_kb") * 1024
                if len(result["bytes"]) < threshold_bytes:
                    logger.info(f"Embedding small image: {filename_suggestion or 'unnamed'}")
                    img_fmt = save_format.lower()
                    b64_data = base64.b64encode(result["bytes"]).decode("utf-8")
                    result["action"] = "embed"
                    result["data_uri"] = f"data:image/{img_fmt};base64,{b64_data}"
            
            return result
            
        except UnidentifiedImageError:
            logger.warning(f"Could not identify image format: {filename_suggestion or 'unnamed'}")
            return result  # Return original bytes
        except Exception as e:
            logger.warning(f"Error processing image: {e}")
            return result  # Return original bytes
    
    def process_pdf_images(self, raw_images_data: Dict[str, Any], output_dir: str) -> Dict[str, Any]:
        """
        Process images extracted from PDF
        
        Args:
            raw_images_data (dict): Dictionary of raw image data
            output_dir (str): Directory to save processed images
            
        Returns:
            dict: Information about processed images for markdown updating
        """
        logger.info(f"Processing {len(raw_images_data)} images extracted from PDF")
        if not raw_images_data:
            return {}
            
        os.makedirs(output_dir, exist_ok=True)
        processed_images_info = {}
        
        for placeholder_path, img_info in raw_images_data.items():
            img_bytes = img_info['bytes']
            suggested_name = img_info.get('filename_suggestion', os.path.basename(placeholder_path))
            
            # Get base filename and ensure proper extension
            base_name, ext = os.path.splitext(suggested_name)
            if not ext.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']:
                ext = '.png'
            final_name = f"{base_name}{ext}"
            
            # Process the image
            result = self.process_image(img_bytes, final_name)
            
            if result["action"] == "remove":
                processed_images_info[placeholder_path] = {"action": "remove"}
            elif result["action"] == "embed":
                processed_images_info[placeholder_path] = {
                    "action": "embed", 
                    "data": result["data_uri"]
                }
            else:  # save
                save_format = result["format"]
                final_name = f"{base_name}.{save_format.lower()}"
                final_path = os.path.join(output_dir, final_name)
                
                with open(final_path, "wb") as f:
                    f.write(result["bytes"])
                
                relative_path = os.path.join("media", final_name).replace("\\", "/")
                processed_images_info[placeholder_path] = {
                    "action": "relink", 
                    "new_path": relative_path
                }
                
        return processed_images_info
    
    def update_markdown_with_processed_images(self, md_content: str, processed_images_info: Dict[str, Any]) -> str:
        """
        Update markdown content with processed image information
        
        Args:
            md_content (str): Original markdown content
            processed_images_info (dict): Information about processed images
            
        Returns:
            str: Updated markdown content
        """
        if not processed_images_info:
            return md_content
            
        # Sort by length descending to handle longer paths first (avoiding partial replacements)
        sorted_placeholders = sorted(processed_images_info.keys(), key=len, reverse=True)
        temp_content = md_content
        
        for placeholder in sorted_placeholders:
            info = processed_images_info[placeholder]
            escaped_placeholder = re.escape(placeholder)
            pattern = re.compile(r"!\[([^\]]*)\]\(" + escaped_placeholder + r"(\s*\"(?:[^\"]*)\")?\)")
            
            if info["action"] == "remove":
                replacement = ""
                action_desc = "REMOVED"
            elif info["action"] == "embed":
                replacement = r"![\1](" + info["data"] + r"\2)"
                action_desc = "EMBEDDED"
            elif info["action"] == "relink":
                replacement = r"![\1](" + info["new_path"] + r"\2)"
                action_desc = f"RELINKED to {info['new_path']}"
            else:
                continue  # Skip if action is not recognized
                
            new_content, count = pattern.subn(replacement, temp_content)
            if count > 0:
                logger.info(f"Image MD replacement: {count} instance(s) of '{placeholder}' -> {action_desc}")
            temp_content = new_content
            
        return temp_content
#!filepath document_processor/utils/pandoc_utils.py
import os
import re
import logging
import pypandoc
from typing import List, Dict, Any, Optional, Callable

logger = logging.getLogger(__name__)

class PandocUtils:
    """Utilities for Pandoc operations"""
    
    _pandoc_installed: Optional[bool] = None
    last_file_had_external_images: bool = False
    last_file_external_image_count: int = 0
    status_callback: Optional[Callable[[str], None]] = None
    
    @classmethod
    def check_installed_locally(cls) -> bool:
        """Checks if Pandoc is installed and accessible via pypandoc."""
        if cls._pandoc_installed is not None:
            return cls._pandoc_installed
            
        try:
            version = pypandoc.get_pandoc_version()
            logger.info(f"Pandoc version {version} detected.")
            cls._pandoc_installed = True
        except Exception:
            logger.warning("Pandoc executable not found or pypandoc is not properly configured. Some file conversions may be unavailable.")
            cls._pandoc_installed = False
        return cls._pandoc_installed

    @classmethod
    def is_supported_format(cls, file_path: str) -> bool:
        """Checks if the file format is generally supported by Pandoc for conversion to Markdown."""
        if not cls.check_installed_locally():
            return False
            
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        supported_by_pandoc_for_us = [
            '.docx', '.odt', '.epub', '.html', '.htm', '.rtf',
            '.tex', '.xml', '.csv', '.tsv', '.opml', '.org'
        ]
        return ext in supported_by_pandoc_for_us
    
    @staticmethod
    def fix_table_captions(content: str) -> str:
        """Applies specific regex fix for table captions from Pandoc output."""
        pattern = r'(\n\n): \[\]\{.*?\}(Tabela[^\n]+)'
        replacement = r'\n\n**\2**'
        return re.sub(pattern, replacement, content)
    
    @staticmethod
    def fix_md_media_paths(md_file_path: str) -> None:
        """Fix any incorrect media paths in the final markdown file"""
        try:
            with open(md_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Replace incorrect double media references
            if 'media/media/' in content:
                content = content.replace('media/media/', 'media/')
                logger.info(f"Fixed double media references in markdown file")
                
                with open(md_file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
        except Exception as e:
            logger.warning(f"Failed to fix media paths in markdown: {e}")
    
    @classmethod
    def convert_file(cls, input_file: str, output_dir_for_md: str, md_filename_itself: str, options: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Converts a file to Markdown using Pandoc.
        
        Args:
            input_file (str): Path to input file
            output_dir_for_md (str): Output directory for Markdown and media
            md_filename_itself (str): Filename for the output Markdown file
            options (dict, optional): Options for conversion
            
        Returns:
            str: Path to generated Markdown file or None if conversion failed
        """
        from .image_utils import ImageProcessor  # Import here to avoid circular imports
        
        if options is None: 
            options = {}
            
        output_md_file_abs = os.path.join(output_dir_for_md, md_filename_itself)
        extra_args = ["--wrap=none", "--columns=1000", "--markdown-headings=atx", "--log=pandoc_log.txt"]
        markdown_format = "gfm"
        pandoc_media_output_subfolder_name = "media"

        media_dir = os.path.join(output_dir_for_md, pandoc_media_output_subfolder_name)
        os.makedirs(media_dir, exist_ok=True)
        
        input_file_to_use = cls._predownload_external_images(input_file, media_dir, options=options)

        if options.get("images") == "separate":
            # Pandoc's CWD will be output_dir_for_md, so "media" is relative to that.
            extra_args.append(f"--extract-media={pandoc_media_output_subfolder_name}")
        elif options.get("images") == "embed":
            extra_args.append("--self-contained")
        
        if options.get("toc"): extra_args.append("--toc")
        if options.get("standalone"): extra_args.append("--standalone")
        
        try:
            logger.info(f"Pandoc converting {os.path.basename(input_file_to_use)} to {md_filename_itself} in {output_dir_for_md}")
            os.makedirs(os.path.dirname(output_md_file_abs), exist_ok=True)
            
            pypandoc.convert_file(
                input_file_to_use,
                markdown_format,
                outputfile=output_md_file_abs,
                extra_args=extra_args,
                cworkdir=output_dir_for_md # Set Pandoc's CWD
            )
            
            if not os.path.exists(output_md_file_abs):
                logger.error(f"Pandoc call completed but output MD file NOT FOUND: {output_md_file_abs}")
                return None
            logger.info(f"Pandoc output MD file successfully created: {output_md_file_abs}")
            cls.fix_md_media_paths(output_md_file_abs)

            if input_file_to_use.endswith('.modified.html') and input_file_to_use != input_file:
                try:
                    os.remove(input_file_to_use)
                    logger.info(f"Cleaned up temporary HTML file: {input_file_to_use}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to clean up temp file {input_file_to_use}: {cleanup_error}")
            
            if options.get("images") == "separate":
                expected_media_dir = os.path.join(output_dir_for_md, pandoc_media_output_subfolder_name)
                if os.path.exists(expected_media_dir) and os.path.isdir(expected_media_dir):
                    logger.info(f"Pandoc media directory found: {expected_media_dir} with {len(os.listdir(expected_media_dir))} items.")
                else:
                    logger.info(f"Pandoc media directory not created: {expected_media_dir} (OK if no images in source).")

            with open(output_md_file_abs, 'r', encoding='utf-8', errors='ignore') as file: 
                content = file.read()
            content = cls.fix_table_captions(content)
            with open(output_md_file_abs, 'w', encoding='utf-8') as file: 
                file.write(content)
                
            return output_md_file_abs
        except Exception as e:
            logger.error(f"Error during Pandoc conversion of {input_file_to_use}: {e}", exc_info=True)
            if input_file_to_use.endswith('.modified.html') and input_file_to_use != input_file:
                try:
                    os.remove(input_file_to_use)
                except:
                    pass
            return None
    @classmethod
    def _predownload_external_images(cls, input_file: str, media_dir: str, options: Optional[Dict[str, Any]] = None) -> str:
        """Pre-download external images in HTML files and replace URLs with local paths."""
        # Only process HTML files
        if not input_file.lower().endswith(('.html', '.htm')):
            return input_file
            
        try:
            from bs4 import BeautifulSoup
            import requests
            import hashlib
            import concurrent.futures
            
            if not os.path.exists(input_file):
                logger.warning(f"Input file does not exist: {input_file}")
                return input_file
                
            os.makedirs(media_dir, exist_ok=True)
            logger.info(f"Pre-downloading external images for {input_file}")
            
            # Parse HTML
            with open(input_file, 'r', encoding='utf-8', errors='replace') as f:
                html_content = f.read()
                
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find all external image URLs and store in a more efficient structure
            image_urls = []
            img_elements_map = {}  # Map URLs to LISTS of HTML elements
            
            for img in soup.find_all('img'):
                src = img.get('src', '')
                if src and src.startswith(('http://', 'https://')):
                    image_urls.append(src)
                    # Create a list for each URL if it doesn't exist
                    if src not in img_elements_map:
                        img_elements_map[src] = []
                    # Add this element to the list for its URL
                    img_elements_map[src].append(img)
            
            if not image_urls:
                logger.info("No external images found in HTML file")
                return input_file
            
            # Use set() to get unique URLs for download (avoid duplicates)
            unique_urls = list(set(image_urls))
            logger.info(f"Found {len(image_urls)} external images ({len(unique_urls)} unique URLs) to download")
            
            # Set flags to indicate external images were found - for status notifications
            cls.last_file_had_external_images = True
            cls.last_file_external_image_count = len(image_urls)
            
            # Update status message if callback is provided
            if cls.status_callback and callable(cls.status_callback):
                filename = os.path.basename(input_file)
                cls.status_callback(f"Processing {filename}... \nFile contains {len(image_urls)} external image(s). Processing may take longer than usual.")
            
            # Get timeout from options if provided
            options = options or {}
            timeout = None
            if options.get('limit_image_download', True):  # Default to True for backwards compatibility
                timeout = options.get('image_download_timeout', 90)  # Default 90 seconds
                logger.info(f"Using configured image download timeout: {timeout} seconds")
            
            # Download images in parallel
            downloaded_images = cls._download_images_parallel(unique_urls, media_dir, timeout=timeout)
            
            # Update HTML with downloaded image references
            modified = False
            total_replaced = 0
            
            for url, img_elements_list in img_elements_map.items():
                if url in downloaded_images:
                    # Update ALL occurrences of this URL
                    for img_element in img_elements_list:
                        img_element['src'] = downloaded_images[url]
                        total_replaced += 1
                    modified = True
                    logger.info(f"Updated {len(img_elements_list)} image references: {url} → {downloaded_images[url]}")
            
            # If we modified the HTML, write a new file
            if modified:
                modified_html = os.path.join(os.path.dirname(media_dir), 
                                        os.path.basename(input_file) + ".modified.html")
                try:
                    with open(modified_html, 'w', encoding='utf-8') as f:
                        f.write(str(soup))
                    logger.info(f"Created modified HTML with {total_replaced} local image references at {modified_html}")
                    if os.path.exists(modified_html):
                        return modified_html
                    else:
                        logger.warning(f"Modified HTML file was not created: {modified_html}")
                        return input_file
                except Exception as e:
                    logger.warning(f"Failed to write modified HTML: {e}")
                    return input_file
            else:
                logger.info("No images were successfully downloaded")
                return input_file
                
        except Exception as e:
            logger.warning(f"Image pre-download process failed: {e}", exc_info=True)
            return input_file
    @staticmethod
    def _download_images_parallel(image_urls: List[str], media_dir: str, max_workers: int = 5, timeout: int = 90) -> Dict[str, str]:
        """
        Download multiple images in parallel with timeout controls.
        
        Args:
            image_urls (list): List of image URLs to download
            media_dir (str): Directory to save downloaded images
            max_workers (int): Maximum number of parallel downloads
            timeout (int): Timeout for each download in seconds
            
        Returns:
            dict: Mapping of original URLs to local file paths
        """
        import requests
        import hashlib
        import concurrent.futures
        import time
        
        downloaded = {}
        
        def download_single(url):
            """Download a single image with timeout"""
            start_time = time.time()
            try:
                # Generate filename from URL hash
                img_hash = hashlib.md5(url.encode()).hexdigest()[:12]
                ext = os.path.splitext(url)[1]
                if not ext or len(ext) > 5:  # Handle URLs without extensions or unusual ones
                    ext = '.jpg'
                filename = f"ext_img_{img_hash}{ext}"
                local_path = os.path.join(media_dir, filename)
                
                # Skip if already downloaded
                if os.path.exists(local_path):
                    logger.info(f"Using cached image for: {url}")
                    return url, os.path.join("media", os.path.basename(local_path))
                
                # Download with timeout
                response = requests.get(url, timeout=timeout)
                if response.status_code == 200:
                    with open(local_path, 'wb') as f:
                        f.write(response.content)
                    elapsed = time.time() - start_time
                    logger.info(f"Downloaded: {url} → {filename} ({elapsed:.2f}s)")
                    return url, os.path.join("media", os.path.basename(local_path))
                else:
                    logger.warning(f"Failed to download {url}, status code: {response.status_code}")
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Download timeout for {url} (>{timeout} seconds)")
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed for {url}: {e}")
            except Exception as e:
                logger.warning(f"Error processing {url}: {e}")
                
            return url, None
        
        # Use thread pool for parallel downloads
        max_workers = min(max_workers, len(image_urls))
        
        logger.info(f"Starting parallel download of {len(image_urls)} images with {max_workers} workers")
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all download tasks
            future_to_url = {executor.submit(download_single, url): url for url in image_urls}
            
            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    orig_url, local_path = future.result()
                    if local_path:
                        downloaded[orig_url] = local_path
                except Exception as e:
                    logger.warning(f"Download task failed for {url}: {e}")
        
        logger.info(f"Completed downloads: {len(downloaded)}/{len(image_urls)} successful")
        return downloaded

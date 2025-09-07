# ui.py
import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import logging
from typing import Dict, Any, Optional, TypedDict


class UIConfig(TypedDict):
    embed_small_images: bool
    small_image_threshold_kb: int
    exclude_decorative: bool
    decorative_threshold_px: int
    apply_max_res: bool
    max_image_res_px: int
    limit_image_download: bool
    image_download_timeout: int
# Ensure this import is correct based on your file structure
from document_processor import RAGConverter, PANDOC_INSTALLED, pandoc_is_supported_format_locally
import threading
import sys  # Import sys to help with path for PyInstaller

logger = logging.getLogger(__name__)


def resource_path(relative_path: str) -> str:
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)


class App(ctk.CTk):
    """Main application class for the RAG Prep Tool GUI."""
    def __init__(self) -> None:
        super().__init__()

        self.title("RAG Prep Tool")
        self.geometry("700x640")

        # Initialize converter attribute for static analyzers
        self.converter: Optional[RAGConverter] = None

        try:
            icon_path = resource_path("app_icon.ico")
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
            else:
                logger.warning(f"Window icon not found at {icon_path}")
        except Exception as e:
            logger.error(f"Error setting window icon: {e}")

        # --- WIDGETS INITIALIZATION ---
        self.description_label: ctk.CTkLabel = ctk.CTkLabel(self, text="RAG Prep Tool: Converts files to Markdown (.md) for RAG systems.\n""" \
                                                                              "Input: Select a folder containing supported files.\n""" \
                                                                              "Output: ZIP archives will be created directly in the specified Output Folder Path.\n\n""" \
                                                                              "Support formats like: PDF, DOCX, DOC, PPTX, XLSX, XLS, CSV, TSV, HTML, ODT, RTF, TXT, EPUB, """ \
                                                                              "JSON, MARKDOWN, MD and common source code files.",
                                                                              wraplength=680, justify="left")
        self.description_label.pack(pady=10, padx=10)

        if not PANDOC_INSTALLED:
            self.pandoc_warning_label: ctk.CTkLabel = ctk.CTkLabel(self,
                                                                    text="Warning: Pandoc executable not found or pypandoc issue.\nNon-PDF file conversions may fail or be limited.",
                                                                    text_color="orange", wraplength=680, justify="left")
            self.pandoc_warning_label.pack(pady=(0, 5), padx=10)
        else:
            logger.info("Pandoc integration enabled.")

        self.config_frame: ctk.CTkFrame = ctk.CTkFrame(self)
        self.config_frame.pack(pady=5, padx=10, fill="x")

        self.cb_embed_small_images: ctk.CTkCheckBox = ctk.CTkCheckBox(self.config_frame, text="Embed small images as base64 (PDFs only)")
        self.cb_embed_small_images.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.small_image_kb_label: ctk.CTkLabel = ctk.CTkLabel(self.config_frame, text="Small image threshold (KB):")
        self.small_image_kb_label.grid(row=0, column=1, padx=5, pady=5, sticky="e")
        self.small_image_kb_entry: ctk.CTkEntry = ctk.CTkEntry(self.config_frame, width=50)
        self.small_image_kb_entry.grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.small_image_kb_entry.insert(0, "5")

        self.cb_exclude_decorative: ctk.CTkCheckBox = ctk.CTkCheckBox(self.config_frame, text="Exclude decorative images (PDFs only)")
        self.cb_exclude_decorative.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.decorative_px_label: ctk.CTkLabel = ctk.CTkLabel(self.config_frame, text="Decorative threshold (pixels, W & H <):")
        self.decorative_px_label.grid(row=1, column=1, padx=5, pady=5, sticky="e")
        self.decorative_px_entry: ctk.CTkEntry = ctk.CTkEntry(self.config_frame, width=50)
        self.decorative_px_entry.grid(row=1, column=2, padx=5, pady=5, sticky="w")
        self.decorative_px_entry.insert(0, "50")

        self.cb_apply_max_res: ctk.CTkCheckBox = ctk.CTkCheckBox(self.config_frame, text="Apply max image resolution (PDFs only)")
        self.cb_apply_max_res.grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.max_res_px_label: ctk.CTkLabel = ctk.CTkLabel(self.config_frame, text="Max image resolution (pixels, W/H):")
        self.max_res_px_label.grid(row=2, column=1, padx=5, pady=5, sticky="e")
        self.max_res_px_entry: ctk.CTkEntry = ctk.CTkEntry(self.config_frame, width=50)
        self.max_res_px_entry.grid(row=2, column=2, padx=5, pady=5, sticky="w")
        self.max_res_px_entry.insert(0, "1024")

        self.cb_limit_image_download: ctk.CTkCheckBox = ctk.CTkCheckBox(self.config_frame, text="Set timeout for external images")
        self.cb_limit_image_download.grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.cb_limit_image_download.select()
        self.image_timeout_label: ctk.CTkLabel = ctk.CTkLabel(self.config_frame, text="Download timeout (seconds):")
        self.image_timeout_label.grid(row=3, column=1, padx=5, pady=5, sticky="e")
        self.image_timeout_entry: ctk.CTkEntry = ctk.CTkEntry(self.config_frame, width=50)
        self.image_timeout_entry.grid(row=3, column=2, padx=5, pady=5, sticky="w")
        self.image_timeout_entry.insert(0, "90")

        self.input_folder_path_label: ctk.CTkLabel = ctk.CTkLabel(self, text="Input Folder Path (containing source files):")
        self.input_folder_path_label.pack(pady=(10, 0), padx=10, anchor="w")
        self.input_folder_path_frame: ctk.CTkFrame = ctk.CTkFrame(self)
        self.input_folder_path_frame.pack(fill="x", padx=10, pady=(0, 5))
        self.input_folder_path_entry: ctk.CTkEntry = ctk.CTkEntry(self.input_folder_path_frame, placeholder_text="Select folder with source files...")
        self.input_folder_path_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.select_input_folder_button: ctk.CTkButton = ctk.CTkButton(self.input_folder_path_frame, text="Select Input Folder", command=self.select_input_folder)
        self.select_input_folder_button.pack(side="left")

        self.output_folder_path_label: ctk.CTkLabel = ctk.CTkLabel(self, text="Output Folder Path (ZIP archives will be saved here):")
        self.output_folder_path_label.pack(pady=(10, 0), padx=10, anchor="w")
        self.output_folder_path_frame: ctk.CTkFrame = ctk.CTkFrame(self)
        self.output_folder_path_frame.pack(fill="x", padx=10, pady=(0, 5))
        self.output_folder_path_entry: ctk.CTkEntry = ctk.CTkEntry(self.output_folder_path_frame, placeholder_text="Select folder for outputs (or leave blank for default)...")
        self.output_folder_path_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.select_output_folder_button: ctk.CTkButton = ctk.CTkButton(self.output_folder_path_frame, text="Select Output Folder", command=self.select_output_folder)
        self.select_output_folder_button.pack(side="left")

        self.file_name_label: ctk.CTkLabel = ctk.CTkLabel(self, text="Output File Suffix (optional, appends to original name):")
        self.file_name_label.pack(pady=(5, 0), padx=10, anchor="w")
        self.file_name_entry: ctk.CTkEntry = ctk.CTkEntry(self, placeholder_text="e.g., 'rag_version'")
        self.file_name_entry.pack(fill="x", padx=10, pady=(0, 10))

        self.convert_button: ctk.CTkButton = ctk.CTkButton(self, text="Convert", command=self.start_conversion_thread)
        self.convert_button.pack(pady=20, padx=10, ipady=5)
        self.status_label: ctk.CTkLabel = ctk.CTkLabel(self, text="")
        self.status_label.pack(pady=(0, 5), padx=10)
        self.progress_bar: ctk.CTkProgressBar = ctk.CTkProgressBar(self)
        self.progress_bar.pack(pady=(0, 10), padx=10, fill="x")
        self.progress_bar.set(0)
        
        self.converter: Optional[RAGConverter] = None

    def select_input_folder(self) -> None:
        """Opens a dialog to select the input folder and updates the corresponding entry field."""
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.input_folder_path_entry.delete(0, ctk.END)
            self.input_folder_path_entry.insert(0, folder_selected)

    def select_output_folder(self) -> None:
        """Opens a dialog to select the output folder and updates the corresponding entry field."""
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.output_folder_path_entry.delete(0, ctk.END)
            self.output_folder_path_entry.insert(0, folder_selected)

    def update_status(self, message: str) -> None:
        """Updates the status label with the given message, changing color for external image notifications.

        Args:
            message (str): The status message to display.
        """
        if "external image(s)" in message:
            self.status_label.configure(text=message, text_color="orange")
        else:
            self.status_label.configure(text=message, text_color=("gray10", "gray90"))
        self.update_idletasks()

    def update_progress(self, value: float) -> None:
        """Updates the progress bar with the given value.

        Args:
            value (float): The progress value (0-100).
        """
        self.progress_bar.set(value / 100.0)
        self.update_idletasks()

    def get_config(self) -> Optional[UIConfig]:
        """Retrieves the current configuration settings from the UI elements.

        Returns:
            Optional[UIConfig]: A dictionary containing the configuration settings, or None if validation fails.
        """
        try:
            small_kb = int(self.small_image_kb_entry.get()) if self.small_image_kb_entry.get() else 0
            decorative_px = int(self.decorative_px_entry.get()) if self.decorative_px_entry.get() else 0
            max_res_px = int(self.max_res_px_entry.get()) if self.max_res_px_entry.get() else 0
            image_timeout = int(self.image_timeout_entry.get()) if self.image_timeout_entry.get() else 0
        except ValueError as e:
            logger.error(f"Invalid number in configuration fields: {e}")
            messagebox.showerror("Error", "Invalid number in configuration fields. Please enter valid integers.")
            return None
        
        config: UIConfig = {
            "embed_small_images": self.cb_embed_small_images.get() == 1,
            "small_image_threshold_kb": small_kb,
            "exclude_decorative": self.cb_exclude_decorative.get() == 1,
            "decorative_threshold_px": decorative_px,
            "apply_max_res": self.cb_apply_max_res.get() == 1,
            "max_image_res_px": max_res_px,
            "limit_image_download": self.cb_limit_image_download.get() == 1,
            "image_download_timeout": image_timeout,
        }
        return config

    def start_conversion_thread(self) -> None:
        """Initiates the conversion process in a separate thread to keep the UI responsive.

        Performs input validation and handles Pandoc warnings if necessary.
        """
        input_folder = self.input_folder_path_entry.get()
        output_base_folder = self.output_folder_path_entry.get().strip()

        if not input_folder or not os.path.isdir(input_folder):
            messagebox.showerror("Error", "Please select a valid input folder.")
            return

        if output_base_folder and not os.path.isdir(output_base_folder):
            messagebox.showerror("Error", "The specified output folder path is not a valid directory.")
            return

        if not output_base_folder:
            output_base_folder = input_folder

        config = self.get_config()
        if config is None:
            return
        output_suffix = self.file_name_entry.get().strip()

        if not PANDOC_INSTALLED:
            has_non_pdf_pandoc_supported = False
            if callable(pandoc_is_supported_format_locally):
                for f_name in os.listdir(input_folder):
                    f_path = os.path.join(input_folder, f_name)
                    if os.path.isfile(f_path) and os.path.splitext(f_name)[1].lower() != ".pdf" \
                            and pandoc_is_supported_format_locally(f_path):
                        has_non_pdf_pandoc_supported = True
                        break
                if has_non_pdf_pandoc_supported:
                    messagebox.showwarning("Pandoc Missing",
                                           "Pandoc executable not found or pypandoc issue. Non-PDF file conversions requiring Pandoc will fail.")

        self.convert_button.configure(state="disabled")
        self.status_label.configure(text="Starting conversion...")
        self.progress_bar.set(0)
        self.converter = RAGConverter(config, status_callback=self.update_status, progress_callback=self.update_progress)

        thread = threading.Thread(target=self.run_conversion, args=(input_folder, output_base_folder, output_suffix))
        thread.daemon = True
        thread.start()

    def run_conversion(self, input_folder: str, output_base_folder: str, output_suffix: str) -> None:
        """Executes the document conversion process.

        Args:
            input_folder (str): The path to the input folder containing source files.
            output_base_folder (str): The path to the output folder for ZIP archives.
            output_suffix (str): The suffix to append to output filenames.
        """
        try:
            if self.converter:
                self.converter.process_folder(input_folder, output_base_folder, output_suffix)
        except PermissionError as e:
            error_msg = f"Permission error: Cannot access a file because it's in use by another process.\n\nTry closing any applications that might be viewing the files and try again.\n\nTechnical details: {str(e)}"
            logger.error(f"Permission error during conversion: {str(e)}")
            messagebox.showerror("File Access Error", error_msg)
        except Exception as e:
            self.update_status(f"An unexpected error occurred: {e}")
            logger.exception("An unexpected error occurred during conversion")
            messagebox.showerror("Fatal Error", f"An unexpected error occurred during conversion: {e}")
        finally:
            self.convert_button.configure(state="normal")

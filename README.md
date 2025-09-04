# RAG Prep Tool

## Purpose

The RAG Prep Tool is a desktop application designed to convert various document formats, including PDFs with images, into Markdown (`.md`) files. These Markdown files are optimized for use as context in Retrieval-Augmented Generation (RAG) applications and other Natural Language Processing (NLP) tasks. The tool packages the generated Markdown file along with extracted media (images) into a ZIP archive.

## Features

*   Converts PDF files, preserving text, attempting to maintain structure, and extracting images.
*   Supports other document formats like PPTX, DOCX, HTML, EPUB, ODT, TXT, MD, JSON, XLSX, XLS, CSV, TSV and common source code files via Pandoc integration.
*   Outputs a ZIP package containing:
    *   The main Markdown file (named after the input file, with an optional user-defined suffix).
    *   A `media/` folder containing all extracted images (for PDFs, these are processed; for Pandoc files, they are as extracted by Pandoc).
    *   A `metadata.json` file with basic properties from the source document.
*   User-configurable options for PDF image processing:
    *   Embedding small images as base64 directly in the Markdown.
    *   Excluding decorative images based on pixel size.
    *   Applying a maximum resolution to images.
*   User-selectable input folder for source documents.
*   User-selectable output folder for the generated ZIP archives.
*   Optional suffix for output filenames.
*   Simple graphical user interface.

## Technologies Used

*   **Python 3.8+**
*   **GUI:**
    *   **CustomTkinter:** For the modern-looking graphical user interface
    *   **Tkinter:** Base GUI library (filedialog, messagebox components)
*   **Document Processing:**
    *   **PyMuPDF (fitz) & pymupdf4llm:** For PDF parsing, text extraction, and initial Markdown conversion
    *   **Pillow (PIL):** For image processing (resizing, format conversion) of extracted images
    *   **pypandoc:** Python wrapper for Pandoc to convert various document formats to Markdown
    *   **python-pptx:** For processing PowerPoint presentations
    *   **pandas:** For DataFrame-based processing of tabular data
    *   **openpyxl & xlrd:** For Excel file processing
    *   **tabulate:** For converting tabular data to Markdown tables
*   **Web Processing:**
    *   **BeautifulSoup4:** For parsing and manipulating HTML content
    *   **Requests:** For downloading external images referenced in HTML documents
    *   **concurrent.futures:** For parallel downloading of external images
*   **Standard Python Libraries:** `os`, `zipfile`, `json`, `shutil`, `re`, `logging`, `threading`, 
    `io`, `base64`, `gc`, `time`, `hashlib`, `sys`, `traceback`

## Prerequisites

Before running the application, you need the following installed on your system:

1.  **Python:** Version 3.8 or newer. You can download it from [python.org](https://www.python.org/).
2.  **Pandoc:** This is **required** for converting non-PDF files (like DOCX, HTML, EPUB, etc.).
    *   Download and install Pandoc from [pandoc.org/installing.html](https://pandoc.org/installing.html).
    *   Ensure Pandoc is added to your system's PATH environment variable during installation so the application can find it. You can verify by opening a terminal/command prompt and typing `pandoc --version`.

## Setup and Installation

### Using the Executable (Recommended for Most Users)

1. **Download the Application**
   - Download the RAG Prep Tool executable file (.exe) from the release page (`\rag_prep_tool\dist`)
   - Extract the ZIP file to a location of your choice

2. **Install Prerequisites**
   - This application requires Pandoc to be installed separately
   - Download and install Pandoc from [pandoc.org/installing.html](https://pandoc.org/installing.html)
   - Make sure Pandoc is added to your PATH during installation (usually selected by default)

3. **Launch the Application**
   - Double-click on `rag_prep_tool.exe` to start the application
   - The user interface will open, allowing you to select input/output folders and configure options

4. **Troubleshooting**
   - If you see "Pandoc not found" errors, verify Pandoc is installed and in your PATH
   - To check if Pandoc is properly installed, open Command Prompt and type `pandoc --version`

### Working with Source Code (For Developers)

If you prefer to run from source or want to modify the application:
1.  **Clone or Download the Project:**
    Get the project files onto your local machine.

2.  **Create a Virtual Environment (Recommended):**
    Open a terminal or command prompt in the project's root directory.
    ```bash
    python -m venv rag_env
    ```

3.  **Activate the Virtual Environment:**
    *   **Windows:**
        ```bash
        rag_env\Scripts\activate
        ```
    *   **macOS/Linux:**
        ```bash
        source rag_env/bin/activate
        ```
    Your terminal prompt should now indicate the active environment (e.g., `(rag_env)`).

4.  **Install Dependencies:**
    Ensure you have a `requirements.txt` file (provided below) in the project root. Then run:
    ```bash
    pip install -r requirements.txt
    ```

## How to Run the Application

1.  Ensure your virtual environment is activated.
2.  Navigate to the source directory of the project (e.g., where `rag_prep_tool.py` is located, often a `src/` folder).
    ```bash
    cd path/to/your/project/src 
    ```
3.  Run the main application script:
    ```bash
    python rag_prep_tool.py
    ```
    The "RAG Prep Tool" window should appear. If Pandoc was not found, a warning will be displayed in the UI, and functionality for non-PDF files will be affected.

## Using the Tool

1.  **Configure Options (Optional):**
    *   Adjust settings for PDF image handling (base64 embedding, decorative image exclusion, max resolution). These options primarily affect PDF processing.
2.  **Select Input Folder:**
    *   Click "Select Input Folder" and choose the directory containing the source files you want to convert.
3.  **Select Output Folder:**
    *   Click "Select Output Folder" and choose the directory where the generated ZIP archives should be saved. If left blank, it defaults to the input folder.
4.  **Output File Suffix (Optional):**
    *   Enter a suffix to append to the original filename for the output ZIP package and internal Markdown file (e.g., `_rag`).
5.  **Convert:**
    *   Click the "Convert" button to start the process.
    *   Status messages and a progress bar will indicate the current operation.
    *   Generated ZIP archives will be placed in the selected output folder. Each ZIP contains the Markdown file and a `media/` folder with images.

## Creating an Executable (e.g., for Windows)

You can package the application into a standalone executable using PyInstaller.

1.  **Install PyInstaller:**
    If not already installed in your virtual environment:
    ```bash
    pip install pyinstaller
    ```

2.  **Run PyInstaller:**
    Open your terminal (with the virtual environment activated) and navigate to the directory containing your main script (`rag_prep_tool.py`).
    A common command is:
    ```bash
    pyinstaller --name RAGPrepTool --onefile --windowed --icon=your_icon.ico rag_prep_tool.py
    ```
    or (with icon and assets):
    ```bash
    pyinstaller --name RAGPrepTool --onefile --windowed --icon="app_icon.ico" --add-data "app_icon.ico;." --add-data "path_to_env\Lib\site-packages\customtkinter\assets;customtkinter\assets" rag_prep_tool.py
    ```

    *   `--name RAGPrepTool`: Sets the name of the executable.
    *   `--onefile`: Creates a single executable file (can be slower to start). For a folder distribution (faster start, more files), omit this.
    *   `--windowed`: Prevents a console window from appearing when the GUI runs. For debugging, use `--console` or omit this.
    *   `--icon=your_icon.ico`: (Optional) Specify a path to an icon file for your executable.

3.  **Handling customtkinter Assets:**
    `customtkinter` requires theme and font assets. PyInstaller might not pick these up automatically. You'll likely need to use the `--add-data` flag.
    *   First, find the path to `customtkinter`'s assets in your environment:
        ```python
        # Run this in a Python interpreter within your venv
        import customtkinter
        import os
        print(os.path.join(os.path.dirname(customtkinter.__file__), "assets"))
        ```
    *   Let's say the output is `path_to_env/Lib/site-packages/customtkinter/assets`.
    *   Your PyInstaller command would then include:
        ```bash
        pyinstaller ... --add-data "path_to_env/Lib/site-packages/customtkinter/assets:customtkinter/assets" ... rag_prep_tool.py
        ```
        (Replace `path_to_env` with the actual path. The part after `:` is the destination within the packaged app.)

4.  **Hidden Imports (If Needed):**
    Sometimes PyInstaller misses less obvious imports. If you get `ModuleNotFoundError` from the executable for libraries like `pypandoc` or parts of `fitz` (PyMuPDF), you might need to add them as hidden imports:
    ```bash
    pyinstaller ... --hidden-import="pypandoc" --hidden-import="fitz" --hidden-import="fitz_new" ... rag_prep_tool.py
    ```

5.  **Output:**
    The executable will be created in a `dist` subfolder within your current directory.

6.  **Important for Distribution:**
    *   **Pandoc Prerequisite:** If your packaged application processes non-PDF files, the user's system **must have Pandoc installed and in their PATH**. Your executable calls Pandoc as an external program. You would typically state this as a system requirement for your application. Bundling Pandoc itself is more complex and involves licensing considerations for Pandoc.
    *   **Testing:** Test the executable thoroughly on a clean machine (without Python or development tools installed, but with Pandoc if testing non-PDF functionality) to ensure it runs correctly.

## Troubleshooting

*   **Pandoc Not Found:** Ensure Pandoc is installed and in your system's PATH. The UI will display a warning if it's not detected on startup.
*   **`TypeError: RAGConverter() takes no arguments` (or similar):** This usually means Python is running an old, cached version of `document_processor.py`. Delete any `__pycache__` folders and `.pyc` files in your source directory and restart your Python interpreter/IDE.
*   **Image Issues with Pandoc Files:** If images from DOCX/HTML are not appearing, ensure the `pandoc_raw_...md` file (enable saving it in `_call_pandoc_convert_file` for debugging) shows correct initial image links from Pandoc, and that the `media` folder is being created by Pandoc inside the `_temp` directory during processing.

## Authors

*   Dawid Głowienkowski

---
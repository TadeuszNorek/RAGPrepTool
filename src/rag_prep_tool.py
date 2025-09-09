import customtkinter as ctk
import logging
from logging.handlers import RotatingFileHandler
import sys
from ui import App

def setup_logging() -> None:
    """
    Configures logging to file and console.
    """
    log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    class AsciiArrowFilter(logging.Filter):
        """Ensure log messages avoid Unicode arrows for broader console compatibility."""
        def filter(self, record: logging.LogRecord) -> bool:
            try:
                msg = record.getMessage()
            except Exception:
                return True
            if '→' in msg:
                record.msg = msg.replace('→', '->')
                record.args = ()
            return True

    # Log to file
    log_file = "rag_prep_tool.log"
    file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=2) # 5MB per file, 2 backups
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.INFO)
    file_handler.addFilter(AsciiArrowFilter())

    # Ensure console uses UTF-8 to avoid UnicodeEncodeError on Windows consoles
    try:
        sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]
    except Exception:
        pass

    # Log to console
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(log_formatter)
    stream_handler.setLevel(logging.INFO)
    stream_handler.addFilter(AsciiArrowFilter())

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    # Avoid duplicate handlers if setup_logging is called multiple times
    if not any(isinstance(h, RotatingFileHandler) for h in root_logger.handlers):
        root_logger.addHandler(file_handler)
    if not any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
        root_logger.addHandler(stream_handler)

    logging.info("Logging initialized.")

def main() -> None:
    """
    Main function to initialize and run the RAG Prep Tool application.
    """
    setup_logging()
    ctk.set_appearance_mode("System")  # Modes: "System" (default), "Dark", "Light"
    ctk.set_default_color_theme("blue")  # Themes: "blue" (default), "green", "dark-blue"

    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()

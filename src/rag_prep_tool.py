import customtkinter as ctk
import logging
from logging.handlers import RotatingFileHandler
import sys
from ui import App

def setup_logging():
    """
    Configures logging to file and console.
    """
    log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Log to file
    log_file = "rag_prep_tool.log"
    file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=2) # 5MB per file, 2 backups
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.INFO)

    # Log to console
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(log_formatter)
    stream_handler.setLevel(logging.INFO)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(stream_handler)

    logging.info("Logging initialized.")

def main():
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
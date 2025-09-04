import customtkinter as ctk
from ui import App

def main():
    """
    Main function to initialize and run the RAG Prep Tool application.
    """
    ctk.set_appearance_mode("System")  # Modes: "System" (default), "Dark", "Light"
    ctk.set_default_color_theme("blue")  # Themes: "blue" (default), "green", "dark-blue"

    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()
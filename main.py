"""
Entity Editor - Main Application Entry Point

A modular, extensible 2D entity editor for game development.
"""

import sys
from PySide6.QtWidgets import QApplication
from src.ui import MainWindow


def main():
    """Main application entry point."""
    app = QApplication(sys.argv)
    
    # Set application info
    app.setApplicationName("Entity Editor")
    app.setOrganizationName("GameDev")
    app.setApplicationVersion("1.0.0")
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Run event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

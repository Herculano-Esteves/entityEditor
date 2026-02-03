"""
Entity Editor & Tools Suite - Main Entry Point

A modular, extensible 2D entity editor and toolset for game development.
"""

import sys
import os

# Ensure src is in path so we can import from src
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from PySide6.QtWidgets import QApplication
from src.launcher import Launcher

def main():
    """Main application entry point."""
    app = QApplication(sys.argv)
    
    # Set application info
    app.setApplicationName("Game Tools Suite")
    app.setOrganizationName("GameDev")
    app.setApplicationVersion("2.0.0")
    
    # Run Launcher
    launcher = Launcher()
    launcher.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

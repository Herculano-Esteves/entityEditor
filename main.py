"""
Entity Editor & Tools Suite - Main Entry Point

A modular, extensible 2D entity editor and toolset for game development.
"""

import sys
import os
import logging
import argparse
import builtins

# Ensure src is in path so we can import from src
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
)

def setup_wrlogs() -> None:
    """Intercept and print all file read/write operations for debugging."""
    original_open = builtins.open

    def hooked_open(file, mode='r', buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
        try:
            filepath = str(file)
            # Filter out Python libraries and system files to avoid overwhelming log spam
            if ("AppData" not in filepath and 
                "site-packages" not in filepath and 
                not filepath.startswith("<")):
                
                if 'w' in mode or 'a' in mode or '+' in mode or 'x' in mode:
                    action = "WRITE"
                else:
                    action = "READ"
                    
                print(f"[\033[93mWRLOGS\033[0m] {action}: {filepath}")
        except Exception:
            pass
        return original_open(file, mode, buffering, encoding, errors, newline, closefd, opener)

    builtins.open = hooked_open
    print("[\033[93mWRLOGS\033[0m] Real-time file I/O logging enabled.")


from PySide6.QtWidgets import QApplication
from src.launcher import Launcher

def main():
    """Main application entry point."""
    parser = argparse.ArgumentParser(description="Entity Editor & Tools Suite", add_help=False)
    parser.add_argument("-wrlogs", "--wrlogs", action="store_true", help="Log all real-time file reads and writes")
    # parse_known_args so we don't break PySide's own argv parsing
    args, unknown = parser.parse_known_args()

    if args.wrlogs:
        setup_wrlogs()

    # Pass the remaining args to Qt
    qt_args = [sys.argv[0]] + unknown
    app = QApplication(qt_args)
    
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


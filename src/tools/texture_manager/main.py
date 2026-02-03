
import sys
from PySide6.QtWidgets import QApplication
from src.tools.texture_manager.ui import TextureManagerWindow

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Texture Manager")
    
    window = TextureManagerWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

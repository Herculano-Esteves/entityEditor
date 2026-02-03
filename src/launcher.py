
import sys
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, QApplication, 
                               QSpacerItem, QSizePolicy, QFileDialog, QMessageBox)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont

from src.common.game_project import GameProject

# Keep tool imports lazy or direct, as needed
from src.tools.entity_editor.ui.main_window import MainWindow as EntityEditorWindow
from src.tools.texture_manager.ui import TextureManagerWindow

class Launcher(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Game Tools Launcher")
        self.resize(400, 500)
        
        self.project_context = None
        self.tool_windows = [] 
        
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Header
        title = QLabel("Game Tools")
        title.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(20)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)
        
        # Project Info
        self.lbl_project = QLabel("No Project Loaded")
        self.lbl_project.setAlignment(Qt.AlignCenter)
        self.lbl_project.setStyleSheet("color: #888; font-style: italic;")
        layout.addWidget(self.lbl_project)
        
        # Load Project
        btn_load = self._create_btn("📂 Open Project (.gameproj)", self._load_project)
        btn_load.setStyleSheet("background-color: #2196F3; color: white;")
        layout.addWidget(btn_load)
        
        layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Minimum))
        
        # Tools
        self.btn_editor = self._create_btn("Entity Editor", self._launch_editor)
        self.btn_editor.setEnabled(False) # Disabled until project loaded
        layout.addWidget(self.btn_editor)
        
        self.btn_tex = self._create_btn("Texture Manager", self._launch_texture_manager)
        self.btn_tex.setEnabled(False) # Disabled until project loaded
        layout.addWidget(self.btn_tex)
        
        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        # Quit
        btn_quit = QPushButton("Quit")
        btn_quit.clicked.connect(self.close)
        layout.addWidget(btn_quit)
        
    def _create_btn(self, text, slot):
        btn = QPushButton(text)
        btn.setMinimumHeight(45)
        btn.setFont(QFont("Segoe UI", 12))
        btn.clicked.connect(slot)
        return btn
        
    def _load_project(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open Game Project", "", "Game Project (*.gameproj)"
        )
        if filepath:
            try:
                self.project_context = GameProject(filepath)
                self.lbl_project.setText(f"Project: {os.path.basename(filepath)}")
                self.lbl_project.setStyleSheet("color: #4CAF50; font-weight: bold;")
                
                # Enable tools
                self.btn_editor.setEnabled(True)
                self.btn_tex.setEnabled(True)
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load project: {e}")
                self.project_context = None

    def _launch_editor(self):
        if not self.project_context: return
        print("Launching Entity Editor...")
        try:
            win = EntityEditorWindow(self.project_context)
            win.show()
            self.tool_windows.append(win)
        except Exception as e:
            print(f"Error launching Entity Editor: {e}")
            import traceback
            traceback.print_exc()

    def _launch_texture_manager(self):
        if not self.project_context: return
        print("Launching Texture Manager...")
        try:
            win = TextureManagerWindow(self.project_context)
            win.show()
            self.tool_windows.append(win)
        except Exception as e:
            print(f"Error launching Texture Manager: {e}")
            import traceback
            traceback.print_exc()

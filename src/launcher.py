
import logging
import sys
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, QApplication,
                               QSpacerItem, QSizePolicy, QFileDialog, QMessageBox)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont

from src.common.game_project import GameProject
from src.common.session_manager import SessionManager

# Keep tool imports lazy or direct, as needed
from src.tools.entity_editor.ui.main_window import MainWindow as EntityEditorWindow
from src.tools.texture_manager.ui import TextureManagerWindow

logger = logging.getLogger(__name__)
class Launcher(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Game Tools Launcher")
        self.resize(400, 500)
        
        self.project_context = None
        self.tool_windows = [] 
        
        self._setup_ui()
        
        # Check for last session
        self._check_last_session()
        
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
        
    def _check_last_session(self) -> None:
        last_project = SessionManager.load_last_project()
        if last_project and os.path.exists(last_project):
            logger.info("Restoring last session: %s", last_project)
            self._load_project_from_path(last_project)

    def _load_project(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open Game Project", "", "Game Project (*.json);;All Files (*.*)"
        )
        if filepath:
            self._load_project_from_path(filepath)

    def _load_project_from_path(self, filepath: str) -> None:
        project = GameProject.load(filepath)
        if project is None:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to load project file:\n{filepath}\n\nCheck that it is a valid JSON project file.",
            )
            self.project_context = None
            return

        # Always ensure the registry file exists on disk (creates empty {} if absent).
        # This allows the Entity Editor to open even before the Texture Manager
        # has been used, and the Texture Manager will sync textures on its own open.
        project.ensure_registry()

        self.project_context = project
        self.lbl_project.setText(f"Project: {project.name}")
        self.lbl_project.setStyleSheet("color: #4CAF50; font-weight: bold;")

        # Show a hint if the textures folder is empty (non-blocking, just informational)
        if not project.has_textures:
            logger.info(
                "Project loaded but textures folder is empty: %s",
                project.abs_textures_path,
            )

        # Enable tools
        self.btn_editor.setEnabled(True)
        self.btn_tex.setEnabled(True)

        # Persist the path so we can re-open it next launch
        SessionManager.save_last_project(filepath)

    def _launch_editor(self) -> None:
        if not self.project_context:
            return

        # No blocking guard: ensure_registry() already ran on project load,
        # so the registry file always exists at this point.
        # The Entity Editor will show placeholder textures if the registry is
        # empty — the user can populate it via the Texture Manager at any time.
        if not self.project_context.has_textures:
            logger.info(
                "Opening Entity Editor with an empty textures folder."
            )

        logger.info("Launching Entity Editor...")
        try:
            win = EntityEditorWindow(self.project_context)
            win.show()
            self.tool_windows.append(win)
        except Exception as e:
            logger.exception("Error launching Entity Editor: %s", e)
            QMessageBox.critical(self, "Error", f"Failed to launch Entity Editor:\n{e}")

    def _launch_texture_manager(self) -> None:
        if not self.project_context:
            return
        logger.info("Launching Texture Manager...")
        try:
            win = TextureManagerWindow(self.project_context)
            win.show()
            self.tool_windows.append(win)
        except Exception as e:
            logger.exception("Error launching Texture Manager: %s", e)
            QMessageBox.critical(self, "Error", f"Failed to launch Texture Manager:\n{e}")

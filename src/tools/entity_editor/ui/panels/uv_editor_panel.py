"""
UV Editor Panel for Entity Editor.

Simplified panel with just the UV editor widget (no tile library).
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.tools.entity_editor.ui.widgets import UVEditorWidget


class UVEditorPanel(QWidget):
    """
    UV editor panel with texture view and interactive UV rectangle editing.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # UV editor (full panel)
        self.uv_editor = UVEditorWidget()
        layout.addWidget(self.uv_editor)

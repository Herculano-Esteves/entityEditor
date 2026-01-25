
from abc import ABC, abstractmethod
from typing import Optional
from PySide6.QtCore import QObject
from PySide6.QtGui import QMouseEvent, QKeyEvent

from src.core.state.editor_state import EditorState

class AbstractTool(QObject):
    """
    Abstract base class for viewport interaction tools.
    
    Tools allow we separating distinct interaction modes (Select, Move, Rotate, etc.)
    from the main viewport code.
    """
    
    def __init__(self, state: EditorState):
        super().__init__()
        self._state = state
        self.active = False
        
    def activate(self):
        """Called when tool becomes active."""
        self.active = True
        
    def deactivate(self):
        """Called when tool becomes inactive."""
        self.active = False
        
    def mouse_press(self, event: QMouseEvent, world_pos):
        """Handle mouse press event."""
        pass
        
    def mouse_move(self, event: QMouseEvent, world_pos):
        """Handle mouse move event."""
        pass
        
    def mouse_release(self, event: QMouseEvent, world_pos):
        """Handle mouse release event."""
        pass
        
    def key_press(self, event: QKeyEvent):
        """Handle key press event."""
        pass
        
    def update_cursor(self, event: QMouseEvent, world_pos):
        """Update cursor based on mouse position."""
        pass

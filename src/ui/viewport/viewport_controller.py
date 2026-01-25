
from PySide6.QtCore import QObject
from PySide6.QtGui import QMouseEvent, QKeyEvent

from src.core.state.editor_state import EditorState
from src.ui.viewport.tools.abstract_tool import AbstractTool
from src.ui.viewport.tools.select_tool import SelectTool

class ViewportController(QObject):
    """
    Controller for the Viewport.
    Routes input events to the active tool.
    """
    
    def __init__(self, view, state: EditorState):
        super().__init__()
        self._view = view
        self._state = state
        self._active_tool: AbstractTool = None
        
        # Default tool
        self.set_tool(SelectTool(state, view)) 
        
    def set_tool(self, tool: AbstractTool):
        """Switch the active tool."""
        if self._active_tool:
            self._active_tool.deactivate()
        
        self._active_tool = tool
        if self._active_tool:
            self._active_tool.activate()
            
    def mouse_press(self, event: QMouseEvent):
        if self._active_tool:
            world_pos = self._view.screen_to_world(event.position())
            self._active_tool.mouse_press(event, world_pos)
            self._view.update() # Request repaint
            
    def mouse_move(self, event: QMouseEvent):
        if self._active_tool:
            world_pos = self._view.screen_to_world(event.position())
            self._active_tool.mouse_move(event, world_pos)
            self._view.update()
            
    def mouse_release(self, event: QMouseEvent):
        if self._active_tool:
            world_pos = self._view.screen_to_world(event.position())
            self._active_tool.mouse_release(event, world_pos)
            self._view.update()

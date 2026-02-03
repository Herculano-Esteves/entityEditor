
from typing import Optional
from PySide6.QtCore import QObject, Signal

from src.tools.entity_editor.core.history_manager import HistoryManager
from src.tools.entity_editor.core.signal_hub import get_signal_hub
from src.tools.entity_editor.data import Entity

class HistoryService(QObject):
    """
    Service for managing undo/redo history.
    Wraps the existing HistoryManager but integrates with the new EditorState.
    """
    
    def __init__(self):
        super().__init__()
        self._manager = HistoryManager(signal_hub=get_signal_hub())
        
    def set_entity(self, entity: Optional[Entity]):
        """Set the entity for history tracking."""
        self._manager.set_entity(entity)
        
    def begin_change(self, description: str):
        """Start a transaction."""
        self._manager.begin_change(description)
        
    def end_change(self):
        """Commit a transaction."""
        self._manager.end_change()
        
    def cancel_change(self):
        """Cancel a transaction."""
        self._manager.cancel_change()
        
    def undo(self):
        self._manager.undo()
        
    def redo(self):
        self._manager.redo()
        
    def can_undo(self) -> bool:
        return self._manager.can_undo()
        
    def can_redo(self) -> bool:
        return self._manager.can_redo()
        
    def execute(self, command):
        """Execute a command directly (Legacy support)."""
        self._manager.execute(command)

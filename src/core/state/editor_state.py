
from typing import Optional, List
from PySide6.QtCore import QObject, Signal

from src.data import Entity, BodyPart, Hitbox
from src.core.signal_hub import get_signal_hub
from src.core.services.history_service import HistoryService
from src.core.state.selection import Selection

class EditorState(QObject):
    """
    Central service for managing the editor's state.
    
    This class is the single source of truth for:
    - The current loaded Entity
    - The active selection (via Selection service)
    - The Undo/Redo history (via History service)
    
    It acts as a facade over the legacy SignalHub for now, gradually replacing it.
    """
    
    _instance = None
    
    # Signals (Replacing SignalHub eventually)
    entity_changed = Signal(object)  # New entity loaded
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EditorState, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        super().__init__()
        self._entity: Optional[Entity] = None
        self._selection = Selection()
        self._history = HistoryService()
        self._signal_hub = get_signal_hub()
        self._initialized = True
            
    @property
    def selection(self) -> Selection:
        """Access the selection service."""
        return self._selection
        
    @property
    def history(self) -> HistoryService:
        """Access the history service."""
        return self._history
            
    @property
    def current_entity(self) -> Optional[Entity]:
        """Access the current loaded entity."""
        return self._entity
            
    def get_entity(self) -> Optional[Entity]:
        """Get the current loaded entity."""
        return self._entity
        
    def set_entity(self, entity: Optional[Entity]):
        """
        Set the current entity. 
        This is the ONLY way the active entity should be changed.
        """
        self._entity = entity
        self._history.set_entity(entity)
        self.entity_changed.emit(entity)
        self._signal_hub.notify_entity_loaded(entity) # Legacy support

    def update_entity(self):
        """Notify that the entity has been modified."""
        self._signal_hub.notify_entity_modified()

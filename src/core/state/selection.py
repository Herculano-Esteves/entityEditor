
from typing import Optional, List, Union
from PySide6.QtCore import QObject, Signal

from src.data import BodyPart, Hitbox
from src.core.signal_hub import get_signal_hub

class Selection(QObject):
    """
    Central service for managing selection state.
    
    Replaces the scattered _selected_bodypart/_selected_hitbox logic
    in ViewportWidget and Panels.
    """
    
    _instance = None
    
    # Signals
    selection_changed = Signal() 
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Selection, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        super().__init__()
        self._selected_bodyparts: List[BodyPart] = []
        self._primary_bodypart: Optional[BodyPart] = None
        self._selected_hitbox: Optional[Hitbox] = None
        self._signal_hub = get_signal_hub()
        self._initialized = True
        
    @property
    def selected_bodyparts(self) -> List[BodyPart]:
        return list(self._selected_bodyparts)
        
    @property
    def selected_body_parts(self) -> List[BodyPart]:
        """Alias for compatibility."""
        return self.selected_bodyparts

    @property
    def primary_bodypart(self) -> Optional[BodyPart]:
        return self._primary_bodypart
        
    @property
    def selected_body_part(self) -> Optional[BodyPart]:
        """Alias for compatibility."""
        return self._primary_bodypart
        
    @property
    def selected_hitbox(self) -> Optional[Hitbox]:
        return self._selected_hitbox
        
    @property
    def has_selection(self) -> bool:
        """Return True if any body part is selected."""
        return len(self._selected_bodyparts) > 0

    def is_selected(self, bodypart: BodyPart) -> bool:
        """Check if a body part is selected."""
        return bodypart in self._selected_bodyparts

    def is_hitbox_selected(self, hitbox: Hitbox) -> bool:
        """Check if a hitbox is selected."""
        return self._selected_hitbox == hitbox
        
    def select_bodypart(self, bodypart: Optional[BodyPart], additive: bool = False):
        """
        Select a body part.
        
        Args:
            bodypart: The body part to select (or None to clear)
            additive: If True, toggles selection of this part while keeping others.
                      If False, clears other selections.
        """
        if bodypart is None:
            if not additive:
                self.clear_selection()
            return
            
        if additive:
            if bodypart in self._selected_bodyparts:
                self._selected_bodyparts.remove(bodypart)
                if self._primary_bodypart == bodypart:
                    self._primary_bodypart = self._selected_bodyparts[0] if self._selected_bodyparts else None
            else:
                self._selected_bodyparts.append(bodypart)
                self._primary_bodypart = bodypart
        else:
            self._selected_bodyparts = [bodypart]
            self._primary_bodypart = bodypart
            self._selected_hitbox = None # Selecting a new body part usually clears hitbox selection
            
        self._notify()

    def set_selection(self, bodypart: BodyPart):
        """Set primary selection (clears others). Alias for select_bodypart(bp, False)."""
        self.select_bodypart(bodypart, additive=False)

    def add_to_selection(self, bodypart: BodyPart):
        """Add to selection. Alias for select_bodypart(bp, True)."""
        if bodypart not in self._selected_bodyparts:
            self._selected_bodyparts.append(bodypart)
            # Notify but don't change primary unless it was empty
            if not self._primary_bodypart:
                self._primary_bodypart = bodypart
            self._notify()

    def toggle_selection(self, bodypart: BodyPart):
        """Toggle selection. Alias for select_bodypart(bp, True)."""
        self.select_bodypart(bodypart, additive=True)

    def select_bodyparts(self, bodyparts: List[BodyPart]):
        """Select a list of body parts (replaces current selection)."""
        self._selected_bodyparts = list(bodyparts)
        self._primary_bodypart = bodyparts[0] if bodyparts else None
        self._selected_hitbox = None
        self._notify()
        
    def select_hitbox(self, hitbox: Optional[Hitbox]):
        """Select a hitbox."""
        self._selected_hitbox = hitbox
        if hitbox:
            # Usually selecting a hitbox implies we are editing its parent body part ??
            # For now keeping it simple.
            pass
        self._notify()
        self._signal_hub.notify_hitbox_selected(hitbox) # Legacy sync
    
    def deselect_hitbox(self):
        """Deselect hitbox."""
        self.select_hitbox(None)
        
    def clear_selection(self):
        """Clear all selection."""
        self._selected_bodyparts = []
        self._primary_bodypart = None
        self._selected_hitbox = None
        self._notify()
        self._signal_hub.notify_hitbox_selected(None)

    def _notify(self):
        self.selection_changed.emit()
        # Legacy Sync
        self._signal_hub.notify_bodyparts_selection_changed(self._selected_bodyparts)
        self._signal_hub.notify_bodypart_selected(self._primary_bodypart)

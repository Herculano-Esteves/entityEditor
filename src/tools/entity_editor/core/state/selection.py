
from typing import Optional, List, Union
from PySide6.QtCore import QObject, Signal

from src.tools.entity_editor.data import BodyPart, Hitbox
from src.tools.entity_editor.core.signal_hub import get_signal_hub

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
        self._selected_parts: set[BodyPart] = set()
        self._primary_part: Optional[BodyPart] = None
        
        self._selected_hitbox: Optional[Hitbox] = None
        self._signal_hub = get_signal_hub()
        self._initialized = True
        
    @property
    def selected_bodyparts(self) -> List[BodyPart]:
        """Dynamically resolve selected IDs to current entity body parts."""
        # We need access to current entity from somewhere to resolve IDs.
        # Ideally EditorState holds both, but Selection is IN EditorState usually?
        # Actually EditorState holds Selection.
        # We can acccess via singleton or passed reference, but this class is initialized in EditorState.
        # Circular import risk if we import EditorState here? 
        # Actually EditorState imports Selection. 
        # We can rely on signal hub or injection, OR iterate over current entity if available?
        from src.tools.entity_editor.core.state.editor_state import EditorState
        entity = EditorState().current_entity
        if not entity: return []
        
        # Preserve order from entity list (stable sort) or selection order? 
        # Usually standard is: Return selected items in render order (entity list order)
        # Filter entity.body_parts to only include those in self._selected_parts
        return [bp for bp in entity.body_parts if bp in self._selected_parts]
        
    @property
    def selected_body_parts(self) -> List[BodyPart]:
        """Alias for compatibility."""
        return self.selected_bodyparts

    @property
    def primary_bodypart(self) -> Optional[BodyPart]:
        return self._primary_part
        
    @property
    def selected_body_part(self) -> Optional[BodyPart]:
        """Alias for compatibility."""
        return self.primary_bodypart
        
    @property
    def selected_hitbox(self) -> Optional[Hitbox]:
        return self._selected_hitbox
        
    @property
    def has_selection(self) -> bool:
        """Return True if any body part is selected."""
        return len(self._selected_parts) > 0

    def is_selected(self, bodypart: BodyPart) -> bool:
        """Check if a body part is selected."""
        return bodypart in self._selected_parts

    def is_hitbox_selected(self, hitbox: Hitbox) -> bool:
        """Check if a hitbox is selected."""
        return self._selected_hitbox == hitbox
        
    def select_bodypart(self, bodypart: Optional[BodyPart], additive: bool = False):
        """
        Select a body part.
        """
        if bodypart is None:
            if not additive:
                self.clear_selection()
            return
            
        if additive:
            if bodypart in self._selected_parts:
                self._selected_parts.remove(bodypart)
                if self._primary_part == bodypart:
                    # Pick new primary?
                    self._primary_part = next(iter(self._selected_parts)) if self._selected_parts else None
            else:
                self._selected_parts.add(bodypart)
                self._primary_part = bodypart
        else:
            self._selected_parts = {bodypart}
            self._primary_part = bodypart
            self._selected_hitbox = None 
            
        self._notify()

    def set_selection(self, bodypart: BodyPart):
        """Set primary selection (clears others). Alias for select_bodypart(bp, False)."""
        self.select_bodypart(bodypart, additive=False)

    def add_to_selection(self, bodypart: BodyPart):
        """Add to selection. Alias for select_bodypart(bp, True)."""
        if bodypart not in self._selected_parts:
            self._selected_parts.add(bodypart)
            if not self._primary_part:
                self._primary_part = bodypart
            self._notify()

    def toggle_selection(self, bodypart: BodyPart):
        """Toggle selection. Alias for select_bodypart(bp, True)."""
        self.select_bodypart(bodypart, additive=True)

    def select_bodyparts(self, bodyparts: List[BodyPart]):
        """Select a list of body parts."""
        self._selected_parts = set(bodyparts)
        self._primary_part = bodyparts[0] if bodyparts else None
        self._selected_hitbox = None
        self._notify()
        
    def select_hitbox(self, hitbox: Optional[Hitbox]):
        """Select a hitbox."""
        self._selected_hitbox = hitbox
        self._notify()
        self._signal_hub.notify_hitbox_selected(hitbox) 
    
    def deselect_hitbox(self):
        """Deselect hitbox."""
        self.select_hitbox(None)
        
    def clear_selection(self):
        """Clear all selection."""
        self._selected_parts.clear()
        self._primary_part = None
        self._selected_hitbox = None
        self._notify()
        self._signal_hub.notify_hitbox_selected(None)

    def _notify(self):
        self.selection_changed.emit()
        self._signal_hub.notify_bodyparts_selection_changed(self.selected_bodyparts)
        self._signal_hub.notify_bodypart_selected(self.primary_bodypart)

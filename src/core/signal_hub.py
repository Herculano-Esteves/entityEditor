"""
Signal Hub for Entity Editor.

Central event dispatcher to decouple UI components.
Uses Qt signals to notify components about changes without tight coupling.
"""

from PySide6.QtCore import QObject, Signal
from typing import Optional, Any


class SignalHub(QObject):
    """
    Centralized signal dispatcher for the Entity Editor.
    
    All UI components can connect to these signals to stay synchronized
    without direct references to each other.
    """
    
    # Entity-level signals
    entity_loaded = Signal(object)  # Emitted when a new entity is loaded (passes Entity)
    entity_modified = Signal()       # Emitted when any entity property changes
    entity_saved = Signal(str)       # Emitted when entity is saved (passes filepath)
    
    # Body part signals
    bodypart_selected = Signal(object)   # Emitted when a body part is selected (passes BodyPart or None)
    bodypart_added = Signal(object)      # Emitted when a body part is added (passes BodyPart)
    bodypart_removed = Signal(object)    # Emitted when a body part is removed (passes BodyPart)
    bodypart_modified = Signal(object)   # Emitted when a body part is modified (passes BodyPart)
    bodypart_reordered = Signal()        # Emitted when body parts are reordered
    
    # Hitbox signals
    hitbox_selected = Signal(object)     # Emitted when a hitbox is selected (passes Hitbox or None)
    hitbox_added = Signal(object)        # Emitted when a hitbox is added (passes Hitbox)
    hitbox_removed = Signal(object)      # Emitted when a hitbox is removed (passes Hitbox)
    hitbox_modified = Signal(object)     # Emitted when a hitbox is modified (passes Hitbox)
    
    # Texture signals
    texture_loaded = Signal(str)         # Emitted when a texture is loaded (passes filepath)
    uv_modified = Signal(object)         # Emitted when UV rect is modified (passes BodyPart)
    
    # Viewport signals
    viewport_selection_changed = Signal(object)  # Emitted when selection changes in viewport
    viewport_transform_changed = Signal()        # Emitted when viewport zoom/pan changes
    
    def __init__(self):
        super().__init__()
    
    def notify_entity_loaded(self, entity):
        """Notify that a new entity has been loaded."""
        self.entity_loaded.emit(entity)
    
    def notify_entity_modified(self):
        """Notify that the entity has been modified."""
        self.entity_modified.emit()
    
    def notify_entity_saved(self, filepath: str):
        """Notify that the entity has been saved."""
        self.entity_saved.emit(filepath)
    
    def notify_bodypart_selected(self, bodypart):
        """Notify that a body part has been selected."""
        self.bodypart_selected.emit(bodypart)
    
    def notify_bodypart_added(self, bodypart):
        """Notify that a body part has been added."""
        self.bodypart_added.emit(bodypart)
        self.entity_modified.emit()
    
    def notify_bodypart_removed(self, bodypart):
        """Notify that a body part has been removed."""
        self.bodypart_removed.emit(bodypart)
        self.entity_modified.emit()
    
    def notify_bodypart_modified(self, bodypart):
        """Notify that a body part has been modified."""
        self.bodypart_modified.emit(bodypart)
        self.entity_modified.emit()
    
    def notify_bodypart_reordered(self):
        """Notify that body parts have been reordered."""
        self.bodypart_reordered.emit()
        self.entity_modified.emit()
    
    def notify_hitbox_selected(self, hitbox):
        """Notify that a hitbox has been selected."""
        self.hitbox_selected.emit(hitbox)
    
    def notify_hitbox_added(self, hitbox):
        """Notify that a hitbox has been added."""
        self.hitbox_added.emit(hitbox)
        self.entity_modified.emit()
    
    def notify_hitbox_removed(self, hitbox):
        """Notify that a hitbox has been removed."""
        self.hitbox_removed.emit(hitbox)
        self.entity_modified.emit()
    
    def notify_hitbox_modified(self, hitbox):
        """Notify that a hitbox has been modified."""
        self.hitbox_modified.emit(hitbox)
        self.entity_modified.emit()
    
    def notify_texture_loaded(self, filepath: str):
        """Notify that a texture has been loaded."""
        self.texture_loaded.emit(filepath)
    
    def notify_uv_modified(self, bodypart):
        """Notify that a UV rect has been modified."""
        self.uv_modified.emit(bodypart)
        self.entity_modified.emit()
    
    def notify_viewport_selection_changed(self, selected_object):
        """Notify that viewport selection has changed."""
        self.viewport_selection_changed.emit(selected_object)


# Global signal hub instance
_signal_hub_instance: Optional[SignalHub] = None


def get_signal_hub() -> SignalHub:
    """
    Get the global signal hub instance.
    Creates one if it doesn't exist.
    """
    global _signal_hub_instance
    if _signal_hub_instance is None:
        _signal_hub_instance = SignalHub()
    return _signal_hub_instance

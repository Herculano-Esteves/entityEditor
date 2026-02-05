"""
Command classes for undo/redo functionality.

Implements the Command Pattern for undoable operations in the entity editor.
"""

import copy
from typing import Any, Dict
from src.tools.entity_editor.data import BodyPart, Hitbox, Vec2


class Command:
    """Base class for undoable commands."""
    
    def execute(self, entity, signal_hub=None):
        """Execute the command."""
        raise NotImplementedError
    
    def undo(self, entity, signal_hub=None):
        """Undo the command."""
        raise NotImplementedError
    
    def get_description(self) -> str:
        """Get a human-readable description of this command."""
        return "Action"


class AddBodyPartCommand(Command):
    """Command to add a body part to the entity."""
    
    def __init__(self, bodypart: BodyPart, insert_index: int = -1):
        self.bodypart = bodypart
        self.insert_index = insert_index
    
    def execute(self, entity, signal_hub=None):
        """Add the body part to the entity."""
        if self.insert_index >= 0:
            entity.body_parts.insert(self.insert_index, self.bodypart)
        else:
            entity.add_body_part(self.bodypart)
            
        if signal_hub:
            signal_hub.notify_bodypart_added(self.bodypart)
            if self.insert_index >= 0:
                signal_hub.notify_bodypart_reordered() # List order changed
    
    def undo(self, entity, signal_hub=None):
        """Remove the body part from the entity."""
        entity.remove_body_part(self.bodypart)
        if signal_hub:
            signal_hub.notify_bodypart_removed(self.bodypart)
    
    def get_description(self) -> str:
        return f"Add {self.bodypart.name}"


class RemoveBodyPartCommand(Command):
    """Command to remove a body part from the entity."""
    
    def __init__(self, bodypart: BodyPart):
        self.bodypart = bodypart
        self.index = None  # Store index to restore at same position
    
    def execute(self, entity, signal_hub=None):
        """Remove the body part from the entity."""
        # Store index for undo
        self.index = entity.body_parts.index(self.bodypart)
        entity.remove_body_part(self.bodypart)
        if signal_hub:
            signal_hub.notify_bodypart_removed(self.bodypart)
    
    def undo(self, entity, signal_hub=None):
        """Re-add the body part at its original position."""
        if self.index is not None:
            entity.body_parts.insert(self.index, self.bodypart)
        else:
            entity.add_body_part(self.bodypart)
        if signal_hub:
            signal_hub.notify_bodypart_added(self.bodypart)
    
    def get_description(self) -> str:
        return f"Remove {self.bodypart.name}"


class ModifyBodyPartCommand(Command):
    """Command to modify body part properties."""
    
    def __init__(self, bodypart: BodyPart, old_state: Dict[str, Any], new_state: Dict[str, Any]):
        self.bodypart = bodypart
        self.old_state = old_state
        self.new_state = new_state
    
    def execute(self, entity, signal_hub=None):
        """Apply new state to body part."""
        self._apply_state(self.new_state)
        if signal_hub:
            signal_hub.notify_bodypart_modified(self.bodypart)
    
    def undo(self, entity, signal_hub=None):
        """Restore old state to body part."""
        self._apply_state(self.old_state)
        if signal_hub:
            signal_hub.notify_bodypart_modified(self.bodypart)
    
    def _apply_state(self, state: Dict[str, Any]):
        """Apply a state dictionary to the body part."""
        for key, value in state.items():
            if key == 'position':
                if isinstance(value, dict):
                    self.bodypart.position.x = value['x']
                    self.bodypart.position.y = value['y']
                else:
                    self.bodypart.position.x = value.x
                    self.bodypart.position.y = value.y
            elif key == 'size':
                if isinstance(value, dict):
                    self.bodypart.size.x = value['x']
                    self.bodypart.size.y = value['y']
                else:
                    self.bodypart.size.x = value.x
                    self.bodypart.size.y = value.y
            elif key == 'uv_rect':
                if isinstance(value, dict):
                    self.bodypart.uv_rect.x = value['x']
                    self.bodypart.uv_rect.y = value['y']
                    self.bodypart.uv_rect.width = value['width']
                    self.bodypart.uv_rect.height = value['height']
                else:
                    self.bodypart.uv_rect.x = value.x
                    self.bodypart.uv_rect.y = value.y
                    self.bodypart.uv_rect.width = value.width
                    self.bodypart.uv_rect.height = value.height
            elif key == 'pivot_offset':
                if isinstance(value, dict):
                    self.bodypart.pivot_offset.x = value['x']
                    self.bodypart.pivot_offset.y = value['y']
                else:
                    self.bodypart.pivot_offset.x = value.x
                    self.bodypart.pivot_offset.y = value.y
            else:
                setattr(self.bodypart, key, value)
    
    def get_description(self) -> str:
        props = ", ".join(self.new_state.keys())
        return f"Modify {self.bodypart.name} ({props})"


class MoveBodyPartCommand(Command):
    """Command to move a body part."""
    
    def __init__(self, bodypart: BodyPart, old_pos: Vec2, new_pos: Vec2):
        self.bodypart = bodypart
        self.old_pos = Vec2(old_pos.x, old_pos.y)
        self.new_pos = Vec2(new_pos.x, new_pos.y)
    
    def execute(self, entity, signal_hub=None):
        """Move body part to new position."""
        self.bodypart.position.x = self.new_pos.x
        self.bodypart.position.y = self.new_pos.y
        if signal_hub:
            signal_hub.notify_bodypart_modified(self.bodypart)
    
    def undo(self, entity, signal_hub=None):
        """Move body part back to old position."""
        self.bodypart.position.x = self.old_pos.x
        self.bodypart.position.y = self.old_pos.y
        if signal_hub:
            signal_hub.notify_bodypart_modified(self.bodypart)
    
    def get_description(self) -> str:
        return f"Move {self.bodypart.name}"


class AddHitboxCommand(Command):
    """Command to add a hitbox to a body part."""
    
    def __init__(self, parent_bodypart: BodyPart, hitbox: Hitbox, insert_index: int = -1):
        self.parent_bodypart = parent_bodypart
        self.hitbox = hitbox
        self.insert_index = insert_index
    
    def execute(self, entity, signal_hub=None):
        """Add the hitbox to the parent body part."""
        if self.insert_index >= 0:
            self.parent_bodypart.hitboxes.insert(self.insert_index, self.hitbox)
        else:
            self.parent_bodypart.hitboxes.append(self.hitbox)
            
        if signal_hub:
            signal_hub.notify_hitbox_added(self.hitbox)
    
    def undo(self, entity, signal_hub=None):
        """Remove the hitbox from the parent body part."""
        self.parent_bodypart.hitboxes.remove(self.hitbox)
        if signal_hub:
            signal_hub.notify_hitbox_removed(self.hitbox)
    
    def get_description(self) -> str:
        return f"Add hitbox {self.hitbox.name}"


class RemoveHitboxCommand(Command):
    """Command to remove a hitbox from a body part."""
    
    def __init__(self, parent_bodypart: BodyPart, hitbox: Hitbox):
        self.parent_bodypart = parent_bodypart
        self.hitbox = hitbox
        self.index = None
    
    def execute(self, entity, signal_hub=None):
        """Remove the hitbox from the parent body part."""
        self.index = self.parent_bodypart.hitboxes.index(self.hitbox)
        self.parent_bodypart.hitboxes.remove(self.hitbox)
        if signal_hub:
            signal_hub.notify_hitbox_removed(self.hitbox)
    
    def undo(self, entity, signal_hub=None):
        """Re-add the hitbox at its original position."""
        if self.index is not None:
            self.parent_bodypart.hitboxes.insert(self.index, self.hitbox)
        else:
            self.parent_bodypart.hitboxes.append(self.hitbox)
        if signal_hub:
            signal_hub.notify_hitbox_added(self.hitbox)
    
    def get_description(self) -> str:
        return f"Remove hitbox {self.hitbox.name}"


class ModifyHitboxCommand(Command):
    """Command to modify hitbox properties."""
    
    def __init__(self, hitbox: Hitbox, old_state: Dict[str, Any], new_state: Dict[str, Any]):
        self.hitbox = hitbox
        self.old_state = old_state
        self.new_state = new_state
    
    def execute(self, entity, signal_hub=None):
        """Apply new state to hitbox."""
        self._apply_state(self.new_state)
        if signal_hub:
            signal_hub.notify_hitbox_modified(self.hitbox)
    
    def undo(self, entity, signal_hub=None):
        """Restore old state to hitbox."""
        self._apply_state(self.old_state)
        if signal_hub:
            signal_hub.notify_hitbox_modified(self.hitbox)
    
    def _apply_state(self, state: Dict[str, Any]):
        """Apply a state dictionary to the hitbox."""
        for key, value in state.items():
            # Handle integer direct fields
            setattr(self.hitbox, key, value)
    
    def get_description(self) -> str:
        props = ", ".join(self.new_state.keys())
        return f"Modify hitbox {self.hitbox.name} ({props})"


class MoveHitboxCommand(Command):
    """Command to move a hitbox."""
    
    def __init__(self, hitbox: Hitbox, old_pos: Vec2, new_pos: Vec2):
        self.hitbox = hitbox
        self.old_pos = Vec2(old_pos.x, old_pos.y)
        self.new_pos = Vec2(new_pos.x, new_pos.y)
    
    def execute(self, entity, signal_hub=None):
        """Move hitbox to new position."""
        self.hitbox.x = int(self.new_pos.x)
        self.hitbox.y = int(self.new_pos.y)
        if signal_hub:
            signal_hub.notify_hitbox_modified(self.hitbox)
    
    def undo(self, entity, signal_hub=None):
        """Move hitbox back to old position."""
        self.hitbox.x = int(self.old_pos.x)
        self.hitbox.y = int(self.old_pos.y)
        if signal_hub:
            signal_hub.notify_hitbox_modified(self.hitbox)
    
    def get_description(self) -> str:
        return f"Move hitbox {self.hitbox.name}"

"""
Snapshot-based undo command for capturing entity states.

Much simpler than per-property commands - just stores complete entity state.
"""

import copy
from src.data import Entity


class EntitySnapshotCommand:
    """Command that stores complete entity state snapshots for undo/redo."""
    
    def __init__(self, entity: Entity, description: str = "Change"):
        """
        Create snapshot command.
        
        Args:
            entity: The entity to snapshot
            description: Human-readable description of the change
        """
        # Deep copy the CURRENT state as "before" state
        self.before_state = copy.deepcopy(entity)
        self.after_state = None  # Will be set when finalizing
        self.description = description
        
    def finalize(self, entity: Entity):
        """Capture the 'after' state. Call this after the change is made."""
        self.after_state = copy.deepcopy(entity)
    
    def execute(self, entity: Entity, signal_hub=None):
        """Apply the 'after' state."""
        if self.after_state:
            self._apply_state(entity, self.after_state)
            if signal_hub:
                signal_hub.notify_entity_modified()
    
    def undo(self, entity: Entity, signal_hub=None):
        """Restore the 'before' state."""
        self._apply_state(entity, self.before_state)
        if signal_hub:
            signal_hub.notify_entity_modified()
    
    def _apply_state(self, entity: Entity, snapshot: Entity):
        """Apply a snapshot to the entity."""
        # Copy all attributes from snapshot to entity
        entity.name = snapshot.name
        entity.entity_id = snapshot.entity_id
        entity.pivot.x = snapshot.pivot.x
        entity.pivot.y = snapshot.pivot.y
        entity.version = snapshot.version
        entity.tags = copy.deepcopy(snapshot.tags)
        entity.metadata = copy.deepcopy(snapshot.metadata)
        
        # Replace body parts list
        entity.body_parts.clear()
        for bp in snapshot.body_parts:
            entity.body_parts.append(copy.deepcopy(bp))
        
        # Replace entity hitboxes
        entity.entity_hitboxes.clear()
        for hb in snapshot.entity_hitboxes:
            entity.entity_hitboxes.append(copy.deepcopy(hb))
    
    def get_description(self) -> str:
        return self.description

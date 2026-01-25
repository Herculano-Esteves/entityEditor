"""
State-based Undo/Redo System

Pure state snapshot approach - no commands, no complexity.
Complete entity state is captured before edits, comparison determines if undo entry is created.

Key principles:
- State-based, not action-based
- Transaction model (begin_edit / end_edit)
- No per-widget logic - works everywhere
- JSON serialization for deep equality
- Automatic memory management

Author: Entity Editor Team
Date: 2026-01-24
"""

import json
from typing import List, Optional, Callable
from dataclasses import dataclass
from src.data import Entity


@dataclass
class EditorState:
    """Immutable snapshot of complete editor state at a point in time.
    
    Uses JSON serialization because:
    - Deep equality via string comparison (fast, reliable)
    - Memory efficient (Python interns strings)
    - Human-readable for debugging
    - No object reference issues
    - Works even if Entity structure changes
    
    Attributes:
        entity_json: JSON string representation of Entity
        description: Human-readable description (e.g., "Move body part")
    """
    
    entity_json: str
    description: str
    
    @classmethod
    def from_entity(cls, entity: Entity, description: str = "") -> 'EditorState':
        """Create snapshot from current entity state.
        
        Args:
            entity: Entity to snapshot
            description: Human-readable description of this state
            
        Returns:
            EditorState containing serialized entity
        """
        entity_dict = entity.to_dict()
        # sort_keys ensures deterministic JSON for comparison
        entity_json = json.dumps(entity_dict, sort_keys=True, indent=None)
        return cls(entity_json=entity_json, description=description)
    
    def to_entity(self) -> Entity:
        """Restore Entity from this snapshot.
        
        Returns:
            Entity reconstructed from JSON
        """
        entity_dict = json.loads(self.entity_json)
        return Entity.from_dict(entity_dict)
    
    def __eq__(self, other) -> bool:
        """Two states are equal if their entity data matches exactly.
        
        String comparison is fastest and most reliable for deep equality.
        """
        if not isinstance(other, EditorState):
            return False
        return self.entity_json == other.entity_json
    
    def get_size_bytes(self) -> int:
        """Get approximate memory footprint of this snapshot."""
        return len(self.entity_json)


class StateHistory:
    """Manages undo/redo using pure state snapshots.
    
    Philosophy:
        - No commands, no per-widget logic, no special cases
        - Just save complete state before any change
        - Compare before/after to detect changes
        - Restore old state to undo
    
    Transaction model:
        history.begin_edit("Edit description")  # Captures "before" snapshot
        # ... user makes changes to entity ...
        history.end_edit()  # Compares "after" to "before", saves if different
    
    Works for:
        - Viewport mouse interactions
        - UI panel edits (spinboxes, text fields, combos)
        - Dialog confirmations
        - Button clicks
        - Any entity mutation from any source
    
    Memory management:
        - Enforces maximum undo steps (default 50)
        - Each step typically 10-100 KB
        - Total memory usage: ~5 MB for 50 steps
        - Automatically removes oldest entries when limit reached
    """
    
    def __init__(self, entity: Optional[Entity] = None, max_size: int = 50):
        """Initialize state history manager.
        
        Args:
            entity: Entity to manage (can be set later via set_entity)
            max_size: Maximum number of undo steps to retain
        """
        self._entity = entity
        self._max_size = max_size
        
        # Undo/redo stacks (newest entries at end)
        self._undo_stack: List[EditorState] = []
        self._redo_stack: List[EditorState] = []
        
        # Active transaction tracking
        self._transaction_snapshot: Optional[EditorState] = None
        self._transaction_description: str = ""
        
        # Observer callbacks for UI updates
        # Signature: callback(can_undo: bool, can_redo: bool)
        self._observers: List[Callable[[bool, bool], None]] = []
    
    def set_entity(self, entity: Optional[Entity]):
        """Set entity and clear all history.
        
        Call this when loading a new entity document.
        
        Args:
            entity: New entity to manage, or None
        """
        self._entity = entity
        self.clear()
    
    def add_observer(self, callback: Callable[[bool, bool], None]):
        """Register callback to be notified of history state changes.
        
        Callback will be invoked whenever undo/redo availability changes.
        Useful for updating menu item enabled states.
        
        Args:
            callback: Function taking (can_undo, can_redo) booleans
        """
        self._observers.append(callback)
    
    def _notify_observers(self):
        """Notify all observers that history state has changed."""
        can_undo = self.can_undo()
        can_redo = self.can_redo()
        for callback in self._observers:
            try:
                callback(can_undo, can_redo)
            except Exception as e:
                print(f"Error in history observer: {e}")
    
    # ─────────────────────────────────────────────────────────────
    # TRANSACTION API (Primary public interface)
    # ─────────────────────────────────────────────────────────────
    
    def begin_edit(self, description: str = "Edit"):
        """Begin an edit transaction.
        
        Captures current entity state as "before" snapshot.
        Call this BEFORE user starts making changes.
        
        Common usage patterns:
            - Mouse press: begin_edit("Move body part")
            - Focus in: begin_edit("Edit hitbox")
            - Dialog open: begin_edit("Edit UV mapping")
        
        Args:
            description: Human-readable description for undo menu
        
        Note:
            If begin_edit() is called while a transaction is active,
            the previous transaction is automatically ended first.
        """
        if not self._entity:
            return
        
        # If already in transaction, commit it first (nested transaction)
        if self._transaction_snapshot is not None:
            self.end_edit()
        
        # Capture pre-edit state
        self._transaction_snapshot = EditorState.from_entity(
            self._entity, 
            description
        )
        self._transaction_description = description
    
    def end_edit(self):
        """End an edit transaction.
        
        Compares current state to "before" snapshot captured in begin_edit().
        - If different: pushes "before" snapshot to undo stack
        - If same: discards transaction (no-op edit)
        
        Call this AFTER user finishes making changes.
        
        Common usage patterns:
            - Mouse release: end_edit()
            - Focus out: end_edit()
            - Dialog accept: end_edit()
        
        Note:
            Safe to call even if no transaction is active (no-op).
        """
        if not self._entity or not self._transaction_snapshot:
            return
        
        # Capture post-edit state
        current_state = EditorState.from_entity(
            self._entity,
            self._transaction_description
        )
        
        # Only save if something actually changed
        if current_state != self._transaction_snapshot:
            # Push "before" snapshot to undo stack
            self._undo_stack.append(self._transaction_snapshot)
            
            # Enforce maximum size by removing oldest
            if len(self._undo_stack) > self._max_size:
                self._undo_stack.pop(0)
            
            # New edit invalidates forward history
            self._redo_stack.clear()
            
            self._notify_observers()
        
        # Clear transaction state
        self._transaction_snapshot = None
        self._transaction_description = ""
    
    def cancel_edit(self):
        """Cancel current transaction without saving.
        
        Useful for:
            - Dialog cancel button
            - ESC key handling
            - Error conditions
        
        Note:
            This only cancels the TRACKING of the edit.
            Model changes have already happened!
            To restore old state, call undo() after cancel_edit().
        """
        self._transaction_snapshot = None
        self._transaction_description = ""
    
    # ─────────────────────────────────────────────────────────────
    # UNDO/REDO API
    # ─────────────────────────────────────────────────────────────
    
    def undo(self) -> bool:
        """Undo last edit by restoring previous state.
        
        Restores entity to state before last committed edit.
        Current state is saved to redo stack for potential redo.
        
        Returns:
            True if undo was performed, False if nothing to undo
        """
        if not self.can_undo() or not self._entity:
            return False
        
        # Capture current state for redo
        current_state = EditorState.from_entity(self._entity, "")
        self._redo_stack.append(current_state)
        
        # Restore previous state
        previous_state = self._undo_stack.pop()
        restored_entity = previous_state.to_entity()
        
        # Replace entity contents in-place (preserves object identity)
        # This is critical so UI references to entity remain valid
        self._entity.name = restored_entity.name
        self._entity.entity_id = restored_entity.entity_id
        self._entity.pivot = restored_entity.pivot
        self._entity.body_parts = restored_entity.body_parts
        self._entity.entity_hitboxes = restored_entity.entity_hitboxes
        self._entity.version = restored_entity.version
        self._entity.tags = restored_entity.tags
        self._entity.metadata = restored_entity.metadata
        
        self._notify_observers()
        return True
    
    def redo(self) -> bool:
        """Redo previously undone edit.
        
        Restores entity to state after undone edit.
        
        Returns:
            True if redo was performed, False if nothing to redo
        """
        if not self.can_redo() or not self._entity:
            return False
        
        # Capture current state for undo
        current_state = EditorState.from_entity(self._entity, "")
        self._undo_stack.append(current_state)
        
        # Restore forward state
        forward_state = self._redo_stack.pop()
        restored_entity = forward_state.to_entity()
        
        # Replace entity contents in-place
        self._entity.name = restored_entity.name
        self._entity.entity_id = restored_entity.entity_id
        self._entity.pivot = restored_entity.pivot
        self._entity.body_parts = restored_entity.body_parts
        self._entity.entity_hitboxes = restored_entity.entity_hitboxes
        self._entity.version = restored_entity.version
        self._entity.tags = restored_entity.tags
        self._entity.metadata = restored_entity.metadata
        
        self._notify_observers()
        return True
    
    def can_undo(self) -> bool:
        """Check if undo operation is available."""
        return len(self._undo_stack) > 0
    
    def can_redo(self) -> bool:
        """Check if redo operation is available."""
        return len(self._redo_stack) > 0
    
    def get_undo_description(self) -> Optional[str]:
        """Get description of action that would be undone.
        
        Returns:
            Description string, or None if no undo available
        """
        if self.can_undo():
            return self._undo_stack[-1].description
        return None
    
    def get_redo_description(self) -> Optional[str]:
        """Get description of action that would be redone.
        
        Returns:
            Description string, or None if no redo available
        """
        if self.can_redo():
            return self._redo_stack[-1].description
        return None
    
    def clear(self):
        """Clear all undo/redo history.
        
        Call when loading new document or resetting editor.
        """
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._transaction_snapshot = None
        self._transaction_description = ""
        self._notify_observers()
    
    # ─────────────────────────────────────────────────────────────
    # DIAGNOSTICS & DEBUGGING
    # ─────────────────────────────────────────────────────────────
    
    def get_memory_usage(self) -> int:
        """Get total memory used by history in bytes.
        
        Returns:
            Approximate memory footprint
        """
        total = 0
        for state in self._undo_stack:
            total += state.get_size_bytes()
        for state in self._redo_stack:
            total += state.get_size_bytes()
        return total
    
    def get_history_info(self) -> dict:
        """Get diagnostic information about history state.
        
        Useful for debugging and performance monitoring.
        
        Returns:
            Dictionary containing history statistics
        """
        return {
            'undo_steps': len(self._undo_stack),
            'redo_steps': len(self._redo_stack),
            'memory_bytes': self.get_memory_usage(),
            'memory_mb': self.get_memory_usage() / (1024 * 1024),
            'max_size': self._max_size,
            'in_transaction': self._transaction_snapshot is not None,
            'transaction_desc': self._transaction_description if self._transaction_snapshot else None,
        }
    
    def print_history_info(self):
        """Print diagnostic information to console.
        
        For debugging - shows current history state.
        """
        info = self.get_history_info()
        print(f"=== History State ===")
        print(f"Undo steps: {info['undo_steps']}")
        print(f"Redo steps: {info['redo_steps']}")
        print(f"Memory usage: {info['memory_mb']:.2f} MB")
        print(f"Max size: {info['max_size']}")
        print(f"In transaction: {info['in_transaction']}")
        if info['transaction_desc']:
            print(f"Transaction: {info['transaction_desc']}")

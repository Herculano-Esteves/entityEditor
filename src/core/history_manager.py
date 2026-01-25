"""
History Manager for undo/redo functionality.

Manages a linear stack of Command objects for undo/redo operations.
"""

from typing import Optional, List
from src.data import Entity
from src.core.command import Command
from src.core.snapshot_command import EntitySnapshotCommand


class HistoryManager:
    """Manages undo/redo history using a linear stack of commands."""
    
    def __init__(self, entity: Optional[Entity] = None, signal_hub=None, max_size: int = 50):
        """
        Initialize the history manager.
        
        Args:
            entity: The entity to manage history for
            signal_hub: Signal hub for notifications
            max_size: Maximum number of commands to keep in history
        """
        self._entity = entity
        self._signal_hub = signal_hub
        self._commands: List[Command] = []
        self._current_index = -1  # Points to current command (-1 means no commands)
        self._max_size = max_size
        self._pending_snapshot = None  # For begin_change/end_change pattern
    
    def set_entity(self, entity: Optional[Entity]):
        """Set the entity and clear history."""
        self._entity = entity
        self.clear()
    
    def execute(self, command: Command):
        """
        Execute a command and add it to history.
        
        Args:
            command: The command to execute
        """
        if not self._entity:
            return
        
        # Discard all redo history (everything after current index)
        self._commands = self._commands[:self._current_index + 1]
        
        # Execute the command
        command.execute(self._entity, self._signal_hub)
        
        # Add to history
        self._commands.append(command)
        
        # Enforce max size by removing oldest commands
        if len(self._commands) > self._max_size:
            self._commands.pop(0)
        else:
            self._current_index += 1
        
        # Notify changes
        if self._signal_hub:
            self._signal_hub.notify_entity_modified()
            self._update_undo_redo_state()
    
    def undo(self) -> bool:
        """
        Undo the last command.
        
        Returns:
            True if undo was performed, False if nothing to undo
        """
        if not self.can_undo():
            return False
        
        # Undo current command
        command = self._commands[self._current_index]
        command.undo(self._entity, self._signal_hub)
        self._current_index -= 1
        
        # Notify changes
        if self._signal_hub:
            self._signal_hub.notify_entity_modified()
            self._update_undo_redo_state()
        
        return True
    
    def redo(self) -> bool:
        """
        Redo the next command.
        
        Returns:
            True if redo was performed, False if nothing to redo
        """
        if not self.can_redo():
            return False
        
        # Redo next command
        self._current_index += 1
        command = self._commands[self._current_index]
        command.execute(self._entity, self._signal_hub)
        
        # Notify changes
        if self._signal_hub:
            self._signal_hub.notify_entity_modified()
            self._update_undo_redo_state()
        
        return True
    
    def can_undo(self) -> bool:
        """Check if undo is available."""
        return self._current_index >= 0
    
    def can_redo(self) -> bool:
        """Check if redo is available."""
        return self._current_index < len(self._commands) - 1
    
    def get_undo_description(self) -> Optional[str]:
        """Get description of the command that would be undone."""
        if self.can_undo():
            return self._commands[self._current_index].get_description()
        return None
    
    def get_redo_description(self) -> Optional[str]:
        """Get description of the command that would be redone."""
        if self.can_redo():
            return self._commands[self._current_index + 1].get_description()
        return None
    
    def clear(self):
        """Clear all history."""
        self._commands.clear()
        self._current_index = -1
        if self._signal_hub:
            self._update_undo_redo_state()
    
    def get_history_size(self) -> int:
        """Get the current number of commands in history."""
        return len(self._commands)
    
    def set_max_size(self, max_size: int):
        """
        Set the maximum history size.
        
        Args:
            max_size: New maximum size (must be > 0)
        """
        if max_size <= 0:
            raise ValueError("Max size must be greater than 0")
        
        self._max_size = max_size
        
        # Trim history if needed
        if len(self._commands) > max_size:
            # Remove oldest commands
            num_to_remove = len(self._commands) - max_size
            self._commands = self._commands[num_to_remove:]
            self._current_index -= num_to_remove
            if self._current_index < -1:
                self._current_index = -1
            
            if self._signal_hub:
                self._update_undo_redo_state()
    
    def begin_change(self, description: str = "Change"):
        """Begin tracking a change. Call before making modifications."""
        if self._entity and not self._pending_snapshot:
            self._pending_snapshot = EntitySnapshotCommand(self._entity, description)
    
    def end_change(self):
        """End tracking and save the change. Call after modifications complete."""
        if self._pending_snapshot and self._entity:
            self._pending_snapshot.finalize(self._entity)
            
            # Discard redo history
            self._commands = self._commands[:self._current_index + 1]
            
            # Add snapshot to history
            self._commands.append(self._pending_snapshot)
            
            # Enforce max size
            if len(self._commands) > self._max_size:
                self._commands.pop(0)
            else:
                self._current_index += 1
            
            self._pending_snapshot = None
            
            # Update undo/redo state
            if self._signal_hub:
                self._update_undo_redo_state()
    
    def cancel_change(self):
        """Cancel a pending change without saving it."""
        self._pending_snapshot = None
    
    def _update_undo_redo_state(self):
        """Notify signal hub of undo/redo availability."""
        if self._signal_hub:
            self._signal_hub.notify_undo_redo_state_changed(
                self.can_undo(),
                self.can_redo(),
                self.get_undo_description(),
                self.get_redo_description()
            )

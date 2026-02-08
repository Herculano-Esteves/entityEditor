from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtCore import Qt
from src.tools.entity_editor.core.command import RemoveBodyPartsCommand, RemoveHitboxCommand

class InputManager:
    """
    Centralized input manager for the Entity Editor.
    Handles shortcuts and input events that trigger global commands.
    """
    
    def __init__(self, state):
        self._state = state
        self._shortcuts = []
        
    def get_shortcut(self, action_name: str) -> QKeySequence:
        """Get the standard shortcut for a named action."""
        shortcuts = {
            'new': QKeySequence.New,
            'open': QKeySequence.Open,
            'save': QKeySequence.Save,
            'save_as': QKeySequence.SaveAs,
            'quit': QKeySequence.Quit,
            'undo': QKeySequence.Undo,
            'redo': QKeySequence.Redo,
            'delete': QKeySequence.Delete
        }
        return shortcuts.get(action_name)

    def setup_shortcuts(self, widget):
        """Register shortcuts on the given widget."""
        
        # Delete / Backspace
        self._add_shortcut(widget, self.get_shortcut('delete'), self.delete_selection)
        self._add_shortcut(widget, QKeySequence(Qt.Key_Backspace), self.delete_selection)
        
    def _add_shortcut(self, widget, key, callback):
        if not key: return
        shortcut = QShortcut(key, widget)
        shortcut.activated.connect(callback)
        self._shortcuts.append(shortcut)
        
    def delete_selection(self):
        """Context-sensitive delete action."""
        
        # 1. Hitbox Edit Mode
        if self._state.hitbox_edit_mode:
            hb = self._state.selection.selected_hitbox
            # Do NOT rely on selected_body_part. Find the actual parent.
            if hb and self._state.current_entity:
                parent_bp = None
                for bp in self._state.current_entity.body_parts:
                    if hb in bp.hitboxes:
                        parent_bp = bp
                        break
                
                if parent_bp:
                    if self._state.history:
                        self._state.history.execute(RemoveHitboxCommand(parent_bp, hb))
                    else:
                        # Fallback if no history
                        parent_bp.remove_hitbox(hb)
                        from src.tools.entity_editor.core import get_signal_hub
                        get_signal_hub().notify_hitbox_removed(hb)
            return

        # 2. Body Part Selection
        # Use selected_body_parts list if available (for multi-select)
        # If not available (state doesn't track list yet?), use selected_body_part
        
        # State.selection usually has selected_body_parts (list)
        selected_bps = self._state.selection.selected_body_parts
        if not selected_bps and self._state.selection.selected_body_part:
            selected_bps = [self._state.selection.selected_body_part]
            
        if selected_bps:
            if self._state.history:
                self._state.history.execute(RemoveBodyPartsCommand(selected_bps))
            else:
                # Fallback
                from src.tools.entity_editor.core import get_signal_hub
                for bp in selected_bps:
                    if bp in self._state.current_entity.body_parts:
                        self._state.current_entity.remove_body_part(bp)
                        get_signal_hub().notify_bodypart_removed(bp)

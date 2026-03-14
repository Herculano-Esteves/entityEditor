"""
Centralized input manager for the Entity Editor.
Handles shortcuts and input events that trigger global editor actions.
"""

import logging

from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtCore import Qt

from src.tools.entity_editor.core.signal_hub import get_signal_hub

logger = logging.getLogger(__name__)


class InputManager:
    """
    Handles keyboard shortcuts and input events for the Entity Editor.
    All operations are direct state mutations — no undo/redo.
    """

    def __init__(self, state) -> None:
        self._state = state
        self._shortcuts: list[QShortcut] = []

    def get_shortcut(self, action_name: str) -> QKeySequence:
        """Get the standard shortcut for a named action."""
        shortcuts = {
            "new": QKeySequence.New,
            "open": QKeySequence.Open,
            "save": QKeySequence.Save,
            "save_as": QKeySequence.SaveAs,
            "quit": QKeySequence.Quit,
            "delete": QKeySequence.Delete,
        }
        return shortcuts.get(action_name)

    def setup_shortcuts(self, widget) -> None:
        """Register shortcuts on the given widget."""
        self._add_shortcut(widget, self.get_shortcut("delete"), self.delete_selection)
        self._add_shortcut(widget, QKeySequence(Qt.Key_Backspace), self.delete_selection)

    def _add_shortcut(self, widget, key: QKeySequence, callback) -> None:
        if not key:
            return
        shortcut = QShortcut(key, widget)
        shortcut.activated.connect(callback)
        self._shortcuts.append(shortcut)

    def delete_selection(self) -> None:
        """Context-sensitive delete: removes the selected hitbox or body part(s)."""
        hub = get_signal_hub()

        # 1. Hitbox edit mode — delete the selected hitbox
        if self._state.hitbox_edit_mode:
            hb = self._state.selection.selected_hitbox
            if hb and self._state.current_entity:
                for bp in self._state.current_entity.body_parts:
                    if hb in bp.hitboxes:
                        bp.hitboxes.remove(hb)
                        self._state.selection.deselect_hitbox()
                        hub.notify_hitbox_removed(hb)
                        hub.notify_entity_modified()
                        logger.debug("Deleted hitbox '%s'", hb.name)
                        break
            return

        # 2. Body part selection — delete all selected body parts
        selected_bps = self._state.selection.selected_body_parts
        if not selected_bps and self._state.selection.selected_body_part:
            selected_bps = [self._state.selection.selected_body_part]

        if selected_bps and self._state.current_entity:
            for bp in list(selected_bps):
                if bp in self._state.current_entity.body_parts:
                    self._state.current_entity.body_parts.remove(bp)
                    hub.notify_bodypart_removed(bp)
                    logger.debug("Deleted body part '%s'", bp.name)
            self._state.selection.clear_selection()
            hub.notify_entity_modified()

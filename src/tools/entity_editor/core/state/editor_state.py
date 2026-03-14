from typing import Optional
from PySide6.QtCore import QObject, Signal

from src.tools.entity_editor.data import Entity, BodyPart, Hitbox
from src.tools.entity_editor.core.signal_hub import get_signal_hub
from src.tools.entity_editor.core.state.selection import Selection


class EditorState(QObject):
    """
    Central service for managing the editor's state.

    This class is the single source of truth for:
    - The current loaded Entity
    - The active selection (via Selection service)

    Undo/redo has been intentionally removed.
    """

    _instance = None

    # Signals
    entity_changed = Signal(object)       # New entity loaded
    hitbox_edit_mode_changed = Signal(bool)
    selection_on_top_changed = Signal(bool)

    def __new__(cls) -> "EditorState":
        if cls._instance is None:
            cls._instance = super(EditorState, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized") and self._initialized:
            return

        super().__init__()
        self._entity: Optional[Entity] = None
        self._current_filepath: Optional[str] = None
        self._selection = Selection()
        self._signal_hub = get_signal_hub()
        self._hitbox_edit_mode = False
        self._selection_on_top = True
        self._grid_visible = True
        self._grid_size = 16
        self._initialized = True

    # --- Selection ---

    @property
    def selection(self) -> Selection:
        """Access the selection service."""
        return self._selection

    # --- Entity ---

    @property
    def current_entity(self) -> Optional[Entity]:
        """Access the current loaded entity."""
        return self._entity

    def get_entity(self) -> Optional[Entity]:
        """Get the current loaded entity."""
        return self._entity

    @property
    def current_filepath(self) -> Optional[str]:
        return self._current_filepath

    def set_current_filepath(self, filepath: Optional[str]) -> None:
        self._current_filepath = filepath

    def set_entity(self, entity: Optional[Entity]) -> None:
        """
        Set the current entity.
        This is the ONLY way the active entity should be changed.
        """
        self._entity = entity
        self.entity_changed.emit(entity)
        self._signal_hub.notify_entity_loaded(entity)

    def update_entity(self) -> None:
        """Notify that the entity has been modified."""
        self._signal_hub.notify_entity_modified()

    # --- Hitbox Edit Mode ---

    @property
    def hitbox_edit_mode(self) -> bool:
        return self._hitbox_edit_mode

    def set_hitbox_edit_mode(self, enabled: bool) -> None:
        if self._hitbox_edit_mode != enabled:
            self._hitbox_edit_mode = enabled
            self.hitbox_edit_mode_changed.emit(enabled)
            self._signal_hub.notify_hitbox_edit_mode_changed(enabled)

    # --- Selection On Top ---

    @property
    def selection_on_top(self) -> bool:
        return self._selection_on_top

    def set_selection_on_top(self, enabled: bool) -> None:
        if self._selection_on_top != enabled:
            self._selection_on_top = enabled
            self.selection_on_top_changed.emit(enabled)

    # --- Grid Settings ---

    grid_changed = Signal(bool, int)  # visible, size

    @property
    def grid_visible(self) -> bool:
        return self._grid_visible

    @property
    def grid_size(self) -> int:
        return self._grid_size

    def set_grid_settings(self, visible: bool, size: int) -> None:
        self._grid_visible = visible
        self._grid_size = size
        self.grid_changed.emit(visible, size)

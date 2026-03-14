"""
Hitbox Editor Panel for Entity Editor.

Panel for managing and editing hitboxes attached to body parts.
"""

import copy
import logging

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QGroupBox, QFormLayout, QLineEdit, QPushButton, QSpinBox,
    QComboBox, QCheckBox, QLabel,
)
from PySide6.QtCore import Qt

from src.tools.entity_editor.data import Entity, Hitbox, Vec2, HitboxShape
from src.tools.entity_editor.core import get_signal_hub
from src.tools.entity_editor.core.state.editor_state import EditorState
from src.tools.entity_editor.core.naming_utils import generate_unique_name

logger = logging.getLogger(__name__)


class HitboxPanel(QWidget):
    """Panel for managing hitboxes attached to the selected body part."""

    HITBOX_TYPES = ["collision", "damage", "trigger", "interaction", "custom"]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self._state = EditorState()
        self._updating_ui = False

        self._setup_ui()
        self._connect_signals()

        self._refresh_list()
        self._update_properties()

    def _setup_ui(self) -> None:
        """Set up the UI layout."""
        layout = QVBoxLayout(self)

        # Info label
        self._info_label = QLabel("Hitboxes for selected body part:")
        layout.addWidget(self._info_label)

        # Hitbox list
        self._hitbox_list = QListWidget()
        self._hitbox_list.itemSelectionChanged.connect(self._on_list_selection_changed)
        layout.addWidget(self._hitbox_list)

        # Buttons
        buttons_layout = QHBoxLayout()

        self._edit_mode_check = QCheckBox("Edit Hitboxes")
        self._edit_mode_check.toggled.connect(self._on_edit_mode_changed)
        self._edit_mode_check.setToolTip("Enable hitbox editing mode in viewport")
        buttons_layout.addWidget(self._edit_mode_check)

        buttons_layout.addStretch()

        self._add_btn = QPushButton("Add")
        self._add_btn.clicked.connect(self._on_add_hitbox)
        buttons_layout.addWidget(self._add_btn)

        self._duplicate_btn = QPushButton("Duplicate")
        self._duplicate_btn.clicked.connect(self._on_duplicate_hitbox)
        buttons_layout.addWidget(self._duplicate_btn)

        self._remove_btn = QPushButton("Remove")
        self._remove_btn.clicked.connect(self._on_remove_hitbox)
        buttons_layout.addWidget(self._remove_btn)

        layout.addLayout(buttons_layout)

        # Properties group
        self._props_group = QGroupBox("Hitbox Properties")
        props_layout = QFormLayout()

        self._name_edit = QLineEdit()
        self._name_edit.editingFinished.connect(self._on_name_changed)
        props_layout.addRow("Name:", self._name_edit)

        self._type_combo = QComboBox()
        self._type_combo.addItems(self.HITBOX_TYPES)
        self._type_combo.currentTextChanged.connect(self._on_type_changed)
        props_layout.addRow("Type:", self._type_combo)

        self._shape_combo = QComboBox()
        self._shape_combo.addItems(["Rectangle", "Circle"])
        self._shape_combo.currentIndexChanged.connect(self._on_shape_changed)
        props_layout.addRow("Shape:", self._shape_combo)

        self._pos_x_spin = QSpinBox()
        self._pos_x_spin.setRange(-10000, 10000)
        self._pos_x_spin.valueChanged.connect(lambda v: self._on_property_changing("x", v))
        props_layout.addRow("X (px):", self._pos_x_spin)

        self._pos_y_spin = QSpinBox()
        self._pos_y_spin.setRange(-10000, 10000)
        self._pos_y_spin.valueChanged.connect(lambda v: self._on_property_changing("y", v))
        props_layout.addRow("Y (px):", self._pos_y_spin)

        self._width_spin = QSpinBox()
        self._width_spin.setRange(1, 10000)
        self._width_spin.valueChanged.connect(lambda v: self._on_property_changing("w", v))
        self._width_label = QLabel("Width (px):")
        props_layout.addRow(self._width_label, self._width_spin)

        self._height_spin = QSpinBox()
        self._height_spin.setRange(1, 10000)
        self._height_spin.valueChanged.connect(lambda v: self._on_property_changing("h", v))
        self._height_label = QLabel("Height (px):")
        props_layout.addRow(self._height_label, self._height_spin)

        self._radius_spin = QSpinBox()
        self._radius_spin.setRange(1, 10000)
        self._radius_spin.valueChanged.connect(lambda v: self._on_property_changing("r", v))
        self._radius_label = QLabel("Radius (px):")
        props_layout.addRow(self._radius_label, self._radius_spin)

        self._enabled_check = QCheckBox("Enabled")
        self._enabled_check.toggled.connect(lambda v: self._on_property_changing("enabled", v))
        props_layout.addRow("", self._enabled_check)

        self._props_group.setLayout(props_layout)
        layout.addWidget(self._props_group)

        layout.addStretch()

        self._update_properties_enabled()

    def _connect_signals(self) -> None:
        if hasattr(self._state.selection, "selection_changed"):
            self._state.selection.selection_changed.connect(self._on_state_selection_changed)

        hub = get_signal_hub()
        hub.entity_loaded.connect(lambda e: self._refresh_list())
        hub.bodyparts_selection_changed.connect(lambda s: self._refresh_list())
        hub.hitbox_added.connect(lambda h: self._refresh_list())
        hub.hitbox_removed.connect(lambda h: self._refresh_list())
        hub.hitbox_modified.connect(self._on_hitbox_modified)
        hub.hitbox_selected.connect(self._on_external_hitbox_selected)

    def _refresh_list(self) -> None:
        """Rebuild the hitbox list widget from the currently selected body part."""
        scroll_val = self._hitbox_list.verticalScrollBar().value()

        self._hitbox_list.blockSignals(True)
        self._hitbox_list.clear()

        bp = self._state.selection.selected_body_part
        if not bp:
            self._info_label.setText("No body part selected.")
            self._hitbox_list.setEnabled(False)
            self._add_btn.setEnabled(False)
        else:
            self._info_label.setText(f"Hitboxes for: {bp.name}")
            self._hitbox_list.setEnabled(True)
            self._add_btn.setEnabled(True)

            for hitbox in bp.hitboxes:
                item = QListWidgetItem()
                item.setData(Qt.UserRole, hitbox)
                self._hitbox_list.addItem(item)

                widget = QWidget()
                row_layout = QHBoxLayout(widget)
                row_layout.setContentsMargins(4, 2, 4, 2)
                row_layout.setSpacing(4)

                eye_btn = QPushButton("👁" if hitbox.enabled else "⚫")
                eye_btn.setFixedSize(20, 20)
                eye_btn.setFlat(True)
                eye_btn.clicked.connect(lambda checked, h=hitbox: self._toggle_hitbox_visibility(h))
                row_layout.addWidget(eye_btn)

                name_lbl = QLabel(f"{hitbox.name} ({hitbox.hitbox_type})")
                row_layout.addWidget(name_lbl)
                row_layout.addStretch()

                item.setSizeHint(widget.sizeHint())
                self._hitbox_list.setItemWidget(item, widget)

                if self._state.selection.is_hitbox_selected(hitbox):
                    item.setSelected(True)

        self._hitbox_list.blockSignals(False)
        self._hitbox_list.verticalScrollBar().setValue(scroll_val)
        self._update_properties_enabled()

    def _on_list_selection_changed(self) -> None:
        items = self._hitbox_list.selectedItems()
        if items:
            hitbox = items[0].data(Qt.UserRole)
            self._state.selection.select_hitbox(hitbox)
        else:
            self._state.selection.deselect_hitbox()
        self._update_properties()

    def _on_state_selection_changed(self) -> None:
        self._hitbox_list.blockSignals(True)
        self._hitbox_list.clearSelection()

        hb = self._state.selection.selected_hitbox
        if hb:
            for i in range(self._hitbox_list.count()):
                item = self._hitbox_list.item(i)
                if item.data(Qt.UserRole) == hb:
                    item.setSelected(True)
                    break

        self._hitbox_list.blockSignals(False)
        self._update_properties()

    def _on_external_hitbox_selected(self, hitbox) -> None:
        if hitbox != self._state.selection.selected_hitbox:
            self._state.selection.select_hitbox(hitbox)

    def _update_properties(self) -> None:
        self._updating_ui = True
        hb = self._state.selection.selected_hitbox

        if hb:
            self._name_edit.setText(hb.name)
            self._type_combo.setCurrentText(hb.hitbox_type)
            self._shape_combo.setCurrentIndex(int(hb.shape))
            self._pos_x_spin.setValue(hb.x)
            self._pos_y_spin.setValue(hb.y)
            self._width_spin.setValue(hb.width)
            self._height_spin.setValue(hb.height)
            self._radius_spin.setValue(hb.radius)

            is_circle = (hb.shape == HitboxShape.CIRCLE)
            self._width_spin.setVisible(not is_circle)
            self._width_label.setVisible(not is_circle)
            self._height_spin.setVisible(not is_circle)
            self._height_label.setVisible(not is_circle)
            self._radius_spin.setVisible(is_circle)
            self._radius_label.setVisible(is_circle)

            self._enabled_check.setChecked(hb.enabled)
            self._props_group.setEnabled(True)
            self._props_group.setTitle(f"Properties: {hb.name}")
        else:
            self._name_edit.clear()
            self._props_group.setEnabled(False)
            self._props_group.setTitle("Hitbox Properties (None Selected)")

        self._updating_ui = False
        self._update_properties_enabled()

    def _update_properties_enabled(self) -> None:
        has_sel = (self._state.selection.selected_hitbox is not None)
        self._remove_btn.setEnabled(has_sel)
        self._duplicate_btn.setEnabled(has_sel)

    # --- Actions ---

    def _toggle_hitbox_visibility(self, hitbox: Hitbox) -> None:
        hitbox.enabled = not hitbox.enabled
        get_signal_hub().notify_hitbox_modified(hitbox)
        if hitbox == self._state.selection.selected_hitbox:
            self._update_properties()
        self._refresh_list()

    def _on_add_hitbox(self) -> None:
        bp = self._state.selection.selected_body_part
        if not bp:
            return

        count = len(bp.hitboxes)
        hb = Hitbox(f"Hitbox_{count}", 0, 0, 32, 32)
        bp.hitboxes.append(hb)
        get_signal_hub().notify_hitbox_added(hb)
        # Select the new hitbox so the properties panel shows it immediately
        self._state.selection.select_hitbox(hb)
        self._refresh_list()
        logger.debug("Added hitbox '%s' to '%s'", hb.name, bp.name)

    def _on_remove_hitbox(self) -> None:
        hb = self._state.selection.selected_hitbox
        bp = self._state.selection.selected_body_part
        if not hb or not bp:
            return

        if hb in bp.hitboxes:
            bp.hitboxes.remove(hb)
        self._state.selection.deselect_hitbox()
        get_signal_hub().notify_hitbox_removed(hb)
        self._refresh_list()
        logger.debug("Removed hitbox '%s' from '%s'", hb.name, bp.name)

    def _on_duplicate_hitbox(self) -> None:
        hb = self._state.selection.selected_hitbox
        bp = self._state.selection.selected_body_part
        if not hb or not bp:
            return

        new_hb = copy.deepcopy(hb)
        existing_names = {h.name for h in bp.hitboxes}
        new_hb.name = generate_unique_name(hb.name, existing_names)

        try:
            insert_index = bp.hitboxes.index(hb) + 1
            bp.hitboxes.insert(insert_index, new_hb)
        except ValueError:
            bp.hitboxes.append(new_hb)

        get_signal_hub().notify_hitbox_added(new_hb)
        self._state.selection.select_hitbox(new_hb)
        self._refresh_list()
        logger.debug("Duplicated hitbox '%s' -> '%s'", hb.name, new_hb.name)

    def _on_edit_mode_changed(self, enabled: bool) -> None:
        self._state.set_hitbox_edit_mode(enabled)

    # --- Property Editing ---

    def _on_property_changing(self, prop: str, value) -> None:
        if self._updating_ui:
            return
        hb = self._state.selection.selected_hitbox
        if not hb:
            return

        if prop == "x":
            hb.x = value
        elif prop == "y":
            hb.y = value
        elif prop == "w":
            hb.width = value
        elif prop == "h":
            hb.height = value
        elif prop == "r":
            hb.radius = value
        elif prop == "enabled":
            hb.enabled = value

        get_signal_hub().notify_hitbox_modified(hb)
        get_signal_hub().notify_entity_modified()

    def _on_name_changed(self) -> None:
        if self._updating_ui:
            return
        hb = self._state.selection.selected_hitbox
        bp = self._state.selection.selected_body_part

        if hb and bp and hb.name != self._name_edit.text():
            new_name = self._name_edit.text()
            existing_names = {h.name for h in bp.hitboxes if h != hb}
            unique_name = generate_unique_name(new_name, existing_names)

            if unique_name != new_name:
                self._name_edit.setText(unique_name)

            hb.name = unique_name
            get_signal_hub().notify_hitbox_modified(hb)
            get_signal_hub().notify_entity_modified()
            self._refresh_list()

    def _on_type_changed(self, text: str) -> None:
        if self._updating_ui:
            return
        hb = self._state.selection.selected_hitbox
        if hb:
            hb.hitbox_type = text
            get_signal_hub().notify_hitbox_modified(hb)
            get_signal_hub().notify_entity_modified()
            self._refresh_list()

    def _on_shape_changed(self, index: int) -> None:
        if self._updating_ui:
            return
        hb = self._state.selection.selected_hitbox
        if hb:
            hb.shape = HitboxShape(index)
            get_signal_hub().notify_hitbox_modified(hb)
            self._update_properties()

    def _on_hitbox_modified(self, hb) -> None:
        if hb == self._state.selection.selected_hitbox:
            self._update_properties()

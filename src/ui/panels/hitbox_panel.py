"""
Hitbox Editor Panel for Entity Editor.

Panel for managing and editing hitboxes.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QGroupBox, QFormLayout, QLineEdit, QPushButton, QSpinBox,
    QComboBox, QCheckBox, QLabel
)
from PySide6.QtCore import Qt
import sys
import os
import copy

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.data import Entity, Hitbox, Vec2
from src.core import get_signal_hub, AddHitboxCommand, RemoveHitboxCommand, ModifyHitboxCommand
from src.core import get_signal_hub, AddHitboxCommand, RemoveHitboxCommand, ModifyHitboxCommand
from src.core.state.editor_state import EditorState
from src.core.naming_utils import generate_unique_name, ensure_unique_name

class HitboxPanel(QWidget):
    """Panel for managing hitboxes."""
    
    HITBOX_TYPES = ["collision", "damage", "trigger", "interaction", "custom"]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._state = EditorState()
        self._updating_ui = False
        
        self._setup_ui()
        self._connect_signals()
        
        self._refresh_list()
        self._update_properties()
    
    def _setup_ui(self):
        """Setup the UI layout."""
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
        
        # Edit mode toggle
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
        
        # Name
        self._name_edit = QLineEdit()
        self._name_edit.editingFinished.connect(self._on_name_changed)
        props_layout.addRow("Name:", self._name_edit)
        
        # Type
        self._type_combo = QComboBox()
        self._type_combo.addItems(self.HITBOX_TYPES)
        self._type_combo.currentTextChanged.connect(self._on_type_changed)
        props_layout.addRow("Type:", self._type_combo)
        
        # Position (integers only)
        self._pos_x_spin = QSpinBox()
        self._pos_x_spin.setRange(-10000, 10000)
        self._pos_x_spin.valueChanged.connect(lambda v: self._on_property_changing('x', v))
        props_layout.addRow("X (px):", self._pos_x_spin)
        
        self._pos_y_spin = QSpinBox()
        self._pos_y_spin.setRange(-10000, 10000)
        self._pos_y_spin.valueChanged.connect(lambda v: self._on_property_changing('y', v))
        props_layout.addRow("Y (px):", self._pos_y_spin)
        
        # Size
        self._width_spin = QSpinBox()
        self._width_spin.setRange(1, 10000)
        self._width_spin.valueChanged.connect(lambda v: self._on_property_changing('w', v))
        props_layout.addRow("Width (px):", self._width_spin)
        
        self._height_spin = QSpinBox()
        self._height_spin.setRange(1, 10000)
        self._height_spin.valueChanged.connect(lambda v: self._on_property_changing('h', v))
        props_layout.addRow("Height (px):", self._height_spin)
        
        # Enabled
        self._enabled_check = QCheckBox("Enabled")
        self._enabled_check.toggled.connect(lambda v: self._on_property_changing('enabled', v))
        props_layout.addRow("", self._enabled_check)
        
        self._props_group.setLayout(props_layout)
        layout.addWidget(self._props_group)
        
        layout.addStretch()
        
        self._update_properties_enabled()

    def _connect_signals(self):
        # State signals
        if hasattr(self._state.selection, "selection_changed"):
             self._state.selection.selection_changed.connect(self._on_state_selection_changed)
        
        # Hub signals
        hub = get_signal_hub()
        hub.entity_loaded.connect(lambda e: self._refresh_list())
        hub.bodyparts_selection_changed.connect(lambda s: self._refresh_list()) # Refresh when selected BP changes
        hub.hitbox_added.connect(lambda h: self._refresh_list())
        hub.hitbox_removed.connect(lambda h: self._refresh_list())
        hub.hitbox_modified.connect(self._on_hitbox_modified)
        hub.hitbox_selected.connect(self._on_external_hitbox_selected)

    def _refresh_list(self):
        self._hitbox_list.blockSignals(True)
    def _refresh_list(self):
        # Save scroll position
        scroll_val = self._hitbox_list.verticalScrollBar().value()
        
        self._hitbox_list.blockSignals(True)
        self._hitbox_list.clear()
        
        # Determined by selected body part
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
                
                # Custom Widget
                widget = QWidget()
                layout = QHBoxLayout(widget)
                layout.setContentsMargins(4, 2, 4, 2)
                layout.setSpacing(4)
                
                # Eye Button
                eye_btn = QPushButton("👁" if hitbox.enabled else "⚫")
                eye_btn.setFixedSize(20, 20)
                eye_btn.setFlat(True)
                eye_btn.clicked.connect(lambda checked, h=hitbox: self._toggle_hitbox_visibility(h))
                layout.addWidget(eye_btn)
                
                # Label
                name_lbl = QLabel(f"{hitbox.name} ({hitbox.hitbox_type})")
                layout.addWidget(name_lbl)
                layout.addStretch()
                
                item.setSizeHint(widget.sizeHint())
                self._hitbox_list.setItemWidget(item, widget)
                
                if self._state.selection.is_hitbox_selected(hitbox):
                    item.setSelected(True)
            
            # Also show Entity Hitboxes if any?
            # Current Panel logic seemed focused on BodyPart hitboxes or mixed?
            # Looking at original file: `_selected_bodypart` was used.
            # If `_selected_bodypart` is None, it might show Entity hitboxes?
            # Let's stick to BodyPart hitboxes for now, or check logical flow.
            # If no BP selected, maybe show Entity Hitboxes?
            if not bp and self._state.current_entity and hasattr(self._state.current_entity, 'entity_hitboxes'):
                 # Show entity hitboxes logic if needed
                 pass

        self._hitbox_list.blockSignals(False)
        
        # Restore scroll position
        if scroll_val is not None:
            self._hitbox_list.verticalScrollBar().setValue(scroll_val)
            
        self._update_properties_enabled()

    def _on_list_selection_changed(self):
        items = self._hitbox_list.selectedItems()
        if items:
            hitbox = items[0].data(Qt.UserRole)
            self._state.selection.select_hitbox(hitbox)
        else:
            self._state.selection.deselect_hitbox()
            
        self._update_properties()

    def _on_state_selection_changed(self):
        # Sync list selection
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
        
        # If BodyPart changed, list is refreshed via hub signal `bodyparts_selection_changed`, so we are good.

    def _on_external_hitbox_selected(self, hitbox):
        # Triggered by signal hub (e.g. from Viewport)
        # Should be covered by state selection change, but if not:
        if hitbox != self._state.selection.selected_hitbox:
            self._state.selection.select_hitbox(hitbox)

    def _update_properties(self):
        self._updating_ui = True
        hb = self._state.selection.selected_hitbox
        
        if hb:
            self._name_edit.setText(hb.name)
            self._type_combo.setCurrentText(hb.hitbox_type)
            self._pos_x_spin.setValue(hb.x)
            self._pos_y_spin.setValue(hb.y)
            self._width_spin.setValue(hb.width)
            self._height_spin.setValue(hb.height)
            self._enabled_check.setChecked(hb.enabled)
            
            self._props_group.setEnabled(True)
            self._props_group.setTitle(f"Properties: {hb.name}")
        else:
            self._name_edit.clear()
            self._props_group.setEnabled(False)
            self._props_group.setTitle("Hitbox Properties (None Selected)")
            
        self._updating_ui = False
        self._update_properties_enabled()

    def _update_properties_enabled(self):
        has_sel = (self._state.selection.selected_hitbox is not None)
        self._remove_btn.setEnabled(has_sel)
        self._duplicate_btn.setEnabled(has_sel)

    # --- Actions ---

    def _toggle_hitbox_visibility(self, hitbox):
        hitbox.enabled = not hitbox.enabled
        get_signal_hub().notify_hitbox_modified(hitbox)
        # Update UI property if selected
        if hitbox == self._state.selection.selected_hitbox:
            self._update_properties()
        # Refresh list to update icon
        self._refresh_list()

    def _on_add_hitbox(self):
        bp = self._state.selection.selected_body_part
        if not bp: return
        
        count = len(bp.hitboxes)
        hb = Hitbox(f"Hitbox_{count}", 0, 0, 32, 32)
        
        if self._state.history:
            self._state.history.execute(AddHitboxCommand(bp, hb))
        else:
            bp.add_hitbox(hb)
            get_signal_hub().notify_hitbox_added(hb)

    def _on_remove_hitbox(self):
        hb = self._state.selection.selected_hitbox
        bp = self._state.selection.selected_body_part
        if not hb or not bp: return # Assuming Hitbox belongs to selected BP
        
        if self._state.history:
            self._state.history.execute(RemoveHitboxCommand(bp, hb))
        else:
            bp.remove_hitbox(hb)
            get_signal_hub().notify_hitbox_removed(hb)

    def _on_duplicate_hitbox(self):
        hb = self._state.selection.selected_hitbox
        bp = self._state.selection.selected_body_part
        if not hb or not bp: return
        
        new_hb = copy.deepcopy(hb)
        existing_names = {h.name for h in bp.hitboxes}
        new_hb.name = generate_unique_name(hb.name, existing_names)
        # Offset removed as per user request
        # new_hb.x += 10
        # new_hb.y += 10
        
        # Find insertion index
        try:
            current_index = bp.hitboxes.index(hb)
            insert_index = current_index + 1
        except ValueError:
            insert_index = -1
        
        if self._state.history:
            self._state.history.execute(AddHitboxCommand(bp, new_hb, insert_index))
        else:
            if insert_index >= 0:
                bp.hitboxes.insert(insert_index, new_hb)
            else:
                bp.add_hitbox(new_hb)
            get_signal_hub().notify_hitbox_added(new_hb)

    def _on_edit_mode_changed(self, enabled):
        self._state.set_hitbox_edit_mode(enabled)

    # --- Property Editing ---

    def _on_property_changing(self, prop, value):
        if self._updating_ui: return
        hb = self._state.selection.selected_hitbox
        if not hb: return
        
        # Direct modify for preview
        # TODO: Better Undo support (begin_change / end_change on focus)
        if prop == 'x': hb.x = value
        elif prop == 'y': hb.y = value
        elif prop == 'w': hb.width = value
        elif prop == 'h': hb.height = value
        elif prop == 'enabled': hb.enabled = value
        
        get_signal_hub().notify_hitbox_modified(hb)

    def _on_name_changed(self):
        if self._updating_ui: return
        hb = self._state.selection.selected_hitbox
        bp = self._state.selection.selected_body_part
        
        if hb and bp and hb.name != self._name_edit.text():
            new_name = self._name_edit.text()
            existing_names = {h.name for h in bp.hitboxes if h != hb}
            
            unique_name = ensure_unique_name(new_name, existing_names)
            
            if unique_name != new_name:
                self._name_edit.setText(unique_name)
            
            hb.name = unique_name
            get_signal_hub().notify_hitbox_modified(hb)
            self._refresh_list()

    def _on_type_changed(self, text):
        if self._updating_ui: return
        hb = self._state.selection.selected_hitbox
        if hb:
            hb.hitbox_type = text
            get_signal_hub().notify_hitbox_modified(hb)
            self._refresh_list() # Update list label

    def _on_hitbox_modified(self, hb):
        if hb == self._state.selection.selected_hitbox:
            self._update_properties()

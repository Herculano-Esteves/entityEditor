"""
Body Parts Panel for Entity Editor.

Panel for managing and editing body parts.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QGroupBox, QFormLayout, QLineEdit, QPushButton, QSpinBox,
    QLabel, QFileDialog, QCheckBox, QDoubleSpinBox, QComboBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
import sys
import os
import copy
import re


# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.tools.entity_editor.data.entity_data import Entity, BodyPart, Vec2, UVRect, BodyPartType
from src.tools.entity_editor.core.entity_manager import get_entity_manager
from src.tools.entity_editor.core.geometry_utils import calculate_entity_bounds
from src.tools.entity_editor.core import get_signal_hub, AddBodyPartCommand, RemoveBodyPartCommand, RemoveBodyPartsCommand, MoveBodyPartCommand, ModifyBodyPartCommand
from src.tools.entity_editor.core.state.editor_state import EditorState
from src.tools.entity_editor.rendering import get_texture_manager
from src.tools.entity_editor.ui.dialogs.uv_editor_dialog import UVEditorDialog
from src.tools.entity_editor.core.naming_utils import generate_unique_name, ensure_unique_name

class BodyPartsPanel(QWidget):
    """Panel for managing body parts."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # State
        self._state = EditorState()
        self._texture_manager = get_texture_manager()
        
        # State tracking for undo
        self._parameter_change_start_value = None
        self._updating_ui = False
        
        # Isolation State
        self._isolating_bp = None # The body part currently isolated
        self._isolation_snapshot = {} # Map[bp_id, bool] - visibility state before isolation
        
        self._setup_ui()
        self._connect_signals()
        
        # Initial Refresh
        self._refresh_list()
        self._update_properties()
    
    def _setup_ui(self):
        """Setup the UI layout."""
        layout = QVBoxLayout(self)
        
        # Body parts list
        list_label = QLabel("Body Parts:")
        layout.addWidget(list_label)
        
        # Options
        opts_layout = QHBoxLayout()
        self._sel_on_top_check = QCheckBox("Show Selection on Top")
        self._sel_on_top_check.setToolTip("If enabled, selected body part is drawn above others")
        self._sel_on_top_check.setChecked(self._state.selection_on_top)
        self._sel_on_top_check.toggled.connect(self._on_sel_on_top_toggled)
        opts_layout.addWidget(self._sel_on_top_check)
        opts_layout.addStretch()
        layout.addLayout(opts_layout)
        
        self._bodyparts_list = QListWidget()
        self._bodyparts_list.setSelectionMode(QListWidget.ExtendedSelection)  # Enable multi-select
        self._bodyparts_list.setDragDropMode(QListWidget.InternalMove) # Enable reordering
        self._bodyparts_list.model().rowsMoved.connect(self._on_list_reordered) 
        # Note: We handle selection manually to sync with state
        self._bodyparts_list.itemSelectionChanged.connect(self._on_list_selection_changed)
        layout.addWidget(self._bodyparts_list)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        self._add_btn = QPushButton("Add")
        self._add_btn.clicked.connect(self._on_add_bodypart)
        buttons_layout.addWidget(self._add_btn)
        
        self._remove_btn = QPushButton("Remove")
        self._remove_btn.clicked.connect(self._on_remove_bodypart)
        buttons_layout.addWidget(self._remove_btn)
        
        self._rename_btn = QPushButton("Rename")
        self._rename_btn.clicked.connect(self._on_rename_bodypart)
        buttons_layout.addWidget(self._rename_btn)
        
        self._duplicate_btn = QPushButton("Duplicate")
        self._duplicate_btn.clicked.connect(self._on_duplicate_bodypart)
        buttons_layout.addWidget(self._duplicate_btn)
        
        layout.addLayout(buttons_layout)
        
        # Properties group
        self._props_group = QGroupBox("Properties")
        props_layout = QFormLayout()
        
        # Name
        self._name_edit = QLineEdit()
        self._name_edit.editingFinished.connect(self._on_name_changed)
        props_layout.addRow("Name:", self._name_edit)
        
        # Part Type
        self._type_combo = QComboBox()
        self._type_combo.addItems(["Sprite", "Entity Reference"])
        self._type_combo.currentIndexChanged.connect(self._on_type_changed)
        props_layout.addRow("Type:", self._type_combo)

        # Entity Reference (Hidden by default)
        self._ref_combo = QComboBox()
        self._ref_combo.setToolTip("Select Entity to embed")
        self._ref_combo.currentIndexChanged.connect(self._on_entity_ref_changed)
        self._ref_label = QLabel("Entity Ref:")
        props_layout.addRow(self._ref_label, self._ref_combo)
        
        # Position
        self._pos_x_spin = QSpinBox()
        self._pos_x_spin.setRange(-10000, 10000)
        self._pos_x_spin.valueChanged.connect(lambda v: self._on_property_changing('x', v))
        self._pos_x_spin.editingFinished.connect(self._on_property_changed_finished)
        props_layout.addRow("Position X (px):", self._pos_x_spin)
        
        self._pos_y_spin = QSpinBox()
        self._pos_y_spin.setRange(-10000, 10000)
        self._pos_y_spin.valueChanged.connect(lambda v: self._on_property_changing('y', v))
        self._pos_y_spin.editingFinished.connect(self._on_property_changed_finished)
        props_layout.addRow("Position Y (px):", self._pos_y_spin)
        
        # Size
        self._size_x_spin = QSpinBox()
        self._size_x_spin.setRange(1, 10000)
        self._size_x_spin.valueChanged.connect(lambda v: self._on_property_changing('w', v))
        self._size_x_spin.editingFinished.connect(self._on_property_changed_finished)
        props_layout.addRow("Size W (px):", self._size_x_spin)
        
        self._size_y_spin = QSpinBox()
        self._size_y_spin.setRange(1, 10000)
        self._size_y_spin.valueChanged.connect(lambda v: self._on_property_changing('h', v))
        self._size_y_spin.editingFinished.connect(self._on_property_changed_finished)
        props_layout.addRow("Size H (px):", self._size_y_spin)
        
        # Scale (Pixel Scale)
        self._scale_spin = QSpinBox()
        self._scale_spin.setRange(1, 100)
        self._scale_spin.setSuffix("x")
        self._scale_spin.valueChanged.connect(lambda v: self._on_property_changing('scale', v))
        self._scale_spin.editingFinished.connect(self._on_property_changed_finished)
        props_layout.addRow("Pixel Scale:", self._scale_spin)
        
        # Rotation
        self._rot_spin = QSpinBox()
        self._rot_spin.setRange(-360, 360)
        self._rot_spin.setSuffix("°")
        self._rot_spin.valueChanged.connect(lambda v: self._on_property_changing('rot', v))
        self._rot_spin.editingFinished.connect(self._on_property_changed_finished)
        props_layout.addRow("Rotation:", self._rot_spin)
        
        # Z-Order
        self._z_spin = QSpinBox()
        self._z_spin.setRange(-100, 100)
        self._z_spin.valueChanged.connect(lambda v: self._on_property_changing('z', v))
        self._z_spin.editingFinished.connect(self._on_property_changed_finished)
        props_layout.addRow("Z-Order:", self._z_spin)
        
        # Pivot Point
        self._pivot_x_spin = QSpinBox()
        self._pivot_x_spin.setRange(-10000, 10000)
        self._pivot_x_spin.valueChanged.connect(lambda v: self._on_property_changing('pivot_x', v))
        self._pivot_x_spin.editingFinished.connect(self._on_property_changed_finished)
        props_layout.addRow("Pivot X:", self._pivot_x_spin)
        
        self._pivot_y_spin = QSpinBox()
        self._pivot_y_spin.setRange(-10000, 10000)
        self._pivot_y_spin.valueChanged.connect(lambda v: self._on_property_changing('pivot_y', v))
        self._pivot_y_spin.editingFinished.connect(self._on_property_changed_finished)
        props_layout.addRow("Pivot Y:", self._pivot_y_spin)
        
        # Texture (Replaced with ComboBox)
        self._tex_combo = QComboBox()
        self._tex_combo.setToolTip("Select Texture ID from Registry")
        self._tex_combo.currentIndexChanged.connect(self._on_texture_changed)
        self._tex_label = QLabel("Texture ID:")
        props_layout.addRow(self._tex_label, self._tex_combo)
        
        # UV Editor
        self._uv_group = QGroupBox("UV Mapping")
        uv_layout = QVBoxLayout()
        
        uv_btns = QHBoxLayout()
        self._visual_uv_btn = QPushButton("Visual UV Editor")
        self._visual_uv_btn.clicked.connect(self._on_visual_uv_edit)
        uv_btns.addWidget(self._visual_uv_btn)
        
        self._reset_uv_btn = QPushButton("Reset Full")
        self._reset_uv_btn.clicked.connect(self._on_reset_uv)
        uv_btns.addWidget(self._reset_uv_btn)
        
        uv_layout.addLayout(uv_btns)

        # Flip
        flip_layout = QHBoxLayout()
        flip_label = QLabel("Flip:")
        flip_layout.addWidget(flip_label)

        self._flip_x_check = QCheckBox("X")
        self._flip_x_check.toggled.connect(self._on_flip_changed)
        flip_layout.addWidget(self._flip_x_check)
        
        self._flip_y_check = QCheckBox("Y")
        self._flip_y_check.toggled.connect(self._on_flip_changed)
        flip_layout.addWidget(self._flip_y_check)

        flip_layout.addStretch() # align left
        
        uv_layout.addLayout(flip_layout)

        self._uv_group.setLayout(uv_layout)
        props_layout.addRow(self._uv_group)
        
        self._props_group.setLayout(props_layout)
        layout.addWidget(self._props_group)
        
        # Stretch to fill space
        layout.addStretch()
        
        self._update_properties_enabled()

    def _connect_signals(self):
        # Listen to State
        if hasattr(self._state.selection, "selection_changed"):
             self._state.selection.selection_changed.connect(self._on_state_selection_changed)
        
        # SignalHub (for legacy or broader events)
        signal_hub = get_signal_hub()
        signal_hub.entity_loaded.connect(self._on_entity_loaded)
        signal_hub.bodypart_added.connect(lambda _: self._refresh_list())
        signal_hub.bodypart_removed.connect(lambda _: self._refresh_list())
        signal_hub.bodypart_removed.connect(lambda _: self._refresh_list())
        signal_hub.bodypart_reordered.connect(self._refresh_list)
        signal_hub.bodypart_modified.connect(self._on_bodypart_modified)
        signal_hub.referenced_entity_saved.connect(self._on_referenced_entity_saved)
        signal_hub.entity_saved.connect(self._on_global_entity_saved)
            
    def _on_entity_loaded(self, entity):
        self._refresh_list()
        self._update_properties()
        # Auto-refresh geometry for all references on load
        if entity:
            self._validate_all_references(entity)

    def _on_global_entity_saved(self, filepath: str):
        """Called when ANY entity is saved. Refresh list to get new entities in dropdown."""
        # Only refresh properties if we are showing the dropdown, to get the new item.
        # But we don't want to break current selection flow.
        # Ideally just update the combo? 
        # For simplicity, if we have a selection, update properties.
        if self._state.selection.selected_body_part:
            self._update_properties()

    def _on_referenced_entity_saved(self, filepath: str):
        """Called when a referenced entity is saved/updated."""
        entity = self._state.current_entity
        if not entity: return
        
        # Check if we have any parts referencing this
        # We need the name of the saved entity
        name = os.path.splitext(os.path.basename(filepath))[0]
        
        count = 0
        for bp in entity.body_parts:
            if bp.part_type.name == 'ENTITY_REF' and bp.entity_ref == name:
                if self._update_ref_geometry(bp):
                    count += 1
                    
        if count > 0:
            print(f"Updated {count} references to {name}")
            get_signal_hub().notify_entity_modified()
            self._update_properties()

    def _validate_all_references(self, entity):
        """Check all entity references and update geometry if stale."""
        changed = False
        for bp in entity.body_parts:
            if bp.part_type.name == 'ENTITY_REF' and bp.entity_ref:
                if self._update_ref_geometry(bp):
                    changed = True
        
        if changed:
            print("Auto-updated stale entity references on load.")
            # We don't necessarily want to mark as modified immediately on load?
            # User request: "only new imports come with correct area" -> implies they want current file to match.
            # If we mark modified, user knows something changed.
            get_signal_hub().notify_entity_modified()

    def _update_ref_geometry(self, bp) -> bool:
        """
        Update the geometry (size, pivot_offset) of a BodyPart to match its referenced entity.
        Returns True if changes were made.
        """
        if not bp.entity_ref: return False
        
        ref_entity = get_entity_manager().get_entity_def(bp.entity_ref)
        if not ref_entity: return False
        
        min_x, min_y, w, h = calculate_entity_bounds(ref_entity)
        
        # Calculate Target Pivot Offset
        off_x = -(min_x + w/2)
        off_y = -(min_y + h/2)
        
        # We need to preserve the "World Pivot" location of the child entity.
        # Current World Pivot = Pos + Size/2 + CurrentPivotOffset
        current_pivot_x = bp.position.x + bp.size.x/2 + bp.pivot_offset.x
        current_pivot_y = bp.position.y + bp.size.y/2 + bp.pivot_offset.y
        
        # New Pos = WorldPivot - NewSize/2 - NewPivotOffset
        new_pos_x = current_pivot_x - w/2 - off_x
        new_pos_y = current_pivot_y - h/2 - off_y
        
        changed = False
        
        if bp.size.x != w or bp.size.y != h:
            bp.size.x = w
            bp.size.y = h
            changed = True
            
        if bp.pivot_offset.x != off_x or bp.pivot_offset.y != off_y:
            bp.pivot_offset.x = off_x
            bp.pivot_offset.y = off_y
            changed = True
            
        if bp.position.x != new_pos_x or bp.position.y != new_pos_y:
            bp.position.x = new_pos_x
            bp.position.y = new_pos_y
            changed = True
            
        return changed
        
    def _refresh_list(self):
        """Refresh the body parts list from state."""
        # Save scroll position
        scroll_val = self._bodyparts_list.verticalScrollBar().value()
        
        self._bodyparts_list.blockSignals(True)
        self._bodyparts_list.clear()
        
        entity = self._state.current_entity
        if entity:
            for bp in entity.body_parts:
                item = QListWidgetItem()
                item.setData(Qt.UserRole, bp)
                self._bodyparts_list.addItem(item)
                
                # Custom widget
                widget = QWidget()
                layout = QHBoxLayout(widget)
                layout.setContentsMargins(4, 2, 4, 2)
                layout.setSpacing(4)
                
                # Eye button
                eye_btn = QPushButton("👁" if bp.visible else "⚫")
                eye_btn.setFixedSize(20, 20)
                eye_btn.setFlat(True)
                eye_btn.clicked.connect(lambda checked, b=bp: self._toggle_visibility(b))
                layout.addWidget(eye_btn)
                
                # Isolate button (Target icon or similar)
                is_isolated = (self._isolating_bp == bp)
                iso_btn = QPushButton("🎯" if is_isolated else "⭕")
                iso_btn.setFixedSize(20, 20)
                iso_btn.setFlat(True)
                iso_btn.setToolTip("Isolate (Hide others)")
                iso_btn.clicked.connect(lambda checked, b=bp: self._toggle_isolation(b))
                layout.addWidget(iso_btn)
                
                # Name
                name_lbl = QLabel(bp.name)
                layout.addWidget(name_lbl)
                layout.addStretch()
                
                item.setSizeHint(widget.sizeHint())
                self._bodyparts_list.setItemWidget(item, widget)
                
                # Restore selection
                if self._state.selection.is_selected(bp):
                    item.setSelected(True)
                    
        self._bodyparts_list.blockSignals(False)
        
        # Restore scroll position
        if scroll_val is not None:
            self._bodyparts_list.verticalScrollBar().setValue(scroll_val)
            
        self._update_properties_enabled()

    def _on_list_selection_changed(self):
        """Handle UI selection change."""
        selected_items = self._bodyparts_list.selectedItems()
        selected_bps = [item.data(Qt.UserRole) for item in selected_items]
        
        self._state.selection.blockSignals(True)
        
        if not selected_bps:
            self._state.selection.clear_selection()
        else:
            self._state.selection.clear_selection()
            # Selection service now handles IDs internally, so passing objects is fine.
            # It will extract .id from them.
            self._state.selection.select_bodyparts(selected_bps)
                    
        self._state.selection.blockSignals(False)
        get_signal_hub().notify_bodyparts_selection_changed(selected_bps)
        self._update_properties()

    def _on_state_selection_changed(self):
        """Handle selection change from State."""
        self._bodyparts_list.blockSignals(True)
        self._bodyparts_list.clearSelection()
        
        # State now returns objects that match IDs.
        # However, the objects returned by `selected_body_parts` might be NEW objects if undo happened.
        # We must match by ID against the widget items.
        
        selected_bps = self._state.selection.selected_body_parts
        selected_objects = set(selected_bps)
        
        for i in range(self._bodyparts_list.count()):
            item = self._bodyparts_list.item(i)
            bp = item.data(Qt.UserRole)
            # Compare object references
            if bp in selected_objects:
                item.setSelected(True)
                
        self._bodyparts_list.blockSignals(False)
        self._update_properties()

    def _update_properties(self):
        """Update property fields from primary selection."""
        self._updating_ui = True
        
        bp = self._state.selection.selected_body_part
        if bp:
            self._name_edit.setText(bp.name)
            
            # Type
            self._type_combo.blockSignals(True)
            self._type_combo.setCurrentIndex(int(bp.part_type))
            self._type_combo.blockSignals(False)
            
            # Common Properties
            self._pos_x_spin.setValue(int(bp.position.x))
            self._pos_y_spin.setValue(int(bp.position.y))
            self._size_x_spin.setValue(int(bp.size.x))
            self._size_y_spin.setValue(int(bp.size.y))
            self._rot_spin.setValue(int(bp.rotation))
            self._scale_spin.setValue(int(bp.pixel_scale))
            self._z_spin.setValue(int(bp.z_order))
            self._pivot_x_spin.setValue(int(bp.pivot.x))
            self._pivot_y_spin.setValue(int(bp.pivot.y))
            
            # Show/Hide based on Type
            is_ref = (bp.part_type == BodyPartType.ENTITY_REF)
            
            self._ref_label.setVisible(is_ref)
            self._ref_combo.setVisible(is_ref)
            
            self._tex_label.setVisible(not is_ref)
            self._tex_combo.setVisible(not is_ref)
            self._uv_group.setVisible(not is_ref)
            
            if is_ref:
                # Populate Entity Ref
                self._ref_combo.blockSignals(True)
                self._ref_combo.clear()
                
                # Get available entities from manager
                available = get_entity_manager().get_available_entity_names()
                
                # Filter out current entity AND any entities that depend on current entity
                current_file = self._state.current_filepath
                if current_file:
                    current_name = os.path.splitext(os.path.basename(current_file))[0]
                    
                    # 1. Remove Self
                    if current_name in available:
                        available.remove(current_name)
                        
                    # 2. Remove Circular Dependencies
                    # If "current" is referenced by Candidate, then adding Candidate to "current" creates cycle.
                    # Candidate depends on Current? 
                    # check if Current is in get_all_dependencies(Candidate)
                    
                    to_remove = []
                    for candidate in available:
                        deps = get_entity_manager().get_all_dependencies(candidate)
                        if current_name in deps:
                            to_remove.append(candidate)
                            
                    for r in to_remove:
                        available.remove(r)
                
                self._ref_combo.addItem("") # Empty option
                self._ref_combo.addItems(available)
                
                if bp.entity_ref and bp.entity_ref in available:
                    self._ref_combo.setCurrentText(bp.entity_ref)
                elif bp.entity_ref:
                     self._ref_combo.addItem(f"{bp.entity_ref} (Missing)")
                     self._ref_combo.setCurrentText(f"{bp.entity_ref} (Missing)")
                     
                self._ref_combo.blockSignals(False)
                
                # Size constraints for REF?
                # Usually size is just a container size or initial size.
                # If we want to auto-set size to entity size, we could, but let's allow manual override for now.
                self._size_x_spin.setReadOnly(False)
                self._size_y_spin.setReadOnly(False)
                self._size_x_spin.setToolTip("Bounding box size")
                self._size_y_spin.setToolTip("Bounding box size")

            else:
                self._flip_x_check.setChecked(bp.flip_x)
                self._flip_y_check.setChecked(bp.flip_y)
                
                # Populate Texture Combo
                self._tex_combo.blockSignals(True)
                self._tex_combo.clear()
                
                registry = self._texture_manager._registry
                if registry:
                    keys = registry._keys_order
                    self._tex_combo.addItems(keys)
                    
                    if bp.texture_id in keys:
                        self._tex_combo.setCurrentText(bp.texture_id)
                    else:
                         # e.g. "ERROR" or unknown
                        if bp.texture_id:
                            self._tex_combo.addItem(f"{bp.texture_id} (Missing)")
                            self._tex_combo.setCurrentText(f"{bp.texture_id} (Missing)")

                self._tex_combo.blockSignals(False)
                
                # Enforce constraints UI
                has_texture = bool(bp.texture_id)
                self._size_x_spin.setReadOnly(has_texture)
                self._size_y_spin.setReadOnly(has_texture)
                if has_texture:
                    self._size_x_spin.setToolTip("Size is locked to Texture size * Pixel Scale")
                    self._size_y_spin.setToolTip("Size is locked to Texture size * Pixel Scale")
                else:
                    self._size_x_spin.setToolTip("")
                    self._size_y_spin.setToolTip("")
            
            self._props_group.setEnabled(True)
            self._props_group.setTitle(f"Properties: {bp.name}")
        else:
            self._name_edit.clear()
            self._tex_combo.clear()
            self._ref_combo.clear()
            self._props_group.setEnabled(False)
            self._props_group.setTitle("Properties (None Selected)")
            
        self._updating_ui = False
        self._update_properties_enabled()

    def _update_properties_enabled(self):
        has_selection = self._state.selection.has_selection
        self._remove_btn.setEnabled(has_selection)
        self._rename_btn.setEnabled(has_selection)
        self._duplicate_btn.setEnabled(has_selection)
        self._Entity_exists = (self._state.current_entity is not None)
        self._add_btn.setEnabled(self._Entity_exists)

    # --- Actions ---

    def _toggle_visibility(self, bodypart):
        bodypart.visible = not bodypart.visible
        get_signal_hub().notify_bodypart_modified(bodypart)
        self._refresh_list()
        
    def _on_sel_on_top_toggled(self, checked):
        self._state.set_selection_on_top(checked)
        get_signal_hub().notify_entity_modified() # Trigger redraw

    def _toggle_isolation(self, bodypart):
        entity = self._state.current_entity
        if not entity: return

        if self._isolating_bp == bodypart:
            # Disable Isolation: Restore snapshot
            self._isolating_bp = None
            for bp in entity.body_parts:
                if id(bp) in self._isolation_snapshot:
                    bp.visible = self._isolation_snapshot[id(bp)]
            self._isolation_snapshot.clear()
        else:
            # Enable Isolation
            # If already isolating another, restore first? Or just switch focus?
            # Switching focus seems better: "Isolate THIS one now"
            
            # If start fresh isolation
            if self._isolating_bp is None:
                self._isolation_snapshot = {id(bp): bp.visible for bp in entity.body_parts}
            
            self._isolating_bp = bodypart
            
            # Apply: Hide all except target
            for bp in entity.body_parts:
                if bp == bodypart:
                    bp.visible = True
                else:
                    bp.visible = False
            
        # Notify changes (blindly notify all or just entity? Entity mod is safer for batch visual update)
        # But we need panel refresh.
        # We can iterate and emit modified for checks.
        get_signal_hub().notify_entity_modified() # Force full redraw?
        self._refresh_list()

    def _on_add_bodypart(self):
        if not self._state.current_entity: return
        
        count = len(self._state.current_entity.body_parts)
        # Default size is 64x64, so pivot should be 32x32 (Center)
        size = Vec2(64,64)
        center = Vec2(size.x / 2, size.y / 2)
        bp = BodyPart(name=f"BodyPart_{count}", position=Vec2(0,0), size=size, pivot=center)
        
        if self._state.history:
            self._state.history.execute(AddBodyPartCommand(bp))
        else:
            self._state.current_entity.add_body_part(bp) # Fallback
            get_signal_hub().notify_bodypart_added(bp)

    def _on_remove_bodypart(self):
        # Update: Handle multiple selection
        selected_items = self._bodyparts_list.selectedItems()
        if not selected_items: return
        
        selected_bps = [item.data(Qt.UserRole) for item in selected_items]
        if not selected_bps: return
        
        if self._state.history:
            # Use batch command for atomic removal
            self._state.history.execute(RemoveBodyPartsCommand(selected_bps))
            # Selection clearing is handled by signal updates usually, but we can force clear if needed.
            # But let the signal hub do its job.
        else:
            # Fallback (manual loop, though history should always be there)
            for bp in selected_bps:
                if bp in self._state.current_entity.body_parts:
                    self._state.current_entity.remove_body_part(bp)
                    get_signal_hub().notify_bodypart_removed(bp)

    def _on_duplicate_bodypart(self):
        bp = self._state.selection.selected_body_part
        if not bp: return
        
        existing_names = {b.name for b in self._state.current_entity.body_parts}
        new_name = generate_unique_name(bp.name, existing_names)
        
        new_bp = copy.deepcopy(bp)
        new_bp.name = new_name
        # Offset removed as per user request
        # new_bp.position.x += 10
        # new_bp.position.y += 10
        
        # Find index to insert after
        try:
            current_index = self._state.current_entity.body_parts.index(bp)
            insert_index = current_index + 1
        except ValueError:
            insert_index = -1
        
        if self._state.history:
            self._state.history.execute(AddBodyPartCommand(new_bp, insert_index))
        else:
            if insert_index >= 0:
                self._state.current_entity.body_parts.insert(insert_index, new_bp)
                get_signal_hub().notify_bodypart_added(new_bp)
                get_signal_hub().notify_bodypart_reordered()
            else:
                self._state.current_entity.add_body_part(new_bp)
                get_signal_hub().notify_bodypart_added(new_bp)


    def _on_rename_bodypart(self):
        self._name_edit.setFocus()
        self._name_edit.selectAll()

    # --- Property Editing (With Undo Support) ---

    def _on_property_changing(self, prop_name, value):
        """Called when spinbox values change."""
        if self._updating_ui: return
        
        bp = self._state.selection.selected_body_part
        if not bp: return
        
        if prop_name == 'x': bp.position.x = value
        elif prop_name == 'y': bp.position.y = value
        elif prop_name == 'w': bp.size.x = value
        elif prop_name == 'h': bp.size.y = value
        elif prop_name == 'rot': bp.rotation = value
        elif prop_name == 'scale': 
            bp.pixel_scale = value
            self._enforce_aspect_ratio(bp) # If texture exists, update size
        elif prop_name == 'z': bp.z_order = value
        elif prop_name == 'pivot_x': bp.pivot.x = value
        elif prop_name == 'pivot_y': bp.pivot.y = value
        
        # UVs handled by dialog now

        
        # If UV changed, size might change if we want strict pixel mapping of UV region?
        # Usually UV change *on same texture* means we might want to resize relevant to new sub-rect?
        # Let's enforce it for now if texture is present.
        # If UV changed via dialog, we update size there.
        # Here we only handle manual spinbox changes (none for UV anymore)

        get_signal_hub().notify_bodypart_modified(bp)
        
        # If size changed, we might need to update spins if we auto-calculated
        if prop_name in ['scale']:
            self._updating_ui = True
            self._size_x_spin.setValue(int(bp.size.x))
            self._size_y_spin.setValue(int(bp.size.y))
            self._updating_ui = False

    def _on_property_changed_finished(self):
        """Called when editing finishes (e.g. lost focus)."""
        bp = self._state.selection.selected_body_part
        if not bp: return
        
        sender = self.sender()
        prop = None
        new_val = None
        
        # Identify property
        if sender == self._pos_x_spin: prop, new_val = 'x', self._pos_x_spin.value()
        elif sender == self._pos_y_spin: prop, new_val = 'y', self._pos_y_spin.value()
        elif sender == self._size_x_spin: prop, new_val = 'size_x', self._size_x_spin.value()
        elif sender == self._size_y_spin: prop, new_val = 'size_y', self._size_y_spin.value()
        elif sender == self._scale_spin: prop, new_val = 'scale', self._scale_spin.value()
        elif sender == self._rot_spin: prop, new_val = 'rot', self._rot_spin.value()
        elif sender == self._z_spin: prop, new_val = 'z', self._z_spin.value()
        elif sender == self._pivot_x_spin: prop, new_val = 'pivot_x', self._pivot_x_spin.value()
        elif sender == self._pivot_y_spin: prop, new_val = 'pivot_y', self._pivot_y_spin.value()
        
        if prop and self._parameter_change_start_value is not None:
             # Check if actually changed
             if self._parameter_change_start_value == new_val:
                 return
                 
             # Create Command
             key_map = {
                 'x': 'position', 'y': 'position',
                 'size_x': 'size', 'size_y': 'size',
                 'scale': 'pixel_scale',
                 'rot': 'rotation',
                 'z': 'z_order',
                 'pivot_x': 'pivot', 'pivot_y': 'pivot'
             }
             
             key = key_map.get(prop)
             old_state = {}
             new_state = {}
             
             if key == 'position':
                 old_state[key] = copy.deepcopy(bp.position)
                 old_vec = Vec2(bp.position.x, bp.position.y)
                 if prop == 'x': old_vec.x = self._parameter_change_start_value
                 else: old_vec.y = self._parameter_change_start_value
                 old_state[key] = old_vec
                 new_state[key] = copy.deepcopy(bp.position)
                 
             elif key == 'size':
                 old_vec = Vec2(bp.size.x, bp.size.y)
                 if prop == 'size_x': old_vec.x = self._parameter_change_start_value
                 else: old_vec.y = self._parameter_change_start_value
                 old_state[key] = old_vec
                 new_state[key] = copy.deepcopy(bp.size)
                 
                 # AUTO-RESET PIVOT ON MANUAL RESIZE
                 # "Always be set to center every time it changes size"
                 new_pivot = Vec2(bp.size.x / 2, bp.size.y / 2)
                 old_state['pivot'] = copy.deepcopy(bp.pivot)
                 new_state['pivot'] = new_pivot
                 # Apply locally
                 bp.pivot.x = new_pivot.x
                 bp.pivot.y = new_pivot.y
                 self._pivot_x_spin.blockSignals(True)
                 self._pivot_x_spin.setValue(int(new_pivot.x))
                 self._pivot_y_spin.setValue(int(new_pivot.y))
                 self._pivot_x_spin.blockSignals(False)

             elif key == 'pivot':
                 old_vec = Vec2(bp.pivot.x, bp.pivot.y)
                 if prop == 'pivot_x': old_vec.x = self._parameter_change_start_value
                 else: old_vec.y = self._parameter_change_start_value
                 old_state[key] = old_vec
                 new_state[key] = copy.deepcopy(bp.pivot)

             else:
                 old_state[key] = self._parameter_change_start_value
                 new_state[key] = new_val
                 
             if self._state.history:
                 self._state.history.execute(ModifyBodyPartCommand(bp, old_state, new_state))
                 
             self._parameter_change_start_value = None

    def _on_name_changed(self):
        bp = self._state.selection.selected_body_part
        if bp and bp.name != self._name_edit.text():
            new_name = self._name_edit.text()
            
            existing_names = {b.name for b in self._state.current_entity.body_parts if b != bp}
            unique_name = ensure_unique_name(new_name, existing_names)
            
            if unique_name != new_name:
                # Update UI to show enforced name
                self._name_edit.setText(unique_name)
            
            bp.name = unique_name
            get_signal_hub().notify_bodypart_modified(bp) 
            self._refresh_list()

    def _on_flip_changed(self):
        if self._updating_ui: return
        bp = self._state.selection.selected_body_part
        if bp:
            bp.flip_x = self._flip_x_check.isChecked()
            bp.flip_y = self._flip_y_check.isChecked()
            get_signal_hub().notify_bodypart_modified(bp)
            
    def _on_type_changed(self, index):
        if self._updating_ui: return
        bp = self._state.selection.selected_body_part
        if not bp: return
        
        new_type = BodyPartType(index)
        if bp.part_type == new_type: return
        
        # Create command
        old_state = {'part_type': bp.part_type}
        new_state = {'part_type': new_type}
        
        if self._state.history:
            self._state.history.execute(ModifyBodyPartCommand(bp, old_state, new_state))
        else:
             bp.part_type = new_type
             get_signal_hub().notify_bodypart_modified(bp)
             
        self._update_properties() # To toggle visibility
        
    def _on_entity_ref_changed(self, index):
        if self._updating_ui: return
        bp = self._state.selection.selected_body_part
        if not bp: return
        
        ref_name = self._ref_combo.currentText()
        if " (Missing)" in ref_name:
            ref_name = ref_name.replace(" (Missing)", "")
            
        if bp.entity_ref == ref_name: return
        
        old_state = {'entity_ref': bp.entity_ref}
        new_state = {'entity_ref': ref_name}
        
        if self._state.history:
            self._state.history.execute(ModifyBodyPartCommand(bp, old_state, new_state))
        else:
             bp.entity_ref = ref_name
             get_signal_hub().notify_bodypart_modified(bp)
             
        # Auto-Resize logic (Post-change)
        # If we just switched to a valid ref, update size to match
        if ref_name:
            ref_entity = get_entity_manager().get_entity_def(ref_name)
            if ref_entity:
                min_x, min_y, w, h = calculate_entity_bounds(ref_entity)
                
                # Calculate required Pivot Offset
                # Logic: Offset = -(min + Size/2)
                off_x = -(min_x + w/2)
                off_y = -(min_y + h/2)
                
                # Pivot Preservation Logic
                # When changing reference, we want to keep the Pivot at the same spot.
                current_pivot_x = bp.position.x + bp.size.x/2 + bp.pivot_offset.x
                current_pivot_y = bp.position.y + bp.size.y/2 + bp.pivot_offset.y
                
                new_pos_x = current_pivot_x - w/2 - off_x
                new_pos_y = current_pivot_y - h/2 - off_y
                
                # Check if change needed
                if bp.size.x != w or bp.size.y != h or \
                   bp.pivot_offset.x != off_x or bp.pivot_offset.y != off_y or \
                   bp.position.x != new_pos_x or bp.position.y != new_pos_y:
                     
                     old_props = {
                        'position': copy.deepcopy(bp.position),
                        'size': copy.deepcopy(bp.size),
                        'pivot_offset': copy.deepcopy(bp.pivot_offset)
                     }
                     new_props = {
                        'position': Vec2(new_pos_x, new_pos_y),
                        'size': Vec2(w, h),
                        'pivot_offset': Vec2(off_x, off_y)
                     }
                     
                     if self._state.history:
                         self._state.history.execute(ModifyBodyPartCommand(bp, old_props, new_props))
                     else:
                         bp.position.x = new_pos_x
                         bp.position.y = new_pos_y
                         bp.size.x = w
                         bp.size.y = h
                         bp.pivot_offset.x = off_x
                         bp.pivot_offset.y = off_y
                         get_signal_hub().notify_bodypart_modified(bp)

                     self._update_properties() # Refresh UI spins


    def _on_texture_changed(self, index):
        if self._updating_ui: return
        bp = self._state.selection.selected_body_part
        if not bp: return
        
        tex_id = self._tex_combo.currentText()
        # Handle "(Missing)" suffix if we accidentally selected it (though user shouldn't be able to select it if we didn't add it)
        # Actually if we added it, it's selectable.
        if " (Missing)" in tex_id:
            tex_id = tex_id.replace(" (Missing)", "")
            
        # Prepare state change
        old_state = {
            'texture_id': bp.texture_id,
            'uv_rect': copy.deepcopy(bp.uv_rect),
            'size': copy.deepcopy(bp.size),
            'pivot': copy.deepcopy(bp.pivot),
            'position': copy.deepcopy(bp.position)
        }
        
        # Calculate new state
        tex_size = self._texture_manager.get_texture_size(tex_id)
        w, h = 64.0, 64.0
        if tex_size:
            w = float(tex_size[0] * bp.pixel_scale)
            h = float(tex_size[1] * bp.pixel_scale)
            
        new_pivot = Vec2(w / 2, h / 2)
        
        # Calculate new position to keep pivot at same World location
        # OldWorldPivot = OldPos + OldPivot
        # NewPos = OldWorldPivot - NewPivot
        old_world_pivot_x = bp.position.x + bp.pivot.x
        old_world_pivot_y = bp.position.y + bp.pivot.y
        
        new_pos_x = old_world_pivot_x - new_pivot.x
        new_pos_y = old_world_pivot_y - new_pivot.y
        
        new_state = {
            'texture_id': tex_id,
            'uv_rect': {'x': 0.0, 'y': 0.0, 'width': 1.0, 'height': 1.0},
            'size': Vec2(w, h),
            'pivot': new_pivot,
            'position': Vec2(new_pos_x, new_pos_y)
        }
        
        if self._state.history:
            self._state.history.execute(ModifyBodyPartCommand(bp, old_state, new_state))
        else:
            bp.texture_id = tex_id
            bp.uv_rect.x = 0.0; bp.uv_rect.y = 0.0
            bp.uv_rect.width = 1.0; bp.uv_rect.height = 1.0
            bp.size.x = w; bp.size.y = h
            bp.pivot = new_pivot
            bp.position.x = new_pos_x; bp.position.y = new_pos_y
            get_signal_hub().notify_bodypart_modified(bp)
            
        self._update_properties()

    def _on_visual_uv_edit(self):
        bp = self._state.selection.selected_body_part
        if not bp or not bp.texture_id: return
        
        # Get texture
        pixmap = self._texture_manager.get_texture(bp.texture_id)
        if not pixmap: return
        
        # Show Dialog
        dialog = UVEditorDialog(self)
        dialog.load_texture(pixmap, (bp.uv_rect.x, bp.uv_rect.y, bp.uv_rect.width, bp.uv_rect.height))
        
        if dialog.exec():
            # Apply Result
            nx, ny, nw, nh = dialog.get_uv_rect()
            
            bp.uv_rect.x = nx
            bp.uv_rect.y = ny
            bp.uv_rect.width = nw
            bp.uv_rect.height = nh
            
            self._enforce_aspect_ratio(bp)
            get_signal_hub().notify_bodypart_modified(bp)
            self._update_properties()

    def _on_reset_uv(self):
        bp = self._state.selection.selected_body_part
        if not bp: return
        
        bp.uv_rect.x = 0.0
        bp.uv_rect.y = 0.0
        bp.uv_rect.width = 1.0
        bp.uv_rect.height = 1.0
        
        self._enforce_aspect_ratio(bp)
        get_signal_hub().notify_bodypart_modified(bp)
        self._update_properties()

    def _enforce_aspect_ratio(self, bp):
        """Enforce strict size based on texture and pixel scale."""
        if not bp.texture_id: return
        
        tex_size = self._texture_manager.get_texture_size(bp.texture_id)
        if tex_size:
            w, h = tex_size
            # Calculate pixel size of UV rect
            # UV width is normalized (0-1), so pixel width is w * uv.w
            # Multiply by pixel_scale
            
            target_w = w * bp.uv_rect.width * bp.pixel_scale
            target_h = h * bp.uv_rect.height * bp.pixel_scale
            
            bp.size.x = int(round(target_w))
            bp.size.y = int(round(target_h))
            
            # Auto-Reset Pivot to Center (User Requirement: "Standard is in the center... always be set to center every time it changes size")
            bp.pivot.x = bp.size.x / 2
            bp.pivot.y = bp.size.y / 2
            
            # Force update of spins if UI is active?
            # _update_properties will handle it when called.
            if not self._updating_ui:
                self._size_x_spin.blockSignals(True)
                self._size_y_spin.blockSignals(True)
                self._pivot_x_spin.blockSignals(True)
                self._pivot_y_spin.blockSignals(True)
                
                self._size_x_spin.setValue(int(bp.size.x))
                self._size_y_spin.setValue(int(bp.size.y))
                self._pivot_x_spin.setValue(int(bp.pivot.x))
                self._pivot_y_spin.setValue(int(bp.pivot.y))
                
                self._size_x_spin.blockSignals(False)
                self._size_y_spin.blockSignals(False)
                self._pivot_x_spin.blockSignals(False)
                self._pivot_y_spin.blockSignals(False)

    def _on_bodypart_modified(self, bp):
        if bp == self._state.selection.selected_body_part:
            self._update_properties()
            
    def _on_list_reordered(self):
        new_order = []
        for i in range(self._bodyparts_list.count()):
            item = self._bodyparts_list.item(i)
            new_order.append(item.data(Qt.UserRole))
        
        self._state.current_entity.body_parts = new_order
        get_signal_hub().notify_bodypart_reordered()

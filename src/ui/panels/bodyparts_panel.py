"""
Body Parts Panel for Entity Editor.

Panel for managing and editing body parts.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QGroupBox, QFormLayout, QLineEdit, QPushButton, QSpinBox,
    QLabel, QFileDialog, QCheckBox, QDoubleSpinBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
import sys
import os
import copy
import re

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.data import Entity, BodyPart, Vec2, UVRect
from src.core import get_signal_hub, AddBodyPartCommand, RemoveBodyPartCommand, MoveBodyPartCommand, ModifyBodyPartCommand
from src.core.state.editor_state import EditorState
from src.rendering import get_texture_manager
from src.ui.dialogs.uv_editor_dialog import UVEditorDialog
from src.core.naming_utils import generate_unique_name, ensure_unique_name

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
        
        # Texture
        tex_layout = QHBoxLayout()
        self._tex_path_edit = QLineEdit()
        self._tex_path_edit.setReadOnly(True)
        tex_layout.addWidget(self._tex_path_edit)
        
        self._tex_browse_btn = QPushButton("...")
        self._tex_browse_btn.setFixedSize(30, 20)
        self._tex_browse_btn.clicked.connect(self._on_browse_texture)
        tex_layout.addWidget(self._tex_browse_btn)
        props_layout.addRow("Texture:", tex_layout)
        
        # UV Editor
        uv_group = QGroupBox("UV Mapping")
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

        uv_group.setLayout(uv_layout)
        props_layout.addRow(uv_group)
        
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
        signal_hub.bodypart_reordered.connect(self._refresh_list)
        signal_hub.bodypart_modified.connect(self._on_bodypart_modified)
            
    def _on_entity_loaded(self, entity):
        self._refresh_list()
        self._update_properties()
        
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
            for i, bp in enumerate(selected_bps):
                if i == 0:
                    self._state.selection.set_selection(bp)
                else:
                    self._state.selection.add_to_selection(bp)
                    
        self._state.selection.blockSignals(False)
        get_signal_hub().notify_bodyparts_selection_changed(selected_bps)
        self._update_properties()

    def _on_state_selection_changed(self):
        """Handle selection change from State."""
        self._bodyparts_list.blockSignals(True)
        self._bodyparts_list.clearSelection()
        
        selected_bps = self._state.selection.selected_body_parts
        
        for i in range(self._bodyparts_list.count()):
            item = self._bodyparts_list.item(i)
            bp = item.data(Qt.UserRole)
            if bp in selected_bps:
                item.setSelected(True)
                
        self._bodyparts_list.blockSignals(False)
        self._update_properties()

    def _update_properties(self):
        """Update property fields from primary selection."""
        self._updating_ui = True
        
        bp = self._state.selection.selected_body_part
        if bp:
            self._name_edit.setText(bp.name)
            self._pos_x_spin.setValue(int(bp.position.x))
            self._pos_y_spin.setValue(int(bp.position.y))
            self._size_x_spin.setValue(int(bp.size.x))
            self._size_y_spin.setValue(int(bp.size.y))
            self._rot_spin.setValue(int(bp.rotation))
            self._scale_spin.setValue(int(bp.pixel_scale))
            self._z_spin.setValue(int(bp.z_order))
            self._tex_path_edit.setText(bp.texture_path or "")
            self._flip_x_check.setChecked(bp.flip_x)
            self._flip_y_check.setChecked(bp.flip_y)
            
            # UVs updated via Dialog now

            
            # Enforce constraints UI
            has_texture = bool(bp.texture_path)
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
        bp = BodyPart(f"BodyPart_{count}", Vec2(0,0), Vec2(64,64))
        
        if self._state.history:
            self._state.history.execute(AddBodyPartCommand(bp))
        else:
            self._state.current_entity.add_body_part(bp) # Fallback
            get_signal_hub().notify_bodypart_added(bp)

    def _on_remove_bodypart(self):
        bp = self._state.selection.selected_body_part
        if not bp: return
        
        if self._state.history:
            self._state.history.execute(RemoveBodyPartCommand(bp))
        else:
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
        pass

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

    def _on_browse_texture(self):
        bp = self._state.selection.selected_body_part
        if not bp: return
        
        path, _ = QFileDialog.getOpenFileName(self, "Select Texture", "", "Images (*.png *.jpg *.bmp)")
        if path:
            if "assets" in path:
                try:
                    rel_path = os.path.relpath(path, os.getcwd())
                    path = rel_path
                except:
                   pass
            
            bp.texture_path = path
            self._tex_path_edit.setText(path)
            
            # Reset UVs to full on new texture load? Usually yes.
            bp.uv_rect.x = 0.0
            bp.uv_rect.y = 0.0
            bp.uv_rect.width = 1.0
            bp.uv_rect.height = 1.0
            
            # Enforce Size
            self._enforce_aspect_ratio(bp)
            
            get_signal_hub().notify_bodypart_modified(bp)
            self._update_properties()

    def _on_visual_uv_edit(self):
        bp = self._state.selection.selected_body_part
        if not bp or not bp.texture_path: return
        
        # Get texture
        pixmap = self._texture_manager.get_texture(bp.texture_path)
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
        if not bp.texture_path: return
        
        tex_size = self._texture_manager.get_texture_size(bp.texture_path)
        if tex_size:
            w, h = tex_size
            # Calculate pixel size of UV rect
            # UV width is normalized (0-1), so pixel width is w * uv.w
            # Multiply by pixel_scale
            
            target_w = w * bp.uv_rect.width * bp.pixel_scale
            target_h = h * bp.uv_rect.height * bp.pixel_scale
            
            bp.size.x = int(round(target_w))
            bp.size.y = int(round(target_h))

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


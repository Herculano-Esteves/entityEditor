"""
Body Parts Panel for Entity Editor.

Panel for managing and editing body parts.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QGroupBox, QFormLayout, QLineEdit, QPushButton, QSpinBox,
    QLabel, QFileDialog, QCheckBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.data import Entity, BodyPart, Vec2, UVRect
from src.core import get_signal_hub, AddBodyPartCommand, RemoveBodyPartCommand, MoveBodyPartCommand, ModifyBodyPartCommand


class BodyPartsPanel(QWidget):
    """Panel for managing body parts."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._entity = None
        self._selected_bodypart = None  # Primary selection (for properties panel)
        self._selected_bodyparts = []   # Multi-selection list
        self._signal_hub = get_signal_hub()
        self._history_manager = None  # Will be set via signal hub when entity loads
        
        # Track property state for undo
        self._property_edit_old_state = None
        self._updating_ui = False  # Flag to prevent change tracking during programmatic updates
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Setup the UI layout."""
        layout = QVBoxLayout(self)
        
        # Body parts list
        list_label = QLabel("Body Parts:")
        layout.addWidget(list_label)
        
        self._bodyparts_list = QListWidget()
        self._bodyparts_list.setSelectionMode(QListWidget.ExtendedSelection)  # Enable multi-select
        self._bodyparts_list.currentItemChanged.connect(self._on_selection_changed)
        self._bodyparts_list.itemSelectionChanged.connect(self._on_multi_selection_changed)
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
        props_group = QGroupBox("Properties")
        props_layout = QFormLayout()
        
        # Name
        self._name_edit = QLineEdit()
        self._name_edit.editingFinished.connect(self._on_name_changed)  # Only when done editing
        props_layout.addRow("Name:", self._name_edit)
        
        # Position
        self._pos_x_spin = QSpinBox()
        self._pos_x_spin.setRange(-10000, 10000)
        self._pos_x_spin.valueChanged.connect(self._on_property_changed)
        self._pos_x_spin.editingFinished.connect(self._on_editing_finished)
        props_layout.addRow("Position X (px):", self._pos_x_spin)
        
        self._pos_y_spin = QSpinBox()
        self._pos_y_spin.setRange(-10000, 10000)
        self._pos_y_spin.valueChanged.connect(self._on_property_changed)
        self._pos_y_spin.editingFinished.connect(self._on_editing_finished)
        props_layout.addRow("Position Y (px):", self._pos_y_spin)
        
        # Size
        self._size_x_spin = QSpinBox()
        self._size_x_spin.setRange(1, 10000)
        self._size_x_spin.setValue(64)
        self._size_x_spin.valueChanged.connect(self._on_property_changed)
        self._size_x_spin.editingFinished.connect(self._on_editing_finished)
        props_layout.addRow("Width (px):", self._size_x_spin)
        
        self._size_y_spin = QSpinBox()
        self._size_y_spin.setRange(1, 10000)
        self._size_y_spin.setValue(64)
        self._size_y_spin.valueChanged.connect(self._on_property_changed)
        self._size_y_spin.editingFinished.connect(self._on_editing_finished)
        props_layout.addRow("Height (px):", self._size_y_spin)
        
        # Pixel scale
        self._pixel_scale_spin = QSpinBox()
        self._pixel_scale_spin.setRange(1, 16)
        self._pixel_scale_spin.setValue(1)
        self._pixel_scale_spin.setSuffix("x")
        self._pixel_scale_spin.valueChanged.connect(self._on_property_changed)
        self._pixel_scale_spin.editingFinished.connect(self._on_editing_finished)
        self._pixel_scale_spin.setToolTip("Sprite scale multiplier (1x = 1:1 pixels, 2x = each pixel is 2x2, etc.)")
        props_layout.addRow("Pixel Scale:", self._pixel_scale_spin)
        
        # Z-order
        self._z_order_spin = QSpinBox()
        self._z_order_spin.setRange(-100, 100)
        self._z_order_spin.valueChanged.connect(self._on_property_changed)
        self._z_order_spin.editingFinished.connect(self._on_editing_finished)
        props_layout.addRow("Z-Order:", self._z_order_spin)
        
        # Show above while editing checkbox
        self._show_above_check = QCheckBox("Show Above While Editing")
        self._show_above_check.setChecked(True)  # Enabled by default
        self._show_above_check.toggled.connect(self._on_show_above_changed)
        self._show_above_check.setToolTip("Temporarily show this bodypart above all others while editing (makes hitbox editing easier)")
        props_layout.addRow("", self._show_above_check)
        
        # Texture
        texture_layout = QHBoxLayout()
        self._texture_edit = QLineEdit()
        self._texture_edit.textChanged.connect(self._on_property_changed)
        texture_layout.addWidget(self._texture_edit)
        
        self._browse_btn = QPushButton("Browse...")
        self._browse_btn.clicked.connect(self._on_browse_texture)
        texture_layout.addWidget(self._browse_btn)
        
        props_layout.addRow("Texture:", texture_layout)
        
        # Flip UV (for mirroring)
        flip_layout = QHBoxLayout()
        self._flip_x_check = QCheckBox("Flip X")
        self._flip_x_check.toggled.connect(self._on_property_changed)
        self._flip_x_check.setToolTip("Mirror texture horizontally (for left/right variants)")
        flip_layout.addWidget(self._flip_x_check)
        
        self._flip_y_check = QCheckBox("Flip Y")
        self._flip_y_check.toggled.connect(self._on_property_changed)
        self._flip_y_check.setToolTip("Mirror texture vertically")
        flip_layout.addWidget(self._flip_y_check)
        flip_layout.addStretch()
        props_layout.addRow("UV Flip:", flip_layout)
        
        # Rotation
        self._rotation_spin = QSpinBox()
        self._rotation_spin.setRange(-360, 360)
        self._rotation_spin.setSuffix("°")
        self._rotation_spin.valueChanged.connect(self._on_property_changed)
        self._rotation_spin.editingFinished.connect(self._on_editing_finished)
        self._rotation_spin.setToolTip("Rotation in degrees")
        props_layout.addRow("Rotation:", self._rotation_spin)
        
        # UV Map button
        self._edit_uv_btn = QPushButton("Edit UV Map...")
        self._edit_uv_btn.clicked.connect(self._on_edit_uv_map)
        props_layout.addRow("", self._edit_uv_btn)
        
        props_group.setLayout(props_layout)
        layout.addWidget(props_group)
        
        self._update_properties_enabled()
    
    def _connect_signals(self):
        """Connect to signal hub."""
        self._signal_hub.entity_loaded.connect(self.set_entity)
        self._signal_hub.bodypart_selected.connect(self._on_external_selection)
        self._signal_hub.bodypart_added.connect(lambda _: self._refresh_list())
        self._signal_hub.bodypart_removed.connect(lambda _: self._refresh_list())
        self._signal_hub.bodypart_modified.connect(self._on_external_modification)
    
    def set_entity(self, entity: Entity):
        """Set the entity to edit."""
        self._entity = entity
        self._selected_bodypart = None
        
        # Get history manager from parent window
        parent_window = self.window()
        if hasattr(parent_window, 'get_history_manager'):
            self._history_manager = parent_window.get_history_manager()
        
        self._refresh_list()
    
    def _refresh_list(self):
        """Refresh the body parts list while preserving selection."""
        # Store currently selected bodypart
        selected_bp = None
        current_item = self._bodyparts_list.currentItem()
        if current_item:
            selected_bp = current_item.data(Qt.UserRole)
        
        self._bodyparts_list.clear()
        
        if not self._entity:
            return
        
        for bp in self._entity.body_parts:
            # Create list item
            item = QListWidgetItem()
            item.setData(Qt.UserRole, bp)
            self._bodyparts_list.addItem(item)
            
            # Create custom widget with eye icon and name
            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(4, 2, 4, 2)
            layout.setSpacing(4)
            
            # Eye button for visibility toggle
            eye_btn = QPushButton()
            eye_btn.setFixedSize(20, 20)
            eye_btn.setFlat(True)
            eye_btn.setText("👁" if bp.visible else "⚫")
            eye_btn.setToolTip("Toggle visibility")
            eye_btn.clicked.connect(lambda checked, bodypart=bp: self._toggle_visibility(bodypart))
            layout.addWidget(eye_btn)
            
            # Name label
            name_label = QLabel(bp.name)
            layout.addWidget(name_label)
            layout.addStretch()
            
            item.setSizeHint(widget.sizeHint())
            self._bodyparts_list.setItemWidget(item, widget)
        
        # Restore selection
        if selected_bp:
            for i in range(self._bodyparts_list.count()):
                item = self._bodyparts_list.item(i)
                if item.data(Qt.UserRole) == selected_bp:
                    self._bodyparts_list.setCurrentItem(item)
                    break
    
    def _on_selection_changed(self, current, previous):
        """Handle single selection change (for properties panel)."""
        if current:
            bodypart = current.data(Qt.UserRole)
            self._selected_bodypart = bodypart
            self._update_properties()
            self._signal_hub.notify_bodypart_selected(bodypart)
        else:
            self._selected_bodypart = None
            self._update_properties()
            self._signal_hub.notify_bodypart_selected(None)
    
    def _on_multi_selection_changed(self):
        """Handle multi-selection change (for viewport)."""
        selected_items = self._bodyparts_list.selectedItems()
        self._selected_bodyparts = [item.data(Qt.UserRole) for item in selected_items]
        
        # Emit multi-selection signal for viewport
        self._signal_hub.notify_bodyparts_selection_changed(self._selected_bodyparts)
        
        self._update_properties_enabled()
    
    def _on_external_selection(self, bodypart):
        """Handle external body part selection."""
        if bodypart != self._selected_bodypart:
            self._selected_bodypart = bodypart
            self._select_in_list(bodypart)
            self._update_properties()
    
    def _select_in_list(self, bodypart):
        """Select a body part in the list."""
        for i in range(self._bodyparts_list.count()):
            item = self._bodyparts_list.item(i)
            if item.data(Qt.UserRole) == bodypart:
                self._bodyparts_list.setCurrentItem(item)
                return
        
        # Not found, clear selection
        self._bodyparts_list.setCurrentItem(None)
    
    def _toggle_visibility(self, bodypart):
        """Toggle body part visibility."""
        bodypart.visible = not bodypart.visible
        self._signal_hub.notify_bodypart_modified(bodypart)
        self._refresh_list()  # Refresh to update eye icon
    
    def _on_add_bodypart(self):
        """Add a new body part."""
        if not self._entity:
            return
        
        count = len(self._entity.body_parts)
        bp = BodyPart(
            name=f"BodyPart_{count}",
            position=Vec2(0, 0),
            size=Vec2(64, 64),
            z_order=0  # Always start at 0
        )
        
        # Use command if history manager available
        if self._history_manager:
            cmd = AddBodyPartCommand(bp)
            self._history_manager.execute(cmd)
        else:
            # Fallback to direct modification
            self._entity.add_body_part(bp)
            self._signal_hub.notify_bodypart_added(bp)
        
        self._refresh_list()
        
        # Select the new body part
        self._bodyparts_list.setCurrentRow(self._bodyparts_list.count() - 1)
    
    def _on_remove_bodypart(self):
        """Remove the selected body part."""
        if not self._entity or not self._selected_bodypart:
            return
        
        # Use command if history manager available
        if self._history_manager:
            cmd = RemoveBodyPartCommand(self._selected_bodypart)
            self._history_manager.execute(cmd)
        else:
            # Fallback to direct modification
            self._entity.remove_body_part(self._selected_bodypart)
            self._signal_hub.notify_bodypart_removed(self._selected_bodypart)
        
        self._refresh_list()
    
    def _on_rename_bodypart(self):
        """Rename the selected body part."""
        if not self._selected_bodypart:
            return
        
        # The name edit field already handles this
        self._name_edit.setFocus()
        self._name_edit.selectAll()
    
    def _on_duplicate_bodypart(self):
        """Duplicate the selected body part."""
        if not self._entity or not self._selected_bodypart:
            return
        
        # Create a copy
        import copy
        bp_copy = copy.deepcopy(self._selected_bodypart)
        
        # Modify name (add "2" or increment number)
        base_name = bp_copy.name
        if base_name[-1].isdigit():
            # Has number at end, increment it
            import re
            match = re.match(r'(.+?)(\d+)$', base_name)
            if match:
                bp_copy.name = match.group(1) + str(int(match.group(2)) + 1)
            else:
                bp_copy.name = base_name + "2"
        else:
            bp_copy.name = base_name + "2"
        
        # Offset position slightly so it's visible
        bp_copy.position.x += 10
        bp_copy.position.y += 10
        
        # Use command if history manager available
        if self._history_manager:
            cmd = AddBodyPartCommand(bp_copy)
            self._history_manager.execute(cmd)
        else:
            # Fallback to direct modification
            self._entity.add_body_part(bp_copy)
            self._signal_hub.notify_bodypart_added(bp_copy)
        
        self._refresh_list()
        
        # Select the new body part
        for i in range(self._bodyparts_list.count()):
            item = self._bodyparts_list.item(i)
            if item.data(Qt.UserRole) == bp_copy:
                self._bodyparts_list.setCurrentItem(item)
                break
    
    def _on_name_changed(self):
        """Handle name editing finished (to update list labels)."""
        if not self._selected_bodypart:
            return
        
        old_name = self._selected_bodypart.name
        self._selected_bodypart.name = self._name_edit.text()
        
        # Update only the label widget for the current item (don't refresh entire list)
        if old_name != self._selected_bodypart.name:
            current_item = self._bodyparts_list.currentItem()
            if current_item:
                widget = self._bodyparts_list.itemWidget(current_item)
                if widget:
                    # Find the QLabel in the widget and update its text
                    label = widget.findChild(QLabel)
                    if label:
                        label.setText(self._selected_bodypart.name)
        
        # Notify modification
        self._signal_hub.notify_bodypart_modified(self._selected_bodypart)
    
    def _on_property_changed(self):
        """Handle property input field changes."""
        if not self._selected_bodypart:
            return
        
        # Don't process if we're programmatically updating the UI
        if hasattr(self, '_updating_ui') and self._updating_ui:
            return
        
        # Update body part from UI (skip name, it has its own handler)
        self._selected_bodypart.position.x = self._pos_x_spin.value()
        self._selected_bodypart.position.y = self._pos_y_spin.value()
        self._selected_bodypart.size.x = self._size_x_spin.value()
        self._selected_bodypart.size.y = self._size_y_spin.value()
        self._selected_bodypart.z_order = self._z_order_spin.value()
        self._selected_bodypart.pixel_scale = self._pixel_scale_spin.value()
        self._selected_bodypart.rotation = self._rotation_spin.value()
        self._selected_bodypart.flip_x = self._flip_x_check.isChecked()
        self._selected_bodypart.flip_y = self._flip_y_check.isChecked()
        self._selected_bodypart.texture_path = self._texture_edit.text()
        
        # Notify modification (for viewport refresh)
        self._signal_hub.notify_bodypart_modified(self._selected_bodypart)
    
    def _on_editing_finished(self):
        """Called when editing is finished (Enter pressed or focus lost) - finalize undo snapshot."""
        if self._history_manager:
            self._history_manager.end_change()
    
    def _on_browse_texture(self):
        """Browse for texture file."""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select Texture",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp)"
        )
        
        if filename:
            self._texture_edit.setText(filename)
            
            # Auto-size body part to match texture UV region (1:1 pixel mapping)
            if self._selected_bodypart:
                from src.rendering import get_texture_manager
                tex_manager = get_texture_manager()
                tex_size = tex_manager.get_texture_size(filename)
                
                if tex_size:
                    # Calculate pixel size of UV region
                    uv = self._selected_bodypart.uv_rect
                    pixel_width = int(uv.width * tex_size[0])
                    pixel_height = int(uv.height * tex_size[1])
                    
                    # Set body part size to match (will be scaled by pixel_scale at render)
                    self._selected_bodypart.size.x = pixel_width
                    self._selected_bodypart.size.y = pixel_height
                    
                    # Update UI
                    self._update_properties()
                    
                    # Enable UV edit button now that texture is assigned
                    self._update_properties_enabled()
    
    def _on_edit_uv_map(self):
        """Open UV editor dialog for selected body part."""
        if not self._selected_bodypart:
            return
        
        #Check if texture is assigned
        if not self._selected_bodypart.texture_path:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "No Texture",
                "Please assign a texture to this body part before editing UV map."
            )
            return
        
        # Open UV editor dialog
        from src.ui.dialogs import UVEditorDialog
        dialog = UVEditorDialog(self._selected_bodypart, self)
        if dialog.exec():
            # User clicked OK - changes are already applied
            self._signal_hub.notify_bodypart_modified(self._selected_bodypart)
    
    def _update_properties(self):
        """Update properties from selected body part."""
        if not self._selected_bodypart:
            return
        
        # Block signals
        self._name_edit.blockSignals(True)
        self._pos_x_spin.blockSignals(True)
        self._pos_y_spin.blockSignals(True)
        self._size_x_spin.blockSignals(True)
        self._size_y_spin.blockSignals(True)
        self._pixel_scale_spin.blockSignals(True)
        self._z_order_spin.blockSignals(True)
        self._texture_edit.blockSignals(True)
        self._flip_x_check.blockSignals(True)
        self._flip_y_check.blockSignals(True)
        self._rotation_spin.blockSignals(True)
        
        self._name_edit.setText(self._selected_bodypart.name)
        self._pos_x_spin.setValue(self._selected_bodypart.position.x)
        self._pos_y_spin.setValue(self._selected_bodypart.position.y)
        self._size_x_spin.setValue(self._selected_bodypart.size.x)
        self._size_y_spin.setValue(self._selected_bodypart.size.y)
        self._pixel_scale_spin.setValue(self._selected_bodypart.pixel_scale)
        self._z_order_spin.setValue(self._selected_bodypart.z_order)
        self._texture_edit.setText(self._selected_bodypart.texture_path)
        self._flip_x_check.setChecked(self._selected_bodypart.flip_x)
        self._flip_y_check.setChecked(self._selected_bodypart.flip_y)
        self._rotation_spin.setValue(int(self._selected_bodypart.rotation))
        
        # Unblock signals
        self._name_edit.blockSignals(False)
        self._pos_x_spin.blockSignals(False)
        self._pos_y_spin.blockSignals(False)
        self._size_x_spin.blockSignals(False)
        self._size_y_spin.blockSignals(False)
        self._pixel_scale_spin.blockSignals(False)
        self._z_order_spin.blockSignals(False)
        self._texture_edit.blockSignals(False)
        self._flip_x_check.blockSignals(False)
        self._flip_y_check.blockSignals(False)
        self._rotation_spin.blockSignals(False)
    
    def _update_properties_enabled(self):
        """Enable/disable properties based on selection."""
        enabled = self._selected_bodypart is not None
        has_texture = enabled and self._selected_bodypart.texture_path != ""
        
        self._name_edit.setEnabled(enabled)
        self._pos_x_spin.setEnabled(enabled)
        self._pos_y_spin.setEnabled(enabled)
        self._size_x_spin.setEnabled(enabled)
        self._size_y_spin.setEnabled(enabled)
        self._pixel_scale_spin.setEnabled(enabled)
        self._z_order_spin.setEnabled(enabled)
        self._texture_edit.setEnabled(enabled)
        self._browse_btn.setEnabled(enabled)
        self._flip_x_check.setEnabled(enabled)
        self._flip_y_check.setEnabled(enabled)
        self._rotation_spin.setEnabled(enabled)
        self._remove_btn.setEnabled(enabled)
        self._rename_btn.setEnabled(enabled)
        self._duplicate_btn.setEnabled(enabled)
        self._edit_uv_btn.setEnabled(has_texture)  # Only enabled when texture assigned
    
    def _on_external_modification(self, bodypart):
        """Handle external modification."""
        if bodypart == self._selected_bodypart:
            self._update_properties()
    
    def _on_show_above_changed(self, checked: bool):
        """Handle show-above-while-editing checkbox toggle."""
        self._signal_hub.notify_bodypart_show_above_changed(checked)

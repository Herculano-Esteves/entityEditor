"""
Body Parts Panel for Entity Editor.

Panel for managing and editing body parts.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                                QListWidget, QListWidgetItem, QFormLayout, 
                                QDoubleSpinBox, QLineEdit, QFileDialog, QGroupBox,
                                QSpinBox, QLabel)
from PySide6.QtCore import Qt
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.data import Entity, BodyPart, Vec2, UVRect
from src.core import get_signal_hub


class BodyPartsPanel(QWidget):
    """Panel for managing body parts."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._entity = None
        self._selected_bodypart = None
        self._signal_hub = get_signal_hub()
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Setup the UI layout."""
        layout = QVBoxLayout(self)
        
        # Body parts list
        list_label = QLabel("Body Parts:")
        layout.addWidget(list_label)
        
        self._bodyparts_list = QListWidget()
        self._bodyparts_list.currentItemChanged.connect(self._on_selection_changed)
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
        
        layout.addLayout(buttons_layout)
        
        # Properties group
        props_group = QGroupBox("Properties")
        props_layout = QFormLayout()
        
        # Name
        self._name_edit = QLineEdit()
        self._name_edit.textChanged.connect(self._on_property_changed)
        props_layout.addRow("Name:", self._name_edit)
        
        # Position
        self._pos_x_spin = QDoubleSpinBox()
        self._pos_x_spin.setRange(-10000, 10000)
        self._pos_x_spin.valueChanged.connect(self._on_property_changed)
        props_layout.addRow("Position X:", self._pos_x_spin)
        
        self._pos_y_spin = QDoubleSpinBox()
        self._pos_y_spin.setRange(-10000, 10000)
        self._pos_y_spin.valueChanged.connect(self._on_property_changed)
        props_layout.addRow("Position Y:", self._pos_y_spin)
        
        # Size
        self._size_x_spin = QDoubleSpinBox()
        self._size_x_spin.setRange(0.1, 10000)
        self._size_x_spin.setValue(64)
        self._size_x_spin.valueChanged.connect(self._on_property_changed)
        props_layout.addRow("Width:", self._size_x_spin)
        
        self._size_y_spin = QDoubleSpinBox()
        self._size_y_spin.setRange(0.1, 10000)
        self._size_y_spin.setValue(64)
        self._size_y_spin.valueChanged.connect(self._on_property_changed)
        props_layout.addRow("Height:", self._size_y_spin)
        
        # Z-order
        self._z_order_spin = QSpinBox()
        self._z_order_spin.setRange(-100, 100)
        self._z_order_spin.valueChanged.connect(self._on_property_changed)
        props_layout.addRow("Z-Order:", self._z_order_spin)
        
        # Texture
        texture_layout = QHBoxLayout()
        self._texture_edit = QLineEdit()
        self._texture_edit.textChanged.connect(self._on_property_changed)
        texture_layout.addWidget(self._texture_edit)
        
        self._browse_btn = QPushButton("Browse...")
        self._browse_btn.clicked.connect(self._on_browse_texture)
        texture_layout.addWidget(self._browse_btn)
        
        props_layout.addRow("Texture:", texture_layout)
        
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
        self._refresh_list()
    
    def _refresh_list(self):
        """Refresh the body parts list."""
        self._bodyparts_list.clear()
        
        if not self._entity:
            return
        
        for bp in self._entity.body_parts:
            item = QListWidgetItem(bp.name)
            item.setData(Qt.UserRole, bp)
            self._bodyparts_list.addItem(item)
    
    def _on_selection_changed(self, current, previous):
        """Handle selection change in list."""
        if current:
            bp = current.data(Qt.UserRole)
            self._selected_bodypart = bp
            self._update_properties()
            self._signal_hub.notify_bodypart_selected(bp)
        else:
            self._selected_bodypart = None
            self._signal_hub.notify_bodypart_selected(None)
        
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
    
    def _on_add_bodypart(self):
        """Add a new body part."""
        if not self._entity:
            return
        
        count = len(self._entity.body_parts)
        bp = BodyPart(
            name=f"BodyPart_{count}",
            position=Vec2(0, 0),
            size=Vec2(64, 64),
            z_order=count
        )
        self._entity.add_body_part(bp)
        self._signal_hub.notify_bodypart_added(bp)
        self._refresh_list()
        
        # Select the new body part
        self._bodyparts_list.setCurrentRow(self._bodyparts_list.count() - 1)
    
    def _on_remove_bodypart(self):
        """Remove the selected body part."""
        if not self._entity or not self._selected_bodypart:
            return
        
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
    
    def _on_property_changed(self):
        """Handle property change."""
        if not self._selected_bodypart:
            return
        
        # Update body part from UI
        self._selected_bodypart.name = self._name_edit.text()
        self._selected_bodypart.position.x = self._pos_x_spin.value()
        self._selected_bodypart.position.y = self._pos_y_spin.value()
        self._selected_bodypart.size.x = self._size_x_spin.value()
        self._selected_bodypart.size.y = self._size_y_spin.value()
        self._selected_bodypart.z_order = self._z_order_spin.value()
        self._selected_bodypart.texture_path = self._texture_edit.text()
        
        # Update list item name
        current_item = self._bodyparts_list.currentItem()
        if current_item:
            current_item.setText(self._selected_bodypart.name)
        
        self._signal_hub.notify_bodypart_modified(self._selected_bodypart)
    
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
        self._z_order_spin.blockSignals(True)
        self._texture_edit.blockSignals(True)
        
        self._name_edit.setText(self._selected_bodypart.name)
        self._pos_x_spin.setValue(self._selected_bodypart.position.x)
        self._pos_y_spin.setValue(self._selected_bodypart.position.y)
        self._size_x_spin.setValue(self._selected_bodypart.size.x)
        self._size_y_spin.setValue(self._selected_bodypart.size.y)
        self._z_order_spin.setValue(self._selected_bodypart.z_order)
        self._texture_edit.setText(self._selected_bodypart.texture_path)
        
        # Unblock signals
        self._name_edit.blockSignals(False)
        self._pos_x_spin.blockSignals(False)
        self._pos_y_spin.blockSignals(False)
        self._size_x_spin.blockSignals(False)
        self._size_y_spin.blockSignals(False)
        self._z_order_spin.blockSignals(False)
        self._texture_edit.blockSignals(False)
    
    def _update_properties_enabled(self):
        """Enable/disable properties based on selection."""
        enabled = self._selected_bodypart is not None
        
        self._name_edit.setEnabled(enabled)
        self._pos_x_spin.setEnabled(enabled)
        self._pos_y_spin.setEnabled(enabled)
        self._size_x_spin.setEnabled(enabled)
        self._size_y_spin.setEnabled(enabled)
        self._z_order_spin.setEnabled(enabled)
        self._texture_edit.setEnabled(enabled)
        self._browse_btn.setEnabled(enabled)
        self._remove_btn.setEnabled(enabled)
        self._rename_btn.setEnabled(enabled)
    
    def _on_external_modification(self, bodypart):
        """Handle external modification."""
        if bodypart == self._selected_bodypart:
            self._update_properties()

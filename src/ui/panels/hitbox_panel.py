"""
Hitbox Editor Panel for Entity Editor.

Panel for managing and editing hitboxes.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                                QListWidget, QListWidgetItem, QFormLayout, 
                                QDoubleSpinBox, QLineEdit, QComboBox, QGroupBox, QLabel)
from PySide6.QtCore import Qt
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.data import Entity, Hitbox, Vec2
from src.core import get_signal_hub


class HitboxPanel(QWidget):
    """Panel for managing hitboxes."""
    
    HITBOX_TYPES = ["collision", "damage", "trigger", "interaction", "custom"]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._entity = None
        self._selected_bodypart = None
        self._selected_hitbox = None
        self._signal_hub = get_signal_hub()
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Setup the UI layout."""
        layout = QVBoxLayout(self)
        
        # Info label
        info_label = QLabel("Hitboxes for selected body part:")
        layout.addWidget(info_label)
        
        # Hitbox list
        self._hitbox_list = QListWidget()
        self._hitbox_list.currentItemChanged.connect(self._on_selection_changed)
        layout.addWidget(self._hitbox_list)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        self._add_btn = QPushButton("Add Hitbox")
        self._add_btn.clicked.connect(self._on_add_hitbox)
        buttons_layout.addWidget(self._add_btn)
        
        self._remove_btn = QPushButton("Remove")
        self._remove_btn.clicked.connect(self._on_remove_hitbox)
        buttons_layout.addWidget(self._remove_btn)
        
        layout.addLayout(buttons_layout)
        
        # Properties group
        props_group = QGroupBox("Hitbox Properties")
        props_layout = QFormLayout()
        
        # Name
        self._name_edit = QLineEdit()
        self._name_edit.textChanged.connect(self._on_property_changed)
        props_layout.addRow("Name:", self._name_edit)
        
        # Type
        self._type_combo = QComboBox()
        self._type_combo.addItems(self.HITBOX_TYPES)
        self._type_combo.currentTextChanged.connect(self._on_property_changed)
        props_layout.addRow("Type:", self._type_combo)
        
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
        self._size_x_spin.setValue(32)
        self._size_x_spin.valueChanged.connect(self._on_property_changed)
        props_layout.addRow("Width:", self._size_x_spin)
        
        self._size_y_spin = QDoubleSpinBox()
        self._size_y_spin.setRange(0.1, 10000)
        self._size_y_spin.setValue(32)
        self._size_y_spin.valueChanged.connect(self._on_property_changed)
        props_layout.addRow("Height:", self._size_y_spin)
        
        props_group.setLayout(props_layout)
        layout.addWidget(props_group)
        
        layout.addStretch()
        
        self._update_properties_enabled()
    
    def _connect_signals(self):
        """Connect to signal hub."""
        self._signal_hub.entity_loaded.connect(self.set_entity)
        self._signal_hub.bodypart_selected.connect(self._on_bodypart_selected)
        self._signal_hub.bodypart_modified.connect(lambda _: self._refresh_list())
    
    def set_entity(self, entity: Entity):
        """Set the entity to edit."""
        self._entity = entity
        self._selected_bodypart = None
        self._selected_hitbox = None
        self._refresh_list()
    
    def _on_bodypart_selected(self, bodypart):
        """Handle body part selection."""
        self._selected_bodypart = bodypart
        self._selected_hitbox = None
        self._refresh_list()
    
    def _refresh_list(self):
        """Refresh the hitbox list."""
        self._hitbox_list.clear()
        
        if not self._selected_bodypart:
            self._add_btn.setEnabled(False)
            return
        
        self._add_btn.setEnabled(True)
        
        for hitbox in self._selected_bodypart.hitboxes:
            item = QListWidgetItem(f"{hitbox.name} ({hitbox.hitbox_type})")
            item.setData(Qt.UserRole, hitbox)
            self._hitbox_list.addItem(item)
    
    def _on_selection_changed(self, current, previous):
        """Handle selection change in list."""
        if current:
            self._selected_hitbox = current.data(Qt.UserRole)
            self._update_properties()
            self._signal_hub.notify_hitbox_selected(self._selected_hitbox)
        else:
            self._selected_hitbox = None
            self._signal_hub.notify_hitbox_selected(None)
        
        self._update_properties_enabled()
    
    def _on_add_hitbox(self):
        """Add a new hitbox."""
        if not self._selected_bodypart:
            return
        
        count = len(self._selected_bodypart.hitboxes)
        hitbox = Hitbox(
            name=f"Hitbox_{count}",
            position=Vec2(0, 0),
            size=Vec2(32, 32),
            hitbox_type="collision"
        )
        self._selected_bodypart.hitboxes.append(hitbox)
        self._signal_hub.notify_hitbox_added(hitbox)
        self._refresh_list()
        
        # Select the new hitbox
        self._hitbox_list.setCurrentRow(self._hitbox_list.count() - 1)
    
    def _on_remove_hitbox(self):
        """Remove the selected hitbox."""
        if not self._selected_bodypart or not self._selected_hitbox:
            return
        
        if self._selected_hitbox in self._selected_bodypart.hitboxes:
            self._selected_bodypart.hitboxes.remove(self._selected_hitbox)
            self._signal_hub.notify_hitbox_removed(self._selected_hitbox)
            self._refresh_list()
    
    def _on_property_changed(self):
        """Handle property change."""
        if not self._selected_hitbox:
            return
        
        # Update hitbox from UI
        self._selected_hitbox.name = self._name_edit.text()
        self._selected_hitbox.hitbox_type = self._type_combo.currentText()
        self._selected_hitbox.position.x = self._pos_x_spin.value()
        self._selected_hitbox.position.y = self._pos_y_spin.value()
        self._selected_hitbox.size.x = self._size_x_spin.value()
        self._selected_hitbox.size.y = self._size_y_spin.value()
        
        # Update list item name
        current_item = self._hitbox_list.currentItem()
        if current_item:
            current_item.setText(f"{self._selected_hitbox.name} ({self._selected_hitbox.hitbox_type})")
        
        self._signal_hub.notify_hitbox_modified(self._selected_hitbox)
    
    def _update_properties(self):
        """Update properties from selected hitbox."""
        if not self._selected_hitbox:
            return
        
        # Block signals
        self._name_edit.blockSignals(True)
        self._type_combo.blockSignals(True)
        self._pos_x_spin.blockSignals(True)
        self._pos_y_spin.blockSignals(True)
        self._size_x_spin.blockSignals(True)
        self._size_y_spin.blockSignals(True)
        
        self._name_edit.setText(self._selected_hitbox.name)
        self._type_combo.setCurrentText(self._selected_hitbox.hitbox_type)
        self._pos_x_spin.setValue(self._selected_hitbox.position.x)
        self._pos_y_spin.setValue(self._selected_hitbox.position.y)
        self._size_x_spin.setValue(self._selected_hitbox.size.x)
        self._size_y_spin.setValue(self._selected_hitbox.size.y)
        
        # Unblock signals
        self._name_edit.blockSignals(False)
        self._type_combo.blockSignals(False)
        self._pos_x_spin.blockSignals(False)
        self._pos_y_spin.blockSignals(False)
        self._size_x_spin.blockSignals(False)
        self._size_y_spin.blockSignals(False)
    
    def _update_properties_enabled(self):
        """Enable/disable properties based on selection."""
        enabled = self._selected_hitbox is not None
        
        self._name_edit.setEnabled(enabled)
        self._type_combo.setEnabled(enabled)
        self._pos_x_spin.setEnabled(enabled)
        self._pos_y_spin.setEnabled(enabled)
        self._size_x_spin.setEnabled(enabled)
        self._size_y_spin.setEnabled(enabled)
        self._remove_btn.setEnabled(enabled)

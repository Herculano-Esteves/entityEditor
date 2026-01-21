"""
Entity Properties Panel for Entity Editor.

Panel for editing entity-level metadata and properties.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLineEdit, 
                                QLabel, QDoubleSpinBox, QGroupBox)
from PySide6.QtCore import Qt
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.data import Entity
from src.core import get_signal_hub


class EntityPanel(QWidget):
    """Panel for editing entity properties."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._entity = None
        self._signal_hub = get_signal_hub()
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Setup the UI layout."""
        layout = QVBoxLayout(self)
        
        # Entity metadata group
        metadata_group = QGroupBox("Entity Metadata")
        metadata_layout = QFormLayout()
        
        self._name_edit = QLineEdit()
        self._name_edit.textChanged.connect(self._on_name_changed)
        metadata_layout.addRow("Name:", self._name_edit)
        
        self._id_label = QLabel("N/A")
        metadata_layout.addRow("ID:", self._id_label)
        
        metadata_group.setLayout(metadata_layout)
        layout.addWidget(metadata_group)
        
        # Pivot group
        pivot_group = QGroupBox("Pivot Point")
        pivot_layout = QFormLayout()
        
        self._pivot_x_spin = QDoubleSpinBox()
        self._pivot_x_spin.setRange(-10000, 10000)
        self._pivot_x_spin.valueChanged.connect(self._on_pivot_changed)
        pivot_layout.addRow("X:", self._pivot_x_spin)
        
        self._pivot_y_spin = QDoubleSpinBox()
        self._pivot_y_spin.setRange(-10000, 10000)
        self._pivot_y_spin.valueChanged.connect(self._on_pivot_changed)
        pivot_layout.addRow("Y:", self._pivot_y_spin)
        
        pivot_group.setLayout(pivot_layout)
        layout.addWidget(pivot_group)
        
        layout.addStretch()
    
    def _connect_signals(self):
        """Connect to signal hub."""
        self._signal_hub.entity_loaded.connect(self.set_entity)
    
    def set_entity(self, entity: Entity):
        """Set the entity to edit."""
        self._entity = entity
        self._update_ui()
    
    def _update_ui(self):
        """Update UI from entity data."""
        if not self._entity:
            self._name_edit.setText("")
            self._id_label.setText("N/A")
            self._pivot_x_spin.setValue(0)
            self._pivot_y_spin.setValue(0)
            return
        
        # Block signals to prevent feedback loop
        self._name_edit.blockSignals(True)
        self._pivot_x_spin.blockSignals(True)
        self._pivot_y_spin.blockSignals(True)
        
        self._name_edit.setText(self._entity.name)
        self._id_label.setText(self._entity.entity_id)
        self._pivot_x_spin.setValue(self._entity.pivot.x)
        self._pivot_y_spin.setValue(self._entity.pivot.y)
        
        self._name_edit.blockSignals(False)
        self._pivot_x_spin.blockSignals(False)
        self._pivot_y_spin.blockSignals(False)
    
    def _on_name_changed(self, text: str):
        """Handle name change."""
        if self._entity:
            self._entity.name = text
            self._signal_hub.notify_entity_modified()
    
    def _on_pivot_changed(self):
        """Handle pivot change."""
        if self._entity:
            self._entity.pivot.x = self._pivot_x_spin.value()
            self._entity.pivot.y = self._pivot_y_spin.value()
            self._signal_hub.notify_entity_modified()

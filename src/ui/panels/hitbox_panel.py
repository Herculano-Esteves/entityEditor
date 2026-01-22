"""
Hitbox Editor Panel for Entity Editor.

Panel for managing and editing hitboxes.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QGroupBox, QFormLayout, QLineEdit, QPushButton, QDoubleSpinBox,
    QComboBox, QCheckBox, QLabel
)
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
        
        # Edit mode toggle
        self._edit_mode_check = QCheckBox("Edit Hitboxes")
        self._edit_mode_check.toggled.connect(self._on_edit_mode_changed)
        self._edit_mode_check.setToolTip("Enable hitbox editing mode\n(Shortcut: Hold Shift)")
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
        props_group = QGroupBox("Hitbox Properties")
        props_layout = QFormLayout()
        
        # Name
        self._name_edit = QLineEdit()
        self._name_edit.editingFinished.connect(self._on_name_changed)  # Only when done editing
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
            # Disable edit mode when no body part selected
            self._edit_mode_check.setEnabled(False)
            if self._edit_mode_check.isChecked():
                self._edit_mode_check.setChecked(False)
            return
        
        # Enable edit mode when body part is selected
        self._edit_mode_check.setEnabled(True)
        
        self._add_btn.setEnabled(True)
        
        for hitbox in self._selected_bodypart.hitboxes:
            # Create list item
            item = QListWidgetItem()
            item.setData(Qt.UserRole, hitbox)
            self._hitbox_list.addItem(item)
            
            # Create custom widget with eye icon and name
            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(4, 2, 4, 2)
            layout.setSpacing(4)
            
            # Eye button for visibility toggle
            eye_btn = QPushButton()
            eye_btn.setFixedSize(20, 20)
            eye_btn.setFlat(True)
            eye_btn.setText("👁" if hitbox.enabled else "⚫")
            eye_btn.setToolTip("Toggle visibility")
            eye_btn.clicked.connect(lambda checked, hb=hitbox: self._toggle_visibility(hb))
            layout.addWidget(eye_btn)
            
            # Name label with type color indicator
            type_color = {"collision": "#ff6464", "damage": "#ffc864", "trigger": "#64ff64"}.get(hitbox.hitbox_type, "#c8c8c8")
            name_label = QLabel(f'<span style="color:{type_color}">■</span> {hitbox.name}')
            layout.addWidget(name_label)
            layout.addStretch()
            
            item.setSizeHint(widget.sizeHint())
            self._hitbox_list.setItemWidget(item, widget)
    
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
        
        # Default hitbox size matches body part's rendered size
        default_w = self._selected_bodypart.size.x * self._selected_bodypart.pixel_scale
        default_h = self._selected_bodypart.size.y * self._selected_bodypart.pixel_scale
        
        hitbox = Hitbox(
            name=f"Hitbox_{count}",
            position=Vec2(0, 0),
            size=Vec2(default_w, default_h),
            hitbox_type="collision"
        )
        self._selected_bodypart.hitboxes.append(hitbox)
        self._signal_hub.notify_hitbox_added(hitbox)
        self._refresh_list()
        
        # Select the new hitbox
        self._hitbox_list.setCurrentRow(self._hitbox_list.count() - 1)
    
    def _on_duplicate_hitbox(self):
        """Duplicate the selected hitbox."""
        if not self._selected_bodypart or not self._selected_hitbox:
            return
        
        # Create a copy
        import copy
        hitbox_copy = copy.deepcopy(self._selected_hitbox)
        
        # Modify name (add "2" or increment number)
        base_name = hitbox_copy.name
        if base_name[-1].isdigit():
            import re
            match = re.match(r'(.+?)(\d+)$', base_name)
            if match:
                hitbox_copy.name = match.group(1) + str(int(match.group(2)) + 1)
            else:
                hitbox_copy.name = base_name + "2"
        else:
            hitbox_copy.name = base_name + "2"
        
        # Offset position slightly
        hitbox_copy.position.x += 5
        hitbox_copy.position.y += 5
        
        self._selected_bodypart.hitboxes.append(hitbox_copy)
        self._signal_hub.notify_hitbox_added(hitbox_copy)
        self._refresh_list()
        
        # Select the new hitbox
        self._hitbox_list.setCurrentRow(self._hitbox_list.count() - 1)
    
    def _on_edit_mode_changed(self, checked: bool):
        """Handle edit mode toggle."""
        self._signal_hub.notify_hitbox_edit_mode_changed(checked)
    
    def _toggle_visibility(self, hitbox):
        """Toggle hitbox visibility."""
        hitbox.enabled = not hitbox.enabled
        self._signal_hub.notify_hitbox_modified(hitbox)
        self._refresh_list()  # Refresh to update eye icon
    
    def _on_remove_hitbox(self):
        """Remove the selected hitbox."""
        if not self._selected_bodypart or not self._selected_hitbox:
            return
        
        if self._selected_hitbox in self._selected_bodypart.hitboxes:
            self._selected_bodypart.hitboxes.remove(self._selected_hitbox)
            self._signal_hub.notify_hitbox_removed(self._selected_hitbox)
            self._refresh_list()
    
    def _on_name_changed(self):
        """Handle name editing finished (to update list labels)."""
        if not self._selected_hitbox:
            return
        
        old_name = self._selected_hitbox.name
        self._selected_hitbox.name = self._name_edit.text()
        
        # Update only the label widget for the current item (don't refresh entire list)
        if old_name != self._selected_hitbox.name:
            current_item = self._hitbox_list.currentItem()
            if current_item:
                widget = self._hitbox_list.itemWidget(current_item)
                if widget:
                    # Find the QLabel in the widget and update its text
                    from PySide6.QtWidgets import QLabel
                    label = widget.findChild(QLabel)
                    if label:
                        # Update with colored type indicator
                        type_color = {"collision": "#ff6464", "damage": "#ffc864", "trigger": "#64ff64"}.get(self._selected_hitbox.hitbox_type, "#c8c8c8")
                        label.setText(f'<span style="color:{type_color}">■</span> {self._selected_hitbox.name}')
        
        # Notify modification
        self._signal_hub.notify_hitbox_modified(self._selected_hitbox)
    
    def _on_property_changed(self):
        """Handle property change."""
        if not self._selected_hitbox:
            return
        
        # Update hitbox from UI (skip name, it has its own handler)
        self._selected_hitbox.hitbox_type = self._type_combo.currentText()
        self._selected_hitbox.position.x = self._pos_x_spin.value()
        self._selected_hitbox.position.y = self._pos_y_spin.value()
        self._selected_hitbox.size.x = self._size_x_spin.value()
        self._selected_hitbox.size.y = self._size_y_spin.value()
        
        # Notify modification
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
        self._duplicate_btn.setEnabled(enabled)

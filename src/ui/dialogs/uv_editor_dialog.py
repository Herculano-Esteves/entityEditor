"""
UV Editor Dialog

Modal dialog for editing UV coordinates with both visual and text-based controls.
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                                QPushButton, QDoubleSpinBox, QSpinBox, QLabel,
                                QGroupBox, QFileDialog, QLineEdit, QSplitter)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.data import BodyPart
from src.ui.widgets import UVEditorWidget
from src.rendering import get_texture_manager


class UVEditorDialog(QDialog):
    """
    Modal dialog for editing UV mapping for a body part.
    
    Features:
    - Visual texture preview with draggable UV rectangle
    - Text inputs for precise UV coordinates (0-1)
    - Text inputs for pixel coordinates (auto-synced)
    - Texture selection
    """
    
    def __init__(self, body_part: BodyPart, parent=None):
        super().__init__(parent)
        
        self.body_part = body_part
        self._original_uv = None  # Backup for cancel
        self._updating = False  # Flag to prevent feedback loops
        
        # Store original UV values for cancel
        self._backup_uv()
        
        # Auto-update body part size to match current UV (fixes outdated sizes)
        self._auto_size_from_uv()
        
        self.setWindowTitle(f"UV Editor: {body_part.name}")
        self.resize(900, 600)
        
        self._setup_ui()
        self._load_current_values()
        self._connect_signals()
    
    def _auto_size_from_uv(self):
        """Auto-size body part to match UV pixel dimensions."""
        from src.rendering import get_texture_manager
        texture_manager = get_texture_manager()
        size = texture_manager.get_texture_size(self.body_part.texture_path)
        
        if size:
            tex_w, tex_h = size
            uv = self.body_part.uv_rect
            pixel_width = int(uv.width * tex_w)
            pixel_height = int(uv.height * tex_h)
            
            # Update body part size to match UV region (1:1 pixel mapping)
            self.body_part.size.x = pixel_width
            self.body_part.size.y = pixel_height
    
    def _backup_uv(self):
        """Backup current UV values for cancel operation."""
        uv = self.body_part.uv_rect
        self._original_uv = {
            'x': uv.x,
            'y': uv.y,
            'width': uv.width,
            'height': uv.height
        }
        self._original_texture = self.body_part.texture_path
    
    def _restore_uv(self):
        """Restore UV values from backup."""
        uv = self.body_part.uv_rect
        uv.x = self._original_uv['x']
        uv.y = self._original_uv['y']
        uv.width = self._original_uv['width']
        uv.height = self._original_uv['height']
        self.body_part.texture_path = self._original_texture
    
    def _setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Texture selection at top
        texture_layout = QHBoxLayout()
        texture_layout.addWidget(QLabel("Texture:"))
        
        self._texture_path_edit = QLineEdit()
        self._texture_path_edit.setText(self.body_part.texture_path)
        self._texture_path_edit.setReadOnly(True)
        texture_layout.addWidget(self._texture_path_edit, stretch=1)
        
        self._browse_btn = QPushButton("Browse...")
        self._browse_btn.clicked.connect(self._on_browse_texture)
        texture_layout.addWidget(self._browse_btn)
        
        layout.addLayout(texture_layout)
        
        # Main content: splitter with visual editor and controls
        splitter = QSplitter(Qt.Horizontal)
        
        # Left side: Visual editor
        self._uv_widget = UVEditorWidget()
        self._uv_widget.set_body_part(self.body_part)
        splitter.addWidget(self._uv_widget)
        
        # Right side: Text controls
        controls_widget = self._create_controls_panel()
        splitter.addWidget(controls_widget)
        
        # Set splitter sizes (visual editor gets more space)
        splitter.setSizes([500, 300])
        
        layout.addWidget(splitter, stretch=1)
        
        # Bottom buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        self._ok_btn = QPushButton("OK")
        self._ok_btn.clicked.connect(self.accept)
        self._ok_btn.setDefault(True)
        buttons_layout.addWidget(self._ok_btn)
        
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(self._cancel_btn)
        
        layout.addLayout(buttons_layout)
    
    def _create_controls_panel(self):
        """Create the right-side controls panel."""
        widget = QGroupBox("UV Coordinates")
        layout = QVBoxLayout(widget)
        
        # UV Coordinates (0.0 - 1.0)
        uv_group = QGroupBox("Normalized UV (0.0 - 1.0)")
        uv_layout = QFormLayout()
        
        self._uv_x_spin = QDoubleSpinBox()
        self._uv_x_spin.setRange(0.0, 1.0)
        self._uv_x_spin.setDecimals(4)
        self._uv_x_spin.setSingleStep(0.01)
        uv_layout.addRow("X:", self._uv_x_spin)
        
        self._uv_y_spin = QDoubleSpinBox()
        self._uv_y_spin.setRange(0.0, 1.0)
        self._uv_y_spin.setDecimals(4)
        self._uv_y_spin.setSingleStep(0.01)
        uv_layout.addRow("Y:", self._uv_y_spin)
        
        self._uv_w_spin = QDoubleSpinBox()
        self._uv_w_spin.setRange(0.0, 1.0)
        self._uv_w_spin.setDecimals(4)
        self._uv_w_spin.setSingleStep(0.01)
        uv_layout.addRow("Width:", self._uv_w_spin)
        
        self._uv_h_spin = QDoubleSpinBox()
        self._uv_h_spin.setRange(0.0, 1.0)
        self._uv_h_spin.setDecimals(4)
        self._uv_h_spin.setSingleStep(0.01)
        uv_layout.addRow("Height:", self._uv_h_spin)
        
        uv_group.setLayout(uv_layout)
        layout.addWidget(uv_group)
        
        # Pixel Coordinates
        px_group = QGroupBox("Pixel Coordinates")
        px_layout = QFormLayout()
        
        self._px_x_spin = QSpinBox()
        self._px_x_spin.setRange(0, 99999)
        px_layout.addRow("X:", self._px_x_spin)
        
        self._px_y_spin = QSpinBox()
        self._px_y_spin.setRange(0, 99999)
        px_layout.addRow("Y:", self._px_y_spin)
        
        self._px_w_spin = QSpinBox()
        self._px_w_spin.setRange(1, 99999)
        px_layout.addRow("Width:", self._px_w_spin)
        
        self._px_h_spin = QSpinBox()
        self._px_h_spin.setRange(1, 99999)
        px_layout.addRow("Height:", self._px_h_spin)
        
        px_group.setLayout(px_layout)
        layout.addWidget(px_group)
        
        # Texture info
        self._texture_info_label = QLabel("No texture loaded")
        layout.addWidget(self._texture_info_label)
        
        layout.addStretch()
        
        return widget
    
    def _load_current_values(self):
        """Load current UV values into spinboxes."""
        self._updating = True
        
        uv = self.body_part.uv_rect
        self._uv_x_spin.setValue(uv.x)
        self._uv_y_spin.setValue(uv.y)
        self._uv_w_spin.setValue(uv.width)
        self._uv_h_spin.setValue(uv.height)
        
        # Update pixel coordinates
        self._update_pixel_coords()
        
        # Update texture info
        self._update_texture_info()
        
        self._updating = False
    
    def _connect_signals(self):
        """Connect signals for two-way sync."""
        # UV spinboxes → update body part and pixel coords
        self._uv_x_spin.valueChanged.connect(self._on_uv_changed)
        self._uv_y_spin.valueChanged.connect(self._on_uv_changed)
        self._uv_w_spin.valueChanged.connect(self._on_uv_changed)
        self._uv_h_spin.valueChanged.connect(self._on_uv_changed)
        
        # Pixel spinboxes → update UV coords
        self._px_x_spin.valueChanged.connect(self._on_pixel_changed)
        self._px_y_spin.valueChanged.connect(self._on_pixel_changed)
        self._px_w_spin.valueChanged.connect(self._on_pixel_changed)
        self._px_h_spin.valueChanged.connect(self._on_pixel_changed)
        
        # Visual editor → update spinboxes
        self._uv_widget.uv_changed.connect(self._on_visual_uv_changed)
    
    def _on_uv_changed(self):
        """Handle UV spinbox changes."""
        if self._updating:
            return
        
        self._updating = True
        
        # Update body part UV
        self.body_part.uv_rect.x = self._uv_x_spin.value()
        self.body_part.uv_rect.y = self._uv_y_spin.value()
        self.body_part.uv_rect.width = self._uv_w_spin.value()
        self.body_part.uv_rect.height = self._uv_h_spin.value()
        
        # Auto-resize body part to match UV pixel dimensions (maintains pixel_scale)
        texture_manager = get_texture_manager()
        size = texture_manager.get_texture_size(self.body_part.texture_path)
        if size:
            tex_w, tex_h = size
            pixel_width = int(self.body_part.uv_rect.width * tex_w)
            pixel_height = int(self.body_part.uv_rect.height * tex_h)
            
            # Update body part size to match UV region (1:1 pixel mapping)
            self.body_part.size.x = pixel_width
            self.body_part.size.y = pixel_height
        
        # Update pixel coordinates
        self._update_pixel_coords()
        
        # Update visual editor
        self._uv_widget._on_bodypart_modified(self.body_part)
        
        self._updating = False
    
    def _on_pixel_changed(self):
        """Handle pixel spinbox changes."""
        if self._updating:
            return
        
        # Get texture size
        texture_manager = get_texture_manager()
        size = texture_manager.get_texture_size(self.body_part.texture_path)
        
        if not size:
            return
        
        tex_w, tex_h = size
        
        self._updating = True
        
        # Convert pixels to UV
        uv_x = self._px_x_spin.value() / tex_w
        uv_y = self._px_y_spin.value() / tex_h
        uv_w = self._px_w_spin.value() / tex_w
        uv_h = self._px_h_spin.value() / tex_h
        
        # Update UV spinboxes
        self._uv_x_spin.setValue(uv_x)
        self._uv_y_spin.setValue(uv_y)
        self._uv_w_spin.setValue(uv_w)
        self._uv_h_spin.setValue(uv_h)
        
        # Update body part UV
        self.body_part.uv_rect.x = uv_x
        self.body_part.uv_rect.y = uv_y
        self.body_part.uv_rect.width = uv_w
        self.body_part.uv_rect.height = uv_h
        
        # Auto-resize body part to match UV pixel dimensions
        pixel_width = self._px_w_spin.value()
        pixel_height = self._px_h_spin.value()
        self.body_part.size.x = pixel_width
        self.body_part.size.y = pixel_height
        
        # Update visual editor
        self._uv_widget.set_body_part(self.body_part)
        
        self._updating = False
    
    def _on_visual_uv_changed(self, body_part):
        """Handle UV changes from visual editor."""
        if self._updating:
            return
        
        self._updating = True
        
        # Update UV spinboxes (widget already handled auto-sizing)
        uv = body_part.uv_rect
        self._uv_x_spin.setValue(uv.x)
        self._uv_y_spin.setValue(uv.y)
        self._uv_w_spin.setValue(uv.width)
        self._uv_h_spin.setValue(uv.height)
        
        # Update pixel coordinates
        self._update_pixel_coords()
        
        self._updating = False
    
    def _update_pixel_coords(self):
        """Update pixel coordinate spinboxes from UV coords."""
        texture_manager = get_texture_manager()
        size = texture_manager.get_texture_size(self.body_part.texture_path)
        
        if not size:
            return
        
        tex_w, tex_h = size
        
        uv = self.body_part.uv_rect
        self._px_x_spin.setValue(int(uv.x * tex_w))
        self._px_y_spin.setValue(int(uv.y * tex_h))
        self._px_w_spin.setValue(int(uv.width * tex_w))
        self._px_h_spin.setValue(int(uv.height * tex_h))
    
    def _update_texture_info(self):
        """Update texture info label."""
        texture_manager = get_texture_manager()
        size = texture_manager.get_texture_size(self.body_part.texture_path)
        
        if size:
            self._texture_info_label.setText(f"Texture size: {size[0]} × {size[1]} px")
        else:
            self._texture_info_label.setText("No texture loaded")
    
    def _on_browse_texture(self):
        """Browse for texture file."""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select Texture",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp);;All Files (*.*)"
        )
        
        if filename:
            self.body_part.texture_path = filename
            self._texture_path_edit.setText(filename)
            
            # Reset UV to full texture
            self.body_part.uv_rect.x = 0.0
            self.body_part.uv_rect.y = 0.0
            self.body_part.uv_rect.width = 1.0
            self.body_part.uv_rect.height = 1.0
            
            # Reload
            self._load_current_values()
            self._uv_widget._on_bodypart_modified(self.body_part)
    
    def reject(self):
        """Handle cancel - restore original UV values."""
        self._restore_uv()
        super().reject()

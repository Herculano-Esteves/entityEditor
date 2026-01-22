"""
UV Tile Library Widget

Manages a collection of reusable UV tiles (presets).
Users can create tiles from current UV selection and apply them to body parts.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                                QListWidget, QListWidgetItem, QInputDialog, QMessageBox,
                                QLabel, QFileDialog)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QIcon
from typing import Optional
import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.data import UVTile, UVTileLibrary, BodyPart, UVRect
from src.core import get_signal_hub
from src.rendering import get_texture_manager


class UVTileLibraryWidget(QWidget):
    """
    UV Tile library management widget.
    
    Features:
    - List of UV tiles with previews
    - Create new tiles from selection
- Apply tiles to body parts
    - Import/export tile libraries
    """
    
    tile_selected = Signal(object)  # Emits UVTile when selected
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Library
        self._library = UVTileLibrary()
        self._selected_tile: Optional[UVTile] = None
        self._selected_bodypart: Optional[BodyPart] = None
        
        # Signal hub
        self._signal_hub = get_signal_hub()
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Setup the UI layout."""
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("UV Tile Library")
        title_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(title_label)
        
        # Tile list
        self._tiles_list = QListWidget()
        self._tiles_list.setIconSize(QPixmap(64, 64).size())
        self._tiles_list.currentItemChanged.connect(self._on_selection_changed)
        layout.addWidget(self._tiles_list, stretch=1)
        
        # Buttons row 1
        buttons1_layout = QHBoxLayout()
        
        self._create_btn = QPushButton("Create from Selection")
        self._create_btn.setEnabled(False)
        self._create_btn.clicked.connect(self._on_create_tile)
        buttons1_layout.addWidget(self._create_btn)
        
        self._delete_btn = QPushButton("Delete")
        self._delete_btn.setEnabled(False)
        self._delete_btn.clicked.connect(self._on_delete_tile)
        buttons1_layout.addWidget(self._delete_btn)
        
        layout.addLayout(buttons1_layout)
        
        # Buttons row 2
        buttons2_layout = QHBoxLayout()
        
        self._apply_btn = QPushButton("Apply to Selected Part")
        self._apply_btn.setEnabled(False)
        self._apply_btn.clicked.connect(self._on_apply_tile)
        buttons2_layout.addWidget(self._apply_btn)
        
        layout.addLayout(buttons2_layout)
        
        # Import/Export
        buttons3_layout = QHBoxLayout()
        
        self._import_btn = QPushButton("Import...")
        self._import_btn.clicked.connect(self._on_import_library)
        buttons3_layout.addWidget(self._import_btn)
        
        self._export_btn = QPushButton("Export...")
        self._export_btn.clicked.connect(self._on_export_library)
        buttons3_layout.addWidget(self._export_btn)
        
        layout.addLayout(buttons3_layout)
    
    def _connect_signals(self):
        """Connect to signal hub."""
        self._signal_hub.bodypart_selected.connect(self._on_bodypart_selected)
        self._signal_hub.uv_tile_created.connect(self._on_tile_created_external)
    
    def _on_bodypart_selected(self, bodypart: Optional[BodyPart]):
        """Handle body part selection."""
        self._selected_bodypart = bodypart
        self._create_btn.setEnabled(bodypart is not None and bodypart.texture_path != "")
        self._update_apply_button()
    
    def _on_selection_changed(self, current: QListWidgetItem, previous: QListWidgetItem):
        """Handle tile selection change."""
        if current:
            self._selected_tile = current.data(Qt.UserRole)
            self._delete_btn.setEnabled(True)
            self.tile_selected.emit(self._selected_tile)
        else:
            self._selected_tile = None
            self._delete_btn.setEnabled(False)
        
        self._update_apply_button()
    
    def _update_apply_button(self):
        """Update apply button enabled state."""
        self._apply_btn.setEnabled(
            self._selected_tile is not None and 
            self._selected_bodypart is not None and
            self._selected_bodypart.texture_path == self._selected_tile.texture_path
        )
    
    def _on_create_tile(self):
        """Create a new UV tile from selected body part."""
        if not self._selected_bodypart:
            return
        
        # Ask for name
        name, ok = QInputDialog.getText(
            self,
            "Create UV Tile",
            "Enter tile name:",
            text=f"{self._selected_bodypart.name}_tile"
        )
        
        if not ok or not name:
            return
        
        # Create tile
        tile = UVTile(
            name=name,
            uv_rect=UVRect(
                x=self._selected_bodypart.uv_rect.x,
                y=self._selected_bodypart.uv_rect.y,
                width=self._selected_bodypart.uv_rect.width,
                height=self._selected_bodypart.uv_rect.height
            ),
            texture_path=self._selected_bodypart.texture_path
        )
        
        # Add to library
        self._library.add_tile(tile)
        
        # Add to list
        self._add_tile_to_list(tile)
        
        # Notify
        self._signal_hub.notify_uv_tile_created(tile)
    
    def _on_delete_tile(self):
        """Delete selected UV tile."""
        if not self._selected_tile:
            return
        
        reply = QMessageBox.question(
            self,
            "Delete UV Tile",
            f"Delete tile '{self._selected_tile.name}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Remove from library
            self._library.remove_tile(self._selected_tile.tile_id)
            
            # Remove from list
            current_row = self._tiles_list.currentRow()
            self._tiles_list.takeItem(current_row)
            
            self._selected_tile = None
    
    def _on_apply_tile(self):
        """Apply selected tile to selected body part."""
        if not self._selected_tile or not self._selected_bodypart:
            return
        
        # Check texture match
        if self._selected_bodypart.texture_path != self._selected_tile.texture_path:
            QMessageBox.warning(
                self,
                "Texture Mismatch",
                "The body part and tile use different textures."
            )
            return
        
        # Apply UV rect
        self._selected_bodypart.uv_rect.x = self._selected_tile.uv_rect.x
        self._selected_bodypart.uv_rect.y = self._selected_tile.uv_rect.y
        self._selected_bodypart.uv_rect.width = self._selected_tile.uv_rect.width
        self._selected_bodypart.uv_rect.height = self._selected_tile.uv_rect.height
        self._selected_bodypart.uv_tile_id = self._selected_tile.tile_id
        
        # Notify
        self._signal_hub.notify_uv_tile_applied(self._selected_tile, self._selected_bodypart)
        self._signal_hub.notify_bodypart_modified(self._selected_bodypart)
    
    def _add_tile_to_list(self, tile: UVTile):
        """Add a tile to the list widget."""
        item = QListWidgetItem(tile.name)
        item.setData(Qt.UserRole, tile)
        
        # Try to create preview icon
        if tile.texture_path:
            texture_manager = get_texture_manager()
            pixmap = texture_manager.get_texture(tile.texture_path)
            if pixmap:
                tex_size = texture_manager.get_texture_size(tile.texture_path)
                if tex_size:
                    # Extract UV region
                    px_x, px_y, px_w, px_h = tile.uv_rect.get_pixel_coords(tex_size[0], tex_size[1])
                    sub_pixmap = pixmap.copy(px_x, px_y, px_w, px_h)
                    # Scale to icon size
                    icon_pixmap = sub_pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    item.setIcon(QIcon(icon_pixmap))
        
        self._tiles_list.addItem(item)
    
    def _on_tile_created_external(self, tile: UVTile):
        """Handle tile created from outside this widget."""
        # Check if already in library
        if self._library.get_tile(tile.tile_id):
            return
        
        self._library.add_tile(tile)
        self._add_tile_to_list(tile)
    
    def _on_import_library(self):
        """Import UV tile library from JSON file."""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Import UV Tile Library",
            "",
            "JSON Files (*.json);;All Files (*.*)"
        )
        
        if not filename:
            return
        
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
                imported_lib = UVTileLibrary.from_dict(data)
                
                # Add all tiles
                for tile in imported_lib.tiles:
                    if not self._library.get_tile(tile.tile_id):
                        self._library.add_tile(tile)
                        self._add_tile_to_list(tile)
                
                QMessageBox.information(
                    self,
                    "Import Successful",
                    f"Imported {len(imported_lib.tiles)} tiles."
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Import Failed",
                f"Failed to import library:\n{str(e)}"
            )
    
    def _on_export_library(self):
        """Export UV tile library to JSON file."""
        if not self._library.tiles:
            QMessageBox.information(
                self,
                "Nothing to Export",
                "The UV tile library is empty."
            )
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export UV Tile Library",
            "uv_tiles.json",
            "JSON Files (*.json);;All Files (*.*)"
        )
        
        if not filename:
            return
        
        try:
            with open(filename, 'w') as f:
                json.dump(self._library.to_dict(), f, indent=2)
            
            QMessageBox.information(
                self,
                "Export Successful",
                f"Exported {len(self._library.tiles)} tiles to {filename}."
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Failed",
                f"Failed to export library:\n{str(e)}"
            )
    
    def get_library(self) -> UVTileLibrary:
        """Get the current UV tile library."""
        return self._library
    
    def set_library(self, library: UVTileLibrary):
        """Set the UV tile library."""
        self._library = library
        self._tiles_list.clear()
        
        for tile in library.tiles:
            self._add_tile_to_list(tile)

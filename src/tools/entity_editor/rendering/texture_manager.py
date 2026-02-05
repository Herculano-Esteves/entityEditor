"""
Texture Manager for Entity Editor.

Handles loading, caching, and managing textures for the editor.
"""


from pathlib import Path
from typing import Dict, Optional, Tuple
from PySide6.QtGui import QPixmap, QImage, QPainter, QColor
from PySide6.QtCore import QSize

from src.common.texture_registry import TextureRegistry

class TextureManager:
    """
    Manages texture loading and caching.
    
    Textures are loaded once and cached for reuse across the application.
    Now uses Texture ID for lookup via TextureRegistry.
    """
    
    def __init__(self):
        self._texture_cache: Dict[str, QPixmap] = {}
        self._texture_sizes: Dict[str, Tuple[int, int]] = {}
        self._registry: Optional[TextureRegistry] = None
        self._failed_ids = set()
        self._placeholder: Optional[QPixmap] = None
        
    def set_registry(self, registry: TextureRegistry):
        self._registry = registry
        
    def _create_placeholder(self) -> QPixmap:
        """Create a magenta/black checkerboard placeholder."""
        if self._placeholder:
            return self._placeholder
            
        size = 64
        image = QImage(size, size, QImage.Format_RGB32)
        image.fill(QColor(255, 0, 255)) # Magenta default
        
        # Draw checkerboard
        painter = QPainter(image)
        painter.fillRect(0, 0, size//2, size//2, QColor(0, 0, 0))
        painter.fillRect(size//2, size//2, size//2, size//2, QColor(0, 0, 0))
        painter.end()
        
        self._placeholder = QPixmap.fromImage(image)
        return self._placeholder

    def _resolve_path(self, texture_id: str) -> Optional[str]:
        if not self._registry:
            return None
        return self._registry._registry.get(texture_id)
    
    def load_texture(self, texture_id: str) -> Optional[QPixmap]:
        """
        Load a texture by ID. Returns placeholder if missing.
        """
        # Check cache
        if texture_id in self._texture_cache:
            return self._texture_cache[texture_id]
            
        # If we already failed this ID, return placeholder immediately (no spam)
        if texture_id in self._failed_ids:
            return self._create_placeholder()
        
        # Resolve Path
        path_str = self._resolve_path(texture_id)
        if not path_str:
            # ID not in registry
            if texture_id not in self._failed_ids:
                print(f"[TextureManager] ID not found in registry: {texture_id}")
                self._failed_ids.add(texture_id)
            return self._create_placeholder()

        # Resolve absolute path
        path = Path(path_str)
        if not path.exists():
            if self._registry and self._registry.project:
                 path = Path(self._registry.project.abs_assets_root) / path_str

        # Attempt Load
        if not path.exists() or not path.is_file():
            print(f"[TextureManager] File not found for ID '{texture_id}': {path}")
            self._failed_ids.add(texture_id)
            # Cache the placeholder so we don't try to reload this ID
            placeholder = self._create_placeholder()
            self._texture_cache[texture_id] = placeholder
            self._texture_sizes[texture_id] = (placeholder.width(), placeholder.height())
            return placeholder
        
        # Load image
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            print(f"[TextureManager] Failed to load image: {path}")
            self._failed_ids.add(texture_id)
            return self._create_placeholder()
        
        # Success - Cache
        self._texture_cache[texture_id] = pixmap
        self._texture_sizes[texture_id] = (pixmap.width(), pixmap.height())
        return pixmap
    
    def get_texture(self, texture_id: str) -> Optional[QPixmap]:
        return self.load_texture(texture_id)
    
    def get_texture_size(self, texture_id: str) -> Optional[Tuple[int, int]]:
        if texture_id in self._texture_sizes:
            return self._texture_sizes[texture_id]
        
        pixmap = self.load_texture(texture_id)
        if pixmap:
            return self._texture_sizes[texture_id]
        return None
    
    def clear_cache(self):
        self._texture_cache.clear()
        self._texture_sizes.clear()
    
    def remove_texture(self, texture_id: str):
        if texture_id in self._texture_cache:
            del self._texture_cache[texture_id]
        if texture_id in self._texture_sizes:
            del self._texture_sizes[texture_id]
    
    def is_cached(self, texture_id: str) -> bool:
        return texture_id in self._texture_cache


# Global texture manager instance
_texture_manager_instance: Optional[TextureManager] = None


def get_texture_manager() -> TextureManager:
    global _texture_manager_instance
    if _texture_manager_instance is None:
        _texture_manager_instance = TextureManager()
    return _texture_manager_instance

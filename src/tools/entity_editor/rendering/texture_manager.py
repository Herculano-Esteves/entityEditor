"""
Texture Manager for Entity Editor.

Handles loading, caching, and managing textures for the editor.
"""

from pathlib import Path
from typing import Dict, Optional, Tuple
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import QSize


class TextureManager:
    """
    Manages texture loading and caching.
    
    Textures are loaded once and cached for reuse across the application.
    """
    
    def __init__(self):
        self._texture_cache: Dict[str, QPixmap] = {}
        self._texture_sizes: Dict[str, Tuple[int, int]] = {}
    
    def load_texture(self, filepath: str) -> Optional[QPixmap]:
        """
        Load a texture from file.
        
        Args:
            filepath: Path to the texture file (PNG)
            
        Returns:
            QPixmap if successful, None if failed
        """
        # Check cache first
        if filepath in self._texture_cache:
            return self._texture_cache[filepath]
        
        # Validate file exists
        path = Path(filepath)
        if not path.exists() or not path.is_file():
            print(f"Texture file not found: {filepath}")
            return None
        
        # Load image
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            print(f"Failed to load texture: {filepath}")
            return None
        
        # Cache and return
        self._texture_cache[filepath] = pixmap
        self._texture_sizes[filepath] = (pixmap.width(), pixmap.height())
        return pixmap
    
    def get_texture(self, filepath: str) -> Optional[QPixmap]:
        """
        Get a cached texture or load if not cached.
        
        Args:
            filepath: Path to the texture file
            
        Returns:
            QPixmap if available, None otherwise
        """
        return self.load_texture(filepath)
    
    def get_texture_size(self, filepath: str) -> Optional[Tuple[int, int]]:
        """
        Get the size of a texture.
        
        Args:
            filepath: Path to the texture file
            
        Returns:
            (width, height) tuple if texture is loaded, None otherwise
        """
        if filepath in self._texture_sizes:
            return self._texture_sizes[filepath]
        
        # Try to load it
        pixmap = self.load_texture(filepath)
        if pixmap:
            return self._texture_sizes[filepath]
        return None
    
    def clear_cache(self):
        """Clear all cached textures."""
        self._texture_cache.clear()
        self._texture_sizes.clear()
    
    def remove_texture(self, filepath: str):
        """Remove a specific texture from cache."""
        if filepath in self._texture_cache:
            del self._texture_cache[filepath]
        if filepath in self._texture_sizes:
            del self._texture_sizes[filepath]
    
    def is_cached(self, filepath: str) -> bool:
        """Check if a texture is currently cached."""
        return filepath in self._texture_cache


# Global texture manager instance
_texture_manager_instance: Optional[TextureManager] = None


def get_texture_manager() -> TextureManager:
    """
    Get the global texture manager instance.
    Creates one if it doesn't exist.
    """
    global _texture_manager_instance
    if _texture_manager_instance is None:
        _texture_manager_instance = TextureManager()
    return _texture_manager_instance

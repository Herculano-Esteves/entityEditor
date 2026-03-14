"""
TextureManager for Entity Editor.

Loads, caches, and serves QPixmap instances by texture ID.
Textures are resolved through the TextureRegistry — no hardcoded paths here.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

from PySide6.QtGui import QPixmap, QImage, QPainter, QColor
from PySide6.QtCore import QSize

from src.common.texture_registry import TextureRegistry

logger = logging.getLogger(__name__)


class TextureManager:
    """
    Caches QPixmap objects keyed by texture ID.

    Call :meth:`set_registry` once after construction before any texture
    is requested.  The registry is the sole source of truth for ID → path
    mapping; nothing is hardcoded here.
    """

    def __init__(self) -> None:
        self._texture_cache: Dict[str, QPixmap] = {}
        self._texture_sizes: Dict[str, Tuple[int, int]] = {}
        self._registry: Optional[TextureRegistry] = None
        self._failed_ids: set[str] = set()
        self._placeholder: Optional[QPixmap] = None

    def set_registry(self, registry: TextureRegistry) -> None:
        """Attach the TextureRegistry used for ID → path resolution."""
        self._registry = registry
        # Clear cache whenever the registry changes
        self.clear_cache()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_texture(self, texture_id: str) -> Optional[QPixmap]:
        """Return the QPixmap for *texture_id*, or a placeholder if unavailable."""
        return self._load(texture_id)

    def get_texture_size(self, texture_id: str) -> Optional[Tuple[int, int]]:
        """Return ``(width, height)`` for *texture_id*, loading it if needed."""
        if texture_id not in self._texture_sizes:
            self._load(texture_id)
        return self._texture_sizes.get(texture_id)

    def is_cached(self, texture_id: str) -> bool:
        """``True`` when *texture_id* is already in the pixel cache."""
        return texture_id in self._texture_cache

    def clear_cache(self) -> None:
        """Evict all cached textures and reset the failed-ID set."""
        self._texture_cache.clear()
        self._texture_sizes.clear()
        self._failed_ids.clear()

    def remove_from_cache(self, texture_id: str) -> None:
        """Evict a single texture ID from the cache."""
        self._texture_cache.pop(texture_id, None)
        self._texture_sizes.pop(texture_id, None)
        self._failed_ids.discard(texture_id)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load(self, texture_id: str) -> Optional[QPixmap]:
        """Load and cache a texture, returning placeholder on any failure."""
        if texture_id in self._texture_cache:
            return self._texture_cache[texture_id]

        if texture_id in self._failed_ids:
            return self._placeholder_pixmap()

        if self._registry is None:
            logger.warning(
                "TextureManager: no registry set — cannot resolve '%s'", texture_id
            )
            return self._placeholder_pixmap()

        # Resolve through the public registry API
        abs_path = self._registry.resolve_path(texture_id)

        if abs_path is None:
            logger.warning(
                "TextureManager: texture ID '%s' not found in registry", texture_id
            )
            self._failed_ids.add(texture_id)
            return self._placeholder_pixmap()

        path = Path(abs_path)
        if not path.exists() or not path.is_file():
            logger.warning(
                "TextureManager: file not found for ID '%s': %s", texture_id, path
            )
            self._failed_ids.add(texture_id)
            placeholder = self._placeholder_pixmap()
            self._texture_cache[texture_id] = placeholder
            self._texture_sizes[texture_id] = (placeholder.width(), placeholder.height())
            return placeholder

        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            logger.error(
                "TextureManager: Qt failed to load image for '%s': %s", texture_id, path
            )
            self._failed_ids.add(texture_id)
            return self._placeholder_pixmap()

        self._texture_cache[texture_id] = pixmap
        self._texture_sizes[texture_id] = (pixmap.width(), pixmap.height())
        logger.debug("TextureManager: loaded '%s' from %s", texture_id, path)
        return pixmap

    def _placeholder_pixmap(self) -> QPixmap:
        """Return (and lazily create) the magenta/black checkerboard placeholder."""
        if self._placeholder:
            return self._placeholder

        size = 64
        image = QImage(size, size, QImage.Format_RGB32)
        image.fill(QColor(255, 0, 255))  # magenta

        painter = QPainter(image)
        painter.fillRect(0, 0, size // 2, size // 2, QColor(0, 0, 0))
        painter.fillRect(size // 2, size // 2, size // 2, size // 2, QColor(0, 0, 0))
        painter.end()

        self._placeholder = QPixmap.fromImage(image)
        return self._placeholder


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

_texture_manager_instance: Optional[TextureManager] = None


def get_texture_manager() -> TextureManager:
    """Return the global TextureManager instance, creating it on first call."""
    global _texture_manager_instance
    if _texture_manager_instance is None:
        _texture_manager_instance = TextureManager()
    return _texture_manager_instance

"""
TextureRegistry — maps texture IDs to relative file paths.

Format
------
The registry is a JSON file whose structure is a plain ordered dict::

    {
        "ERROR": "textures/error.png",
        "HERO":  "textures/hero.png"
    }

Keys are uppercase texture IDs used everywhere in entity definitions.
Values are paths relative to the project's *assets root* folder.

Design rules
------------
- Only two built-in IDs exist in the editor itself: ERROR and EMPTY.
  Every other entry is project-specific and comes from the registry file.
- The registry does NOT auto-create or auto-save on first run.
  If the file is absent :attr:`is_empty` is ``True`` and the caller
  (the Launcher) is responsible for directing the user to create one.
- The registry NEVER writes game-specific hardcoded entries to disk.
"""

from __future__ import annotations

import json
import logging
import os
import struct
from typing import Optional

logger = logging.getLogger(__name__)

# The only two entries that the editor itself always needs.
# These are rendered as a checker-board placeholder in the viewport
# when textures are missing.
_BUILTIN_IDS = {
    "ERROR": "textures/error.png",
    "EMPTY": "textures/empty.png",
}

# Image file extensions recognised as textures.
SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(
    {".png", ".jpg", ".jpeg", ".bmp", ".tga", ".gif", ".webp"}
)


class TextureRegistry:
    """
    Ordered map of texture ID → relative path (relative to assets root).

    Construct via :meth:`TextureRegistry.from_project` rather than directly
    so that path resolution is always consistent.
    """

    def __init__(self, project=None):
        """
        Args:
            project (GameProject | None): Loaded project.  When ``None`` the
                registry is empty and read-only (no file I/O will be done).
        """
        self._project = project
        self._registry: dict[str, str] = {}   # {ID: relative_path}
        self._keys_order: list[str] = []       # insertion order
        self.is_dirty: bool = False

        if project is not None:
            bin_abs = project.abs_registry_path
            self._bin_path: Optional[str] = bin_abs
            self._json_path: Optional[str] = os.path.splitext(bin_abs)[0] + ".json"
            self._load()
        else:
            self._bin_path = None
            self._json_path = None
            logger.warning(
                "TextureRegistry created without a project — no file I/O will be done."
            )

    # ------------------------------------------------------------------
    # Public read API
    # ------------------------------------------------------------------

    @property
    def is_empty(self) -> bool:
        """``True`` when the registry has no user-defined entries."""
        return len(self._registry) == 0

    @property
    def has_file(self) -> bool:
        """``True`` when the registry JSON file exists on disk."""
        return self._json_path is not None and os.path.exists(self._json_path)

    def get_path(self, texture_id: str) -> Optional[str]:
        """
        Return the relative path for *texture_id*, or ``None`` if not found.

        The returned path is relative to the project assets root.
        Use :meth:`resolve_path` to get an absolute path.
        """
        return self._registry.get(texture_id)

    def resolve_path(self, texture_id: str) -> Optional[str]:
        """
        Return the absolute path for *texture_id*, or ``None`` if not found.

        Resolves the relative path against the project's assets root.
        """
        rel = self.get_path(texture_id)
        if rel is None:
            return None
        if self._project is None:
            return rel
        return str(os.path.join(self._project.abs_assets_root, rel))

    def get_all(self) -> list[tuple[str, str]]:
        """Return all entries as ``[(id, relative_path), ...]`` in order."""
        return [(k, self._registry[k]) for k in self._keys_order]

    def get_all_ids(self) -> list[str]:
        """Return all texture IDs in insertion order."""
        return list(self._keys_order)

    # ------------------------------------------------------------------
    # Public write API  (mutations set is_dirty = True)
    # ------------------------------------------------------------------

    def add_texture(self, texture_id: str, relative_path: str) -> None:
        """Add or update a texture entry."""
        if texture_id not in self._registry:
            self._keys_order.append(texture_id)
        self._registry[texture_id] = relative_path
        self.is_dirty = True

    def remove_texture(self, texture_id: str) -> None:
        """Remove a texture entry."""
        if texture_id in self._registry:
            del self._registry[texture_id]
            self._keys_order = [k for k in self._keys_order if k != texture_id]
            self.is_dirty = True

    def move_up(self, texture_id: str) -> None:
        """Move an entry one position earlier in the list."""
        if texture_id not in self._keys_order:
            return
        idx = self._keys_order.index(texture_id)
        if idx > 0:
            self._keys_order[idx], self._keys_order[idx - 1] = (
                self._keys_order[idx - 1],
                self._keys_order[idx],
            )
            self.is_dirty = True

    def move_down(self, texture_id: str) -> None:
        """Move an entry one position later in the list."""
        if texture_id not in self._keys_order:
            return
        idx = self._keys_order.index(texture_id)
        if idx < len(self._keys_order) - 1:
            self._keys_order[idx], self._keys_order[idx + 1] = (
                self._keys_order[idx + 1],
                self._keys_order[idx],
            )
            self.is_dirty = True

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def sync_from_folder(self, textures_abs_path: str) -> tuple[int, int]:
        """
        Scan *textures_abs_path* for image files and add any that are not
        already in the registry.

        Rules
        -----
        - The texture ID is the file stem in UPPERCASE
          (e.g. ``hero.png`` → ``"HERO"``).  Sub-folder files use only the
          stem, not the whole relative path, so two files with the same name
          in different sub-folders would collide — the first one wins.
        - Existing entries are **never** overwritten, so manual path overrides
          survive a sync.
        - Paths stored in the registry are relative to the *assets root*, not
          to the textures folder.

        Args:
            textures_abs_path: Absolute path of the folder to scan.

        Returns:
            ``(added, skipped)`` — how many entries were added and how many
            were already present.
        """
        if not os.path.isdir(textures_abs_path):
            logger.warning(
                "sync_from_folder: directory does not exist: %s", textures_abs_path
            )
            return 0, 0

        assets_root = (
            self._project.abs_assets_root if self._project else textures_abs_path
        )

        added = 0
        skipped = 0

        for dirpath, _dirs, filenames in os.walk(textures_abs_path):
            for filename in sorted(filenames):  # sorted for deterministic order
                ext = os.path.splitext(filename)[1].lower()
                if ext not in SUPPORTED_EXTENSIONS:
                    continue

                texture_id = os.path.splitext(filename)[0].upper()
                abs_file = os.path.join(dirpath, filename)

                # Store path relative to assets root, using forward slashes
                try:
                    rel_path = os.path.relpath(abs_file, assets_root).replace("\\", "/")
                except ValueError:
                    # Can happen on Windows when drives differ
                    rel_path = abs_file.replace("\\", "/")

                if texture_id in self._registry:
                    skipped += 1
                    logger.debug(
                        "sync_from_folder: skipped '%s' (already registered)", texture_id
                    )
                else:
                    self._keys_order.append(texture_id)
                    self._registry[texture_id] = rel_path
                    added += 1
                    logger.debug(
                        "sync_from_folder: added '%s' → '%s'", texture_id, rel_path
                    )

        if added > 0:
            self.save()
            logger.info(
                "sync_from_folder: added %d entries, skipped %d existing.",
                added,
                skipped,
            )
        else:
            logger.info(
                "sync_from_folder: nothing new found (skipped %d existing).", skipped
            )

        return added, skipped

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self) -> bool:
        """
        Save to JSON and export the binary registry.

        Returns ``True`` on success, ``False`` on failure.
        Does nothing (returns ``False``) if no project is set.
        """
        if self._json_path is None:
            logger.warning("Cannot save TextureRegistry — no project configured.")
            return False
        try:
            self._save_json()
            self._export_binary()
            self.is_dirty = False
            logger.info("Saved texture registry: %s", self._json_path)
            return True
        except Exception as e:
            logger.error("Failed to save texture registry: %s", e)
            return False

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load from the JSON file.  Does NOT auto-create or auto-save."""
        if not os.path.exists(self._json_path):
            # Registry file does not exist yet — stay empty.
            # The Launcher / Texture Manager will guide the user.
            logger.info(
                "Texture registry file not found: %s — registry is empty.",
                self._json_path,
            )
            return

        try:
            with open(self._json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("Expected a JSON object at the top level.")
            self._registry = data
            self._keys_order = list(data.keys())
            logger.info(
                "Loaded texture registry with %d entries from: %s",
                len(self._registry),
                self._json_path,
            )
        except Exception as e:
            logger.error("Failed to load texture registry %s: %s", self._json_path, e)
            # Leave registry empty — don't populate with hardcoded entries.

    def _save_json(self) -> None:
        os.makedirs(os.path.dirname(self._json_path), exist_ok=True)
        ordered = {k: self._registry[k] for k in self._keys_order}
        with open(self._json_path, "w", encoding="utf-8") as f:
            json.dump(ordered, f, indent=4, ensure_ascii=False)

    def _export_binary(self) -> None:
        os.makedirs(os.path.dirname(self._bin_path), exist_ok=True)
        buffer = bytearray()
        buffer.extend(struct.pack("<I", len(self._registry)))

        def _write_str(buf: bytearray, text: str) -> None:
            encoded = text.encode("utf-8")
            buf.extend(struct.pack("<I", len(encoded)))
            buf.extend(encoded)

        for key in self._keys_order:
            _write_str(buffer, key)
            _write_str(buffer, self._registry[key])

        with open(self._bin_path, "wb") as f:
            f.write(buffer)

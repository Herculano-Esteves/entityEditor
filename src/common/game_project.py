"""
GameProject — Single API for all project file operations.

The project file is a plain JSON file (conventionally named *.gameproj.json
or *.gameproj — the extension is flexible, the content is always JSON).

Layout convention
-----------------
A project defines one root assets folder. Everything else is expressed as a
path relative to that root, so the structure is always:

    <project-root>/
        game_project.json      ← this file
        assets/
            textures/          ← texture images
            entities/          ← entity definition files (.entdef)
            entities/blocks/   ← sub-category example
            fonts/             ← font files
            registry/          ← binary registries (texture_registry.bin …)

You can override any of these sub-paths inside the JSON if your project
has a different layout — the defaults above are used when a key is absent.

Usage
-----
    project = GameProject.load("path/to/game_project.json")
    if project is None:
        # file not found or JSON invalid — caller decides how to handle it

    project.abs_entities_path   # → absolute path to entities folder
    project.resolve("textures/hero.png")  # → absolute path under assets root

    GameProject.save(project, "path/to/game_project.json")
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default sub-paths (relative to the assets root folder)
# ---------------------------------------------------------------------------
_DEFAULTS = {
    "assets_root": "assets",
    "textures_path": "assets/textures",
    "entities_path": "assets/entities",
    "parts_path": "assets/parts",
    "fonts_path": "assets/fonts",
    "registry_path": "assets/registry/texture_registry.bin",
}


@dataclass
class GameProject:
    """
    Represents a loaded game project.

    All paths stored inside the dataclass are *relative to the project root
    directory* (the folder that contains the project JSON file).
    Use the `abs_*` properties to get fully resolved absolute paths.

    Prefer constructing instances via `GameProject.load()` and
    persisting them via `GameProject.save()` rather than touching the
    fields directly.
    """

    # Path to the JSON file itself (set by load/save, not stored inside JSON)
    project_file: Optional[str] = field(default=None, repr=True)

    # Human-readable name for the project
    name: str = "Untitled Project"

    # Root folder for all game assets (relative to project root directory)
    assets_root: str = _DEFAULTS["assets_root"]

    # Sub-paths for specific asset categories (relative to project root dir)
    textures_path: str = _DEFAULTS["textures_path"]
    entities_path: str = _DEFAULTS["entities_path"]
    parts_path: str = _DEFAULTS["parts_path"]
    fonts_path: str = _DEFAULTS["fonts_path"]
    registry_path: str = _DEFAULTS["registry_path"]

    # ---------------------------------------------------------------------------
    # Derived read-only properties
    # ---------------------------------------------------------------------------

    @property
    def root_dir(self) -> str:
        """
        Absolute path of the folder that contains the project file.
        Falls back to the current working directory if no file is set.
        """
        if self.project_file:
            return os.path.dirname(os.path.abspath(self.project_file))
        return os.getcwd()

    def resolve(self, relative_path: str) -> str:
        """
        Resolve *any* path relative to the project root directory to an
        absolute path.

        Example::

            project.resolve("assets/textures/hero.png")
            # → "C:/myproject/assets/textures/hero.png"
        """
        return os.path.abspath(os.path.join(self.root_dir, relative_path))

    def resolve_path(self, relative_path: str) -> str:
        """Alias for :meth:`resolve` — kept for backwards compatibility."""
        return self.resolve(relative_path)

    @property
    def abs_assets_root(self) -> str:
        """Absolute path to the top-level assets folder."""
        return self.resolve(self.assets_root)

    @property
    def abs_textures_path(self) -> str:
        """Absolute path to the textures sub-folder."""
        return self.resolve(self.textures_path)

    @property
    def abs_entities_path(self) -> str:
        """Absolute path to the entities sub-folder."""
        return self.resolve(self.entities_path)

    @property
    def abs_parts_path(self) -> str:
        """Absolute path to the parts sub-folder."""
        return self.resolve(self.parts_path)

    @property
    def abs_fonts_path(self) -> str:
        """Absolute path to the fonts sub-folder."""
        return self.resolve(self.fonts_path)

    @property
    def abs_registry_path(self) -> str:
        """Absolute path to the texture registry file."""
        return self.resolve(self.registry_path)

    @property
    def has_registry(self) -> bool:
        """
        ``True`` when the texture registry JSON file exists on disk.

        The Launcher uses this to decide whether to allow opening the Entity
        Editor.  If ``False``, the user should be directed to the Texture
        Manager to create the registry first.
        """
        json_path = os.path.splitext(self.abs_registry_path)[0] + ".json"
        return os.path.isfile(json_path)

    @property
    def has_textures(self) -> bool:
        """
        ``True`` when at least one supported image file exists inside the
        configured textures folder.

        Used together with :attr:`has_registry` to give the user a specific
        explanation when the registry is missing:

        - ``has_textures is False`` → "Add images to the textures folder first."
        - ``has_registry is False`` → "Open Texture Manager to build the registry."
        """
        from src.common.texture_registry import SUPPORTED_EXTENSIONS  # avoid circular at module level
        tex_dir = self.abs_textures_path
        if not os.path.isdir(tex_dir):
            return False
        for _root, _dirs, files in os.walk(tex_dir):
            for f in files:
                if os.path.splitext(f)[1].lower() in SUPPORTED_EXTENSIONS:
                    return True
        return False

    def ensure_registry(self) -> bool:
        """
        Ensure the texture registry JSON file exists on disk.

        Behaviour
        ---------
        - **Registry already exists** → return ``True``, do nothing.
        - **Registry missing + textures present** → scan the textures folder with
          :meth:`~src.common.texture_registry.TextureRegistry.sync_from_folder`
          and save a populated registry.  Return ``False``.
        - **Registry missing + no textures** → create an empty ``{}`` registry so
          the rest of the application can always rely on the file existing.
          Return ``False``.

        Returns:
            ``True``  — the file already existed (nothing written).
            ``False`` — the file was created or populated now.
        """
        import json as _json
        import logging as _logging
        _log = _logging.getLogger(__name__)

        json_path = os.path.splitext(self.abs_registry_path)[0] + ".json"
        if os.path.isfile(json_path):
            return True  # already there, nothing to do

        # Need to create the registry directory regardless of path taken below.
        try:
            os.makedirs(os.path.dirname(json_path), exist_ok=True)
        except Exception as e:
            _log.error("Failed to create registry directory: %s", e)
            return False

        if self.has_textures:
            # Textures exist — build a proper populated registry by scanning.
            from src.common.texture_registry import TextureRegistry
            reg = TextureRegistry(self)
            added, _ = reg.sync_from_folder(self.abs_textures_path)
            _log.info(
                "Auto-built texture registry with %d entries at: %s", added, json_path
            )
        else:
            # No textures yet — create an empty placeholder so the app never
            # deals with a missing file.
            try:
                with open(json_path, "w", encoding="utf-8") as f:
                    _json.dump({}, f, indent=4)
                _log.info("Created empty texture registry at: %s", json_path)
            except Exception as e:
                _log.error("Failed to create empty texture registry at %s: %s", json_path, e)
                return False

        return False

    # ---------------------------------------------------------------------------
    # Serialisation helpers
    # ---------------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Return a plain dict suitable for JSON serialisation."""
        return {
            "name": self.name,
            "assets_root": self.assets_root,
            "textures_path": self.textures_path,
            "entities_path": self.entities_path,
            "parts_path": self.parts_path,
            "fonts_path": self.fonts_path,
            "registry_path": self.registry_path,
        }

    @classmethod
    def from_dict(cls, data: dict, project_file: Optional[str] = None) -> "GameProject":
        """Create a GameProject from a plain dict (as produced by `to_dict`)."""
        return cls(
            project_file=project_file,
            name=data.get("name", "Untitled Project"),
            assets_root=data.get("assets_root", _DEFAULTS["assets_root"]),
            textures_path=data.get("textures_path", _DEFAULTS["textures_path"]),
            entities_path=data.get("entities_path", _DEFAULTS["entities_path"]),
            parts_path=data.get("parts_path", _DEFAULTS["parts_path"]),
            fonts_path=data.get("fonts_path", _DEFAULTS["fonts_path"]),
            registry_path=data.get("registry_path", _DEFAULTS["registry_path"]),
        )

    # ---------------------------------------------------------------------------
    # File I/O  (the ONLY correct way to load/save a project)
    # ---------------------------------------------------------------------------

    @classmethod
    def load(cls, filepath: str) -> Optional["GameProject"]:
        """
        Load a project from a JSON file.

        Returns the project on success, or ``None`` if the file cannot be
        read or parsed — the caller is responsible for showing an error.
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            project = cls.from_dict(data, project_file=os.path.abspath(filepath))
            logger.info("Loaded project '%s' from: %s", project.name, filepath)
            return project
        except FileNotFoundError:
            logger.error("Project file not found: %s", filepath)
            return None
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON in project file %s: %s", filepath, e)
            return None
        except Exception as e:
            logger.error("Unexpected error loading project %s: %s", filepath, e)
            return None

    @classmethod
    def save(cls, project: "GameProject", filepath: str) -> bool:
        """
        Save a project to a JSON file.

        Updates ``project.project_file`` to the given path on success.
        Returns ``True`` on success, ``False`` on failure.
        """
        try:
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(project.to_dict(), f, indent=4, ensure_ascii=False)
            project.project_file = os.path.abspath(filepath)
            logger.info("Saved project '%s' to: %s", project.name, filepath)
            return True
        except Exception as e:
            logger.error("Failed to save project to %s: %s", filepath, e)
            return False

    @classmethod
    def create_default(cls, project_root: str, name: str = "My Game") -> "GameProject":
        """
        Create a new project with default paths rooted at *project_root*.

        Does NOT create any folders or write any files — call
        `GameProject.save()` and `project.ensure_folders()` separately.
        """
        project_file = os.path.join(project_root, "game_project.json")
        return cls(
            project_file=os.path.abspath(project_file),
            name=name,
        )

    # ---------------------------------------------------------------------------
    # Utility: ensure the asset folder structure exists on disk
    # ---------------------------------------------------------------------------

    def ensure_folders(self) -> None:
        """
        Create all configured asset directories if they do not exist yet.
        Safe to call multiple times (uses exist_ok=True).
        """
        directories = [
            self.abs_assets_root,
            self.abs_textures_path,
            self.abs_entities_path,
            self.abs_parts_path,
            self.abs_fonts_path,
            os.path.dirname(self.abs_registry_path),  # registry/ folder
        ]
        for path in directories:
            os.makedirs(path, exist_ok=True)
            logger.debug("Ensured directory exists: %s", path)

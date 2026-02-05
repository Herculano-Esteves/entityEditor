
import os
from typing import Optional, Dict, Set
from pathlib import Path
from src.tools.entity_editor.data.entity_data import Entity
from src.tools.entity_editor.data.file_io import EntityDeserializer
from src.common.game_project import GameProject

from src.tools.entity_editor.core import get_signal_hub

class EntityManager:
    """
    Manages loading, caching, and resolving Referenced Entities.
    Ensures that composed entities (Entity Ref parts) are loaded efficiently.
    Checks for circular dependencies.
    """
    
    def __init__(self):
        self._project: Optional[GameProject] = None
        self._cache: Dict[str, Entity] = {} # Map[filepath, Entity]
        self._name_to_path: Dict[str, str] = {} # Map[entity_name_or_filename, filepath]
        
        # Connect to signals for Cache Invalidation
        get_signal_hub().entity_saved.connect(self._on_entity_saved)
        
    def set_project(self, project: GameProject):
        """Set the active project and clear cache."""
        self._project = project
        self.clear_cache()
        if project:
            self._scan_available_entities()
            
    def clear_cache(self):
        """Clear all cached entities."""
        self._cache.clear()
        self._name_to_path.clear()
        
    def _scan_available_entities(self):
        """
        Scan entities_path and parts_path to build a map of available entities.
        This allows lookup by filename (e.g. 'Head' -> 'assets/parts/body/Head.entdef')
        """
        if not self._project: return
        
        search_paths = [
            self._project.abs_entities_path,
            self._project.abs_parts_path
        ]
        
        for search_dir in search_paths:
            if not os.path.exists(search_dir): continue
            
            for root, dirs, files in os.walk(search_dir):
                for f in files:
                    if f.endswith('.entdef'):
                        full_path = str(Path(root) / f)
                        name = f.replace('.entdef', '')
                        self._name_to_path[name] = full_path
                        self._name_to_path[f] = full_path
                        
    def _on_entity_saved(self, filepath: str):
        """
        Callback when ANY entity is saved. 
        If it was cached, invalidate it.
        Also trigger a global redraw because this saved entity might be a part of the currently loaded entity.
        """
        # Normalize path separators for comparison
        fs_path = str(Path(filepath).resolve())
        
        # Check if in cache (need to normalize cache keys too potentially, but let's try direct first)
        keys_to_remove = []
        for cached_path in self._cache:
            if str(Path(cached_path).resolve()) == fs_path:
                keys_to_remove.append(cached_path)
                
        for k in keys_to_remove:
            print(f"[EntityManager] Invalidating cache for: {k}")
            del self._cache[k]
            # Notify that this specific entity definition was updated
            get_signal_hub().notify_referenced_entity_saved(k)
            
        # If we invalidated something, we should likely force a re-render of the current view
        # just in case the current entity (or its children) was referencing the saved entity.
        if keys_to_remove:
             # Force update via signal hub
             get_signal_hub().notify_entity_modified()
                        
    def get_entity_def(self, ref_name: str) -> Optional[Entity]:
        """
        Get an Entity definition by its reference name (filename or name).
        Returns None if not found.
        """
        if not self._project: return None
        if not ref_name: return None
        
        # 1. Resolve Path
        filepath = self._name_to_path.get(ref_name)
        if not filepath:
            # Try re-scanning if not found (maybe new file created)
            self._scan_available_entities()
            filepath = self._name_to_path.get(ref_name)
            
        if not filepath:
            print(f"[EntityManager] Could not resolve entity reference: {ref_name}")
            return None
            
        # 2. Check Cache
        if filepath in self._cache:
            return self._cache[filepath]
            
        # 3. Load
        try:
            entity = EntityDeserializer.load(filepath)
            if entity:
                self._cache[filepath] = entity
                return entity
        except Exception as e:
            print(f"[EntityManager] Failed to load referenced entity {filepath}: {e}")
            
        return None
        
    def get_all_dependencies(self, entity_name: str, visited: Set[str] = None) -> Set[str]:
        """
        Recursively get all entity names resulting from the dependency tree of `entity_name`.
        Returns a set of names that `entity_name` depends on (directly or indirectly).
        """
        if visited is None:
            visited = set()
            
        repo_entity = self.get_entity_def(entity_name)
        if not repo_entity:
            return set()
            
        deps = set()
        
        # Check direct dependencies
        for bp in repo_entity.body_parts:
            if bp.part_type.name == 'ENTITY_REF' and bp.entity_ref:  # Check name or value depending on enum impl
                # Just check if truthy and is ref
                 ref_name = bp.entity_ref
                 if ref_name and ref_name not in visited:
                     deps.add(ref_name)
                     visited.add(ref_name)
                     # Recurse
                     sub_deps = self.get_all_dependencies(ref_name, visited)
                     deps.update(sub_deps)
                     
        return deps

    def get_available_entity_names(self) -> list[str]:
        """Return a list of all available entity references (filenames without extension)."""
        # Filter keys to only show "Name" not "Name.entdef" to avoid duplicates in UI
        return sorted([k for k in self._name_to_path.keys() if not k.endswith('.entdef')])


# Global singleton instance
_instance = None

def get_entity_manager() -> EntityManager:
    global _instance
    if _instance is None:
        _instance = EntityManager()
    return _instance

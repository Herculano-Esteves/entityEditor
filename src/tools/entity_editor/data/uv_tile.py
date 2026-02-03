"""
UV Tile data model for Entity Editor.

UV tiles are reusable, named UV rectangle definitions that can be referenced
by multiple body parts. This is particularly useful for sprite sheets and animations.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
import uuid
from .entity_data import UVRect


@dataclass
class UVTile:
    """
    Named UV preset that can be referenced by multiple body parts.
    
    Use cases:
    - Sprite sheet frames (e.g., "walk_frame_0", "walk_frame_1")
    - Common UI elements
    - Animation frames
    - Reusable texture regions
    """
    tile_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "UVTile"
    uv_rect: UVRect = field(default_factory=UVRect)
    texture_path: str = ""  # Source texture for this tile
    
    # Metadata
    tags: List[str] = field(default_factory=list)  # For organization (e.g., "animation", "idle")
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "tile_id": self.tile_id,
            "name": self.name,
            "uv_rect": self.uv_rect.to_dict(),
            "texture_path": self.texture_path,
            "tags": self.tags,
            "description": self.description
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UVTile':
        """Create from dictionary."""
        return cls(
            tile_id=data.get("tile_id", str(uuid.uuid4())),
            name=data.get("name", "UVTile"),
            uv_rect=UVRect.from_dict(data.get("uv_rect", {})),
            texture_path=data.get("texture_path", ""),
            tags=data.get("tags", []),
            description=data.get("description", "")
        )


@dataclass  
class UVTileLibrary:
    """
    Collection of UV tiles.
    Can be saved/loaded as a separate file for reuse across entities.
    """
    tiles: List[UVTile] = field(default_factory=list)
    name: str = "UV Tile Library"
    
    def add_tile(self, tile: UVTile) -> None:
        """Add a tile to the library."""
        self.tiles.append(tile)
    
    def remove_tile(self, tile_id: str) -> bool:
        """Remove a tile by ID. Returns True if successful."""
        for i, tile in enumerate(self.tiles):
            if tile.tile_id == tile_id:
                self.tiles.pop(i)
                return True
        return False
    
    def get_tile(self, tile_id: str) -> Optional[UVTile]:
        """Get a tile by ID."""
        for tile in self.tiles:
            if tile.tile_id == tile_id:
                return tile
        return None
    
    def get_tile_by_name(self, name: str) -> Optional[UVTile]:
        """Get a tile by name (returns first match)."""
        for tile in self.tiles:
            if tile.name == name:
                return tile
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "tiles": [tile.to_dict() for tile in self.tiles]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UVTileLibrary':
        """Create from dictionary."""
        return cls(
            name=data.get("name", "UV Tile Library"),
            tiles=[UVTile.from_dict(t) for t in data.get("tiles", [])]
        )

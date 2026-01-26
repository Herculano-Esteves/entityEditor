"""
Core data models for the Entity Editor.

This module defines the fundamental data structures used throughout the editor:
- Vec2: 2D vector for positions and sizes
- UVRect: UV rectangle with normalized coordinates
- Hitbox: Rectangular collision/interaction area
- BodyPart: Visual component with texture and UV mapping
- Entity: Complete entity definition with body parts
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from enum import Enum
import uuid


@dataclass
class Vec2:
    """2D vector for positions and sizes."""
    x: float = 0.0
    y: float = 0.0
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for serialization."""
        return {"x": self.x, "y": self.y}
    
    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> 'Vec2':
        """Create from dictionary."""
        return cls(x=data.get("x", 0.0), y=data.get("y", 0.0))
    
    def __add__(self, other):
        """Vector addition."""
        if isinstance(other, Vec2):
            return Vec2(self.x + other.x, self.y + other.y)
        return NotImplemented

    def __sub__(self, other):
        """Vector subtraction."""
        if isinstance(other, Vec2):
            return Vec2(self.x - other.x, self.y - other.y)
        return NotImplemented

    def __iter__(self):
        """Allow tuple unpacking."""
        yield self.x
        yield self.y


@dataclass
class UVRect:
    """
    UV rectangle with normalized coordinates (0.0 to 1.0).
    Represents a rectangular region within a texture.
    """
    x: float = 0.0      # Left edge (normalized)
    y: float = 0.0      # Top edge (normalized)
    width: float = 1.0  # Width (normalized)
    height: float = 1.0 # Height (normalized)
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for serialization."""
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> 'UVRect':
        """Create from dictionary."""
        return cls(
            x=data.get("x", 0.0),
            y=data.get("y", 0.0),
            width=data.get("width", 1.0),
            height=data.get("height", 1.0)
        )
    
    def get_pixel_coords(self, texture_width: int, texture_height: int) -> tuple:
        """
        Convert normalized UV coordinates to pixel coordinates.
        Returns (px_x, px_y, px_width, px_height).
        """
        return (
            int(self.x * texture_width),
            int(self.y * texture_height),
            int(self.width * texture_width),
            int(self.height * texture_height)
        )


@dataclass
class Hitbox:
    """
    Hitbox with integer pixel precision.
    
    For pixel-based 2D games, all positions and sizes must be exact integers.
    No floats, no sub-pixel positioning.
    
    Attributes:
        name: Identifier for this hitbox
        x: X position in pixels (integer) relative to parent
        y: Y position in pixels (integer) relative to parent
        width: Width in pixels (integer)
        height: Height in pixels (integer)
        hitbox_type: Type of hitbox ("collision", "damage", "trigger")
        enabled: Whether this hitbox is active/visible
    """
    name: str = "Hitbox"
    x: int = 0           # Position X in pixels (integer only)
    y: int = 0           # Position Y in pixels (integer only)
    width: int = 32      # Width in pixels (integer only)
    height: int = 32     # Height in pixels (integer only)
    hitbox_type: str = "collision"  # "collision", "damage", "trigger"
    enabled: bool = True
    
    def __post_init__(self):
        """Enforce integer types after initialization."""
        self.x = int(self.x)
        self.y = int(self.y)
        self.width = int(self.width)
        self.height = int(self.height)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization (ensures integers)."""
        return {
            "name": self.name,
            "x": int(self.x),
            "y": int(self.y),
            "width": int(self.width),
            "height": int(self.height),
            "hitbox_type": self.hitbox_type,
            "enabled": self.enabled
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Hitbox':
        """Create from dictionary (with migration from old Vec2 format)."""
        # Try new integer format first
        if "x" in data and "y" in data:
            return cls(
                name=data.get("name", "Hitbox"),
                x=int(data.get("x", 0)),
                y=int(data.get("y", 0)),
                width=int(data.get("width", 32)),
                height=int(data.get("height", 32)),
                hitbox_type=data.get("hitbox_type", "collision"),
                enabled=data.get("enabled", True)
            )
        # Migrate from old Vec2 format
        else:
            position = data.get("position", {})
            size = data.get("size", {"x": 32.0, "y": 32.0})
            return cls(
                name=data.get("name", "Hitbox"),
                x=int(position.get("x", 0)),
                y=int(position.get("y", 0)),
                width=int(size.get("x", 32)),
                height=int(size.get("y", 32)),
                hitbox_type=data.get("hitbox_type", "collision"),
                enabled=data.get("enabled", True)
            )


@dataclass
class BodyPart:
    """
    Individual body part of an entity.
    Contains visual representation (texture + UV) and associated hitboxes.
    """
    name: str = "BodyPart"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    position: Vec2 = field(default_factory=Vec2)
    size: Vec2 = field(default_factory=lambda: Vec2(64.0, 64.0))
    texture_path: str = ""  # Relative or absolute path to texture file
    uv_rect: UVRect = field(default_factory=UVRect)
    
    # UV flipping (for mirroring sprites)
    flip_x: bool = False  # Flip texture horizontally
    flip_y: bool = False  # Flip texture vertically
    
    hitboxes: List[Hitbox] = field(default_factory=list)
    
    # UV tile reference (optional)
    uv_tile_id: Optional[str] = None  # Reference to a UVTile for easy reuse
    
    # Pixel scale multiplier (for scaling sprites)
    pixel_scale: int = 1  # 1 = 1:1, 2 = 2x2 per pixel, etc.
    
    # Visual properties
    rotation: float = 0.0  # Rotation in degrees
    z_order: int = 0       # Draw order (higher = drawn on top)
    visible: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "id": self.id,
            "position": self.position.to_dict(),
            "size": self.size.to_dict(),
            "texture_path": self.texture_path,
            "uv_rect": self.uv_rect.to_dict(),
            "flip_x": self.flip_x,
            "flip_y": self.flip_y,
            "hitboxes": [hb.to_dict() for hb in self.hitboxes],
            "uv_tile_id": self.uv_tile_id,
            "pixel_scale": self.pixel_scale,
            "rotation": self.rotation,
            "z_order": self.z_order,
            "visible": self.visible
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BodyPart':
        """Create from dictionary."""
        return cls(
            name=data.get("name", "BodyPart"),
            id=data.get("id", str(uuid.uuid4())),
            position=Vec2.from_dict(data.get("position", {})),
            size=Vec2.from_dict(data.get("size", {"x": 64.0, "y": 64.0})),
            texture_path=data.get("texture_path", ""),
            uv_rect=UVRect.from_dict(data.get("uv_rect", {})),
            flip_x=data.get("flip_x", False),
            flip_y=data.get("flip_y", False),
            hitboxes=[Hitbox.from_dict(hb) for hb in data.get("hitboxes", [])],
            uv_tile_id=data.get("uv_tile_id"),
            pixel_scale=data.get("pixel_scale", 1),
            rotation=data.get("rotation", 0.0),
            z_order=data.get("z_order", 0),
            visible=data.get("visible", True)
        )


@dataclass
class Entity:
    """
    Top-level entity definition.
    Contains metadata, body parts, and optional entity-level hitboxes.
    """
    name: str = "NewEntity"
    entity_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    pivot: Vec2 = field(default_factory=Vec2)  # Entity center/pivot point
    body_parts: List[BodyPart] = field(default_factory=list)
    entity_hitboxes: List[Hitbox] = field(default_factory=list)  # Entity-level hitboxes
    
    # Metadata
    version: str = "1.0"
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)  # Extensible metadata
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "entity_id": self.entity_id,
            "pivot": self.pivot.to_dict(),
            "body_parts": [bp.to_dict() for bp in self.body_parts],
            "entity_hitboxes": [hb.to_dict() for hb in self.entity_hitboxes],
            "version": self.version,
            "tags": self.tags,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Entity':
        """Create from dictionary."""
        return cls(
            name=data.get("name", "NewEntity"),
            entity_id=data.get("entity_id", str(uuid.uuid4())),
            pivot=Vec2.from_dict(data.get("pivot", {})),
            body_parts=[BodyPart.from_dict(bp) for bp in data.get("body_parts", [])],
            entity_hitboxes=[Hitbox.from_dict(hb) for hb in data.get("entity_hitboxes", [])],
            version=data.get("version", "1.0"),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {})
        )
    
    def get_body_part(self, name: str) -> Optional[BodyPart]:
        """Get body part by name."""
        for bp in self.body_parts:
            if bp.name == name:
                return bp
        return None
    
    def add_body_part(self, body_part: BodyPart) -> None:
        """Add a body part to the entity."""
        self.body_parts.append(body_part)
    
    def remove_body_part(self, body_part: BodyPart) -> bool:
        """Remove a body part from the entity. Returns True if successful."""
        if body_part in self.body_parts:
            self.body_parts.remove(body_part)
            return True
        return False
    
    def get_sorted_body_parts(self) -> List[BodyPart]:
        """Get body parts sorted by z_order (for rendering)."""
        return sorted(self.body_parts, key=lambda bp: bp.z_order)

"""Data module for Entity Editor."""
from .entity_data import Entity, BodyPart, Hitbox, Vec2, UVRect, HitboxShape, BodyPartType
from .file_io import EntitySerializer, EntityDeserializer, validate_file
from .uv_tile import UVTile, UVTileLibrary

__all__ = [
    'Entity',
    'BodyPart',
    'Hitbox',
    'Vec2',
    'UVRect',
    'HitboxShape',
    'BodyPartType',
    'EntitySerializer',
    'EntityDeserializer',
    'validate_file',
    'UVTile',
    'UVTileLibrary'
]

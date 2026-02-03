"""
File I/O system for Entity Editor.

Handles serialization and deserialization of Entity data to/from binary .entdef format.
The format uses a simple binary structure with:
- Magic number for validation
- Version header for compatibility
- JSON payload (for flexibility and debugging)
"""

import struct
import json
from pathlib import Path
from typing import Optional
from .entity_data import Entity


# File format constants
MAGIC_NUMBER = b'ENTD'  # Entity Definition magic number
FILE_VERSION = 1


class EntitySerializer:
    """Serializes Entity objects to binary .entdef format."""
    
    @staticmethod
    def save(entity: Entity, filepath: str) -> None:
        """
        Save an entity to a .entdef file.
        
        Args:
            entity: Entity object to save
            filepath: Path to save the file
            
        Raises:
            IOError: If file cannot be written
        """
        # Convert entity to JSON
        entity_dict = entity.to_dict()
        json_str = json.dumps(entity_dict, indent=2)
        json_bytes = json_str.encode('utf-8')
        
        # Write binary format:
        # [MAGIC (4 bytes)][VERSION (4 bytes)][JSON_LENGTH (4 bytes)][JSON_DATA]
        with open(filepath, 'wb') as f:
            # Write magic number
            f.write(MAGIC_NUMBER)
            
            # Write version
            f.write(struct.pack('<I', FILE_VERSION))
            
            # Write JSON length and data
            f.write(struct.pack('<I', len(json_bytes)))
            f.write(json_bytes)
    
    @staticmethod
    def save_json_debug(entity: Entity, filepath: str) -> None:
        """
        Save entity as readable JSON for debugging purposes.
        
        Args:
            entity: Entity object to save
            filepath: Path to save the file (typically .json extension)
        """
        entity_dict = entity.to_dict()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(entity_dict, f, indent=2)


class EntityDeserializer:
    """Deserializes Entity objects from binary .entdef format."""
    
    @staticmethod
    def load(filepath: str) -> Optional[Entity]:
        """
        Load an entity from a .entdef file.
        
        Args:
            filepath: Path to the .entdef file
            
        Returns:
            Entity object if successful, None on error
            
        Raises:
            IOError: If file cannot be read
            ValueError: If file format is invalid
        """
        with open(filepath, 'rb') as f:
            # Read and validate magic number
            magic = f.read(4)
            if magic != MAGIC_NUMBER:
                raise ValueError(f"Invalid file format: magic number mismatch (got {magic}, expected {MAGIC_NUMBER})")
            
            # Read version
            version_bytes = f.read(4)
            if len(version_bytes) < 4:
                raise ValueError("Invalid file format: truncated version header")
            version = struct.unpack('<I', version_bytes)[0]
            
            # Check version compatibility
            if version > FILE_VERSION:
                raise ValueError(f"File version {version} is newer than supported version {FILE_VERSION}")
            
            # Read JSON length
            length_bytes = f.read(4)
            if len(length_bytes) < 4:
                raise ValueError("Invalid file format: truncated length header")
            json_length = struct.unpack('<I', length_bytes)[0]
            
            # Read JSON data
            json_bytes = f.read(json_length)
            if len(json_bytes) < json_length:
                raise ValueError("Invalid file format: truncated JSON data")
            
            # Parse JSON and create Entity
            json_str = json_bytes.decode('utf-8')
            entity_dict = json.loads(json_str)
            return Entity.from_dict(entity_dict)
    
    @staticmethod
    def load_json_debug(filepath: str) -> Optional[Entity]:
        """
        Load entity from readable JSON format (for debugging).
        
        Args:
            filepath: Path to the .json file
            
        Returns:
            Entity object if successful, None on error
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            entity_dict = json.load(f)
            return Entity.from_dict(entity_dict)


def validate_file(filepath: str) -> bool:
    """
    Validate that a file is a valid .entdef file.
    
    Args:
        filepath: Path to check
        
    Returns:
        True if valid, False otherwise
    """
    try:
        path = Path(filepath)
        if not path.exists() or not path.is_file():
            return False
        
        with open(filepath, 'rb') as f:
            magic = f.read(4)
            return magic == MAGIC_NUMBER
    except Exception:
        return False

"""
Generate example entities and test resources for the Entity Editor.

This script creates sample entities with textures for testing purposes.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.data import Entity, BodyPart, Hitbox, Vec2, UVRect, EntitySerializer
from PIL import Image, ImageDraw


def create_test_texture(filepath: str, width: int, height: int, color: tuple):
    """Create a simple test texture."""
    # Create colored rectangle with border
    img = Image.new('RGBA', (width, height), color)
    draw = ImageDraw.Draw(img)
    
    # Draw border
    draw.rectangle([0, 0, width-1, height-1], outline=(0, 0, 0, 255), width=2)
    
    # Draw diagonal lines
    draw.line([0, 0, width, height], fill=(0, 0, 0, 128), width=1)
    draw.line([0, height, width, 0], fill=(0, 0, 0, 128), width=1)
    
    # Save
    img.save(filepath)
    print(f"Created texture: {filepath}")


def create_character_entity():
    """Create a simple character entity for testing."""
    entity = Entity(
        name="TestCharacter",
        pivot=Vec2(64, 100)  # Center bottom
    )
    
    # Create textures directory
    textures_dir = Path("examples/textures")
    textures_dir.mkdir(parents=True, exist_ok=True)
    
    # Head
    head_texture = str(textures_dir / "head.png")
    create_test_texture(head_texture, 64, 64, (255, 200, 150, 255))
    
    head = BodyPart(
        name="Head",
        position=Vec2(32, 0),
        size=Vec2(64, 64),
        texture_path=head_texture,
        z_order=2
    )
    head.hitboxes.append(Hitbox(
        name="HeadCollision",
        position=Vec2(8, 8),
        size=Vec2(48, 48),
        hitbox_type="collision"
    ))
    entity.add_body_part(head)
    
    # Torso
    torso_texture = str(textures_dir / "torso.png")
    create_test_texture(torso_texture, 96, 96, (100, 150, 255, 255))
    
    torso = BodyPart(
        name="Torso",
        position=Vec2(16, 64),
        size=Vec2(96, 96),
        texture_path=torso_texture,
        z_order=1
    )
    torso.hitboxes.append(Hitbox(
        name="TorsoCollision",
        position=Vec2(12, 12),
        size=Vec2(72, 72),
        hitbox_type="collision"
    ))
    entity.add_body_part(torso)
    
    # Left Arm
    arm_texture = str(textures_dir / "arm.png")
    create_test_texture(arm_texture, 64, 80, (200, 100, 100, 255))
    
    left_arm = BodyPart(
        name="LeftArm",
        position=Vec2(-16, 64),
        size=Vec2(32, 80),
        texture_path=arm_texture,
        z_order=0
    )
    entity.add_body_part(left_arm)
    
    # Right Arm
    right_arm = BodyPart(
        name="RightArm",
        position=Vec2(112, 64),
        size=Vec2(32, 80),
        texture_path=arm_texture,
        z_order=0
    )
    entity.add_body_part(right_arm)
    
    # Save entity
    entities_dir = Path("examples/entities")
    entities_dir.mkdir(parents=True, exist_ok=True)
    
    entity_path = str(entities_dir / "test_character.entdef")
    EntitySerializer.save(entity, entity_path)
    print(f"Created entity: {entity_path}")
    
    return entity


def create_simple_entity():
    """Create a very simple entity for basic testing."""
    entity = Entity(
        name="SimpleEntity",
        pivot=Vec2(50, 50)
    )
    
    # Create textures directory
    textures_dir = Path("examples/textures")
    textures_dir.mkdir(parents=True, exist_ok=True)
    
    # Single body part
    box_texture = str(textures_dir / "box.png")
    create_test_texture(box_texture, 100, 100, (150, 255, 150, 255))
    
    box = BodyPart(
        name="Box",
        position=Vec2(0, 0),
        size=Vec2(100, 100),
        texture_path=box_texture,
        z_order=0
    )
    box.hitboxes.append(Hitbox(
        name="BoxCollision",
        position=Vec2(10, 10),
        size=Vec2(80, 80),
        hitbox_type="collision"
    ))
    entity.add_body_part(box)
    
    # Save entity
    entities_dir = Path("examples/entities")
    entities_dir.mkdir(parents=True, exist_ok=True)
    
    entity_path = str(entities_dir / "simple.entdef")
    EntitySerializer.save(entity, entity_path)
    print(f"Created entity: {entity_path}")
    
    return entity


def main():
    """Generate all example entities."""
    print("Generating example entities and textures...")
    
    create_simple_entity()
    create_character_entity()
    
    print("\nDone! Example entities created in examples/ directory.")
    print("You can now open them in the Entity Editor:")
    print("  - examples/entities/simple.entdef")
    print("  - examples/entities/test_character.entdef")


if __name__ == "__main__":
    main()

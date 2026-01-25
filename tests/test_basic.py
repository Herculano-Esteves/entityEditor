"""
Basic tests for Entity Editor.

Run with: python -m pytest tests/
"""

import pytest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data import Entity, BodyPart, Hitbox, Vec2
from src.core import HistoryManager, EntitySnapshotCommand, AddBodyPartCommand


def test_entity_creation():
    """Test creating a basic entity."""
    entity = Entity(name="TestEntity")
    assert entity.name == "TestEntity"
    assert len(entity.body_parts) == 0


def test_add_bodypart():
    """Test adding a body part to an entity."""
    entity = Entity(name="TestEntity")
    bp = BodyPart(name="TestPart", position=Vec2(10, 20), size=Vec2(64, 64))
    
    entity.add_body_part(bp)
    assert len(entity.body_parts) == 1
    assert entity.body_parts[0] == bp


def test_remove_bodypart():
    """Test removing a body part from an entity."""
    entity = Entity(name="TestEntity")
    bp = BodyPart(name="TestPart", position=Vec2(10, 20), size=Vec2(64, 64))
    
    entity.add_body_part(bp)
    entity.remove_body_part(bp)
    assert len(entity.body_parts) == 0


def test_add_hitbox_to_bodypart():
    """Test adding a hitbox to a body part."""
    bp = BodyPart(name="TestPart", position=Vec2(10, 20), size=Vec2(64, 64))
    hb = Hitbox(name="TestHitbox", x=0, y=0, width=32, height=32)
    bp.hitboxes.append(hb)
    
    assert len(bp.hitboxes) == 1
    assert bp.hitboxes[0] == hb
    assert hb.name == "TestHitbox"
    assert hb.x == 0
    assert hb.y == 0
    assert hb.width == 32
    assert hb.height == 32


def test_history_manager_undo_redo():
    """Test undo/redo functionality."""
    entity = Entity(name="TestEntity")
    history = HistoryManager(entity, signal_hub=None)
    
    # Add a body part via command
    bp = BodyPart(name="TestPart", position=Vec2(10, 20), size=Vec2(64, 64))
    cmd = AddBodyPartCommand(bp)
    history.execute(cmd)
    
    assert len(entity.body_parts) == 1
    
    # Undo
    history.undo()
    assert len(entity.body_parts) == 0
    
    # Redo
    history.redo()
    assert len(entity.body_parts) == 1


def test_snapshot_command():
    """Test snapshot-based undo/redo."""
    entity = Entity(name="TestEntity")
    bp = BodyPart(name="TestPart", position=Vec2(10, 20), size=Vec2(64, 64))
    entity.add_body_part(bp)
    
    # Create snapshot before modification
    snapshot = EntitySnapshotCommand(entity, "Test Change")
    
    # Modify entity
    bp.position.x = 100
    
    # Finalize snapshot
    snapshot.finalize(entity)
    
    # Undo
    snapshot.undo(entity, None)
    assert entity.body_parts[0].position.x == 10
    
    # Redo
    snapshot.execute(entity, None)
    assert entity.body_parts[0].position.x == 100


def test_history_max_size():
    """Test that history respects max size limit."""
    entity = Entity(name="TestEntity")
    history = HistoryManager(entity, signal_hub=None, max_size=5)
    
    # Add 10 body parts
    for i in range(10):
        bp = BodyPart(name=f"Part{i}", position=Vec2(i, i), size=Vec2(64, 64))
        cmd = AddBodyPartCommand(bp)
        history.execute(cmd)
    
    # Only last 5 should be in history
    assert history.get_history_size() <= 5


def test_hitbox_enabled_toggle():
    """Test hitbox enabled/disabled state."""
    hb = Hitbox(name="TestHitbox", x=0, y=0, width=32, height=32)
    
    assert hb.enabled == True  # Default is enabled
    hb.enabled = False
    assert hb.enabled == False


def test_bodypart_visibility_toggle():
    """Test body part visibility toggle."""
    bp = BodyPart(name="TestPart", position=Vec2(10, 20), size=Vec2(64, 64))
    
    assert bp.visible == True  # Default
    bp.visible = False
    assert bp.visible == False


if __name__ == "__main__":
    # Run tests when executed directly
    pytest.main([__file__, "-v"])

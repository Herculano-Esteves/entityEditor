"""
Tests for the Entity Editor.

Run with:  pytest tests/ -v
"""

import copy
import json
import os
import tempfile
import pytest

# ---------------------------------------------------------------------------
# Core data model tests
# ---------------------------------------------------------------------------

from src.tools.entity_editor.data.entity_data import (
    Entity, BodyPart, Hitbox, Vec2, UVRect, BodyPartType, HitboxShape,
)
from src.tools.entity_editor.data.file_io import EntitySerializer, EntityDeserializer
from src.tools.entity_editor.core.naming_utils import generate_unique_name
from src.tools.entity_editor.core.geometry_utils import calculate_entity_bounds
from src.common.game_project import GameProject
from src.common.texture_registry import TextureRegistry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def simple_entity() -> Entity:
    entity = Entity(name="TestEntity")
    bp = BodyPart(
        name="Part1",
        position=Vec2(0, 0),
        size=Vec2(64, 64),
        pivot=Vec2(32, 32),
    )
    entity.add_body_part(bp)
    return entity


@pytest.fixture
def empty_entity() -> Entity:
    return Entity(name="EmptyEntity")


@pytest.fixture
def tmp_entdef(tmp_path, simple_entity):
    """Save a simple entity to a temp file and return the path."""
    path = str(tmp_path / "test.entdef")
    EntitySerializer.save(simple_entity, path)
    return path


@pytest.fixture
def tmp_gameproj(tmp_path) -> str:
    """Write a minimal valid JSON project file and return its path."""
    data = {
        "name": "TestProject",
        "assets_root": "assets",
        "textures_path": "assets/textures",
        "entities_path": "assets/entities",
        "fonts_path": "assets/fonts",
        "registry_path": "assets/registry/texture_registry.bin",
    }
    proj_file = tmp_path / "game_project.json"
    proj_file.write_text(json.dumps(data, indent=4), encoding="utf-8")
    return str(proj_file)


# ---------------------------------------------------------------------------
# Entity CRUD
# ---------------------------------------------------------------------------

def test_create_entity():
    entity = Entity(name="MyEntity")
    assert entity.name == "MyEntity"
    assert entity.body_parts == []
    assert entity.entity_hitboxes == []


def test_add_body_part(simple_entity):
    assert len(simple_entity.body_parts) == 1
    assert simple_entity.body_parts[0].name == "Part1"


def test_remove_body_part(simple_entity):
    bp = simple_entity.body_parts[0]
    simple_entity.remove_body_part(bp)
    assert len(simple_entity.body_parts) == 0


def test_body_part_type_is_unique():
    """Ensure BodyPartType has no duplicate class definition — only one canonical version."""
    assert BodyPartType.SIMPLE == 0
    assert BodyPartType.ENTITY_REF == 1
    # Verify it works in a boolean context like IntEnum
    assert int(BodyPartType.SIMPLE) == 0


# ---------------------------------------------------------------------------
# Hitbox management
# ---------------------------------------------------------------------------

# NOTE: BodyPart has NO add_hitbox() / remove_hitbox() methods.
# Hitboxes are stored as a plain list: bp.hitboxes.
# Use bp.hitboxes.append(hb) and bp.hitboxes.remove(hb) directly.

def test_bodypart_has_no_add_hitbox_method(simple_entity):
    """Regression: confirm BodyPart exposes .hitboxes list, not add_hitbox()."""
    bp = simple_entity.body_parts[0]
    assert hasattr(bp, "hitboxes"), "BodyPart must have a .hitboxes list"
    assert not hasattr(bp, "add_hitbox"), "BodyPart must NOT have add_hitbox() – use bp.hitboxes.append()"
    assert not hasattr(bp, "remove_hitbox"), "BodyPart must NOT have remove_hitbox() – use bp.hitboxes.remove()"


def test_add_hitbox(simple_entity):
    bp = simple_entity.body_parts[0]
    hb = Hitbox(name="HitboxA", x=0, y=0, width=32, height=32)
    bp.hitboxes.append(hb)
    assert len(bp.hitboxes) == 1
    assert bp.hitboxes[0].name == "HitboxA"


def test_remove_hitbox(simple_entity):
    bp = simple_entity.body_parts[0]
    hb = Hitbox(name="HitboxB", x=0, y=0, width=32, height=32)
    bp.hitboxes.append(hb)
    bp.hitboxes.remove(hb)
    assert len(bp.hitboxes) == 0


def test_hitbox_default_values():
    """Hitbox defaults match what the Add button creates."""
    hb = Hitbox("Hitbox_0", 0, 0, 32, 32)
    assert hb.x == 0
    assert hb.y == 0
    assert hb.width == 32
    assert hb.height == 32
    assert hb.hitbox_type == "collision"
    assert hb.enabled is True
    assert hb.shape == HitboxShape.RECTANGLE


def test_add_multiple_hitboxes(simple_entity):
    """Adding multiple hitboxes with auto-generated names matches the Add button logic."""
    bp = simple_entity.body_parts[0]
    for i in range(3):
        count = len(bp.hitboxes)  # Same as hitbox_panel._on_add_hitbox
        hb = Hitbox(f"Hitbox_{count}", 0, 0, 32, 32)
        bp.hitboxes.append(hb)
    assert len(bp.hitboxes) == 3
    assert bp.hitboxes[0].name == "Hitbox_0"
    assert bp.hitboxes[1].name == "Hitbox_1"
    assert bp.hitboxes[2].name == "Hitbox_2"


def test_duplicate_hitbox(simple_entity):
    """Duplicating a hitbox keeps data and generates a unique name."""
    bp = simple_entity.body_parts[0]
    original = Hitbox("Attack", 5, 10, 20, 20)
    bp.hitboxes.append(original)

    # Simulate the duplicate logic from hitbox_panel._on_duplicate_hitbox
    new_hb = copy.deepcopy(original)
    existing_names = {h.name for h in bp.hitboxes}
    new_hb.name = generate_unique_name(original.name, existing_names)
    try:
        insert_index = bp.hitboxes.index(original) + 1
        bp.hitboxes.insert(insert_index, new_hb)
    except ValueError:
        bp.hitboxes.append(new_hb)

    assert len(bp.hitboxes) == 2
    assert bp.hitboxes[0].name == "Attack"
    assert bp.hitboxes[1].name == "Attack1"
    # Data is copied correctly
    assert bp.hitboxes[1].x == original.x
    assert bp.hitboxes[1].width == original.width


def test_hitbox_shapes():
    hb_rect = Hitbox(name="R", x=0, y=0, width=10, height=10, shape=HitboxShape.RECTANGLE)
    hb_circ = Hitbox(name="C", x=0, y=0, width=20, height=20, radius=10, shape=HitboxShape.CIRCLE)
    assert hb_rect.shape == HitboxShape.RECTANGLE
    assert hb_circ.shape == HitboxShape.CIRCLE


# ---------------------------------------------------------------------------
# Visibility / enabled toggling
# ---------------------------------------------------------------------------

def test_toggle_body_part_visibility(simple_entity):
    bp = simple_entity.body_parts[0]
    assert bp.visible is True
    bp.visible = False
    assert bp.visible is False


def test_toggle_hitbox_enabled(simple_entity):
    bp = simple_entity.body_parts[0]
    hb = Hitbox(name="H", x=0, y=0, width=10, height=10)
    bp.hitboxes.append(hb)
    assert hb.enabled is True
    hb.enabled = False
    assert hb.enabled is False


# ---------------------------------------------------------------------------
# Serialization round-trip
# ---------------------------------------------------------------------------

def test_serialization_round_trip(simple_entity, tmp_path):
    path = str(tmp_path / "roundtrip.entdef")
    EntitySerializer.save(simple_entity, path)
    loaded = EntityDeserializer.load(path)

    assert loaded is not None
    assert loaded.name == simple_entity.name
    assert len(loaded.body_parts) == len(simple_entity.body_parts)
    assert loaded.body_parts[0].name == simple_entity.body_parts[0].name
    assert loaded.body_parts[0].size.x == simple_entity.body_parts[0].size.x
    assert loaded.body_parts[0].size.y == simple_entity.body_parts[0].size.y


def test_serialization_with_hitboxes(simple_entity, tmp_path):
    bp = simple_entity.body_parts[0]
    bp.hitboxes.append(Hitbox("ColBox", 5, 5, 54, 54))

    path = str(tmp_path / "hitboxes.entdef")
    EntitySerializer.save(simple_entity, path)
    loaded = EntityDeserializer.load(path)

    assert len(loaded.body_parts[0].hitboxes) == 1
    assert loaded.body_parts[0].hitboxes[0].name == "ColBox"
    assert loaded.body_parts[0].hitboxes[0].x == 5
    assert loaded.body_parts[0].hitboxes[0].width == 54


def test_load_nonexistent_file():
    """EntityDeserializer.load raises FileNotFoundError for missing files."""
    with pytest.raises(FileNotFoundError):
        EntityDeserializer.load("/nonexistent/path/entity.entdef")


def test_json_debug_round_trip(simple_entity, tmp_path):
    path = str(tmp_path / "debug.json")
    EntitySerializer.save_json_debug(simple_entity, path)
    assert os.path.exists(path)
    with open(path, "r") as f:
        data = json.load(f)
    assert data["name"] == simple_entity.name


# ---------------------------------------------------------------------------
# generate_unique_name
# ---------------------------------------------------------------------------

def test_unique_name_no_conflict():
    assert generate_unique_name("Part", set()) == "Part"


def test_unique_name_with_conflict():
    result = generate_unique_name("Part", {"Part"})
    assert result == "Part1"


def test_unique_name_increments_existing_number():
    result = generate_unique_name("Part1", {"Part1", "Part2"})
    assert result == "Part3"


def test_unique_name_high_existing_number():
    result = generate_unique_name("Part10", {"Part10", "Part11"})
    assert result == "Part12"


def test_unique_name_no_suffix():
    result = generate_unique_name("BodyPart", {"BodyPart", "BodyPart1", "BodyPart2"})
    assert result == "BodyPart3"


# ---------------------------------------------------------------------------
# calculate_entity_bounds
# ---------------------------------------------------------------------------

def test_bounds_empty_entity(empty_entity):
    min_x, min_y, w, h = calculate_entity_bounds(empty_entity)
    assert (min_x, min_y, w, h) == (0.0, 0.0, 64.0, 64.0)


def test_bounds_single_part():
    entity = Entity(name="E")
    entity.add_body_part(BodyPart("P", position=Vec2(10, 20), size=Vec2(32, 48)))
    min_x, min_y, w, h = calculate_entity_bounds(entity)
    assert min_x == 10.0
    assert min_y == 20.0
    assert w == 32.0
    assert h == 48.0


def test_bounds_multiple_parts():
    entity = Entity(name="E")
    entity.add_body_part(BodyPart("P1", position=Vec2(0, 0), size=Vec2(64, 64)))
    entity.add_body_part(BodyPart("P2", position=Vec2(64, 64), size=Vec2(64, 64)))
    min_x, min_y, w, h = calculate_entity_bounds(entity)
    assert min_x == 0.0
    assert min_y == 0.0
    assert w == 128.0
    assert h == 128.0


def test_bounds_hidden_parts_excluded():
    entity = Entity(name="E")
    visible = BodyPart("Vis", position=Vec2(0, 0), size=Vec2(32, 32))
    hidden = BodyPart("Hid", position=Vec2(100, 100), size=Vec2(64, 64))
    hidden.visible = False
    entity.add_body_part(visible)
    entity.add_body_part(hidden)
    min_x, min_y, w, h = calculate_entity_bounds(entity)
    # Only the visible part should contribute
    assert min_x == 0.0
    assert min_y == 0.0
    assert w == 32.0
    assert h == 32.0


# ---------------------------------------------------------------------------
# GameProject
# ---------------------------------------------------------------------------

def test_game_project_load(tmp_gameproj):
    """load() returns a populated GameProject from a valid JSON file."""
    gp = GameProject.load(tmp_gameproj)
    assert gp is not None
    assert gp.name == "TestProject"
    assert gp.assets_root == "assets"
    assert gp.project_file == os.path.abspath(tmp_gameproj)


def test_game_project_defaults(tmp_gameproj):
    """abs_assets_root resolves relative to the project file directory."""
    gp = GameProject.load(tmp_gameproj)
    root = os.path.dirname(os.path.abspath(tmp_gameproj))
    assert gp.abs_assets_root == os.path.abspath(os.path.join(root, "assets"))


def test_game_project_no_double_assets(tmp_gameproj):
    """Regression: abs_registry_path must NOT contain assets/assets."""
    gp = GameProject.load(tmp_gameproj)
    registry_path = gp.abs_registry_path.replace("\\", "/")
    asset_occurrences = registry_path.split("/").count("assets")
    assert asset_occurrences <= 1, f"Double 'assets' in: {registry_path}"


def test_game_project_entities_path(tmp_gameproj):
    gp = GameProject.load(tmp_gameproj)
    root = os.path.dirname(os.path.abspath(tmp_gameproj))
    expected = os.path.abspath(os.path.join(root, "assets", "entities"))
    assert gp.abs_entities_path == expected


def test_game_project_textures_path(tmp_gameproj):
    gp = GameProject.load(tmp_gameproj)
    root = os.path.dirname(os.path.abspath(tmp_gameproj))
    expected = os.path.abspath(os.path.join(root, "assets", "textures"))
    assert gp.abs_textures_path == expected


def test_game_project_missing_file():
    """load() returns None for a nonexistent file — does not raise."""
    result = GameProject.load("/nonexistent/does_not_exist.json")
    assert result is None


def test_game_project_malformed_json(tmp_path):
    """load() returns None for a file with invalid JSON — does not raise."""
    bad = tmp_path / "bad.json"
    bad.write_text("this is not valid json { broken", encoding="utf-8")
    result = GameProject.load(str(bad))
    assert result is None


def test_game_project_save_and_reload(tmp_path):
    """save() writes JSON that load() can read back, preserving all fields."""
    project = GameProject(
        name="SaveTest",
        assets_root="assets",
        textures_path="assets/textures",
        entities_path="assets/entities",
        fonts_path="assets/fonts",
        registry_path="assets/registry/texture_registry.bin",
    )
    filepath = str(tmp_path / "save_test.json")
    success = GameProject.save(project, filepath)
    assert success is True
    assert os.path.exists(filepath)

    reloaded = GameProject.load(filepath)
    assert reloaded is not None
    assert reloaded.name == "SaveTest"
    assert reloaded.entities_path == "assets/entities"
    assert reloaded.textures_path == "assets/textures"


def test_game_project_ensure_folders(tmp_path):
    """ensure_folders() creates all configured directories."""
    proj_file = str(tmp_path / "game_project.json")
    project = GameProject.create_default(str(tmp_path), name="FolderTest")
    GameProject.save(project, proj_file)

    project.ensure_folders()

    assert os.path.isdir(project.abs_assets_root)
    assert os.path.isdir(project.abs_textures_path)
    assert os.path.isdir(project.abs_entities_path)
    assert os.path.isdir(project.abs_fonts_path)
    assert os.path.isdir(os.path.dirname(project.abs_registry_path))


def test_game_project_create_default(tmp_path):
    """create_default() sets project_file to <root>/game_project.json."""
    project = GameProject.create_default(str(tmp_path), name="MyGame")
    assert project.name == "MyGame"
    assert project.project_file == os.path.abspath(
        os.path.join(str(tmp_path), "game_project.json")
    )
    # All default paths are relative to assets root
    assert project.assets_root == "assets"
    assert project.entities_path == "assets/entities"
    assert project.parts_path == "assets/parts"
    assert project.textures_path == "assets/textures"


def test_game_project_abs_parts_path(tmp_gameproj):
    """abs_parts_path resolves correctly — regression for missing attribute error."""
    gp = GameProject.load(tmp_gameproj)
    root = os.path.dirname(os.path.abspath(tmp_gameproj))
    expected = os.path.abspath(os.path.join(root, "assets", "parts"))
    assert gp.abs_parts_path == expected


def test_game_project_resolve_path_alias(tmp_gameproj):
    """resolve_path() is a backwards-compat alias for resolve() — must not AttributeError."""
    gp = GameProject.load(tmp_gameproj)
    via_resolve = gp.resolve("assets/textures/hero.png")
    via_alias = gp.resolve_path("assets/textures/hero.png")
    assert via_resolve == via_alias


def test_game_project_missing_parts_path_uses_default(tmp_path):
    """A project JSON without parts_path falls back to the default silently."""
    data = {
        "name": "NoParts",
        "assets_root": "assets",
        "textures_path": "assets/textures",
        "entities_path": "assets/entities",
        # parts_path intentionally omitted
        "fonts_path": "assets/fonts",
        "registry_path": "assets/registry/texture_registry.bin",
    }
    proj_file = tmp_path / "no_parts.json"
    proj_file.write_text(json.dumps(data), encoding="utf-8")
    gp = GameProject.load(str(proj_file))
    assert gp is not None
    # Default must be applied
    assert gp.parts_path == "assets/parts"
    assert gp.abs_parts_path  # must not raise AttributeError


def test_game_project_missing_file_logs_error(tmp_path, caplog):
    """load() for a missing file returns None AND logs an error — no silent failure."""
    import logging
    with caplog.at_level(logging.ERROR, logger="src.common.game_project"):
        result = GameProject.load(str(tmp_path / "ghost.json"))
    assert result is None
    assert any("not found" in record.message.lower() or "ghost" in record.message
               for record in caplog.records), \
        "Expected an error log entry mentioning the missing file"


def test_game_project_malformed_json_logs_error(tmp_path, caplog):
    """load() for bad JSON returns None AND logs an error — not a silent failure."""
    import logging
    bad = tmp_path / "bad.json"
    bad.write_text("{ this is : not valid", encoding="utf-8")
    with caplog.at_level(logging.ERROR, logger="src.common.game_project"):
        result = GameProject.load(str(bad))
    assert result is None
    assert any("json" in record.message.lower() or "invalid" in record.message.lower()
               for record in caplog.records), \
        "Expected an error log entry mentioning the JSON parse failure"


def test_game_project_save_and_reload_with_parts(tmp_path):
    """save()/load() round-trip preserves parts_path."""
    project = GameProject(
        name="WithParts",
        assets_root="assets",
        textures_path="assets/textures",
        entities_path="assets/entities",
        parts_path="assets/parts",
        fonts_path="assets/fonts",
        registry_path="assets/registry/texture_registry.bin",
    )
    filepath = str(tmp_path / "with_parts.json")
    GameProject.save(project, filepath)

    reloaded = GameProject.load(filepath)
    assert reloaded is not None
    assert reloaded.parts_path == "assets/parts"
    assert reloaded.abs_parts_path  # must not raise


def test_game_project_ensure_folders_includes_parts(tmp_path):
    """ensure_folders() creates the parts directory too."""
    project = GameProject.create_default(str(tmp_path), name="FolderTest")
    GameProject.save(project, str(tmp_path / "game_project.json"))
    project.ensure_folders()

    assert os.path.isdir(project.abs_assets_root)
    assert os.path.isdir(project.abs_textures_path)
    assert os.path.isdir(project.abs_entities_path)
    assert os.path.isdir(project.abs_parts_path)   # was missing before the fix
    assert os.path.isdir(project.abs_fonts_path)
    assert os.path.isdir(os.path.dirname(project.abs_registry_path))


# ---------------------------------------------------------------------------
# TextureRegistry
# ---------------------------------------------------------------------------

def _write_registry(tmp_path, data: dict) -> GameProject:
    """Helper: create a minimal project + registry JSON and return the project."""
    proj_data = {
        "name": "RegistryTest",
        "assets_root": "assets",
        "textures_path": "assets/textures",
        "entities_path": "assets/entities",
        "parts_path": "assets/parts",
        "fonts_path": "assets/fonts",
        "registry_path": "assets/registry/texture_registry.bin",
    }
    proj_file = tmp_path / "game_project.json"
    proj_file.write_text(json.dumps(proj_data), encoding="utf-8")

    registry_dir = tmp_path / "assets" / "registry"
    registry_dir.mkdir(parents=True, exist_ok=True)
    registry_file = registry_dir / "texture_registry.json"
    registry_file.write_text(json.dumps(data, indent=4), encoding="utf-8")

    return GameProject.load(str(proj_file))


def test_registry_load(tmp_path):
    """TextureRegistry loads entries from the JSON file correctly."""
    project = _write_registry(tmp_path, {"HERO": "textures/hero.png", "ERROR": "textures/error.png"})
    reg = TextureRegistry(project)
    assert not reg.is_empty
    assert reg.get_path("HERO") == "textures/hero.png"
    assert reg.get_path("ERROR") == "textures/error.png"


def test_registry_get_path_missing_key(tmp_path):
    """get_path() returns None for unknown IDs — does not raise."""
    project = _write_registry(tmp_path, {"A": "textures/a.png"})
    reg = TextureRegistry(project)
    assert reg.get_path("DOES_NOT_EXIST") is None


def test_registry_has_file(tmp_path):
    """has_file is True when the JSON exists, False when it does not."""
    project = _write_registry(tmp_path, {})
    reg = TextureRegistry(project)
    assert reg.has_file is True


def test_registry_no_file_is_empty(tmp_path):
    """When the registry JSON is absent, is_empty is True and no exception is raised."""
    proj_data = {
        "name": "NoRegistry", "assets_root": "assets",
        "textures_path": "assets/textures", "entities_path": "assets/entities",
        "parts_path": "assets/parts", "fonts_path": "assets/fonts",
        "registry_path": "assets/registry/texture_registry.bin",
    }
    proj_file = tmp_path / "game_project.json"
    proj_file.write_text(json.dumps(proj_data), encoding="utf-8")
    project = GameProject.load(str(proj_file))
    # No registry file — must not raise; must be empty
    reg = TextureRegistry(project)
    assert reg.is_empty is True
    assert reg.has_file is False


def test_registry_broken_json_is_empty(tmp_path):
    """Broken JSON is handled gracefully — registry stays empty."""
    project = _write_registry(tmp_path, {})  # creates registry dir
    # Overwrite with broken content
    reg_file = tmp_path / "assets" / "registry" / "texture_registry.json"
    reg_file.write_text("{ broken json", encoding="utf-8")
    reg = TextureRegistry(project)
    assert reg.is_empty is True


def test_registry_no_hardcoded_game_entries(tmp_path):
    """Registry must NOT auto-populate game-specific entries (GRENADE etc.)."""
    project = _write_registry(tmp_path, {})
    reg = TextureRegistry(project)
    GAME_SPECIFIC = {"GRENADE", "PLAYERBODY", "DIRT", "KNIFE", "OBJECT_SQUARE_METAL"}
    loaded_ids = set(reg.get_all_ids())
    overlap = GAME_SPECIFIC & loaded_ids
    assert not overlap, f"Game-specific IDs found in fresh registry: {overlap}"


def test_registry_add_texture(tmp_path):
    """add_texture() inserts the key and sets is_dirty to True."""
    project = _write_registry(tmp_path, {})
    reg = TextureRegistry(project)
    reg.add_texture("HERO", "textures/hero.png")
    assert reg.is_dirty is True
    assert reg.get_path("HERO") == "textures/hero.png"
    
    # Save explicitly and reload from disk to verify persistence
    reg.save()
    assert reg.is_dirty is False
    reg2 = TextureRegistry(project)
    assert reg2.get_path("HERO") == "textures/hero.png"


def test_registry_remove_texture(tmp_path):
    """remove_texture() deletes the key and sets is_dirty to True."""
    project = _write_registry(tmp_path, {"A": "textures/a.png", "B": "textures/b.png"})
    reg = TextureRegistry(project)
    reg.remove_texture("A")
    assert reg.is_dirty is True
    assert reg.get_path("A") is None
    # The remaining key survives
    assert reg.get_path("B") == "textures/b.png"


def test_registry_move_up(tmp_path):
    """move_up() changes insertion order and sets is_dirty to True."""
    project = _write_registry(tmp_path, {"A": "a.png", "B": "b.png", "C": "c.png"})
    reg = TextureRegistry(project)
    reg.move_up("B")  # B moves before A
    assert reg.is_dirty is True
    ids = reg.get_all_ids()
    assert ids == ["B", "A", "C"]


def test_registry_move_down(tmp_path):
    """move_down() changes insertion order and sets is_dirty to True."""
    project = _write_registry(tmp_path, {"A": "a.png", "B": "b.png", "C": "c.png"})
    reg = TextureRegistry(project)
    reg.move_down("B")  # B moves after C
    assert reg.is_dirty is True
    ids = reg.get_all_ids()
    assert ids == ["A", "C", "B"]


def test_registry_resolve_path(tmp_path):
    """resolve_path() returns an absolute path under the assets root."""
    project = _write_registry(tmp_path, {"HERO": "textures/hero.png"})
    reg = TextureRegistry(project)
    resolved = reg.resolve_path("HERO")
    assert resolved is not None
    assert os.path.isabs(resolved)
    # Normalise separators so the test passes on both Windows and POSIX
    resolved_norm = resolved.replace("\\", "/")
    assert resolved_norm.endswith("textures/hero.png")


def test_registry_no_project_is_empty():
    """TextureRegistry with no project stays empty and does not raise."""
    reg = TextureRegistry(project=None)
    assert reg.is_empty is True
    assert reg.has_file is False
    assert reg.get_path("ERROR") is None


def test_game_project_has_registry_true(tmp_path):
    """has_registry is True when the registry JSON exists."""
    project = _write_registry(tmp_path, {"ERROR": "textures/error.png"})
    assert project.has_registry is True


def test_game_project_has_registry_false(tmp_path):
    """has_registry is False when no registry file exists (new project)."""
    proj_data = {
        "name": "Fresh", "assets_root": "assets",
        "textures_path": "assets/textures", "entities_path": "assets/entities",
        "parts_path": "assets/parts", "fonts_path": "assets/fonts",
        "registry_path": "assets/registry/texture_registry.bin",
    }
    proj_file = tmp_path / "game_project.json"
    proj_file.write_text(json.dumps(proj_data), encoding="utf-8")
    project = GameProject.load(str(proj_file))
    assert project.has_registry is False


# ---------------------------------------------------------------------------
# TextureRegistry.sync_from_folder  &  GameProject.has_textures
# ---------------------------------------------------------------------------

def _make_project_with_textures(tmp_path, image_names: list[str]) -> tuple:
    """
    Helper: create a project whose textures folder contains the given filenames
    (empty files — content doesn't matter for path-only tests).
    Returns (project, textures_dir).
    """
    proj_data = {
        "name": "SyncTest",
        "assets_root": "assets",
        "textures_path": "assets/textures",
        "entities_path": "assets/entities",
        "parts_path": "assets/parts",
        "fonts_path": "assets/fonts",
        "registry_path": "assets/registry/texture_registry.bin",
    }
    proj_file = tmp_path / "game_project.json"
    proj_file.write_text(json.dumps(proj_data), encoding="utf-8")

    tex_dir = tmp_path / "assets" / "textures"
    tex_dir.mkdir(parents=True, exist_ok=True)
    for name in image_names:
        (tex_dir / name).write_bytes(b"")  # empty file; content irrelevant

    project = GameProject.load(str(proj_file))
    return project, tex_dir


def test_sync_adds_images(tmp_path):
    """sync_from_folder() discovers image files and adds them to the registry."""
    project, tex_dir = _make_project_with_textures(
        tmp_path, ["hero.png", "enemy.png"]
    )
    reg = TextureRegistry(project)
    added, skipped = reg.sync_from_folder(str(tex_dir))

    assert added == 2
    assert skipped == 0
    assert reg.get_path("HERO") is not None
    assert reg.get_path("ENEMY") is not None


def test_sync_id_is_uppercase_stem(tmp_path):
    """sync_from_folder() uses the uppercased file stem as the texture ID."""
    project, tex_dir = _make_project_with_textures(tmp_path, ["my_hero.png"])
    reg = TextureRegistry(project)
    reg.sync_from_folder(str(tex_dir))

    assert reg.get_path("MY_HERO") is not None
    assert reg.get_path("my_hero") is None  # IDs are always uppercase


def test_sync_skips_existing_entries(tmp_path):
    """sync_from_folder() never overwrites an existing entry."""
    project, tex_dir = _make_project_with_textures(tmp_path, ["hero.png"])
    # Pre-register with a custom path
    registry_dir = tmp_path / "assets" / "registry"
    registry_dir.mkdir(parents=True, exist_ok=True)
    (registry_dir / "texture_registry.json").write_text(
        json.dumps({"HERO": "textures/custom_override.png"}), encoding="utf-8"
    )
    reg = TextureRegistry(project)
    added, skipped = reg.sync_from_folder(str(tex_dir))

    assert added == 0
    assert skipped == 1
    # Original path must be preserved
    assert reg.get_path("HERO") == "textures/custom_override.png"


def test_sync_ignores_non_image_files(tmp_path):
    """sync_from_folder() ignores .txt, .json, .bin etc."""
    project, tex_dir = _make_project_with_textures(
        tmp_path, ["hero.png", "readme.txt", "meta.json", "data.bin"]
    )
    reg = TextureRegistry(project)
    added, skipped = reg.sync_from_folder(str(tex_dir))

    assert added == 1  # only hero.png
    assert reg.get_path("HERO") is not None
    assert reg.get_path("README") is None
    assert reg.get_path("META") is None


def test_sync_scans_subfolders(tmp_path):
    """sync_from_folder() recurses into sub-directories."""
    project, tex_dir = _make_project_with_textures(tmp_path, ["hero.png"])
    sub = tex_dir / "enemies"
    sub.mkdir()
    (sub / "zombie.png").write_bytes(b"")

    reg = TextureRegistry(project)
    added, _skipped = reg.sync_from_folder(str(tex_dir))

    assert added == 2
    assert reg.get_path("HERO") is not None
    assert reg.get_path("ZOMBIE") is not None


def test_sync_empty_folder_returns_zero(tmp_path):
    """sync_from_folder() on an empty folder returns (0, 0) and does not save."""
    project, tex_dir = _make_project_with_textures(tmp_path, [])
    reg = TextureRegistry(project)
    added, skipped = reg.sync_from_folder(str(tex_dir))

    assert added == 0
    assert skipped == 0
    assert reg.is_empty


def test_sync_nonexistent_folder(tmp_path):
    """sync_from_folder() on a missing folder returns (0, 0) without raising."""
    project, _tex_dir = _make_project_with_textures(tmp_path, [])
    reg = TextureRegistry(project)
    added, skipped = reg.sync_from_folder("/nonexistent/path/textures")

    assert added == 0
    assert skipped == 0


def test_sync_persists_to_disk(tmp_path):
    """After sync_from_folder(), reloading the registry finds the same entries."""
    project, tex_dir = _make_project_with_textures(tmp_path, ["hero.png"])
    reg = TextureRegistry(project)
    reg.sync_from_folder(str(tex_dir))

    # Reload from disk
    reg2 = TextureRegistry(project)
    assert reg2.get_path("HERO") is not None


def test_has_textures_true(tmp_path):
    """has_textures is True when at least one image file exists."""
    project, _tex_dir = _make_project_with_textures(tmp_path, ["hero.png"])
    assert project.has_textures is True


def test_has_textures_false_empty_folder(tmp_path):
    """has_textures is False when the textures folder has no image files."""
    project, _tex_dir = _make_project_with_textures(tmp_path, [])
    assert project.has_textures is False


def test_has_textures_false_no_folder(tmp_path):
    """has_textures is False when the textures folder does not exist."""
    proj_data = {
        "name": "NoTex", "assets_root": "assets",
        "textures_path": "assets/textures", "entities_path": "assets/entities",
        "parts_path": "assets/parts", "fonts_path": "assets/fonts",
        "registry_path": "assets/registry/texture_registry.bin",
    }
    proj_file = tmp_path / "game_project.json"
    proj_file.write_text(json.dumps(proj_data), encoding="utf-8")
    project = GameProject.load(str(proj_file))
    # textures/ folder never created
    assert project.has_textures is False


def test_has_textures_ignores_non_images(tmp_path):
    """has_textures is False when only non-image files are in the textures folder."""
    project, tex_dir = _make_project_with_textures(
        tmp_path, ["readme.txt", "meta.json"]
    )
    assert project.has_textures is False


# ---------------------------------------------------------------------------
# GameProject.ensure_registry
# ---------------------------------------------------------------------------

def _fresh_project(tmp_path) -> GameProject:
    """Return a project with NO registry file on disk."""
    proj_data = {
        "name": "EnsureTest", "assets_root": "assets",
        "textures_path": "assets/textures", "entities_path": "assets/entities",
        "parts_path": "assets/parts", "fonts_path": "assets/fonts",
        "registry_path": "assets/registry/texture_registry.bin",
    }
    proj_file = tmp_path / "game_project.json"
    proj_file.write_text(json.dumps(proj_data), encoding="utf-8")
    return GameProject.load(str(proj_file))


def test_ensure_registry_creates_file_when_absent(tmp_path):
    """ensure_registry() creates an empty JSON file when none exists."""
    project = _fresh_project(tmp_path)
    assert project.has_registry is False  # precondition

    project.ensure_registry()

    assert project.has_registry is True


def test_ensure_registry_file_is_valid_empty_json(tmp_path):
    """The file created by ensure_registry() contains valid, empty JSON object."""
    project = _fresh_project(tmp_path)
    project.ensure_registry()

    json_path = os.path.splitext(project.abs_registry_path)[0] + ".json"
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data == {}


def test_ensure_registry_returns_false_when_created(tmp_path):
    """ensure_registry() returns False when it had to create the file."""
    project = _fresh_project(tmp_path)
    result = project.ensure_registry()
    assert result is False


def test_ensure_registry_returns_true_when_already_exists(tmp_path):
    """ensure_registry() returns True when the file already exists."""
    project = _write_registry(tmp_path, {"HERO": "textures/hero.png"})
    result = project.ensure_registry()
    assert result is True


def test_ensure_registry_is_idempotent(tmp_path):
    """Calling ensure_registry() twice does not overwrite existing content."""
    project = _fresh_project(tmp_path)
    project.ensure_registry()

    # Manually write some content into the registry
    json_path = os.path.splitext(project.abs_registry_path)[0] + ".json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"HERO": "textures/hero.png"}, f)

    # Second call must NOT overwrite existing content
    project.ensure_registry()

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data == {"HERO": "textures/hero.png"}


def test_ensure_registry_makes_has_registry_true(tmp_path):
    """After ensure_registry(), has_registry is always True regardless of prior state."""
    project = _fresh_project(tmp_path)
    assert project.has_registry is False
    project.ensure_registry()
    assert project.has_registry is True


def test_ensure_registry_creates_parent_directories(tmp_path):
    """ensure_registry() creates the registry/ directory if it doesn't exist."""
    project = _fresh_project(tmp_path)
    reg_dir = os.path.dirname(project.abs_registry_path)
    assert not os.path.isdir(reg_dir)  # precondition: dir doesn't exist yet

    project.ensure_registry()

    assert os.path.isdir(reg_dir)


def test_ensure_registry_auto_syncs_if_textures_present(tmp_path):
    """ensure_registry() populates the registry (sync) if textures are present, instead of creating {}."""
    project, tex_dir = _make_project_with_textures(tmp_path, ["player.png"])
    assert project.has_registry is False
    assert project.has_textures is True
    
    project.ensure_registry()
    
    assert project.has_registry is True
    # verify it actually contains the synced texture, not {}
    reg = TextureRegistry(project)
    assert not reg.is_empty
    assert reg.get_path("PLAYER") is not None


def test_ensure_registry_does_not_touch_textures(tmp_path):
    """ensure_registry() only touches the registry file, not the textures folder."""
    project = _fresh_project(tmp_path)
    project.ensure_registry()
    # Textures folder must not have been created as a side-effect
    assert not os.path.isdir(project.abs_textures_path)

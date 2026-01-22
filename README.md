# Entity Editor

A modular, extensible 2D Entity Editor for character and entity creation for custom game engines.

![Entity Editor](https://img.shields.io/badge/python-3.8+-blue.svg)
![PySide6](https://img.shields.io/badge/PySide6-6.6+-green.svg)

## Features

### Entity Management
- ✅ Create new entities
- ✅ Load existing entities from disk (.entdef format)
- ✅ Save entities back to disk
- ✅ Entity metadata (name, unique ID)
- ✅ Editable pivot point

### Visual Entity Editor
- ✅ 2D preview viewport
- ✅ Display all body parts with textures
- ✅ Interactive selection
- ✅ Drag-and-drop repositioning
- ✅ Zoom and pan controls
- ✅ Grid overlay

### Body Parts
- ✅ Add / remove / rename body parts
- ✅ Position and size editing
- ✅ Texture reference (PNG support)
- ✅ UV rectangle mapping
- ✅ Z-order for draw layering

### Hitboxes
- ✅ Multiple hitboxes per body part
- ✅ Visual editing (drag rectangles)
- ✅ Different hitbox types:
  - collision
  - damage
  - trigger
  - interaction
  - custom

### Modular Architecture
- Signal-based component communication
- Clean separation of concerns
- Extensible data models
- Binary file format with JSON payload

## Installation

### Requirements
- Python 3.8 or higher
- PySide6
- Pillow

### Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/entityEditor.git
cd entityEditor
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the editor:
```bash
python main.py
```

## Usage

### Quick Start

1. **Create Example Entities** (first time):
```bash
python generate_examples.py
```

This creates sample entities in `examples/entities/`:
- `simple.entdef` - A basic entity with one body part
- `test_character.entdef` - A character with head, torso, and arms

2. **Open the Editor**:
```bash
python main.py
```

3. **Load an Example**:
- Click `File → Open...`
- Navigate to `examples/entities/`
- Open `test_character.entdef`

### Creating Entities

1. **New Entity**: `File → New Entity` or `Ctrl+N`
2. **Add Body Parts**: In the Body Parts panel, click "Add"
3. **Edit Properties**: Select a body part and edit position, size, etc.
4. **Add Texture**: Click "Browse..." to select a PNG texture
5. **Position Visually**: Drag body parts in the viewport
6. **Add Hitboxes**: Select a body part, then click "Add Hitbox" in the Hitbox panel
7. **Save**: `File → Save` or `Ctrl+S`

### Viewport Controls

- **Left Click**: Select body parts
- **Left Click + Drag**: Move selected body part
- **Right Click + Drag**: Pan the viewport
- **Mouse Wheel**: Zoom in/out

### File Format

Entities are saved in `.entdef` (Entity Definition) format:
- Binary format with magic number validation
- Version header for compatibility
- JSON payload for flexibility and debugging

## Project Structure

```
entityEditor/
├── main.py                          # Application entry point
├── requirements.txt                 # Dependencies
├── generate_examples.py             # Example generator
│
├── src/
│   ├── data/
│   │   ├── entity_data.py          # Data models (Entity, BodyPart, Hitbox)
│   │   └── file_io.py              # Binary serialization
│   │
│   ├── core/
│   │   └── signal_hub.py           # Event system
│   │
│   ├── rendering/
│   │   └── texture_manager.py      # Texture loading & caching
│   │
│   └── ui/
│       ├── main_window.py          # Main window with menu bar
│       ├── panels/
│       │   ├── entity_panel.py     # Entity properties editor
│       │   ├── bodyparts_panel.py  # Body parts manager
│       │   └── hitbox_panel.py     # Hitbox editor
│       │
│       └── widgets/
│           └── viewport_widget.py  # 2D preview viewport
│
└── examples/
    ├── entities/                    # Sample .entdef files
    └── textures/                    # Sample textures
```

## Architecture

### Data Models
- **Entity**: Top-level container with metadata and body parts
- **BodyPart**: Visual component with position, size, texture, UV mapping
- **Hitbox**: Collision/interaction area with type and bounds
- **Vec2**: 2D vector for positions and sizes
- **UVRect**: Normalized UV coordinates (0.0 to 1.0)

### Signal Hub
Centralized event dispatcher enables decoupled UI components:
- Entity loaded/saved/modified signals
- Body part selection/modification signals
- Hitbox modification signals
- Texture loaded signals

### Texture Manager
Cached texture loading for performance:
- Load once, reuse everywhere
- Automatic PNG loading via PIL
- Size tracking for UV coordinate conversion

## Future Enhancements

The architecture supports easy addition of:
- **UV Editor Panel**: Visual UV rectangle editing with texture preview
- **Animation System**: Keyframe-based body part animation
- **Skeletal Hierarchy**: Parent-child relationships between body parts
- **Undo/Redo**: Command pattern integration
- **Export Formats**: JSON, XML, or custom game engine formats
- **Texture Atlas Support**: Sprite sheet management
- **Multi-entity Editing**: Edit multiple entities simultaneously

## Development

### Design Philosophy
1. **Speed of Iteration**: Quick, responsive editing for game developers
2. **Clarity**: Clean code, clear architecture, well-documented
3. **Extensibility**: Easy to add new features without breaking existing code
4. **Decoupling**: No tight coupling to any specific game engine

### Contributing
This is a game development tool. Contributions focused on usability, performance, and new features are welcome.

## Credits

Created as a professional game development tool. Built with Python 3 and PySide6.

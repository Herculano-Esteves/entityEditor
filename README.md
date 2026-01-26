# Entity Editor

A modular 2D Entity Editor designed for creating complex character rigs and entities for custom game engines.

![Entity Editor](https://img.shields.io/badge/python-3.8+-blue.svg)
![PySide6](https://img.shields.io/badge/PySide6-6.6+-green.svg)
![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)

## Features

### Entity Management
- **Create & Manage**: Easily create, load, and save entities using a robust `.entdef` format.
- **Metadata**: Manage unique IDs, names, and tags for seamless engine integration.
- **Pivot Control**: Precise pivot point adjustment for accurate runtime positioning.

### Visual Editor
- **2D Viewport**: Real-time preview with zoom, pan, and grid snapping.
- **Drag & Drop**: Intuitive direct manipulation of body parts.
- **Selection**: Box selection and multi-select support for efficient editing.

### Body Parts
- **Sprite Management**: Import standard formats (PNG, JPG, BMP).
- **Transformation**: Rotate, scale, and flip sprites with pixel-perfect precision.
- **Z-Ordering**: Layer sprites to build complex characters.
- **UV Editing**: Visual tool for defining texture regions/sub-sprites.

### Hitboxes
- **Collision Definition**: Draw precise hitboxes for physics and gameplay logic.
- **Typed Zones**: Define specific zones for collision, damage, or triggers.
- **Pixel Precision**: Enforced integer coordinates to prevent sub-pixel logic errors.

## Installation

### Requirements
- Python 3.8 or higher
- PySide6
- Pillow

### Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/entityEditor.git
   cd entityEditor
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the editor**:
   ```bash
   python main.py
   ```

## Usage

### Quick Start

1. **Generate Examples** (Optional):
   Run `python generate_examples.py` to create sample entities in `examples/entities/`.

2. **Open the Editor**:
   Run `python main.py`.

3. **Create a New Entity**:
   - Go to `File → New Entity` (Ctrl+N).
   - Use the **Body Parts** panel to add visual components.
   - Use the **Hitbox** panel to add logic zones.
   - Save your work via `File → Save` (Ctrl+S).

### Controls

- **Left Click**: Select body parts.
- **Left Click + Drag**: Box select multiple parts.
- **Right Click + Drag**: Pan the viewport.
- **Mouse Wheel**: Zoom in/out.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

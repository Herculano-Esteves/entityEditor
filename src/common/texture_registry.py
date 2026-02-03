
import json
import os
import struct
from copy import deepcopy

class TextureRegistry:
    """
    Manages the texture registry, handling both JSON (editing) and Binary (game) formats.
    """
    
    def __init__(self, project_context=None):
        """
        Args:
            project_context (GameProject): Loaded project context. If None, uses defaults.
        """
        self.project = project_context
        
        # Default paths if no project
        self.json_path = "assets/registry/texture_registry.json"
        self.bin_path = "assets/registry/texture_registry.bin"
        
        if self.project:
            # We derive JSON path from BIN path usually, or parallel
            # The USER config defines RegistryPath=registry/texture_registry.bin
            # So let's assume JSON lives next to it
            bin_abs = self.project.abs_registry_path
            self.bin_path = bin_abs
            self.json_path = os.path.splitext(bin_abs)[0] + ".json"
        
        self._registry = {} # Dict[str, str] -> KEY: PATH
        self._keys_order = [] # List[str] to maintain order
        self.load()
        
    def load(self):
        """Load from JSON if exists, else load defaults."""
        # Ensure dir exists
        os.makedirs(os.path.dirname(self.json_path), exist_ok=True)
        
        if os.path.exists(self.json_path):
            try:
                with open(self.json_path, 'r') as f:
                    data = json.load(f)
                    self._registry = data
                    self._keys_order = list(self._registry.keys())
            except Exception as e:
                print(f"Error loading registry: {e}")
                self._create_defaults()
        else:
            self._create_defaults()
            self.save()
            
    def _create_defaults(self):
        """Create default registry entries."""
        self._registry = {
            "ERROR": "textures/error.png",
            "EMPTY": "textures/empty.png",
            "GRENADE": "textures/grenade.png",
            "PLAYERBODY": "textures/player.png",
            "DIRT": "textures/dirt.png",
            "KNIFE": "textures/knife.png",
            "OBJECT_SQUARE_METAL": "textures/crate_metal.png"
        }
        self._keys_order = list(self._registry.keys())
        
    def save(self):
        """Save to JSON and Export Binary."""
        self._save_json()
        self._export_binary()
        
    def _save_json(self):
        os.makedirs(os.path.dirname(self.json_path), exist_ok=True)
        
        # reconstruct dict in order
        ordered_dict = {k: self._registry[k] for k in self._keys_order}
        
        with open(self.json_path, 'w') as f:
            json.dump(ordered_dict, f, indent=4)
            
    def _export_binary(self):
        os.makedirs(os.path.dirname(self.bin_path), exist_ok=True)
        
        buffer = bytearray()
        
        # Write count
        count = len(self._registry)
        buffer.extend(struct.pack('<I', count))
        
        def write_string(buf, text):
            encoded = text.encode('utf-8')
            buf.extend(struct.pack('<I', len(encoded)))
            buf.extend(encoded)
            
        # Write entries in order
        for key in self._keys_order:
            path = self._registry[key]
            write_string(buffer, key)
            write_string(buffer, path)
            
        with open(self.bin_path, 'wb') as f:
            f.write(buffer)
            
    # --- Manipulation Methods ---
    
    def get_all(self):
        """Return list of (key, path) tuples."""
        return [(k, self._registry[k]) for k in self._keys_order]
        
    def add_texture(self, key, path):
        """Add or update a texture."""
        if key not in self._registry:
            self._keys_order.append(key)
        self._registry[key] = path
        self.save()
        
    def remove_texture(self, key):
        """Remove a texture."""
        if key in self._registry:
            del self._registry[key]
            if key in self._keys_order:
                self._keys_order.remove(key)
            self.save()
            
    def move_up(self, key):
        if key not in self._keys_order: return
        idx = self._keys_order.index(key)
        if idx > 0:
            self._keys_order[idx], self._keys_order[idx-1] = self._keys_order[idx-1], self._keys_order[idx]
            self.save()
            
    def move_down(self, key):
        if key not in self._keys_order: return
        idx = self._keys_order.index(key)
        if idx < len(self._keys_order) - 1:
            self._keys_order[idx], self._keys_order[idx+1] = self._keys_order[idx+1], self._keys_order[idx]
            self.save()

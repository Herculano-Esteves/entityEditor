
import os

class GameProject:
    """
    Represents a loaded game project (.gameproj).
    Resolves paths relative to the project file.
    """
    
    def __init__(self, filepath=None):
        self.project_file = filepath
        self.root_dir = os.path.dirname(filepath) if filepath else os.getcwd()
        
        # Defaults
        self.assets_root = "assets"
        self.registry_path = "assets/registry/texture_registry.bin"
        self.entities_path = "assets/entities"
        self.fonts_path = "assets/fonts"
        
        if filepath:
            self.load(filepath)
            
    def load(self, filepath):
        self.project_file = filepath
        self.root_dir = os.path.dirname(filepath)
        
        config = {}
        try:
            with open(filepath, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'): continue
                    if '=' in line:
                        key, val = line.split('=', 1)
                        config[key.strip()] = val.strip()
            
            self.assets_root = config.get("AssetsRoot", self.assets_root)
            self.registry_path = config.get("RegistryPath", self.registry_path)
            self.entities_path = config.get("EntitiesPath", self.entities_path)
            self.fonts_path = config.get("FontsPath", self.fonts_path)
            
        except Exception as e:
            print(f"Error loading project {filepath}: {e}")

    def resolve_path(self, relative_path):
        """Get absolute path from a path relative to the project root."""
        return os.path.abspath(os.path.join(self.root_dir, relative_path))
        
    @property
    def abs_assets_root(self):
        return self.resolve_path(self.assets_root)
        
    @property
    def abs_registry_path(self):
        # Registry is inside assets
        return os.path.abspath(os.path.join(self.abs_assets_root, self.registry_path))
        
    @property
    def abs_entities_path(self):
        # Entities are inside assets
        return os.path.abspath(os.path.join(self.abs_assets_root, self.entities_path))

    @property
    def abs_fonts_path(self):
        # Fonts are inside assets
        return os.path.abspath(os.path.join(self.abs_assets_root, self.fonts_path))

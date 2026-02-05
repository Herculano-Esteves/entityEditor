
from src.tools.entity_editor.data.entity_data import Entity, BodyPart, Vec2, Hitbox, BodyPartType
from src.tools.entity_editor.core.entity_manager import get_entity_manager

def calculate_entity_bounds(entity: Entity) -> tuple[float, float]:
    """
    Calculate the bounding box width and height of an entity.
    This considers all visible body parts and recursively referenced entities.
    Returns (width, height). Defaults to (64, 64) if empty.
    """
    if not entity.body_parts and not entity.entity_hitboxes:
        return 64.0, 64.0
        
    min_x = float('inf')
    min_y = float('inf')
    max_x = float('-inf')
    max_y = float('-inf')
    
    found_any = False
    
    # Check Body Parts
    for bp in entity.body_parts:
        if not bp.visible: continue
        
        found_any = True
        
        # Base rect
        x = bp.position.x
        y = bp.position.y
        w = bp.size.x
        h = bp.size.y
        
        # If it's an entity ref, its "size" field might be outdated or just a container.
        # But correctly, if we updated the UX, BP size IS the visual size.
        # So using bp.size is correct assuming we maintain that invariant.
        
        # If we are effectively "just added" and haven't resized yet, this might be small.
        # But for recursive calculation, we assume children are valid.
        
        min_x = min(min_x, x)
        min_y = min(min_y, y)
        max_x = max(max_x, x + w)
        max_y = max(max_y, y + h)
        
    # Check Hitboxes (should they contribute to "visual" size? User said "Area of selection")
    # Usually yes, if I have a hitbox stick out, I want to select it.
    for hb in entity.entity_hitboxes:
        if not hb.enabled: continue
        
        found_any = True
        min_x = min(min_x, entity.pivot.x + hb.x)
        min_y = min(min_y, entity.pivot.y + hb.y)
        max_x = max(max_x, entity.pivot.x + hb.x + hb.width)
        max_y = max(max_y, entity.pivot.y + hb.y + hb.height)
        
    
    if not found_any:
        return 0.0, 0.0, 64.0, 64.0
        
    width = max_x - min_x
    height = max_y - min_y
    
    # Ensure minimum usable size
    return min_x, min_y, max(width, 16.0), max(height, 16.0)

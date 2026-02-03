
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QMouseEvent, QKeyEvent, QPainter, QPen, QColor

from src.tools.entity_editor.core.state.editor_state import EditorState
from src.tools.entity_editor.core import get_signal_hub
from src.tools.entity_editor.ui.viewport.tools.abstract_tool import AbstractTool
from src.tools.entity_editor.data import Vec2

class SelectTool(AbstractTool):
    """
    Tool for selecting and moving entities and hitboxes.
    """
    
    def __init__(self, state: EditorState, view):
        super().__init__(state)
        self._view = view
        self._dragging = False
        
        # Box Selection State
        self._is_box_selecting = False
        self._box_start_pos = Vec2(0, 0)
        self._box_current_pos = Vec2(0, 0)
        
        self._drag_start_pos = Vec2(0, 0)
        self._drag_start_positions = {} # Map(id -> Vec2)
        
        # Hitbox specific state
        self._dragging_hitbox = None # Hitbox reference
        self._dragging_hitbox_parent = None # BodyPart
        self._resize_edge = None
        self._drag_start_hitbox_pos = Vec2(0, 0)
        self._drag_start_hitbox_size = Vec2(0, 0)
        
        # Grid settings (could be moved to EditorState eventually)
        self._grid_size = 1
        
    def activate(self):
        self._reset_state()
        
    def deactivate(self):
        self._reset_state()
        
    def _reset_state(self):
        self._dragging = False
        self._is_box_selecting = False
        self._dragging_hitbox = None
        self._dragging_hitbox_parent = None
        self._resize_edge = None
        self._drag_start_positions.clear()

    def mouse_press(self, event: QMouseEvent, world_pos: Vec2):
        if event.button() == Qt.LeftButton:
            modifiers = event.modifiers()
            
            # 1. Check Hitbox Interaction (if enabled)
            if self._state.hitbox_edit_mode:
                hitbox, parent_bp = self._get_hitbox_at(world_pos)
                if hitbox:
                    self._handle_hitbox_press(hitbox, parent_bp, world_pos)
                    return
            
            # 2. Check BodyPart Interaction
            clicked_bp = self._get_bodypart_at(world_pos)
            if clicked_bp:
                self._handle_bodypart_press(clicked_bp, modifiers, world_pos)
            else:
                # 3. Box Selection Start
                if not (modifiers & Qt.ControlModifier):
                    self._state.selection.clear_selection()
                    self._state.selection.deselect_hitbox()
                
                self._is_box_selecting = True
                self._box_start_pos = world_pos
                self._box_current_pos = world_pos
                
    def mouse_move(self, event: QMouseEvent, world_pos: Vec2):
        # 1. Handle Dragging Hitbox
        if self._dragging_hitbox:
            self._handle_hitbox_drag(world_pos)
            return

        # Cursor Updates (Hover)
        self._update_cursor_shape(world_pos)
        
        # 2. Handle Box Selection
        if self._is_box_selecting:
            self._box_current_pos = world_pos
            return
            
        # 3. Handle Dragging BodyParts
        if self._dragging and self._state.selection.selected_body_parts:
            self._handle_bodypart_drag(world_pos)
            
    def mouse_release(self, event: QMouseEvent, world_pos: Vec2):
        if event.button() == Qt.LeftButton:
            # Commit Hitbox Change
            if self._dragging_hitbox:
                if self._state.history:
                    self._state.history.end_change()
                self._dragging_hitbox = None
                self._resize_edge = None
                
            if self._dragging:
                if self._state.history:
                    # Check if actually moved to avoid empty undo entries?
                    # The service might handle this, or we check here.
                    self._state.history.end_change()
                self._dragging = False
                self._drag_start_positions.clear()
            
            # Commit Box Selection
            if self._is_box_selecting:
                self._handle_box_selection(event.modifiers())
                self._is_box_selecting = False
        
        self._reset_cursor()

    def render(self, painter: QPainter):
        if self._is_box_selecting:
            # Create rect from start/current
            x = min(self._box_start_pos.x, self._box_current_pos.x)
            y = min(self._box_start_pos.y, self._box_current_pos.y)
            w = abs(self._box_current_pos.x - self._box_start_pos.x)
            h = abs(self._box_current_pos.y - self._box_start_pos.y)
            
            rect = QRectF(x, y, w, h)
            
            # Draw semi-transparent blue box
            painter.setPen(QPen(QColor(100, 200, 255), 1))
            painter.setBrush(QColor(100, 200, 255, 50))
            painter.drawRect(rect)
    
    def _handle_box_selection(self, modifiers):
        # Calculate Box Rect
        x = min(self._box_start_pos.x, self._box_current_pos.x)
        y = min(self._box_start_pos.y, self._box_current_pos.y)
        w = abs(self._box_current_pos.x - self._box_start_pos.x)
        h = abs(self._box_current_pos.y - self._box_start_pos.y)
        
        box_rect = QRectF(x, y, w, h)
        
        # Find intersecting body parts
        entity = self._state.current_entity
        if not entity: return
        
        # If strict selection logic needed: 
        # Standard: Select if partially contained (Intersects)
        
        affected_bps = []
        for bp in entity.body_parts:
            if not bp.visible: continue
            
            bp_rect = QRectF(bp.position.x, bp.position.y, bp.size.x, bp.size.y)
            if box_rect.intersects(bp_rect):
                affected_bps.append(bp)
        
        # Apply Selection
        # If Ctrl held, Add/Toggle? Standard is usually Add/Toggle.
        # User request: "select all the bodyparts inside the square"
        # Implying additive or replacement? 
        # Usually Box Select replaces selection unless Modifier is held.
        # Logic in mouse_press already cleared selection if no modifier.
        # So here we just ADD whatever is in the box.
        
        for bp in affected_bps:
            self._state.selection.add_to_selection(bp)

    def _update_cursor_shape(self, world_pos: Vec2):
        if not self._state.hitbox_edit_mode:
            self._reset_cursor()
            return

        hitbox, parent_bp = self._get_hitbox_at(world_pos)
        if hitbox:
            edge = self._get_hitbox_edge(hitbox, parent_bp, world_pos)
            if edge:
                if edge in ['left', 'right']:
                    self._view.setCursor(Qt.SizeHorCursor)
                elif edge in ['top', 'bottom']:
                    self._view.setCursor(Qt.SizeVerCursor)
                elif edge in ['tl', 'br']:
                    self._view.setCursor(Qt.SizeFDiagCursor)
                elif edge in ['tr', 'bl']:
                    self._view.setCursor(Qt.SizeBDiagCursor)
                else:
                    self._view.setCursor(Qt.SizeAllCursor) # Move
                return
        
        self._reset_cursor()

    def _reset_cursor(self):
        self._view.setCursor(Qt.ArrowCursor)

    # --- Logic Helpers ---

    def _handle_hitbox_press(self, hitbox, parent_bp, world_pos: Vec2):
        # Auto-select parent body part if not already selected
        if parent_bp and not self._state.selection.is_selected(parent_bp):
             self._state.selection.set_selection(parent_bp)
        
        # Select Hitbox
        self._state.selection.select_hitbox(hitbox)
        
        # Determine if resizing or moving
        edge = self._get_hitbox_edge(hitbox, parent_bp, world_pos)
        
        self._dragging_hitbox = hitbox
        self._dragging_hitbox_parent = parent_bp
        self._resize_edge = edge
        self._drag_start_pos = world_pos
        self._drag_start_hitbox_pos = Vec2(hitbox.x, hitbox.y)
        self._drag_start_hitbox_size = Vec2(hitbox.width, hitbox.height)
        
        action_name = "Resize Hitbox" if edge else "Move Hitbox"
        if self._state.history:
            self._state.history.begin_change(action_name)

    def _handle_bodypart_press(self, clicked_bp, modifiers, world_pos: Vec2):
        # Handle Selection
        if modifiers & Qt.ControlModifier:
            self._state.selection.toggle_selection(clicked_bp)
        else:
            if not self._state.selection.is_selected(clicked_bp):
                self._state.selection.set_selection(clicked_bp)
        
        # Start Dragging (if we have a selection)
        if self._state.selection.has_selection:
            self._dragging = True
            self._drag_start_pos = world_pos
            self._drag_start_positions = {}
            for bp in self._state.selection.selected_body_parts:
                self._drag_start_positions[id(bp)] = Vec2(bp.position.x, bp.position.y)
            
            if self._state.history:
                self._state.history.begin_change("Move Body Part")

    def _handle_hitbox_drag(self, world_pos: Vec2):
        delta = world_pos - self._drag_start_pos
        
        if self._resize_edge:
            # Resize Logic
            new_x = self._drag_start_hitbox_pos.x
            new_y = self._drag_start_hitbox_pos.y
            new_w = self._drag_start_hitbox_size.x
            new_h = self._drag_start_hitbox_size.y
            
            if self._resize_edge in ['left', 'tl', 'bl']:
                new_x += delta.x
                new_w -= delta.x
            if self._resize_edge in ['right', 'tr', 'br']:
                new_w += delta.x
            if self._resize_edge in ['top', 'tl', 'tr']:
                new_y += delta.y
                new_h -= delta.y
            if self._resize_edge in ['bottom', 'bl', 'br']:
                new_h += delta.y
                
            # Snap and Apply
            new_w = max(1, self._snap(new_w))
            new_h = max(1, self._snap(new_h))
            
            self._dragging_hitbox.x = self._snap(new_x)
            self._dragging_hitbox.y = self._snap(new_y)
            self._dragging_hitbox.width = new_w
            self._dragging_hitbox.height = new_h
        else:
            # Move Logic
            new_x = self._drag_start_hitbox_pos.x + delta.x
            new_y = self._drag_start_hitbox_pos.y + delta.y
            
            self._dragging_hitbox.x = self._snap(new_x)
            self._dragging_hitbox.y = self._snap(new_y)
            
        # Signal update (Legacy compatibility or new signal needed?)
        # For now, we assume direct modification is watched or we trigger update via State?
        # Ideally EditorState should expose a method to notify modification if not automatic.
        # But since we modified data objects directly, we might need to emit a signal.
        # self._state.notify_entity_modified() # Hypothetical method
        get_signal_hub().notify_hitbox_modified(self._dragging_hitbox) 

    def _handle_bodypart_drag(self, world_pos: Vec2):
        delta = world_pos - self._drag_start_pos
        
        for bp in self._state.selection.selected_body_parts:
            if id(bp) in self._drag_start_positions:
                start_pos = self._drag_start_positions[id(bp)]
                new_x = start_pos.x + delta.x
                new_y = start_pos.y + delta.y
                
                bp.position.x = self._snap(new_x)
                bp.position.y = self._snap(new_y)
                
                get_signal_hub().notify_bodypart_modified(bp)

        # self._state.notify_entity_modified()

    # --- Query/Math Helpers ---
    
    def _snap(self, value):
        return int(round(value)) # Pixel perfect integer snapping

    def _get_bodypart_at(self, world_pos: Vec2):
        # Iterate in reverse render order (top to bottom)
        entity = self._state.current_entity
        if not entity:
            return None
            
        # Prepare list in Render Order (Bottom to Top)
        body_parts = list(entity.body_parts)
        body_parts.sort(key=lambda bp: bp.z_order)
        
        # Handle Selection on Top
        if self._state.selection_on_top and self._state.selection.has_selection:
            unselected = [bp for bp in body_parts if not self._state.selection.is_selected(bp)]
            selected = [bp for bp in body_parts if self._state.selection.is_selected(bp)]
            body_parts = unselected + selected
            
        # Iterate in Reverse (Top to Bottom) to find first hit
        for bp in reversed(body_parts):
            if not bp.visible:
                continue
                
            # Simple interaction rect check
            # For more precise checking, we might need rotated rect check
            # but standard rect is usually fine for selection unless heavily rotated
            
            # Using simple bounding box for now (ignoring rotation for selection hit test for simplicity, can enhance later)
            if (bp.position.x <= world_pos.x <= bp.position.x + bp.size.x and 
                bp.position.y <= world_pos.y <= bp.position.y + bp.size.y):
                return bp
        return None

    def _get_hitbox_at(self, world_pos: Vec2):
        # Only if we are in a mode to check hitboxes? 
        # For now, check all visible hitboxes.
        entity = self._state.current_entity
        if not entity:
            return None, None

        # Check BodyPart hitboxes
        # If Selection is active, maybe only check hitboxes of selected bodypart?
        # ViewportWidget logic: "Only draw hitboxes if this is the selected body part, or no body part is selected"
        
        target_bps = entity.body_parts
        # If we have a selection, maybe restriction? 
        # But usually you can click any hitbox.
        
        for bp in reversed(target_bps):
            if not bp.visible:
                continue
            
            # If logic requires only checking selected BP hitboxes:
            if self._state.selection.has_selection and not self._state.selection.is_selected(bp): continue
            
            for hitbox in bp.hitboxes:
                if not hitbox.enabled:
                    continue
                
                # Hitboxes are relative to body part
                abs_x = bp.position.x + hitbox.x
                abs_y = bp.position.y + hitbox.y
                
                if (abs_x <= world_pos.x <= abs_x + hitbox.width and 
                    abs_y <= world_pos.y <= abs_y + hitbox.height):
                    return hitbox, bp
                    
        # Check Entity Hitboxes (if any)
        if hasattr(entity, 'entity_hitboxes'):
             for hitbox in entity.entity_hitboxes:
                if not hitbox.enabled: continue
                # Entity hitboxes relative to pivot? Or 0,0? 
                # ViewportWidget used self._entity.pivot
                offset = entity.pivot
                abs_x = offset.x + hitbox.x
                abs_y = offset.y + hitbox.y
                
                if (abs_x <= world_pos.x <= abs_x + hitbox.width and 
                    abs_y <= world_pos.y <= abs_y + hitbox.height):
                    return hitbox, None # No parent body part
                    
        return None, None

    def _get_hitbox_edge(self, hitbox, parent_bp, world_pos: Vec2):
        # Determine strict corner/edge click
        # Need absolute coords
        offset = parent_bp.position if parent_bp else self._state.current_entity.pivot
        x = offset.x + hitbox.x
        y = offset.y + hitbox.y
        w = hitbox.width
        h = hitbox.height
        
        margin = 5 # Tolerance in world units? Or screen units?
        # Interaction should ideally be screen units, but we are in world_pos here.
        # Assuming 1:1 for simplicity or small margin.
        
        l = abs(world_pos.x - x) < margin
        r = abs(world_pos.x - (x + w)) < margin
        t = abs(world_pos.y - y) < margin
        b = abs(world_pos.y - (y + h)) < margin
        
        if l and t: return 'tl'
        if r and t: return 'tr'
        if l and b: return 'bl'
        if r and b: return 'br'
        if l: return 'left'
        if r: return 'right'
        if t: return 'top'
        if b: return 'bottom'
        return None


from PySide6.QtCore import Qt, QRectF, QPointF, QRect, QLineF
from PySide6.QtGui import QPainter, QPen, QColor, QTransform, QPixmap

from src.tools.entity_editor.core.state.editor_state import EditorState
from src.tools.entity_editor.data import Vec2, HitboxShape
from src.tools.entity_editor.rendering import get_texture_manager
from src.tools.entity_editor.data.entity_data import BodyPartType
from src.tools.entity_editor.core.entity_manager import get_entity_manager

class ViewportRenderer:
    """
    Handles all rendering logic for the Viewport.
    Decoupled from the ViewportWidget interaction logic.
    """
    
    def __init__(self, state: EditorState):
        self._state = state
        self._texture_manager = get_texture_manager()
        
        # Rendering Options (could be moved to State or passed in)
        self.show_hitboxes = True
        self.show_grid = True
        self.show_pivot = True
        self.zoom = 1.0
        
    def render(self, painter: QPainter, view_rect: QRectF, visible_entity=None):
        """
        Main render method.
        :param painter: QPainter to draw with.
        :param view_rect: The visible area in world coordinates (if doing culling) or use painter transform.
        :param visible_entity: Optional override for entity to render (default is state.current_entity)
        """
        entity = visible_entity or self._state.current_entity
        if not entity:
            return

        # 0. Draw Grid
        if self._state.grid_visible:
            self._draw_grid(painter, view_rect)

        # 1. Draw Body Parts
        self._draw_body_parts(painter, entity)
        
        # 2. Draw Hitboxes (if enabled)
        if self._state.hitbox_edit_mode:
            self._draw_hitboxes(painter, entity)
            
        # 3. Draw Pivot (if enabled)
        if self.show_pivot:
            self._draw_pivot(painter, entity)
            
    def _draw_body_parts(self, painter: QPainter, entity, depth=0):
        if depth > 10: # Max recursion depth
            return

        # Sort by z_index? 
        # Current logic just iterates list (order matters).
        # ViewportWidget Logic:
        # parts_to_render = list(self._entity.body_parts)
        # if self._selected_bodypart in parts_to_render and self._show_selected_above:
        #    parts_to_render.remove(self._selected_bodypart)
        #    parts_to_render.append(self._selected_bodypart)
        
        # We can implement z-sort or selection-on-top here.
        body_parts = list(entity.body_parts)
        # Sort by z-order (ascending)
        body_parts.sort(key=lambda bp: bp.z_order)
        
        # Selection on Top Logic (Only at top level, depth 0)
        if depth == 0 and self._state.selection_on_top and self._state.selection.has_selection:
            # Separate selected from unselected
            unselected = [bp for bp in body_parts if not self._state.selection.is_selected(bp)]
            selected = [bp for bp in body_parts if self._state.selection.is_selected(bp)]
            
            # Draw unselected first, then selected
            draw_list = unselected + selected
        else:
            # Draw strictly by Z-order
            draw_list = body_parts
        
        for bp in draw_list:
            if not bp.visible:
                continue
            
            if bp.part_type == BodyPartType.ENTITY_REF:
                self._draw_entity_ref(painter, bp, depth + 1)
            else:
                # Draw Texture
                self._draw_body_part_texture(painter, bp)
            
            # Draw Selection Outline (Only checks top-level selection context)
            if self._state.selection.is_selected(bp):
                self._draw_selection_highlight(painter, bp)

    def _draw_entity_ref(self, painter: QPainter, bp, depth):
        if not bp.entity_ref:
            # Empty ref, maybe draw placeholder
            self._draw_placeholder(painter, bp, QColor(100, 50, 50, 128))
            return

        ref_entity = get_entity_manager().get_entity_def(bp.entity_ref)
        if not ref_entity:
            # Failed to load
            self._draw_placeholder(painter, bp, QColor(255, 0, 0, 128))
            return
            
        # Apply transform
        # We need to transform the painter to the body part's coordinate system
        painter.save()
        
        center_x = bp.position.x + bp.size.x / 2
        center_y = bp.position.y + bp.size.y / 2
        
        painter.translate(center_x, center_y)
        if bp.rotation != 0:
            painter.rotate(bp.rotation)
        if bp.pixel_scale != 1:
            painter.scale(bp.pixel_scale, bp.pixel_scale) 
        if bp.flip_x or bp.flip_y:
            sx = -1 if bp.flip_x else 1
            sy = -1 if bp.flip_y else 1
            painter.scale(sx, sy)
            
        # Apply Pivot Offset
        # This shifts the "Child Pivot" relative to the "BodyPart Center".
        painter.translate(bp.pivot_offset.x, bp.pivot_offset.y)
        
        # Ref entity is centered around ITS pivot.
        # But we are currently at the center of the BodyPart rect.
        # If we draw the Ref Entity at (0,0), its Pivot will be at the center of BodyPart.
        # This seems correct for "attaching" an object.
        
        # However, Ref Entity rendering (via _draw_body_parts) assumes coordinates are relative to Entity Pivot.
        # So drawing at (0,0) here means the Ref Entity's Pivot is co-located with our transformation origin.
        # Our transformation origin is the center of the BodyPart.
        # So: RefEntity.Pivot aligns with BodyPart.Center + PivotOffset.
        
        # Draw children
        self._draw_body_parts(painter, ref_entity, depth)
        
        painter.restore()

    def _draw_placeholder(self, painter: QPainter, bp, color):
        painter.setBrush(color)
        painter.setPen(QPen(QColor(150, 150, 170), 1 / self.zoom))
        painter.drawRect(QRectF(bp.position.x, bp.position.y, bp.size.x, bp.size.y))

    def _draw_body_part_texture(self, painter: QPainter, bp):
        if bp.texture_id:
            pixmap = self._texture_manager.get_texture(bp.texture_id)
            if pixmap:
                # Get UV rectangle in pixel coordinates
                tex_size = self._texture_manager.get_texture_size(bp.texture_id)
                if tex_size:
                    px_x, px_y, px_w, px_h = bp.uv_rect.get_pixel_coords(tex_size[0], tex_size[1])
                    sub_pixmap = pixmap.copy(px_x, px_y, px_w, px_h)
                    
                    # Apply flipping
                    if bp.flip_x or bp.flip_y:
                        flip_transform = QTransform()
                        if bp.flip_x:
                            flip_transform.scale(-1, 1)
                        if bp.flip_y:
                            flip_transform.scale(1, -1)
                        sub_pixmap = sub_pixmap.transformed(flip_transform)
                    
                    # Draw with rotation
                    render_width = bp.size.x * bp.pixel_scale
                    render_height = bp.size.y * bp.pixel_scale
                    
                    painter.save()
                    
                    self._apply_bodypart_transform(painter, bp)
                    
                    target_rect = QRectF(bp.position.x, bp.position.y, render_width, render_height)
                    painter.drawPixmap(target_rect, sub_pixmap, QRectF(sub_pixmap.rect()))
                    
                    painter.restore()
        else:
            # Placeholder for missing texture
            painter.save()
            self._apply_bodypart_transform(painter, bp)
            painter.drawRect(QRectF(bp.position.x, bp.position.y, bp.size.x, bp.size.y))
            painter.restore()

    def _draw_selection_highlight(self, painter: QPainter, bp):
        pen = QPen(QColor(100, 200, 255), 2 / self.zoom)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        
        painter.save()
        self._apply_bodypart_transform(painter, bp)
        painter.drawRect(QRectF(bp.position.x, bp.position.y, bp.size.x, bp.size.y))
        painter.restore()

    def _apply_bodypart_transform(self, painter: QPainter, bp):
        """Apply BodyPart's transform (Pivot + Rotation) to the painter state."""
        if bp.rotation != 0:
            pivot_world_x = bp.position.x + bp.pivot.x
            pivot_world_y = bp.position.y + bp.pivot.y
            
            painter.translate(pivot_world_x, pivot_world_y)
            painter.rotate(bp.rotation)
            painter.translate(-pivot_world_x, -pivot_world_y)
            
        # Ref-Entity Pivot Offset (Additional translation if it applies?)
        # Refer to Step 559: We added painter.translate(bp.pivot_offset.x, ...) for References.
        # Ideally that should be part of this transform IF it applies to all.
        # But 'pivot_offset' is specifically for aligning CHILD Entity.
        # It's an internal render offset, not a "Self Transform".
        # So we leave it as specific handling for Ref Entity rendering logic below.

    def _draw_hitboxes(self, painter: QPainter, entity):
        # Draw BodyPart Hitboxes
        for bp in entity.body_parts:
            if not bp.visible: continue
            
            # Logic from ViewportWidget: "Only draw hitboxes if this is the selected body part, or no body part is selected"
            # We can replicate this behavior or show all.
            has_selection = self._state.selection.has_selection
            is_selected = self._state.selection.is_selected(bp)
            
            if not has_selection or is_selected:
                painter.save()
                self._apply_bodypart_transform(painter, bp)
                for hitbox in bp.hitboxes:
                    # Pass 0,0 offset because transform handles position
                    self._draw_single_hitbox(painter, hitbox, Vec2(0, 0))
                painter.restore()
                    
        # Draw Entity Hitboxes
        if hasattr(entity, 'entity_hitboxes'):
            for hitbox in entity.entity_hitboxes:
                self._draw_single_hitbox(painter, hitbox, entity.pivot)

    def _draw_single_hitbox(self, painter: QPainter, hitbox, offset: Vec2):
        if not hitbox.enabled:
            return
            
        colors = {
            "collision": QColor(255, 100, 100, 100),
            "damage": QColor(255, 200, 100, 100),
            "trigger": QColor(100, 255, 100, 100)
        }
        color = colors.get(hitbox.hitbox_type, QColor(200, 200, 200, 100))
        
        painter.setBrush(color)
        
        is_selected = (hitbox == self._state.selection.selected_hitbox)
        
        if is_selected:
            painter.setPen(QPen(QColor(255, 255, 100), 2 / self.zoom))
        else:
            painter.setPen(QPen(color.darker(150), 1 / self.zoom))
        
        x = int(offset.x + hitbox.x)
        y = int(offset.y + hitbox.y)
        
        if hitbox.shape == HitboxShape.CIRCLE:
             # Draw Circle
             # x,y is Top-Left of bounding box? Or Center?
             # Let's assume Middle for Circle usually, BUT for consistency with Rect (x,y=TopLeft), let's stick to Top-Left?
             # User requested "only radius".
             # If I toggle between Rect/Circle, position shouldn't jump wildly.
             # So x,y as Top-Left of bounding box is safest transition.
             
             r = hitbox.radius
             # Center x,y would be x+r, y+r if x,y is top-left.
             # painter.drawEllipse(center, r, r)
             
             cx = x + r
             cy = y + r
             painter.drawEllipse(QPointF(cx, cy), r, r)
             
             # Logical Rect for handles/selection
             rect = QRect(x, y, r*2, r*2)
        else:
             # Rectangle
             rect = QRect(x, y, hitbox.width, hitbox.height)
             painter.drawRect(rect)
        
        # Draw handles if selected?
        # Maybe let tool handle this? Or renderer draws if selected.
        if is_selected:
            self._draw_resize_handles(painter, rect)

    def _draw_resize_handles(self, painter: QPainter, rect: QRect):
        handle_size = 10 / self.zoom
        painter.setBrush(QColor(255, 255, 100))
        painter.setPen(QPen(QColor(100, 100, 100), 1 / self.zoom))
        
        # Use float coordinates for precise handle placement (matching interaction logic)
        # rect is integer QRect, need to be careful with -1 offset of topRight/bottomRight
        # We want handles at exact bounds: x, x+w, y, y+h
        
        l = rect.x()
        r = rect.x() + rect.width() # Not width()-1
        t = rect.y()
        b = rect.y() + rect.height()
        
        corners = [
            QPointF(l, t),
            QPointF(r, t),
            QPointF(l, b),
            QPointF(r, b)
        ]
        
        for pt in corners:
            painter.drawEllipse(pt, handle_size, handle_size)

    def _draw_pivot(self, painter: QPainter, entity):
        pivot_size = 10 / self.zoom
        painter.setPen(QPen(QColor(255, 255, 0), 2 / self.zoom))
        painter.drawLine(entity.pivot.x - pivot_size, entity.pivot.y, entity.pivot.x + pivot_size, entity.pivot.y)
        painter.drawLine(entity.pivot.x, entity.pivot.y - pivot_size, entity.pivot.x, entity.pivot.y + pivot_size)

    def _draw_grid(self, painter: QPainter, view_rect: QRectF):
        grid_size = self._state.grid_size
        if grid_size <= 0:
            return
            
        left = int(view_rect.left())
        right = int(view_rect.right())
        top = int(view_rect.top())
        bottom = int(view_rect.bottom())
        
        # Calculate steps
        start_x = (left // grid_size) * grid_size
        start_y = (top // grid_size) * grid_size
        
        # Configuration
        # Determine grid color based on background (assumed dark)
        grid_color = QColor(60, 60, 60)
        origin_color = QColor(80, 80, 80)
        
        lines = []
        origin_lines = []
        
        # Vertical lines
        x = start_x
        while x <= right + grid_size:
            line = QLineF(x, top, x, bottom)
            if x == 0:
                origin_lines.append(line)
            else:
                lines.append(line)
            x += grid_size
            
        # Horizontal lines
        y = start_y
        while y <= bottom + grid_size:
            line = QLineF(left, y, right, y)
            if y == 0:
                origin_lines.append(line)
            else:
                lines.append(line)
            y += grid_size
            
        # Draw standard grid
        painter.setPen(QPen(grid_color, 1 / self.zoom))
        painter.drawLines(lines)
        
        # Draw origin lines (slightly brighter)
        if origin_lines:
            painter.setPen(QPen(origin_color, 2 / self.zoom))
            painter.drawLines(origin_lines)

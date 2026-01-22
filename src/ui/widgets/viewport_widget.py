"""
2D Viewport Widget for Entity Editor.

Interactive preview widget that displays the entity with all body parts,
supports selection, drag-and-drop positioning, and visual feedback.
"""

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QPointF, QRectF, Signal, QPoint
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QPainterPath, QTransform
from typing import Optional, List, Tuple
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.data import Entity, BodyPart, Hitbox, Vec2
from src.rendering import get_texture_manager
from src.core import get_signal_hub


class ViewportWidget(QWidget):
    """
    Interactive 2D viewport for visualizing and editing entities.
    
    Features:
    - Displays entity with all body parts and textures
    - Interactive selection and manipulation
    - Drag-and-drop for repositioning
    - Visual feedback for selected items
    - Grid and coordinate display
    """
    
    # Signals
    selection_changed = Signal(object)  # Emits selected BodyPart or None
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # State
        self._entity: Optional[Entity] = None
        self._selected_bodypart: Optional[BodyPart] = None
        self._selected_hitbox: Optional[Hitbox] = None
        
        # View transform
        self._zoom = 1.0
        self._pan_offset = QPointF(0, 0)
        self._view_center = QPointF(0, 0)
        
        # Interaction state
        self._is_dragging = False
        self._drag_start_pos = QPointF()
        self._drag_start_bp_pos = Vec2()
        self._is_panning = False
        self._pan_start_pos = QPointF()
        
        # Hitbox editing state
        self._hitbox_edit_mode = False
        self._dragging_hitbox = None
        self._drag_start_hitbox_pos = Vec2()
        self._dragging_hitbox_parent = None
        self._resize_edge = None  # 'left', 'right', 'top', 'bottom', 'tl', 'tr', 'bl', 'br'
        self._drag_start_hitbox_size = Vec2()
        
        # Display options
        self._show_grid = True
        self._show_pivot = True
        self._show_hitboxes = True
        
        # Grid snap
        self._snap_value = 0.0  # 0 = off
        
        # Setup
        self.setMinimumSize(400, 400)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Connect to signal hub
        self._signal_hub = get_signal_hub()
        self._signal_hub.entity_loaded.connect(self.set_entity)
        self._signal_hub.bodypart_selected.connect(self._on_bodypart_selected)
        self._signal_hub.bodypart_modified.connect(self._on_bodypart_modified)
        self._signal_hub.bodypart_added.connect(lambda _: self.update())
        self._signal_hub.bodypart_removed.connect(lambda _: self.update())
        self._signal_hub.bodypart_reordered.connect(self.update)
        self._signal_hub.snap_value_changed.connect(self._on_snap_value_changed)
        self._signal_hub.hitbox_edit_mode_changed.connect(self._on_hitbox_edit_mode_changed)
        self._signal_hub.hitbox_selected.connect(self._on_hitbox_selected)
    
    def set_entity(self, entity: Optional[Entity]):
        """Set the entity to display."""
        self._entity = entity
        self._selected_bodypart = None
        self._selected_hitbox = None
        
        # Center view on entity pivot
        if entity:
            self._view_center = QPointF(entity.pivot.x, entity.pivot.y)
        
        self.update()
    
    def get_entity(self) -> Optional[Entity]:
        """Get the current entity."""
        return self._entity
    
    def set_zoom(self, zoom: float):
        """Set viewport zoom level."""
        self._zoom = max(0.1, min(10.0, zoom))
        self.update()
    
    def _screen_to_world(self, screen_pos) -> QPointF:
        """Convert screen coordinates to world coordinates."""
        center = QPointF(self.width() / 2, self.height() / 2)
        # Handle both QPoint and QPointF
        if isinstance(screen_pos, QPoint):
            screen_pos = QPointF(screen_pos)
        offset_x = screen_pos.x() - center.x()
        offset_y = screen_pos.y() - center.y()
        world_x = self._view_center.x() + offset_x / self._zoom
        world_y = self._view_center.y() + offset_y / self._zoom
        return QPointF(world_x, world_y)
    
    def _world_to_screen(self, world_pos: QPointF) -> QPointF:
        """Convert world coordinates to screen coordinates."""
        center = QPointF(self.width() / 2, self.height() / 2)
        offset_x = (world_pos.x() - self._view_center.x()) * self._zoom
        offset_y = (world_pos.y() - self._view_center.y()) * self._zoom
        return QPointF(center.x() + offset_x, center.y() + offset_y)
    
    def _get_bodypart_at(self, world_pos: QPointF) -> Optional[BodyPart]:
        """Find body part at world position (reverse z-order for picking)."""
        if not self._entity:
            return None
        
        # Check body parts in reverse z-order (top to bottom)
        sorted_parts = sorted(self._entity.body_parts, key=lambda bp: bp.z_order, reverse=True)
        
        for bp in sorted_parts:
            if not bp.visible:
                continue
            
            # Check if point is inside body part bounds (accounting for pixel_scale)
            left = bp.position.x
            top = bp.position.y
            right = left + (bp.size.x * bp.pixel_scale)
            bottom = top + (bp.size.y * bp.pixel_scale)
            
            if left <= world_pos.x() <= right and top <= world_pos.y() <= bottom:
                return bp
        
        return None
    
    def _get_hitbox_at(self, world_pos: QPointF) -> Tuple[Optional[Hitbox], Optional[BodyPart]]:
        """Find hitbox at world position. Returns (hitbox, parent_bodypart)."""
        if not self._entity:
            return None, None
        
        # Only check hitboxes from the selected body part if one is selected
        if self._selected_bodypart:
            parts_to_check = [self._selected_bodypart]
        else:
            # Check all body parts in reverse z-order
            parts_to_check = sorted(self._entity.body_parts, key=lambda bp: bp.z_order, reverse=True)
        
        for bp in parts_to_check:
            if not bp.visible:
                continue
            
            for hitbox in bp.hitboxes:
                # Calculate absolute hitbox position
                x = bp.position.x + hitbox.position.x
                y = bp.position.y + hitbox.position.y
                
                if x <= world_pos.x() <= x + hitbox.size.x and y <= world_pos.y() <= y + hitbox.size.y:
                    return hitbox, bp
        
        return None, None
    
    def _get_hitbox_edge(self, hitbox: Hitbox, parent_bp: BodyPart, world_pos: QPointF) -> Optional[str]:
        """Determine if click is near edge/corner for resizing. Returns edge identifier or None."""
        grab_distance = 8 / self._zoom  # Pixels in world space
        
        # Calculate absolute hitbox position
        x = parent_bp.position.x + hitbox.position.x
        y = parent_bp.position.y + hitbox.position.y
        w = hitbox.size.x
        h = hitbox.size.y
        
        wx = world_pos.x()
        wy = world_pos.y()
        
        # Check corners first (priority over edges)
        if abs(wx - x) < grab_distance and abs(wy - y) < grab_distance:
            return 'tl'  # top-left
        if abs(wx - (x + w)) < grab_distance and abs(wy - y) < grab_distance:
            return 'tr'  # top-right
        if abs(wx - x) < grab_distance and abs(wy - (y + h)) < grab_distance:
            return 'bl'  # bottom-left
        if abs(wx - (x + w)) < grab_distance and abs(wy - (y + h)) < grab_distance:
            return 'br'  # bottom-right
        
        # Check edges
        if abs(wx - x) < grab_distance and y <= wy <= y + h:
            return 'left'
        if abs(wx - (x + w)) < grab_distance and y <= wy <= y + h:
            return 'right'
        if abs(wy - y) < grab_distance and x <= wx <= x + w:
            return 'top'
        if abs(wy - (y + h)) < grab_distance and x <= wx <= x + w:
            return 'bottom'
        
        return None
    
    def paintEvent(self, event):
        """Paint the viewport."""
        if not self.isVisible():
            return
            
        painter = QPainter(self)
        try:
            # Don't use smooth transform for pixel art - keep it crisp
            # painter.setRenderHint(QPainter.Antialiasing)
            # painter.setRenderHint(QPainter.SmoothPixmapTransform)
            
            # Fill background
            painter.fillRect(self.rect(), QColor(45, 45, 48))
            
            # Setup world transform
            painter.save()
            center = QPointF(self.width() / 2, self.height() / 2)
            painter.translate(center)
            painter.scale(self._zoom, self._zoom)
            painter.translate(-self._view_center)
            
            # Draw grid
            if self._show_grid:
                self._draw_grid(painter)
            
            # Draw entity
            if self._entity:
                self._draw_entity(painter)
            
            painter.restore()
            
            # Draw UI overlay (in screen space)
            self._draw_ui_overlay(painter)
        finally:
            painter.end()
    
    def _draw_grid(self, painter: QPainter):
        """Draw background grid."""
        grid_size = 50
        pen = QPen(QColor(60, 60, 63), 1)
        painter.setPen(pen)
        
        # Calculate visible area
        top_left = self._screen_to_world(QPoint(0, 0))
        bottom_right = self._screen_to_world(QPoint(self.width(), self.height()))
        
        # Draw vertical lines
        start_x = int(top_left.x() / grid_size) * grid_size
        end_x = int(bottom_right.x() / grid_size) * grid_size
        for x in range(start_x, end_x + grid_size, grid_size):
            painter.drawLine(QPointF(x, top_left.y()), QPointF(x, bottom_right.y()))
        
        # Draw horizontal lines
        start_y = int(top_left.y() / grid_size) * grid_size
        end_y = int(bottom_right.y() / grid_size) * grid_size
        for y in range(start_y, end_y + grid_size, grid_size):
            painter.drawLine(QPointF(top_left.x(), y), QPointF(bottom_right.x(), y))
        
        # Draw axes
        pen = QPen(QColor(80, 80, 83), 2)
        painter.setPen(pen)
        painter.drawLine(QPointF(0, top_left.y()), QPointF(0, bottom_right.y()))
        painter.drawLine(QPointF(top_left.x(), 0), QPointF(bottom_right.x(), 0))
    
    def _draw_entity(self, painter: QPainter):
        """Draw the entity with all body parts."""
        # Draw pivot point
        if self._show_pivot:
            pivot_size = 10 / self._zoom
            painter.setPen(QPen(QColor(255, 100, 100), 2 / self._zoom))
            painter.setBrush(Qt.NoBrush)
            painter.drawLine(
                QPointF(self._entity.pivot.x - pivot_size, self._entity.pivot.y),
                QPointF(self._entity.pivot.x + pivot_size, self._entity.pivot.y)
            )
            painter.drawLine(
                QPointF(self._entity.pivot.x, self._entity.pivot.y - pivot_size),
                QPointF(self._entity.pivot.x, self._entity.pivot.y + pivot_size)
            )
        
        # Draw body parts in z-order
        sorted_parts = self._entity.get_sorted_body_parts()
        texture_manager = get_texture_manager()
        
        for bp in sorted_parts:
            if not bp.visible:
                continue
            
            # Draw body part
            if bp.texture_path:
                pixmap = texture_manager.get_texture(bp.texture_path)
                if pixmap:
                    # Get UV rectangle in pixel coordinates
                    tex_size = texture_manager.get_texture_size(bp.texture_path)
                    if tex_size:
                        px_x, px_y, px_w, px_h = bp.uv_rect.get_pixel_coords(tex_size[0], tex_size[1])
                        sub_pixmap = pixmap.copy(px_x, px_y, px_w, px_h)
                        
                        # Apply flipping
                        if bp.flip_x or bp.flip_y:
                            from PySide6.QtGui import QTransform
                            flip_transform = QTransform()
                            if bp.flip_x:
                                flip_transform.scale(-1, 1)
                            if bp.flip_y:
                                flip_transform.scale(1, -1)
                            sub_pixmap = sub_pixmap.transformed(flip_transform)
                        
                        # Draw with rotation
                        render_width = bp.size.x * bp.pixel_scale
                        render_height = bp.size.y * bp.pixel_scale
                        
                        if bp.rotation != 0:
                            # Save state and apply rotation transform
                            painter.save()
                            # Rotate around center of sprite
                            center_x = bp.position.x + render_width / 2
                            center_y = bp.position.y + render_height / 2
                            painter.translate(center_x, center_y)
                            painter.rotate(bp.rotation)
                            painter.translate(-center_x, -center_y)
                        
                        target_rect = QRectF(bp.position.x, bp.position.y, render_width, render_height)
                        painter.drawPixmap(target_rect, sub_pixmap, QRectF(sub_pixmap.rect()))
                        
                        if bp.rotation != 0:
                            painter.restore()
            else:
                # Draw placeholder rectangle
                painter.setBrush(QColor(100, 100, 120, 128))
                painter.setPen(QPen(QColor(150, 150, 170), 1 / self._zoom))
                painter.drawRect(QRectF(bp.position.x, bp.position.y, bp.size.x, bp.size.y))
            
            # Draw selection highlight
            if bp == self._selected_bodypart:
                pen = QPen(QColor(100, 200, 255), 2 / self._zoom)
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(QRectF(bp.position.x, bp.position.y, bp.size.x, bp.size.y))
            
            # Draw hitboxes (only for selected body part if one is selected)
            if self._show_hitboxes:
                # Only draw hitboxes if this is the selected body part, or no body part is selected
                if self._selected_bodypart is None or bp == self._selected_bodypart:
                    for hitbox in bp.hitboxes:
                        self._draw_hitbox(painter, hitbox, bp.position)
        
        # Draw entity-level hitboxes
        if self._show_hitboxes and hasattr(self._entity, 'entity_hitboxes'):
            for hitbox in self._entity.entity_hitboxes:
                self._draw_hitbox(painter, hitbox, self._entity.pivot)
    
    def _draw_hitbox(self, painter: QPainter, hitbox: Hitbox, offset: Vec2):
        """Draw a hitbox."""
        # Choose color based on type
        colors = {
            "collision": QColor(255, 100, 100, 100),
            "damage": QColor(255, 200, 100, 100),
            "trigger": QColor(100, 255, 100, 100)
        }
        color = colors.get(hitbox.hitbox_type, QColor(200, 200, 200, 100))
        
        painter.setBrush(color)
        
        # Highlight selected hitbox
        if hitbox == self._selected_hitbox:
            painter.setPen(QPen(QColor(255, 255, 100), 2 / self._zoom))
        else:
            painter.setPen(QPen(color.darker(150), 1 / self._zoom))
        
        x = offset.x + hitbox.position.x
        y = offset.y + hitbox.position.y
        painter.drawRect(QRectF(x, y, hitbox.size.x, hitbox.size.y))
        
        # Draw resize handles if selected and in edit mode
        if hitbox == self._selected_hitbox and self._hitbox_edit_mode:
            handle_size = 6 / self._zoom
            painter.setBrush(QColor(255, 255, 100))
            painter.setPen(QPen(QColor(100, 100, 100), 1 / self._zoom))
            
            # Corner handles
            painter.drawEllipse(QPointF(x, y), handle_size, handle_size)
            painter.drawEllipse(QPointF(x + hitbox.size.x, y), handle_size, handle_size)
            painter.drawEllipse(QPointF(x, y + hitbox.size.y), handle_size, handle_size)
            painter.drawEllipse(QPointF(x + hitbox.size.x, y + hitbox.size.y), handle_size, handle_size)
    
    def _draw_ui_overlay(self, painter: QPainter):
        """Draw UI overlay in screen space."""
        # Draw zoom indicator
        painter.setPen(QColor(200, 200, 200))
        painter.drawText(10, 20, f"Zoom: {self._zoom:.2f}x")
        
        # Draw coordinates if dragging
        if self._is_dragging and self._selected_bodypart:
            pos_text = f"Position: ({self._selected_bodypart.position.x:.1f}, {self._selected_bodypart.position.y:.1f})"
            painter.drawText(10, 40, pos_text)
    
    def mousePressEvent(self, event):
        """Handle mouse press."""
        if event.button() == Qt.LeftButton:
            world_pos = self._screen_to_world(QPointF(event.pos()))
            
            # Check for hitbox interaction if in edit mode
            if self._hitbox_edit_mode:
                hitbox, parent_bp = self._get_hitbox_at(world_pos)
                
                if hitbox:
                    # Check if clicking near edge for resize
                    edge = self._get_hitbox_edge(hitbox, parent_bp, world_pos)
                    
                    if edge:
                        # Start resizing
                        self._dragging_hitbox = hitbox
                        self._dragging_hitbox_parent = parent_bp
                        self._resize_edge = edge
                        self._drag_start_pos = world_pos
                        self._drag_start_hitbox_pos = Vec2(hitbox.position.x, hitbox.position.y)
                        self._drag_start_hitbox_size = Vec2(hitbox.size.x, hitbox.size.y)
                        self._selected_hitbox = hitbox
                        self._signal_hub.notify_hitbox_selected(hitbox)
                    else:
                        # Start dragging hitbox
                        self._dragging_hitbox = hitbox
                        self._dragging_hitbox_parent = parent_bp
                        self._resize_edge = None
                        self._drag_start_pos = world_pos
                        self._drag_start_hitbox_pos = Vec2(hitbox.position.x, hitbox.position.y)
                        self._selected_hitbox = hitbox
                        self._signal_hub.notify_hitbox_selected(hitbox)
                    self.update()
                    return
                else:
                    # Deselect hitbox
                    self._selected_hitbox = None
                    self._signal_hub.notify_hitbox_selected(None)
                    self.update()
            
            # Normal body part interaction
            clicked_bp = self._get_bodypart_at(world_pos)
            
            if clicked_bp:
                # Start dragging body part
                self._selected_bodypart = clicked_bp
                self._is_dragging = True
                self._drag_start_pos = world_pos
                self._drag_start_bp_pos = Vec2(clicked_bp.position.x, clicked_bp.position.y)
                self._signal_hub.notify_bodypart_selected(clicked_bp)
                self.update()
            else:
                # Deselect
                self._selected_bodypart = None
                self._signal_hub.notify_bodypart_selected(None)
                self.update()
        
        elif event.button() == Qt.MiddleButton or (event.button() == Qt.RightButton):
            # Start panning
            self._is_panning = True
            self._pan_start_pos = QPointF(event.pos())
            self._pan_start_view = QPointF(self._view_center)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move."""
        # Update cursor based on hover state (only when not dragging)
        if not self._dragging_hitbox and not self._is_dragging and not self._is_panning:
            self._update_cursor_for_hover(QPointF(event.pos()))
        
        if self._dragging_hitbox:
            # Drag or resize hitbox
            world_pos = self._screen_to_world(QPointF(event.pos()))
            delta = world_pos - self._drag_start_pos
            
            if self._resize_edge:
                # Resize hitbox
                new_x = self._drag_start_hitbox_pos.x
                new_y = self._drag_start_hitbox_pos.y
                new_w = self._drag_start_hitbox_size.x
                new_h = self._drag_start_hitbox_size.y
                
                # Apply delta based on edge
                if self._resize_edge in ['left', 'tl', 'bl']:
                    new_x += delta.x()
                    new_w -= delta.x()
                if self._resize_edge in ['right', 'tr', 'br']:
                    new_w += delta.x()
                if self._resize_edge in ['top', 'tl', 'tr']:
                    new_y += delta.y()
                    new_h -= delta.y()
                if self._resize_edge in ['bottom', 'bl', 'br']:
                    new_h += delta.y()
                
                # Round to pixels
                new_x = round(new_x)
                new_y = round(new_y)
                new_w = round(new_w)
                new_h = round(new_h)
                
                # Apply grid snap
                if self._snap_value > 0:
                    new_x = self._snap_to_grid(new_x)
                    new_y = self._snap_to_grid(new_y)
                    new_w = self._snap_to_grid(new_w)
                    new_h = self._snap_to_grid(new_h)
                
                # Minimum size
                new_w = max(1, new_w)
                new_h = max(1, new_h)
                
                self._dragging_hitbox.position.x = new_x
                self._dragging_hitbox.position.y = new_y
                self._dragging_hitbox.size.x = new_w
                self._dragging_hitbox.size.y = new_h
            else:
                # Move hitbox
                new_x = self._drag_start_hitbox_pos.x + delta.x()
                new_y = self._drag_start_hitbox_pos.y + delta.y()
                
                # Round to pixels
                new_x = round(new_x)
                new_y = round(new_y)
                
                # Apply grid snap
                if self._snap_value > 0:
                    new_x = self._snap_to_grid(new_x)
                    new_y = self._snap_to_grid(new_y)
                
                self._dragging_hitbox.position.x = new_x
                self._dragging_hitbox.position.y = new_y
            
            self._signal_hub.notify_hitbox_modified(self._dragging_hitbox)
            self.update()
        
        elif self._is_dragging and self._selected_bodypart:
            # Drag body part
            world_pos = self._screen_to_world(QPointF(event.pos()))
            delta = world_pos - self._drag_start_pos
            
            new_x = self._drag_start_bp_pos.x + delta.x()
            new_y = self._drag_start_bp_pos.y + delta.y()
            
            # Always round to pixel precision
            new_x = round(new_x)
            new_y = round(new_y)
            
            # Apply grid snapping if snap value is set (always active, no Ctrl needed)
            if self._snap_value > 0:
                new_x = self._snap_to_grid(new_x)
                new_y = self._snap_to_grid(new_y)
            
            self._selected_bodypart.position.x = new_x
            self._selected_bodypart.position.y = new_y
            
            self._signal_hub.notify_bodypart_modified(self._selected_bodypart)
            self.update()
        
        elif self._is_panning:
            # Pan view
            event_pos = QPointF(event.pos())
            delta_x = event_pos.x() - self._pan_start_pos.x()
            delta_y = event_pos.y() - self._pan_start_pos.y()
            self._view_center = QPointF(
                self._pan_start_view.x() - delta_x / self._zoom,
                self._pan_start_view.y() - delta_y / self._zoom
            )
            self.update()
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release."""
        if event.button() == Qt.LeftButton:
            self._is_dragging = False
            self._dragging_hitbox = None
            self._resize_edge = None
        elif event.button() == Qt.MiddleButton or event.button() == Qt.RightButton:
            self._is_panning = False
    
    def wheelEvent(self, event):
        """Handle mouse wheel for zooming."""
        delta = event.angleDelta().y()
        zoom_factor = 1.1 if delta > 0 else 0.9
        self._zoom *= zoom_factor
        self._zoom = max(0.1, min(10.0, self._zoom))
        self.update()
    
    def _on_bodypart_selected(self, bodypart):
        """Handle external body part selection."""
        if bodypart != self._selected_bodypart:
            self._selected_bodypart = bodypart
            self.update()
    
    def _on_bodypart_modified(self, bodypart):
        """Handle external body part modification."""
        self.update()
    
    def _snap_to_grid(self, value: float) -> float:
        """Snap a value to the current grid if snap is enabled."""
        if self._snap_value <= 0:
            return value
        return round(value / self._snap_value) * self._snap_value
    
    def _on_snap_value_changed(self, snap_value: float):
        """Handle snap value change from signal hub."""
        self._snap_value = snap_value
    
    def _on_hitbox_edit_mode_changed(self, enabled: bool):
        """Handle hitbox edit mode toggle."""
        self._hitbox_edit_mode = enabled
        self.update()
    
    def _on_hitbox_selected(self, hitbox):
        """Handle external hitbox selection."""
        if hitbox != self._selected_hitbox:
            self._selected_hitbox = hitbox
            self.update()
    
    def _update_cursor_for_hover(self, screen_pos: QPointF):
        """Update cursor based on what's under the mouse."""
        if not self._hitbox_edit_mode or not self._entity:
            self.setCursor(Qt.ArrowCursor)
            return
        
        world_pos = self._screen_to_world(screen_pos)
        hitbox, parent_bp = self._get_hitbox_at(world_pos)
        
        if hitbox:
            edge = self._get_hitbox_edge(hitbox, parent_bp, world_pos)
            
            if edge:
                # Set resize cursor based on edge
                cursor_map = {
                    'tl': Qt.SizeFDiagCursor,  # top-left: diagonal ↖↘
                    'tr': Qt.SizeBDiagCursor,  # top-right: diagonal ↗↙
                    'bl': Qt.SizeBDiagCursor,  # bottom-left: diagonal ↗↙
                    'br': Qt.SizeFDiagCursor,  # bottom-right: diagonal ↖↘
                    'left': Qt.SizeHorCursor,  # left: horizontal ↔
                    'right': Qt.SizeHorCursor, # right: horizontal ↔
                    'top': Qt.SizeVerCursor,   # top: vertical ↕
                    'bottom': Qt.SizeVerCursor # bottom: vertical ↕
                }
                self.setCursor(cursor_map.get(edge, Qt.ArrowCursor))
            else:
                # Over hitbox but not near edge - show move cursor
                self.setCursor(Qt.SizeAllCursor)
        else:
            # Not over any hitbox
            self.setCursor(Qt.ArrowCursor)

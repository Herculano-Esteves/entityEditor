"""
2D Viewport Widget for Entity Editor.

Interactive preview widget that displays the entity with all body parts,
supports selection, drag-and-drop positioning, and visual feedback.
"""

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QPointF, QRectF, QRect, Signal, QPoint
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QPainterPath, QTransform
from typing import Optional, List, Tuple
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.data import Entity, BodyPart, Hitbox, Vec2
from src.rendering import get_texture_manager
from src.core import get_signal_hub, MoveBodyPartCommand, MoveHitboxCommand


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
        self._selected_bodypart: Optional[BodyPart] = None  # Primary selection
        self._selected_bodyparts: List[BodyPart] = []  # Multi-selection
        self._selected_hitbox: Optional[Hitbox] = None
        
        # View transform
        self._zoom = 1.0
        self._pan_offset = QPointF(0, 0)
        self._view_center = QPointF(0, 0)
        
        # Interaction state
        self._is_dragging = False
        self._drag_start_pos = QPointF()
        self._drag_start_bp_pos = Vec2()
        self._drag_start_positions = {}  # Dict[BodyPart, Vec2] for multi-selection drag
        self._is_panning = False
        self._pan_start_pos = QPointF()
        self._pan_start_view = QPointF()
        # Hitbox editing state
        self._hitbox_edit_mode = False
        self._dragging_hitbox = None
        self._drag_start_hitbox_pos = Vec2()
        self._dragging_hitbox_parent = None
        self._resize_edge = None  # 'left', 'right', 'top', 'bottom', 'tl', 'tr', 'bl', 'br'
        self._drag_start_hitbox_size = Vec2()
        
        # Rectangle selection state
        self._rect_selecting = False
        self._rect_start_pos: Optional[QPointF] = None
        self._rect_current_pos: Optional[QPointF] = None
        
        # Z-order override for editing
        self._show_selected_above = True  # Show selected bodypart above others while editing
        
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
        self._signal_hub.bodyparts_selection_changed.connect(self._on_bodyparts_selection_changed)
        self._signal_hub.bodypart_modified.connect(self._on_bodypart_modified)
        self._signal_hub.bodypart_added.connect(lambda _: self.update())
        self._signal_hub.bodypart_removed.connect(lambda _: self.update())
        self._signal_hub.bodypart_reordered.connect(self.update)
        self._signal_hub.snap_value_changed.connect(self._on_snap_value_changed)
        self._signal_hub.hitbox_edit_mode_changed.connect(self._on_hitbox_edit_mode_changed)
        self._signal_hub.hitbox_selected.connect(self._on_hitbox_selected)
        self._signal_hub.hitbox_modified.connect(lambda _: self.update())  # Critical: repaint when hitbox modified from UI
        self._signal_hub.bodypart_show_above_changed.connect(self._on_show_above_changed)
        
        # History manager (will be set when entity loads)
        self._history_manager = None
    
    def set_entity(self, entity: Optional[Entity]):
        """Set the entity to display."""
        self._entity = entity
        self._selected_bodypart = None
        self._selected_hitbox = None
        
        # Get history manager from parent window
        parent_window = self.window()
        if hasattr(parent_window, 'get_history_manager'):
            self._history_manager = parent_window.get_history_manager()
        
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
                # Skip disabled hitboxes
                if not hitbox.enabled:
                    continue
                
                # Calculate absolute hitbox position
                # Hitbox uses integer pixel coordinates
                x = int(bp.position.x + hitbox.x)
                y = int(bp.position.y + hitbox.y)
                
                if x <= world_pos.x() <= x + hitbox.width and y <= world_pos.y() <= y + hitbox.height:
                    return hitbox, bp
        
        return None, None
    
    def _get_hitbox_edge(self, hitbox: Hitbox, parent_bp: BodyPart, world_pos: QPointF) -> Optional[str]:
        """Determine if click is near edge/corner for resizing. Returns edge identifier or None."""
        grab_distance = 8 / self._zoom  # Pixels in world space
        
        # Calculate absolute hitbox position
        # Hitbox uses integer pixel coordinates
        x = int(parent_bp.position.x + hitbox.x)
        y = int(parent_bp.position.y + hitbox.y)
        w = hitbox.width
        h = hitbox.height
        
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
                
            # Draw selection rectangle
            if self._rect_selecting and self._rect_start_pos and self._rect_current_pos:
                self._draw_selection_rect(painter)
            
            painter.restore()
            
            # Draw UI overlay (in screen space)
            self._draw_ui_overlay(painter)
        finally:
            painter.end()

    def _draw_selection_rect(self, painter: QPainter):
        """Draw the selection rectangle."""
        if not self._rect_start_pos or not self._rect_current_pos:
            return
            
        # Define rectangle
        top_left = QPointF(
            min(self._rect_start_pos.x(), self._rect_current_pos.x()),
            min(self._rect_start_pos.y(), self._rect_current_pos.y())
        )
        width = abs(self._rect_current_pos.x() - self._rect_start_pos.x())
        height = abs(self._rect_current_pos.y() - self._rect_start_pos.y())
        rect = QRectF(top_left.x(), top_left.y(), width, height)
        
        # Draw rectangle
        color = QColor(100, 200, 255, 60)  # Semi-transparent blue
        border_color = QColor(100, 200, 255, 200)
        
        painter.setBrush(QBrush(color))
        # Use constant width pen regardless of zoom
        painter.setPen(QPen(border_color, 1 / self._zoom, Qt.SolidLine))
        painter.drawRect(rect)
        
    def _finalize_rect_selection(self):
        """Select all body parts within the selection rectangle."""
        if not self._rect_start_pos or not self._rect_current_pos:
            return
            
        # Define selection rect
        left = min(self._rect_start_pos.x(), self._rect_current_pos.x())
        top = min(self._rect_start_pos.y(), self._rect_current_pos.y())
        right = max(self._rect_start_pos.x(), self._rect_current_pos.x())
        bottom = max(self._rect_start_pos.y(), self._rect_current_pos.y())
        
        # Find intersecting body parts
        selected = []
        if self._entity:
            for bp in self._entity.body_parts:
                if not bp.visible:
                    continue
                
                # Check intersection
                bp_left = bp.position.x
                bp_top = bp.position.y
                bp_right = bp_left + (bp.size.x * bp.pixel_scale)
                bp_bottom = bp_top + (bp.size.y * bp.pixel_scale)
                
                # Simple AABB intersection
                if (left < bp_right and right > bp_left and
                    top < bp_bottom and bottom > bp_top):
                    selected.append(bp)
        
        # Update selection
        self._selected_bodyparts = selected
        
        # Update primary selection (last selected or first in list)
        if selected:
            self._selected_bodypart = selected[0]
        else:
            self._selected_bodypart = None
            
        # Notify
        self._signal_hub.notify_bodyparts_selection_changed(self._selected_bodyparts)
    
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
        
        # If show-above is enabled and there's a selected bodypart, render it last
        parts_to_render = sorted_parts
        if self._show_selected_above and self._selected_bodypart and self._selected_bodypart in sorted_parts:
            # Remove selected part from list and add it at the end
            parts_to_render = [bp for bp in sorted_parts if bp != self._selected_bodypart]
            parts_to_render.append(self._selected_bodypart)
        
        for bp in parts_to_render:
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
        # Skip disabled hitboxes
        if not hitbox.enabled:
            return
        
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
        
        # Hitbox uses integer pixel coordinates
        x = int(offset.x + hitbox.x)
        y = int(offset.y + hitbox.y)
        
        rect = QRect(x, y, hitbox.width, hitbox.height)
        painter.drawRect(rect)
        
        # Draw resize handles if selected and in edit mode
        if hitbox == self._selected_hitbox and self._hitbox_edit_mode:
            handle_size = 6 / self._zoom
            painter.setBrush(QColor(255, 255, 100))
            painter.setPen(QPen(QColor(100, 100, 100), 1 / self._zoom))
            
            # Corner handles
            painter.drawEllipse(QPointF(x, y), handle_size, handle_size)
            painter.drawEllipse(QPointF(x + hitbox.width, y), handle_size, handle_size)
            painter.drawEllipse(QPointF(x, y + hitbox.height), handle_size, handle_size)
            painter.drawEllipse(QPointF(x + hitbox.width, y + hitbox.height), handle_size, handle_size)
    
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
            modifiers = event.modifiers()
            
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
                        self._drag_start_hitbox_pos = Vec2(hitbox.x, hitbox.y)
                        self._drag_start_hitbox_size = Vec2(hitbox.width, hitbox.height)
                        self._selected_hitbox = hitbox
                        self._signal_hub.notify_hitbox_selected(hitbox)
                        
                        if self._history_manager:
                            self._history_manager.begin_change("Resize Hitbox")
                    else:
                        # Start dragging hitbox
                        self._dragging_hitbox = hitbox
                        self._dragging_hitbox_parent = parent_bp
                        self._resize_edge = None
                        self._drag_start_pos = world_pos
                        self._drag_start_hitbox_pos = Vec2(hitbox.x, hitbox.y)
                        self._selected_hitbox = hitbox
                        self._signal_hub.notify_hitbox_selected(hitbox)
                        
                        if self._history_manager:
                            self._history_manager.begin_change("Move Hitbox")
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
                # Handle Ctrl+click toggle
                if modifiers & Qt.ControlModifier:
                    # Toggle selection
                    if clicked_bp in self._selected_bodyparts:
                        self._selected_bodyparts.remove(clicked_bp)
                    else:
                        self._selected_bodyparts.append(clicked_bp)
                    
                    # Update primary selection
                    if self._selected_bodyparts:
                        self._selected_bodypart = self._selected_bodyparts[0]
                    else:
                        self._selected_bodypart = None
                    
                    # Notify panel to sync
                    self._signal_hub.notify_bodyparts_selection_changed(self._selected_bodyparts)
                    self.update()
                else:
                    # Normal click - check if clicking on already-selected bodypart
                    if clicked_bp in self._selected_bodyparts:
                        # Start dragging ALL selected bodyparts
                        self._is_dragging = True
                        self._drag_start_pos = world_pos
                        # Store start positions for ALL selected bodyparts using object ID as key
                        self._drag_start_positions = {}
                        for bp in self._selected_bodyparts:
                            self._drag_start_positions[id(bp)] = Vec2(bp.position.x, bp.position.y)
                        
                        if self._history_manager:
                            self._history_manager.begin_change("Move Body Parts")
                    else:
                        # Clicked on non-selected bodypart - select only this one
                        self._selected_bodypart = clicked_bp
                        self._selected_bodyparts = [clicked_bp]
                        self._is_dragging = True
                        self._drag_start_pos = world_pos
                        self._drag_start_positions = {id(clicked_bp): Vec2(clicked_bp.position.x, clicked_bp.position.y)}
                        self._signal_hub.notify_bodypart_selected(clicked_bp)
                        self._signal_hub.notify_bodyparts_selection_changed(self._selected_bodyparts)
                        
                        if self._history_manager:
                            self._history_manager.begin_change("Move Body Parts")
                    
                    self.update()
            else:
                # Clicked on empty space
                if not (modifiers & Qt.ControlModifier):
                    # Clear selection if not holding Ctrl
                    self._selected_bodypart = None
                    self._selected_bodyparts = []
                    self._signal_hub.notify_bodypart_selected(None)
                    self._signal_hub.notify_bodyparts_selection_changed([])
                
                # Start rectangle selection
                self._rect_selecting = True
                self._rect_start_pos = world_pos
                self._rect_current_pos = world_pos
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
            
        # Handle rectangle selection
        if self._rect_selecting:
            self._rect_current_pos = self._screen_to_world(QPointF(event.pos()))
            self.update()
            return
        
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
                
                # Snap to grid and convert to integers (combined operation)
                new_x = self._snap_to_grid_int(new_x)
                new_y = self._snap_to_grid_int(new_y)
                new_w = max(1, self._snap_to_grid_int(new_w))  # Enforce minimum size
                new_h = max(1, self._snap_to_grid_int(new_h))
                
                # Update hitbox with pixel-precise integer coordinates
                self._dragging_hitbox.x = new_x
                self._dragging_hitbox.y = new_y
                self._dragging_hitbox.width = new_w
                self._dragging_hitbox.height = new_h
            else:
                # Move hitbox
                new_x = self._drag_start_hitbox_pos.x + delta.x()
                new_y = self._drag_start_hitbox_pos.y + delta.y()
                
                # Snap to grid and convert to integers (combined operation)
                self._dragging_hitbox.x = self._snap_to_grid_int(new_x)
                self._dragging_hitbox.y = self._snap_to_grid_int(new_y)
            
            self._signal_hub.notify_hitbox_modified(self._dragging_hitbox)
            self.update()
        
        elif self._is_dragging and self._selected_bodyparts:
            # Drag body parts
            world_pos = self._screen_to_world(QPointF(event.pos()))
            delta = world_pos - self._drag_start_pos
            
            # Move ALL selected body part(s)
            for bp in self._selected_bodyparts:
                if id(bp) in self._drag_start_positions:
                    start_pos = self._drag_start_positions[id(bp)]
                    new_x = start_pos.x + delta.x()
                    new_y = start_pos.y + delta.y()
                    
                    # Snap to grid and convert to integers
                    bp.position.x = self._snap_to_grid_int(new_x)
                    bp.position.y = self._snap_to_grid_int(new_y)
                    
                    self._signal_hub.notify_bodypart_modified(bp)
            
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
            
            # Handle rectangle selection finalization
            if self._rect_selecting:
                self._rect_selecting = False
                self._finalize_rect_selection()
                self._rect_start_pos = None
                self._rect_current_pos = None
                self.update()
                return

            # Finish bodypart move (using state snapshot)
            if self._is_dragging and self._selected_bodyparts:
                if self._history_manager:
                    # Check if any position actually changed
                    changed = False
                    for bp in self._selected_bodyparts:
                        if id(bp) in self._drag_start_positions:
                            start_pos = self._drag_start_positions[id(bp)]
                            if bp.position.x != start_pos.x or bp.position.y != start_pos.y:
                                changed = True
                                break
                    
                    if changed:
                        self._history_manager.end_change()
                    else:
                        self._history_manager.cancel_change()
            
            # Finish hitbox move/resize (using state snapshot)
            if self._dragging_hitbox and self._history_manager:
                current_pos = Vec2(self._dragging_hitbox.x, self._dragging_hitbox.y)
                current_size = Vec2(self._dragging_hitbox.width, self._dragging_hitbox.height)
                
                # Check if position OR size changed
                if (current_pos.x != self._drag_start_hitbox_pos.x or 
                    current_pos.y != self._drag_start_hitbox_pos.y or
                    current_size.x != self._drag_start_hitbox_size.x or
                    current_size.y != self._drag_start_hitbox_size.y):
                    self._history_manager.end_change()
                else:
                    self._history_manager.cancel_change()
            
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
    
    def _on_bodyparts_selection_changed(self, selected_bodyparts: list):
        """Handle multi-selection change from panel."""
        self._selected_bodyparts = selected_bodyparts
        # Update primary selection to first in list
        if selected_bodyparts:
            self._selected_bodypart = selected_bodyparts[0]
        self.update()
    
    def _on_bodypart_modified(self, bodypart):
        """Handle external body part modification."""
        self.update()
    
    def _snap_to_grid(self, value: float) -> float:
        """Snap a value to the current grid if snap is enabled."""
        if self._snap_value <= 0:
            return value
        return round(value / self._snap_value) * self._snap_value
    
    def _snap_to_grid_int(self, value: float) -> int:
        """Snap value to grid (if enabled) and return as integer.
        
        This combines grid snapping and pixel rounding into a single operation,
        eliminating redundant int(round()) calls.
        """
        if self._snap_value > 0:
            return int(round(value / self._snap_value) * self._snap_value)
        return int(round(value))
    
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
    
    def _on_show_above_changed(self, enabled: bool):
        """Handle show-above-while-editing toggle."""
        self._show_selected_above = enabled
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

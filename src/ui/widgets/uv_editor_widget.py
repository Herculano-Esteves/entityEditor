"""
UV Editor Widget - Simplified viewport-style approach

Uses direct QPainter rendering like the main viewport widget.
No QGraphicsView, simpler and more reliable.
"""

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QPixmap, QWheelEvent, QMouseEvent
from typing import Optional
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.data import BodyPart
from src.rendering import get_texture_manager


class UVEditorWidget(QWidget):
    """
    Simple UV editor using direct painting (like ViewportWidget).
    
    Features:
    - Texture display with zoom/pan
    - Draggable UV rectangle
    - Resize by dragging edges/corners
    - Pixel-perfect snapping
    """
    
    # Signals
    uv_changed = Signal(object)  # Emits BodyPart when UV changes
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # State
        self._body_part: Optional[BodyPart] = None
        self._texture_pixmap: Optional[QPixmap] = None
        self._texture_width = 0
        self._texture_height = 0
        
        # View transform
        self._zoom = 1.0
        self._view_center = QPointF(0, 0)
        
        # Interaction state
        self._dragging_rect = False
        self._resizing = False
        self._resize_handle = None  # 'tl', 't', 'tr', 'r', 'br', 'b', 'bl', 'l'
        self._drag_start_pos = QPointF()
        self._drag_start_uv_rect = None
        
        # Panning
        self._is_panning = False
        self._pan_start_pos = QPointF()
        self._pan_start_view = QPointF()
        
        # Setup
        self.setMinimumSize(400, 400)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
    
    def set_body_part(self, body_part: Optional[BodyPart]):
        """Set the body part to edit."""
        self._body_part = body_part
        
        if body_part and body_part.texture_path:
            # Load texture
            texture_manager = get_texture_manager()
            self._texture_pixmap = texture_manager.get_texture(body_part.texture_path)
            
            if self._texture_pixmap:
                self._texture_width = self._texture_pixmap.width()
                self._texture_height = self._texture_pixmap.height()
                
                # Center view on texture
                self._view_center = QPointF(self._texture_width / 2, self._texture_height / 2)
                self._zoom = 1.0
        else:
            self._texture_pixmap = None
            self._texture_width = 0
            self._texture_height = 0
        
        self.update()
    
    def _screen_to_world(self, screen_pos: QPointF) -> QPointF:
        """Convert screen coordinates to texture coordinates."""
        center = QPointF(self.width() / 2, self.height() / 2)
        offset_x = screen_pos.x() - center.x()
        offset_y = screen_pos.y() - center.y()
        world_x = self._view_center.x() + offset_x / self._zoom
        world_y = self._view_center.y() + offset_y / self._zoom
        return QPointF(world_x, world_y)
    
    def _world_to_screen(self, world_pos: QPointF) -> QPointF:
        """Convert texture coordinates to screen coordinates."""
        center = QPointF(self.width() / 2, self.height() / 2)
        offset_x = (world_pos.x() - self._view_center.x()) * self._zoom
        offset_y = (world_pos.y() - self._view_center.y()) * self._zoom
        return QPointF(center.x() + offset_x, center.y() + offset_y)
    
    def _get_uv_rect_pixels(self) -> QRectF:
        """Get current UV rectangle in pixel coordinates."""
        if not self._body_part:
            return QRectF()
        
        uv = self._body_part.uv_rect
        x = uv.x * self._texture_width
        y = uv.y * self._texture_height
        w = uv.width * self._texture_width
        h = uv.height * self._texture_height
        return QRectF(x, y, w, h)
    
    def _set_uv_from_pixels(self, rect: QRectF):
        """Set UV from pixel rectangle (with snapping)."""
        if not self._body_part:
            return
        
        # Snap to pixels
        x = round(rect.x())
        y = round(rect.y())
        w = round(rect.width())
        h = round(rect.height())
        
        # Clamp to texture bounds
        x = max(0, min(x, self._texture_width))
        y = max(0, min(y, self._texture_height))
        w = max(1, min(w, self._texture_width - x))
        h = max(1, min(h, self._texture_height - y))
        
        # Convert to UV coordinates
        self._body_part.uv_rect.x = x / self._texture_width
        self._body_part.uv_rect.y = y / self._texture_height
        self._body_part.uv_rect.width = w / self._texture_width
        self._body_part.uv_rect.height = h / self._texture_height
        
        # Auto-resize body part
        self._body_part.size.x = int(w)
        self._body_part.size.y = int(h)
        
        self.uv_changed.emit(self._body_part)
        self.update()
    
    def _get_resize_handle(self, world_pos: QPointF) -> Optional[str]:
        """Get which resize handle is at position."""
        rect = self._get_uv_rect_pixels()
        if rect.isEmpty():
            return None
        
        # Larger grab distance for small rectangles
        # For small UV regions, use a larger grab zone so they're still resizable
        base_grab = 8 / self._zoom  # 8 pixels in screen space
        
        # If rect is small, increase grab distance
        if rect.width() < 30 or rect.height() < 30:
            grab_distance = max(15 / self._zoom, base_grab)
        else:
            grab_distance = base_grab
        
        # Corners
        if (abs(world_pos.x() - rect.left()) < grab_distance and 
            abs(world_pos.y() - rect.top()) < grab_distance):
            return 'tl'
        if (abs(world_pos.x() - rect.right()) < grab_distance and 
            abs(world_pos.y() - rect.top()) < grab_distance):
            return 'tr'
        if (abs(world_pos.x() - rect.left()) < grab_distance and 
            abs(world_pos.y() - rect.bottom()) < grab_distance):
            return 'bl'
        if (abs(world_pos.x() - rect.right()) < grab_distance and 
            abs(world_pos.y() - rect.bottom()) < grab_distance):
            return 'br'
        
        # Edges
        if (rect.left() < world_pos.x() < rect.right() and 
            abs(world_pos.y() - rect.top()) < grab_distance):
            return 't'
        if (rect.left() < world_pos.x() < rect.right() and 
            abs(world_pos.y() - rect.bottom()) < grab_distance):
            return 'b'
        if (rect.top() < world_pos.y() < rect.bottom() and 
            abs(world_pos.x() - rect.left()) < grab_distance):
            return 'l'
        if (rect.top() < world_pos.y() < rect.bottom() and 
            abs(world_pos.x() - rect.right()) < grab_distance):
            return 'r'
        
        return None
    
    def _get_cursor_for_handle(self, handle: Optional[str]) -> Qt.CursorShape:
        """Get cursor for resize handle."""
        if handle in ['tl', 'br']:
            return Qt.SizeFDiagCursor
        elif handle in ['tr', 'bl']:
            return Qt.SizeBDiagCursor
        elif handle in ['t', 'b']:
            return Qt.SizeVerCursor
        elif handle in ['l', 'r']:
            return Qt.SizeHorCursor
        else:
            return Qt.OpenHandCursor
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press."""
        if event.button() == Qt.LeftButton:
            world_pos = self._screen_to_world(QPointF(event.pos()))
            
            # Check for resize handle
            handle = self._get_resize_handle(world_pos)
            if handle:
                self._resizing = True
                self._resize_handle = handle
                self._drag_start_pos = world_pos
                self._drag_start_uv_rect = QRectF(self._get_uv_rect_pixels())
                event.accept()
                return
            
            # Check if clicking inside UV rect - start dragging
            rect = self._get_uv_rect_pixels()
            if rect.contains(world_pos):
                self._dragging_rect = True
                self._drag_start_pos = world_pos
                self._drag_start_uv_rect = QRectF(rect)
                self.setCursor(Qt.ClosedHandCursor)
                event.accept()
                return
        
        elif event.button() == Qt.MiddleButton or (event.button() == Qt.RightButton):
            # Start panning
            self._is_panning = True
            self._pan_start_pos = QPointF(event.pos())
            self._pan_start_view = QPointF(self._view_center)
            event.accept()
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move."""
        world_pos = self._screen_to_world(QPointF(event.pos()))
        
        if self._resizing and self._drag_start_uv_rect:
            # Resize UV rect
            delta = world_pos - self._drag_start_pos
            new_rect = QRectF(self._drag_start_uv_rect)
            
            h = self._resize_handle
            if 'l' in h:
                new_rect.setLeft(new_rect.left() + delta.x())
            if 'r' in h:
                new_rect.setRight(new_rect.right() + delta.x())
            if 't' in h:
                new_rect.setTop(new_rect.top() + delta.y())
            if 'b' in h:
                new_rect.setBottom(new_rect.bottom() + delta.y())
            
            # Ensure minimum size
            if new_rect.width() < 1:
                if 'l' in h:
                    new_rect.setLeft(new_rect.right() - 1)
                else:
                    new_rect.setRight(new_rect.left() + 1)
            if new_rect.height() < 1:
                if 't' in h:
                    new_rect.setTop(new_rect.bottom() - 1)
                else:
                    new_rect.setBottom(new_rect.top() + 1)
            
            self._set_uv_from_pixels(new_rect)
            
        elif self._dragging_rect and self._drag_start_uv_rect:
            # Move UV rect
            delta = world_pos - self._drag_start_pos
            new_rect = self._drag_start_uv_rect.translated(delta.x(), delta.y())
            self._set_uv_from_pixels(new_rect)
            
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
            
        else:
            # Update cursor based on hover
            handle = self._get_resize_handle(world_pos)
            self.setCursor(self._get_cursor_for_handle(handle))
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release."""
        if event.button() == Qt.LeftButton:
            self._dragging_rect = False
            self._resizing = False
            self._resize_handle = None
            self.setCursor(Qt.OpenHandCursor)
        elif event.button() == Qt.MiddleButton or event.button() == Qt.RightButton:
            self._is_panning = False
    
    def wheelEvent(self, event: QWheelEvent):
        """Handle mouse wheel for zooming."""
        delta = event.angleDelta().y()
        zoom_factor = 1.15 if delta > 0 else 1.0 / 1.15
        self._zoom *= zoom_factor
        self._zoom = max(0.1, min(20.0, self._zoom))
        self.update()
    
    def paintEvent(self, event):
        """Paint the UV editor."""
        painter = QPainter(self)
        
        # Fill background
        painter.fillRect(self.rect(), QColor(45, 45, 48))
        
        if not self._texture_pixmap or not self._body_part:
            painter.setPen(QColor(150, 150, 150))
            painter.drawText(self.rect(), Qt.AlignCenter, "No texture loaded")
            return
        
        # Setup transform
        painter.save()
        center = QPointF(self.width() / 2, self.height() / 2)
        painter.translate(center)
        painter.scale(self._zoom, self._zoom)
        painter.translate(-self._view_center)
        
        # Draw texture
        painter.drawPixmap(0, 0, self._texture_pixmap)
        
        # Draw UV rectangle
        rect = self._get_uv_rect_pixels()
        if not rect.isEmpty():
            # Fill
            painter.setBrush(QBrush(QColor(100, 200, 255, 60)))
            painter.setPen(QPen(QColor(100, 200, 255), 2 / self._zoom))
            painter.drawRect(rect)
            
            # Draw resize handles if not too small
            if rect.width() > 20 and rect.height() > 20:
                handle_size = 6 / self._zoom
                painter.setBrush(QBrush(QColor(255, 255, 255)))
                painter.setPen(QPen(QColor(100, 200, 255), 1 / self._zoom))
                
                # 8 handles
                handles = [
                    QPointF(rect.left(), rect.top()),
                    QPointF(rect.center().x(), rect.top()),
                    QPointF(rect.right(), rect.top()),
                    QPointF(rect.right(), rect.center().y()),
                    QPointF(rect.right(), rect.bottom()),
                    QPointF(rect.center().x(), rect.bottom()),
                    QPointF(rect.left(), rect.bottom()),
                    QPointF(rect.left(), rect.center().y()),
                ]
                
                for h in handles:
                    painter.drawEllipse(h, handle_size, handle_size)
        
        painter.restore()

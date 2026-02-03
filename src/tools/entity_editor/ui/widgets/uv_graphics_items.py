"""
Custom QGraphicsItems for UV Editor.

Simplified implementation focused on draggable, resizable UV rectangles.
"""

from PySide6.QtWidgets import QGraphicsItem, QGraphicsPixmapItem, QGraphicsRectItem, QGraphicsEllipseItem
from PySide6.QtCore import Qt, QRectF, QPointF, Signal, QObject
from PySide6.QtGui import QPen, QBrush, QColor, QPainter, QPixmap
from typing import Optional
from enum import Enum


class HandlePosition(Enum):
    """Positions for resize handles."""
    TOP_LEFT = 0
    TOP = 1
    TOP_RIGHT = 2
    RIGHT = 3
    BOTTOM_RIGHT = 4
    BOTTOM = 5
    BOTTOM_LEFT = 6
    LEFT = 7


class UVRectSignals(QObject):
    """Signals for UVRectItem (QGraphicsItem can't have signals directly)."""
    uv_changed = Signal(object)  # Emits self when UV changes
    selected_changed = Signal(object, bool)  # Emits (self, is_selected)


class UVRectItem(QGraphicsRectItem):
    """
    Draggable, resizable UV rectangle overlay.
    
    Simplified: Uses Qt's built-in resizing instead of custom handles.
    User can drag the edges/corners directly to resize.
    """
    
    MIN_SIZE = 10  # Minimum size in pixels
    EDGE_GRAB_SIZE = 10  # Pixels from edge to enable resize
    
    def __init__(self, body_part, texture_width: int, texture_height: int, parent=None):
        """
        Create UV rectangle item.
        
        Args:
            body_part: BodyPart data object
            texture_width: Texture width in pixels
            texture_height: Texture height in pixels
        """
        # Initialize with current UV rect in texture coordinates
        uv = body_part.uv_rect
        x = uv.x * texture_width
        y = uv.y * texture_height
        w = uv.width * texture_width
        h = uv.height * texture_height
        
        super().__init__(x, y, w, h, parent)
        
        self.body_part = body_part
        self.texture_width = texture_width
        self.texture_height = texture_height
        self._is_selected = False
        
        # Resize state
        self._resize_mode = None  # None, or HandlePosition
        self._resize_start_rect = None
        self._resize_start_pos = None
        
        # Signals
        self.signals = UVRectSignals()
        
        # Visual style
        self._update_style()
        
        # Interaction
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)
        
        # Z-order
        self.setZValue(100)
    
    def _update_style(self):
        """Update visual style based on selection state."""
        # Body part specific color (use hash of name for consistency)
        color_hash = hash(self.body_part.name) % 360
        base_color = QColor.fromHsv(color_hash, 200, 200, 100)
        
        if self._is_selected:
            # Selected: solid border, semi-transparent fill
            self.setPen(QPen(QColor(100, 200, 255), 3))
            self.setBrush(QBrush(base_color))
        else:
            # Unselected: thin border, more transparent
            self.setPen(QPen(base_color.lighter(150), 2))
            base_color.setAlpha(60)
            self.setBrush(QBrush(base_color))
    
    def set_selected(self, selected: bool):
        """Set selection state."""
        if self._is_selected == selected:
            return
        
        self._is_selected = selected
        self._update_style()
        self.signals.selected_changed.emit(self, selected)
    
    def update_from_bodypart(self):
        """Update rectangle from body part's UV rect."""
        uv = self.body_part.uv_rect
        x = uv.x * self.texture_width
        y = uv.y * self.texture_height
        w = uv.width * self.texture_width
        h = uv.height * self.texture_height
        
        self.setRect(x, y, w, h)
    
    def update_bodypart_uv(self):
        """Update body part's UV rect from current rectangle position/size."""
        rect = self.rect()
        pos = self.pos()
        
        # Convert to UV coordinates (normalized)
        # Always snap to whole pixels for pixel-perfect positioning
        pixel_x = round(rect.x() + pos.x())
        pixel_y = round(rect.y() + pos.y())
        pixel_w = round(rect.width())
        pixel_h = round(rect.height())
        
        self.body_part.uv_rect.x = pixel_x / self.texture_width
        self.body_part.uv_rect.y = pixel_y / self.texture_height
        self.body_part.uv_rect.width = pixel_w / self.texture_width
        self.body_part.uv_rect.height = pixel_h / self.texture_height
        
        # Clamp to [0, 1]
        self.body_part.uv_rect.x = max(0.0, min(1.0, self.body_part.uv_rect.x))
        self.body_part.uv_rect.y = max(0.0, min(1.0, self.body_part.uv_rect.y))
        self.body_part.uv_rect.width = max(0.0, min(1.0 - self.body_part.uv_rect.x, self.body_part.uv_rect.width))
        self.body_part.uv_rect.height = max(0.0, min(1.0 - self.body_part.uv_rect.y, self.body_part.uv_rect.height))
        
        self.signals.uv_changed.emit(self)
    
    def _get_resize_mode(self, pos: QPointF) -> Optional[HandlePosition]:
        """Determine which edge/corner is being grabbed for resizing."""
        rect = self.rect()
        edge = self.EDGE_GRAB_SIZE
        
        left_edge = abs(pos.x() - rect.left()) < edge
        right_edge = abs(pos.x() - rect.right()) < edge
        top_edge = abs(pos.y() - rect.top()) < edge
        bottom_edge = abs(pos.y() - rect.bottom()) < edge
        
        # Corners have priority
        if top_edge and left_edge:
            return HandlePosition.TOP_LEFT
        elif top_edge and right_edge:
            return HandlePosition.TOP_RIGHT
        elif bottom_edge and left_edge:
            return HandlePosition.BOTTOM_LEFT
        elif bottom_edge and right_edge:
            return HandlePosition.BOTTOM_RIGHT
        # Then edges
        elif top_edge:
            return HandlePosition.TOP
        elif bottom_edge:
            return HandlePosition.BOTTOM
        elif left_edge:
            return HandlePosition.LEFT
        elif right_edge:
            return HandlePosition.RIGHT
        
        return None
    
    def _get_cursor_for_mode(self, mode: Optional[HandlePosition]) -> Qt.CursorShape:
        """Get appropriate cursor for resize mode."""
        if mode is None:
            return Qt.OpenHandCursor
        
        cursors = {
            HandlePosition.TOP_LEFT: Qt.SizeFDiagCursor,
            HandlePosition.TOP: Qt.SizeVerCursor,
            HandlePosition.TOP_RIGHT: Qt.SizeBDiagCursor,
            HandlePosition.RIGHT: Qt.SizeHorCursor,
            HandlePosition.BOTTOM_RIGHT: Qt.SizeFDiagCursor,
            HandlePosition.BOTTOM: Qt.SizeVerCursor,
            HandlePosition.BOTTOM_LEFT: Qt.SizeBDiagCursor,
            HandlePosition.LEFT: Qt.SizeHorCursor,
        }
        return cursors.get(mode, Qt.ArrowCursor)
    
    def hoverMoveEvent(self, event):
        """Update cursor based on hover position."""
        if self._is_selected and not self._resize_mode:
            mode = self._get_resize_mode(event.pos())
            self.setCursor(self._get_cursor_for_mode(mode))
        super().hoverMoveEvent(event)
    
    def mousePressEvent(self, event):
        """Handle mouse press for moving or resizing."""
        if event.button() == Qt.LeftButton and self._is_selected:
            mode = self._get_resize_mode(event.pos())
            if mode is not None:
                # Start resize
                self._resize_mode = mode
                self._resize_start_rect = QRectF(self.rect())
                self._resize_start_pos = event.pos()
                event.accept()
                return
        
        # Default behavior (moving)
        if event.button() == Qt.LeftButton:
            self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for resizing or moving."""
        if self._resize_mode is not None:
            # Resize mode
            delta = event.pos() - self._resize_start_pos
            new_rect = QRectF(self._resize_start_rect)
            
            mode = self._resize_mode
            
            # Adjust rectangle based on resize mode
            if mode in [HandlePosition.LEFT, HandlePosition.TOP_LEFT, HandlePosition.BOTTOM_LEFT]:
                # Adjust left edge
                new_rect.setLeft(new_rect.left() + delta.x())
            if mode in [HandlePosition.RIGHT, HandlePosition.TOP_RIGHT, HandlePosition.BOTTOM_RIGHT]:
                # Adjust right edge
                new_rect.setRight(new_rect.right() + delta.x())
            if mode in [HandlePosition.TOP, HandlePosition.TOP_LEFT, HandlePosition.TOP_RIGHT]:
                # Adjust top edge
                new_rect.setTop(new_rect.top() + delta.y())
            if mode in [HandlePosition.BOTTOM, HandlePosition.BOTTOM_LEFT, HandlePosition.BOTTOM_RIGHT]:
                # Adjust bottom edge
                new_rect.setBottom(new_rect.bottom() + delta.y())
            
            # Ensure minimum size
            if new_rect.width() < self.MIN_SIZE:
                if mode in [HandlePosition.LEFT, HandlePosition.TOP_LEFT, HandlePosition.BOTTOM_LEFT]:
                    new_rect.setLeft(new_rect.right() - self.MIN_SIZE)
                else:
                    new_rect.setRight(new_rect.left() + self.MIN_SIZE)
            
            if new_rect.height() < self.MIN_SIZE:
                if mode in [HandlePosition.TOP, HandlePosition.TOP_LEFT, HandlePosition.TOP_RIGHT]:
                    new_rect.setTop(new_rect.bottom() - self.MIN_SIZE)
                else:
                    new_rect.setBottom(new_rect.top() + self.MIN_SIZE)
            
            # Clamp to texture bounds
            new_rect.setLeft(max(0, new_rect.left()))
            new_rect.setTop(max(0, new_rect.top()))
            new_rect.setRight(min(self.texture_width, new_rect.right()))
            new_rect.setBottom(min(self.texture_height, new_rect.bottom()))
            
            self.setRect(new_rect)
            self.update_bodypart_uv()
            event.accept()
        else:
            # Default move behavior
            super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release."""
        if event.button() == Qt.LeftButton:
            if self._resize_mode is not None:
                self._resize_mode = None
                self._resize_start_rect = None
                self._resize_start_pos = None
                # Update cursor
                mode = self._get_resize_mode(event.pos())
                self.setCursor(self._get_cursor_for_mode(mode))
            else:
                self.setCursor(Qt.OpenHandCursor)
        super().mouseReleaseEvent(event)
    
    def itemChange(self, change, value):
        """Handle item changes(position, selection, etc.)."""
        if change == QGraphicsItem.ItemPositionHasChanged:
            # Position changed - update UV
            self.update_bodypart_uv()
        elif change == QGraphicsItem.ItemSelectedHasChanged:
            # Selection changed
            self.set_selected(value)
        
        return super().itemChange(change, value)
    
    def paint(self, painter, option, widget=None):
        """Custom paint to show name label and resize handles."""
        # Draw rectangle
        super().paint(painter, option, widget)
        
        # Draw name label
        if self._is_selected:
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            painter.setBrush(QBrush(QColor(0, 0, 0, 180)))
            
            rect = self.rect()
            label_rect = QRectF(rect.left(), rect.top() - 20, rect.width(), 18)
            painter.drawRect(label_rect)
            
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(label_rect, Qt.AlignCenter, self.body_part.name)
            
            # Only draw resize handles if rectangle is large enough
            # (avoids overlap on small UV regions)
            if rect.width() > 20 and rect.height() > 20:
                # Get view transform to scale handles appropriately
                view = self.scene().views()[0] if self.scene() and self.scene().views() else None
                scale_factor = 1.0
                if view:
                    transform = view.transform()
                    scale_factor = transform.m11()  # Zoom level
                
                # Scale handle size inversely with zoom (larger when zoomed out)
                base_handle_size = 6
                handle_size = base_handle_size / scale_factor
                handle_size = max(3, min(handle_size, 10))  # Clamp between 3-10 pixels
                
                painter.setPen(QPen(QColor(100, 200, 255), 2 / scale_factor))
                painter.setBrush(QBrush(QColor(255, 255, 255, 200)))
                
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
                
                for handle_pos in handles:
                    painter.drawEllipse(handle_pos, handle_size, handle_size)


class UVGridItem(QGraphicsRectItem):
    """
    Grid overlay for sprite sheet navigation.
    
    Displays a grid over the texture with configurable cell size.
    """
    
    def __init__(self, texture_width: int, texture_height: int, 
                 cell_width: int = 32, cell_height: int = 32, parent=None):
        super().__init__(0, 0, texture_width, texture_height, parent)
        
        self.texture_width = texture_width
        self.texture_height = texture_height
        self.cell_width = cell_width
        self.cell_height = cell_height
        
        # Visual style
        self.setPen(Qt.NoPen)
        self.setBrush(Qt.NoBrush)
        
        # Not interactive
        self.setFlag(QGraphicsItem.ItemIsMovable, False)
        self.setFlag(QGraphicsItem.ItemIsSelectable, False)
        
        # Z-order (behind UV rects, in front of texture)
        self.setZValue(50)
    
    def set_cell_size(self, width: int, height: int):
        """Set grid cell size."""
        self.cell_width = width
        self.cell_height = height
        self.update()
    
    def paint(self, painter, option, widget=None):
        """Paint grid lines."""
        painter.setPen(QPen(QColor(255, 255, 255, 80), 1, Qt.DotLine))
        
        # Vertical lines
        x = 0
        while x <= self.texture_width:
            painter.drawLine(QPointF(x, 0), QPointF(x, self.texture_height))
            x += self.cell_width
        
        # Horizontal lines
        y = 0
        while y <= self.texture_height:
            painter.drawLine(QPointF(0, y), QPointF(self.texture_width, y))
            y += self.cell_height


class TextureBackgroundItem(QGraphicsPixmapItem):
    """
    Texture background for UV editor.
    
    Displays the texture in the scene.
    """
    
    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(pixmap, parent)
        
        # Not interactive
        self.setFlag(QGraphicsItem.ItemIsMovable, False)
        self.setFlag(QGraphicsItem.ItemIsSelectable, False)
        
        # Z-order (at the back)
        self.setZValue(0)
        
        # Use nearest-neighbor for pixel art (no smoothing)
        self.setTransformationMode(Qt.FastTransformation)
    
    def set_pixmap(self, pixmap: QPixmap):
        """Update the displayed pixmap."""
        self.setPixmap(pixmap)

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
from src.core import get_signal_hub

class ViewportWidget(QWidget):
    """
    Interactive 2D viewport for visualizing and editing entities.
    Refactored to be a 'View' that delegates to Controller and Renderer.
    """
    
    # Signals
    selection_changed = Signal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Core State
        from src.core.state.editor_state import EditorState
        self._state = EditorState()
        
        # New Components
        from src.ui.viewport.viewport_controller import ViewportController
        from src.ui.viewport.viewport_renderer import ViewportRenderer
        
        # View Transform State
        self._zoom = 1.0
        self._pan_offset = QPointF(0, 0)
        self._view_center = QPointF(0, 0)
        
        # Setup Components
        # Renderer needs state
        self._renderer = ViewportRenderer(self._state)
        # Controller needs view (self) and state
        self._controller = ViewportController(self, self._state)
        
        # Setup Widget
        self.setMinimumSize(400, 400)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Connect to Signals
        self._signal_hub = get_signal_hub()
        self._connect_signals()
        
    def _connect_signals(self):
        # Repaint on any change
        self._signal_hub.entity_loaded.connect(lambda e: self.update())
        self._signal_hub.bodypart_selected.connect(lambda b: self.update())
        self._signal_hub.bodyparts_selection_changed.connect(lambda b: self.update())
        self._signal_hub.bodypart_modified.connect(lambda b: self.update())
        self._signal_hub.bodypart_added.connect(lambda b: self.update())
        self._signal_hub.bodypart_removed.connect(lambda b: self.update())
        self._signal_hub.bodypart_reordered.connect(self.update)
        self._signal_hub.hitbox_selected.connect(lambda h: self.update())
        self._signal_hub.hitbox_modified.connect(lambda h: self.update())
        self._signal_hub.hitbox_added.connect(lambda h: self.update())
        self._signal_hub.hitbox_removed.connect(lambda h: self.update())
        self._signal_hub.hitbox_edit_mode_changed.connect(lambda e: self.update())
        self._signal_hub.snap_value_changed.connect(lambda v: self.update()) # Renderer might use this eventually

    def set_entity(self, entity: Entity):
        """Set the entity to display."""
        # For compatibility/legacy calls. Ideally handled via EditorState.
        # If the state doesn't have it, we should set it.
        # But set_entity implies loading.
        # Let's assume the caller has updated the state or this is just for the View.
        # In the new architecture, View just reflects State.
        # However, for transition, we trigger update.
        self.update()

    def get_entity(self) -> Optional[Entity]:
        return self._state.current_entity
    
    def set_zoom(self, zoom: float):
        """Set viewport zoom level."""
        self._zoom = zoom
        self.update()
        
    def paintEvent(self, event):
        """Render the viewport."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Fill background
        painter.fillRect(self.rect(), QColor(40, 40, 40))
        
        if not self._state.current_entity:
            painter.setPen(QColor(100, 100, 100))
            painter.drawText(self.rect(), Qt.AlignCenter, "No Entity Loaded")
            return
            
        # Apply View Transform
        painter.save()
        
        # Center view: Screen Center -> View Center
        screen_center_x = self.width() / 2
        screen_center_y = self.height() / 2
        
        painter.translate(screen_center_x, screen_center_y)
        painter.scale(self._zoom, self._zoom)
        painter.translate(-self._view_center.x(), -self._view_center.y())
        
        # Update Renderer State
        self._renderer.zoom = self._zoom
        # Pass generic visual options if needed (or renderer reads from its own config)
        self._renderer.show_grid = True # Should match widget state or user pref
        # self._renderer.show_hitboxes = ? (Accessed via local state or we should check signal hub?)
        # ViewportWidget used 'self._show_hitboxes'.
        # We should probably respect that if we want to keep parity?
        # But 'show_hitboxes' is often a toolbar toggle.
        # Let's assume Renderer defaults for now, or we pass it?
        # Renderer has `self.show_hitboxes`. We can update it here.
        # But we need access to the preferences. 
        # For now, let's assume default is True.
        
        # Draw
        view_rect = QRectF() 
        self._renderer.render(painter, view_rect)
        
        painter.restore()
        
        # Draw Overlay (Zoom level etc)
        self._draw_overlay(painter)

    def _draw_overlay(self, painter: QPainter):
        painter.setPen(QColor(200, 200, 200))
        painter.drawText(10, 20, f"Zoom: {self._zoom:.2f}x")

    # --- Input Handling ( Routed to Controller ) ---

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self._is_panning = True
            self._pan_start_pos = event.position()
            self._pan_start_view_center = QPointF(self._view_center)
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return

        self._controller.mouse_press(event)

    def mouseMoveEvent(self, event):
        if hasattr(self, '_is_panning') and self._is_panning:
            delta = event.position() - self._pan_start_pos
            # Adjust view center based on delta (scaled by zoom)
            self._view_center = self._pan_start_view_center - QPointF(delta.x() / self._zoom, delta.y() / self._zoom)
            self.update()
            event.accept()
            return
            
        self._controller.mouse_move(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton and hasattr(self, '_is_panning'):
            self._is_panning = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
            return
            
        self._controller.mouse_release(event)

    def wheelEvent(self, event):
        """Handle mouse wheel for zooming."""
        zoom_inp = event.angleDelta().y()
        old_zoom = self._zoom
        if zoom_inp > 0:
            self._zoom *= 1.1
        else:
            self._zoom /= 1.1
            
        self._zoom = max(0.1, min(self._zoom, 10.0))
        
        # Adjust view center to keep mouse position stable
        mouse_pos = event.position()
        world_pos_old = self.screen_to_world(mouse_pos, old_zoom)
        
        # Recalculate view center
        screen_center_x = self.width() / 2
        screen_center_y = self.height() / 2
        
        dx = mouse_pos.x() - screen_center_x
        dy = mouse_pos.y() - screen_center_y
        
        self._view_center.setX(world_pos_old.x - (dx / self._zoom))
        self._view_center.setY(world_pos_old.y - (dy / self._zoom))
        
        self.update()
    
    def keyPressEvent(self, event):
        # Forward key events to controller if needed in future
        super().keyPressEvent(event)

    # --- Coordinate Conversion Utilities ---

    def screen_to_world(self, screen_pos: QPointF, override_zoom=None) -> Vec2:
        """Convert screen coordinates to world coordinates."""
        zoom = override_zoom if override_zoom is not None else self._zoom
        
        screen_center_x = self.width() / 2
        screen_center_y = self.height() / 2
        
        dx = screen_pos.x() - screen_center_x
        dy = screen_pos.y() - screen_center_y
        
        world_x = self._view_center.x() + (dx / zoom)
        world_y = self._view_center.y() + (dy / zoom)
        
        return Vec2(world_x, world_y)

    def world_to_screen(self, world_pos: Vec2) -> QPointF:
        """Convert world coordinates to screen coordinates."""
        screen_center_x = self.width() / 2
        screen_center_y = self.height() / 2
        
        rel_x = world_pos.x - self._view_center.x()
        rel_y = world_pos.y - self._view_center.y()
        
        screen_x = screen_center_x + (rel_x * self._zoom)
        screen_y = screen_center_y + (rel_y * self._zoom)
        
        return QPointF(screen_x, screen_y)

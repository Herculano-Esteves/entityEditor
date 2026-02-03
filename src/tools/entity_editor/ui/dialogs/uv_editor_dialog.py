
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QScrollArea, QWidget, QDoubleSpinBox,
                               QGroupBox, QFormLayout)
from PySide6.QtCore import Qt, QRectF, QSize, Signal, QPointF
from PySide6.QtGui import QPixmap, QPainter, QPen, QColor, QBrush, QImage, QPalette, QWheelEvent, QMouseEvent

class UVEditorWidget(QWidget):
    """
    Widget to display texture and handle visual UV selection with Zoom, Pan, and Handles.
    """
    rect_changed = Signal(float, float, float, float) # x, y, w, h (normalized)
    
    def __init__(self):
        super().__init__()
        self._pixmap: QPixmap = None
        self._uv_rect: QRectF = QRectF(0, 0, 1, 1) # Normalized
        
        # Transform State
        self._zoom = 1.0
        self._pan = QPointF(0, 0)
        self._min_zoom = 0.1
        self._max_zoom = 10.0
        
        # Interaction State
        self._is_panning = False
        self._pan_start = QPointF(0, 0)
        
        self._drag_mode = None # None, 'move', 'handle:tl', 'handle:tr', etc.
        self._drag_start_pos = QPointF(0, 0) # Screen pos
        self._drag_start_rect = None # Normalized rect
        
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Handles config
        self._handle_size = 8
        
    def set_texture(self, pixmap: QPixmap):
        self._pixmap = pixmap
        # Reset view
        self.fit_view()
        self.update()

    def fit_view(self):
        if not self._pixmap: return
        # Simple fit logic: strict fit to smallest dimension
        w_ratio = self.width() / self._pixmap.width()
        h_ratio = self.height() / self._pixmap.height()
        self._zoom = min(w_ratio, h_ratio) * 0.9 # 90% fit
        self._pan = QPointF(0, 0)
        self.update()

    def reset_zoom_100(self):
        self._zoom = 1.0
        self._pan = QPointF(0, 0)
        self.update()
        
    def set_uv_rect(self, x, y, w, h):
        self._uv_rect = QRectF(x, y, w, h)
        self.update()
        
    def get_uv_rect(self):
        return (self._uv_rect.x(), self._uv_rect.y(), 
                self._uv_rect.width(), self._uv_rect.height())

    # --- Coordinate Conversion ---
    
    def _uv_to_screen(self, uv_point: QPointF) -> QPointF:
        if not self._pixmap: return QPointF(0, 0)
        tex_w = self._pixmap.width()
        tex_h = self._pixmap.height()
        
        # Image pixel coords
        img_x = uv_point.x() * tex_w
        img_y = uv_point.y() * tex_h
        
        # Apply Zoom & Pan
        # Center context: We render image centered + pan
        center_x = self.width() / 2
        center_y = self.height() / 2
        
        # To make (0,0) of image strictly at center before pan:
        # screen_x = center_x + pan_x + (img_x - tex_w/2) * zoom
        
        screen_x = center_x + self._pan.x() + (img_x - tex_w/2) * self._zoom
        screen_y = center_y + self._pan.y() + (img_y - tex_h/2) * self._zoom
        
        return QPointF(screen_x, screen_y)
    
    def _screen_to_uv(self, screen_point: QPointF) -> QPointF:
        if not self._pixmap: return QPointF(0, 0)
        tex_w = self._pixmap.width()
        tex_h = self._pixmap.height()
        
        center_x = self.width() / 2
        center_y = self.height() / 2
        
        # Inverse of uv_to_screen
        # screen_x = center_x + pan_x + (img_x - tex_w/2) * zoom
        # img_x = ((screen_x - center_x - pan_x) / zoom) + tex_w/2
        
        if self._zoom == 0: return QPointF(0,0)
        
        img_x = ((screen_point.x() - center_x - self._pan.x()) / self._zoom) + tex_w/2
        img_y = ((screen_point.y() - center_y - self._pan.y()) / self._zoom) + tex_h/2
        
        # Normalize
        u = img_x / tex_w
        v = img_y / tex_h
        return QPointF(u, v)

    # --- Drawing ---

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False) # Sharp pixels
        painter.setRenderHint(QPainter.SmoothPixmapTransform, self._zoom < 1.0) 
        
        w = self.width()
        h = self.height()
        
        # Draw Background (Grid)
        painter.fillRect(0, 0, w, h, QColor(40, 40, 40))
        # Optional: draw detailed grid? Skipping for simplicity.
        
        if not self._pixmap:
            painter.drawText(self.rect(), Qt.AlignCenter, "No Texture")
            return
            
        tex_w = self._pixmap.width()
        tex_h = self._pixmap.height()
        
        # Calculate Image Screen Rect
        tl = self._uv_to_screen(QPointF(0, 0))
        br = self._uv_to_screen(QPointF(1, 1))
        img_rect = QRectF(tl, br)
        
        # 1. Draw Texture
        painter.drawPixmap(img_rect.toRect(), self._pixmap)
        
        # 2. Draw Selection Overlay
        # selection in screen coords
        sel_tl = self._uv_to_screen(self._uv_rect.topLeft())
        sel_br = self._uv_to_screen(self._uv_rect.bottomRight())
        sel_rect = QRectF(sel_tl, sel_br)
        
        # Dimming outside selection
        # We can subtract regions or just draw 4 rectangles like before
        # Using a QRegion might be easier or 4 rects
        
        painter.setBrush(QBrush(QColor(0, 0, 0, 150)))
        painter.setPen(Qt.NoPen)
        
        # Top
        painter.drawRect(target_rect(img_rect.left(), img_rect.top(), img_rect.width(), sel_rect.top() - img_rect.top()))
        # Bottom
        painter.drawRect(target_rect(img_rect.left(), sel_rect.bottom(), img_rect.width(), img_rect.bottom() - sel_rect.bottom()))
        # Left
        painter.drawRect(target_rect(img_rect.left(), sel_rect.top(), sel_rect.left() - img_rect.left(), sel_rect.height()))
        # Right
        painter.drawRect(target_rect(sel_rect.right(), sel_rect.top(), img_rect.right() - sel_rect.right(), sel_rect.height()))
        
        # 3. Draw Border
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(0, 255, 0), 1, Qt.SolidLine)) # 1px line often cleaner
        painter.drawRect(sel_rect)
        
        # 4. Draw Handles
        self._draw_handles(painter, sel_rect)
        
    def _draw_handles(self, painter, rect):
        hs = self._handle_size
        painter.setBrush(QColor(255, 255, 255))
        painter.setPen(QPen(QColor(0, 0, 0), 1))
        
        # Corners
        corners = [
            (rect.topLeft(), 'tl'),
            (rect.topRight(), 'tr'),
            (rect.bottomLeft(), 'bl'),
            (rect.bottomRight(), 'br')
        ]
        
        # Edges (Middle points)
        edges = [
            (QPointF(rect.left(), rect.center().y()), 'l'),
            (QPointF(rect.right(), rect.center().y()), 'r'),
            (QPointF(rect.center().x(), rect.top()), 't'),
            (QPointF(rect.center().x(), rect.bottom()), 'b')
        ]
        
        for pt, _ in corners + edges:
            h_rect = QRectF(pt.x() - hs/2, pt.y() - hs/2, hs, hs)
            painter.drawRect(h_rect)

    # --- Interaction ---
    
    def wheelEvent(self, event: QWheelEvent):
        delta = event.angleDelta().y()
        factor = 1.1 if delta > 0 else 0.9
        
        # Mouse-centered zoom?
        # Current logic is center-based zoom. Implementing mouse-centered is nicer.
        # But keeping it simple center-based + panning is robust enough for now.
        
        new_zoom = self._zoom * factor
        new_zoom = max(self._min_zoom, min(new_zoom, self._max_zoom))
        self._zoom = new_zoom
        self.update()
        event.accept()
        
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MiddleButton:
            self._is_panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
            
        if event.button() == Qt.LeftButton:
            # Check handles first
            handle = self._get_handle_at(event.position())
            if handle:
                self._drag_mode = handle
            elif self._is_in_selection(event.position()):
                self._drag_mode = 'move'
            else:
                return # Click outside, maybe start new rect? Or ignore logic for now.
            
            self._drag_start_pos = event.position()
            self._drag_start_rect = QRectF(self._uv_rect)
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        pos = event.position()
        
        # Pan
        if self._is_panning:
            delta = pos - self._pan_start
            self._pan += delta
            self._pan_start = pos
            self.update()
            return
            
        # Hover update cursor
        if not self._drag_mode:
            handle = self._get_handle_at(pos)
            if handle in ['tl', 'br']: self.setCursor(Qt.SizeFDiagCursor)
            elif handle in ['tr', 'bl']: self.setCursor(Qt.SizeBDiagCursor)
            elif handle in ['l', 'r']: self.setCursor(Qt.SizeHorCursor)
            elif handle in ['t', 'b']: self.setCursor(Qt.SizeVerCursor)
            elif self._is_in_selection(pos): self.setCursor(Qt.SizeAllCursor)
            else: self.setCursor(Qt.ArrowCursor)
            
        # Dragging
        if self._drag_mode:
            self._handle_drag(pos)
            
    def mouseReleaseEvent(self, event: QMouseEvent):
        self._is_panning = False
        self._drag_mode = None
        if event.button() == Qt.MiddleButton:
            self.setCursor(Qt.ArrowCursor)
            
    def _get_handle_at(self, pos: QPointF):
        # Calculate screen rect
        sel_tl = self._uv_to_screen(self._uv_rect.topLeft())
        sel_br = self._uv_to_screen(self._uv_rect.bottomRight())
        rect = QRectF(sel_tl, sel_br)
        
        hs = self._handle_size
        hit_r = hs 
        
        # Check corners
        if (pos - rect.topLeft()).manhattanLength() < hit_r: return 'tl'
        if (pos - rect.topRight()).manhattanLength() < hit_r: return 'tr'
        if (pos - rect.bottomLeft()).manhattanLength() < hit_r: return 'bl'
        if (pos - rect.bottomRight()).manhattanLength() < hit_r: return 'br'
        
        # Check edges
        if abs(pos.x() - rect.left()) < hit_r and rect.top() < pos.y() < rect.bottom(): return 'l'
        if abs(pos.x() - rect.right()) < hit_r and rect.top() < pos.y() < rect.bottom(): return 'r'
        if abs(pos.y() - rect.top()) < hit_r and rect.left() < pos.x() < rect.right(): return 't'
        if abs(pos.y() - rect.bottom()) < hit_r and rect.left() < pos.x() < rect.right(): return 'b'
        
        return None
        
    def _is_in_selection(self, pos: QPointF):
        sel_tl = self._uv_to_screen(self._uv_rect.topLeft())
        sel_br = self._uv_to_screen(self._uv_rect.bottomRight())
        rect = QRectF(sel_tl, sel_br)
        return rect.contains(pos)
        
    def _handle_drag(self, pos: QPointF):
        tex_w = self._pixmap.width()
        tex_h = self._pixmap.height()
        
        # Screen delta to Pixel delta
        delta_screen = pos - self._drag_start_pos
        dx_px = (delta_screen.x() / self._zoom)
        dy_px = (delta_screen.y() / self._zoom)
        
        # Convert Start Rect to Pixels
        # We work in pixels to easier handle snapping and constraints
        r_uv = self._drag_start_rect
        r_px = QRectF(
            r_uv.x() * tex_w,
            r_uv.y() * tex_h,
            r_uv.width() * tex_w,
            r_uv.height() * tex_h
        )
        
        new_px = QRectF(r_px)
        
        if self._drag_mode == 'move':
            # Snap delta to integers
            dx = round(dx_px)
            dy = round(dy_px)
            
            new_px.translate(dx, dy)
            
            # Snap entire rect to nearest pixel grid first to avoid drift
            new_px.moveTo(round(new_px.x()), round(new_px.y()))
            
            # Constrain entire rect to bounds (Preserves Size)
            if new_px.left() < 0: new_px.moveLeft(0)
            if new_px.top() < 0: new_px.moveTop(0)
            if new_px.right() > tex_w: new_px.moveRight(tex_w)
            if new_px.bottom() > tex_h: new_px.moveBottom(tex_h)
            
        else:
            # Resize Mode
            # Calculate new raw edges based on delta
            l, t, r, b = r_px.left(), r_px.top(), r_px.right(), r_px.bottom()
            
            if self._drag_mode in ['tl', 'l', 'bl']: l += dx_px
            if self._drag_mode in ['tr', 'r', 'br']: r += dx_px
            if self._drag_mode in ['tl', 't', 'tr']: t += dy_px
            if self._drag_mode in ['bl', 'b', 'br']: b += dy_px
            
            # Snap edges to nearest pixel
            l = round(l)
            r = round(r)
            t = round(t)
            b = round(b)
            
            # Clamp edges to image bounds
            l = max(0, min(l, tex_w))
            r = max(0, min(r, tex_w))
            t = max(0, min(t, tex_h))
            b = max(0, min(b, tex_h))
            
            # Ensure min size of 1 pixel
            if r <= l: r = l + 1
            if b <= t: b = t + 1
            
            new_px.setCoords(l, t, r, b)

        # Convert back to Normalized UV
        final_uv = QRectF(
            new_px.x() / tex_w,
            new_px.y() / tex_h,
            new_px.width() / tex_w,
            new_px.height() / tex_h
        )
        
        self._uv_rect = final_uv
        self.rect_changed.emit(final_uv.x(), final_uv.y(), final_uv.width(), final_uv.height())
        self.update()


def target_rect(x, y, w, h):
    """Helper to create QRectF"""
    return QRectF(x, y, w, h)


class UVEditorDialog(QDialog):
    """Dialog for visual UV editing."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("UV Editor")
        self.resize(1200, 800) # Bigger default size
        
        self._uv_data = (0.0, 0.0, 1.0, 1.0) # x, y, w, h
        
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Left: Editor Widget
        wrapper = QWidget()
        v_layout = QVBoxLayout(wrapper)
        v_layout.setContentsMargins(0, 0, 0, 0)
        
        self._editor_widget = UVEditorWidget()
        self._editor_widget.rect_changed.connect(self._on_rect_changed)
        v_layout.addWidget(self._editor_widget)
        
        # Removed help label as requested
        
        layout.addWidget(wrapper, stretch=1)
        
        # Right: Controls
        sidebar = QWidget()
        sidebar.setFixedWidth(240) # Slightly wider for buttons
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(10, 10, 10, 10)
        
        # 1. View Controls
        view_group = QGroupBox("View Controls")
        view_layout = QVBoxLayout()
        
        vx_btns = QHBoxLayout()
        self._fit_btn = QPushButton("Fit")
        self._fit_btn.setToolTip("Center and fit texture to view")
        self._fit_btn.clicked.connect(lambda: self._editor_widget.fit_view())
        vx_btns.addWidget(self._fit_btn)
        
        self._100_btn = QPushButton("1:1")
        self._100_btn.setToolTip("Zoom to 100%")
        self._100_btn.clicked.connect(lambda: self._editor_widget.reset_zoom_100())
        vx_btns.addWidget(self._100_btn)
        
        view_layout.addLayout(vx_btns)
        view_group.setLayout(view_layout)
        side_layout.addWidget(view_group)

        # 2. UV Bounds
        uv_group = QGroupBox("UV Bounds (0.0 - 1.0)")
        uv_form = QFormLayout()
        
        self._spin_left = self._create_spin("Left (U)")
        uv_form.addRow("Left:", self._spin_left)
        
        self._spin_right = self._create_spin("Right (U)", 1.0)
        uv_form.addRow("Right:", self._spin_right)

        self._spin_top = self._create_spin("Top (V)")
        uv_form.addRow("Top:", self._spin_top)
        
        self._spin_bottom = self._create_spin("Bottom (V)", 1.0)
        uv_form.addRow("Bottom:", self._spin_bottom)
        
        uv_group.setLayout(uv_form)
        side_layout.addWidget(uv_group)
        
        # 3. Actions
        action_group = QGroupBox("Actions")
        act_layout = QVBoxLayout()
        
        self._full_uv_btn = QPushButton("Full Texture UV")
        self._full_uv_btn.clicked.connect(self._on_set_full_uv)
        act_layout.addWidget(self._full_uv_btn)
        
        action_group.setLayout(act_layout)
        side_layout.addWidget(action_group)
        
        side_layout.addStretch()
        
        # Buttons
        self._ok_btn = QPushButton("Apply")
        self._ok_btn.clicked.connect(self.accept)
        self._ok_btn.setFixedHeight(40)
        side_layout.addWidget(self._ok_btn)
        
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.clicked.connect(self.reject)
        side_layout.addWidget(self._cancel_btn)
        
        layout.addWidget(sidebar)

    def _on_set_full_uv(self):
        self.set_uv(0.0, 0.0, 1.0, 1.0)

        
    def _create_spin(self, name, default=0.0):
        spin = QDoubleSpinBox()
        spin.setRange(0.0, 1.0) # Strict 0-1
        spin.setSingleStep(0.01)
        spin.setDecimals(4)
        spin.setValue(default)
        spin.valueChanged.connect(self._on_params_changed)
        return spin
        
    def load_texture(self, pixmap: QPixmap, current_uv: tuple):
        self._editor_widget.set_texture(pixmap)
        x, y, w, h = current_uv
        self.set_uv(x, y, w, h)
        
    def set_uv(self, x, y, w, h):
        self._uv_data = (x, y, w, h)
        
        left = x
        top = y
        right = x + w
        bottom = y + h
        
        # Update inputs (block signals)
        self._block_spin_signals(True)
        
        self._spin_left.setValue(left)
        self._spin_top.setValue(top)
        self._spin_right.setValue(right)
        self._spin_bottom.setValue(bottom)
        
        self._block_spin_signals(False)
        
        # Update widget
        self._editor_widget.set_uv_rect(x, y, w, h)
        
    def _on_rect_changed(self, x, y, w, h):
        # Called from widget
        self._uv_data = (x, y, w, h)
        
        left = x
        top = y
        right = x + w
        bottom = y + h
        
        self._block_spin_signals(True)
        
        self._spin_left.setValue(left)
        self._spin_top.setValue(top)
        self._spin_right.setValue(right)
        self._spin_bottom.setValue(bottom)
        
        self._block_spin_signals(False)
        
    def _on_params_changed(self):
        # Called from spinboxes
        left = self._spin_left.value()
        top = self._spin_top.value()
        right = self._spin_right.value()
        bottom = self._spin_bottom.value()
        
        # Validate Bounds
        # If right < left, swap or clamp?
        # Let's calculate raw first
        w = right - left
        h = bottom - top
        
        # If w < 0, maybe user is dragging Left past Right
        # For a rect, w should be positive.
        if w < 0: w = 0
        if h < 0: h = 0
        
        x = left
        y = top
        
        self._uv_data = (x, y, w, h)
        self._editor_widget.set_uv_rect(x, y, w, h)
        
    def _block_spin_signals(self, block):
        self._spin_left.blockSignals(block)
        self._spin_top.blockSignals(block)
        self._spin_right.blockSignals(block)
        self._spin_bottom.blockSignals(block)
        
    def get_uv_rect(self):
        return self._uv_data

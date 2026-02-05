
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, 
    QPushButton, QLabel, QFileDialog, QLineEdit, QDialog, QFormLayout,
    QSplitter, QFrame, QMessageBox
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, QSize
import os

from src.common.texture_registry import TextureRegistry

class TextureManagerWindow(QMainWindow):
    def __init__(self, project=None):
        super().__init__()
        self.setWindowTitle("Texture Manager")
        self.resize(800, 600)
        
        self.project = project
        self.registry = TextureRegistry(project)
        
        self._setup_ui()
        self._refresh_list()
        
    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QHBoxLayout(central_widget)
        
        # Splitter for List | Preview
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)
        
        # --- Left Panel: List & Controls ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Header Info
        if self.project:
            left_layout.addWidget(QLabel(f"Project: {os.path.basename(self.project.project_file)}"))
        
        self.list_widget = QListWidget()
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        left_layout.addWidget(self.list_widget)
        
        # Controls
        ctrl_layout = QHBoxLayout()
        
        self.btn_add = QPushButton("Add")
        self.btn_add.clicked.connect(self._on_add)
        ctrl_layout.addWidget(self.btn_add)
        
        self.btn_remove = QPushButton("Remove")
        self.btn_remove.clicked.connect(self._on_remove)
        ctrl_layout.addWidget(self.btn_remove)
        
        left_layout.addLayout(ctrl_layout)
        
        order_layout = QHBoxLayout()
        self.btn_up = QPushButton("Up")
        self.btn_up.clicked.connect(self._on_up)
        order_layout.addWidget(self.btn_up)
        
        self.btn_down = QPushButton("Down")
        self.btn_down.clicked.connect(self._on_down)
        order_layout.addWidget(self.btn_down)
        
        left_layout.addLayout(order_layout)
        
        self.btn_save = QPushButton("Save Registry")
        self.btn_save.clicked.connect(self._on_save)
        # Style save button to look important
        self.btn_save.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 5px;")
        left_layout.addWidget(self.btn_save)
        
        splitter.addWidget(left_panel)
        
        # --- Right Panel: Details & Preview ---
        right_panel = QFrame()
        right_panel.setFrameShape(QFrame.StyledPanel)
        right_layout = QVBoxLayout(right_panel)
        
        self.lbl_key = QLabel("Select a texture...")
        self.lbl_key.setStyleSheet("font-size: 16px; font-weight: bold;")
        right_layout.addWidget(self.lbl_key)
        
        self.lbl_path = QLabel("")
        self.lbl_path.setWordWrap(True)
        right_layout.addWidget(self.lbl_path)
        
        self.lbl_preview = QLabel()
        self.lbl_preview.setAlignment(Qt.AlignCenter)
        self.lbl_preview.setStyleSheet("border: 1px solid #444; background-color: #222;")
        right_layout.addWidget(self.lbl_preview, stretch=1)
        
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 500])
        
    def _refresh_list(self):
        selected_key = None
        if self.list_widget.currentItem():
            selected_key = self.list_widget.currentItem().text()
            
        self.list_widget.clear()
        
        for key, path in self.registry.get_all():
            self.list_widget.addItem(key)
            
        # Restore selection
        if selected_key:
            items = self.list_widget.findItems(selected_key, Qt.MatchExactly)
            if items:
                self.list_widget.setCurrentItem(items[0])
                
    def _on_selection_changed(self):
        items = self.list_widget.selectedItems()
        if not items:
            self.lbl_key.setText("None")
            self.lbl_path.setText("")
            self.lbl_preview.clear()
            return
            
        key = items[0].text()
        path_rel = self.registry._registry.get(key, "")
        
        self.lbl_key.setText(key)
        self.lbl_path.setText(path_rel)
        
        # Resolve path 
        # If project exists, resolve via assets root
        # If not, try relative?
        full_path = path_rel
        if self.project:
            full_path = self.project.resolve_path(os.path.join(self.project.assets_root, path_rel))
        
        # Load Preview
        if os.path.exists(full_path):
            pixmap = QPixmap(full_path)
            if not pixmap.isNull():
                # Scale if too big
                if pixmap.width() > 400 or pixmap.height() > 400:
                    pixmap = pixmap.scaled(400, 400, Qt.KeepAspectRatio)
                self.lbl_preview.setPixmap(pixmap)
            else:
                self.lbl_preview.setText(f"Failed to load: {full_path}")
        else:
             self.lbl_preview.setText(f"File not found: {full_path}")
            
    def _on_add(self):
        dialog = AddTextureDialog(self, self.project)
        if dialog.exec():
            key, path = dialog.get_data()
            if key and path:
                self.registry.add_texture(key, path)
                self._refresh_list()
                
    def _on_remove(self):
        item = self.list_widget.currentItem()
        if not item: return
        key = item.text()
        
        confirm = QMessageBox.question(self, "Confirm", f"Delete {key}?")
        if confirm == QMessageBox.Yes:
            self.registry.remove_texture(key)
            self._refresh_list()
            
    def _on_up(self):
        item = self.list_widget.currentItem()
        if not item: return
        key = item.text()
        self.registry.move_up(key)
        self._refresh_list()
        # Reselect
        items = self.list_widget.findItems(key, Qt.MatchExactly)
        if items: self.list_widget.setCurrentItem(items[0])

    def _on_down(self):
        item = self.list_widget.currentItem()
        if not item: return
        key = item.text()
        self.registry.move_down(key)
        self._refresh_list()
        items = self.list_widget.findItems(key, Qt.MatchExactly)
        if items: self.list_widget.setCurrentItem(items[0])
        
    def _on_save(self):
        try:
            self.registry.save()
            QMessageBox.information(self, "Success", "Registry saved to JSON and BIN.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))


class AddTextureDialog(QDialog):
    def __init__(self, parent=None, project=None):
        super().__init__(parent)
        self.setWindowTitle("Add Texture")
        self.project = project
        self.setLayout(QVBoxLayout())
        
        form = QFormLayout()
        self.key_edit = QLineEdit()
        form.addRow("Key (Unique Name):", self.key_edit)
        
        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.browse_btn = QPushButton("...")
        self.browse_btn.clicked.connect(self._browse)
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(self.browse_btn)
        
        form.addRow("Path:", path_layout)
        self.layout().addLayout(form)
        
        btns = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(ok_btn)
        btns.addWidget(cancel_btn)
        self.layout().addLayout(btns)
        
    def _browse(self):
        start_dir = ""
        if self.project:
            start_dir = self.project.abs_assets_root
            # Try to be more specific: 'textures' folder
            tex_dir = os.path.join(start_dir, "textures")
            if os.path.exists(tex_dir):
                start_dir = tex_dir
                
        f, _ = QFileDialog.getOpenFileName(self, "Select Image", start_dir, "Images (*.png *.jpg *.bmp *.tga)")
        if f:
             # Make relative to assets root if possible
            if self.project:
                try:
                    assets_root = self.project.abs_assets_root
                    if os.path.commonpath([assets_root, f]) == assets_root:
                        rel_path = os.path.relpath(f, assets_root)
                        # Ensure forward slashes for cross-platform consistency
                        f = rel_path.replace("\\", "/")
                except ValueError:
                    pass # Different drive or not subpath
            
            self.path_edit.setText(f)
            
            # Suggest Key if empty
            if not self.key_edit.text():
                filename = os.path.splitext(os.path.basename(f))[0]
                self.key_edit.setText(filename.upper())
                
    def get_data(self):
        return self.key_edit.text().upper(), self.path_edit.text()

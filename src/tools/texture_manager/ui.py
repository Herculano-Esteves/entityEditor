"""
Texture Manager Window.

Opens a list of all textures in the registry, allows manual overrides
(custom key / path), and provides a one-click "Sync from Folder" that
discovers images in the project's textures folder and registers them
automatically.

On first open (registry is empty or missing), a sync is performed
automatically so the user sees textures immediately.
"""

from __future__ import annotations

import logging
import os

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QListWidget,
    QPushButton, QLabel, QFileDialog, QLineEdit, QDialog, QFormLayout,
    QSplitter, QFrame, QMessageBox,
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

from src.common.texture_registry import TextureRegistry

logger = logging.getLogger(__name__)


class TextureManagerWindow(QMainWindow):
    """Main window for the Texture Manager tool."""

    def __init__(self, project=None) -> None:
        super().__init__()
        self.setWindowTitle("Texture Manager")
        self.resize(900, 620)

        self.project = project
        self.registry = TextureRegistry(project)

        self._setup_ui()

        # Auto-sync on open so the registry is always up-to-date.
        # If completely empty (new project), a full scan runs automatically;
        # otherwise only new files are added.
        if project is not None:
            self._auto_sync()

        self._refresh_list()

    def closeEvent(self, event) -> None:
        """Called when the window is closed. Auto-save if there are unsaved changes."""
        if self.registry.is_dirty:
            self.registry.save()
            logger.info("Texture Manager auto-saved changes on exit.")
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # ---- Left: list + buttons ----
        left = QWidget()
        left_layout = QVBoxLayout(left)

        if self.project:
            left_layout.addWidget(
                QLabel(f"Project: {os.path.basename(self.project.project_file)}")
            )
            left_layout.addWidget(
                QLabel(f"Textures: {self.project.abs_textures_path}")
            )

        self.list_widget = QListWidget()
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        left_layout.addWidget(self.list_widget)

        # Sync button (primary action)
        self.btn_sync = QPushButton("⟳  Sync from Folder")
        self.btn_sync.setToolTip(
            "Scan the textures folder and add any new image files to the registry"
        )
        self.btn_sync.setStyleSheet(
            "background-color: #2196F3; color: white; font-weight: bold; padding: 5px;"
        )
        self.btn_sync.clicked.connect(self._on_sync)
        left_layout.addWidget(self.btn_sync)

        # Manual controls
        ctrl_layout = QHBoxLayout()
        self.btn_add = QPushButton("Add Manually")
        self.btn_add.clicked.connect(self._on_add)
        ctrl_layout.addWidget(self.btn_add)

        self.btn_remove = QPushButton("Remove")
        self.btn_remove.clicked.connect(self._on_remove)
        ctrl_layout.addWidget(self.btn_remove)
        left_layout.addLayout(ctrl_layout)

        # Re-order controls
        order_layout = QHBoxLayout()
        self.btn_up = QPushButton("▲ Up")
        self.btn_up.clicked.connect(self._on_up)
        order_layout.addWidget(self.btn_up)

        self.btn_down = QPushButton("▼ Down")
        self.btn_down.clicked.connect(self._on_down)
        order_layout.addWidget(self.btn_down)
        left_layout.addLayout(order_layout)

        # Save
        self.btn_save = QPushButton("Save Registry")
        self.btn_save.clicked.connect(self._on_save)
        self.btn_save.setStyleSheet(
            "background-color: #4CAF50; color: white; font-weight: bold; padding: 5px;"
        )
        left_layout.addWidget(self.btn_save)

        splitter.addWidget(left)

        # ---- Right: key / path / preview ----
        right = QFrame()
        right.setFrameShape(QFrame.StyledPanel)
        right_layout = QVBoxLayout(right)

        self.lbl_key = QLabel("Select a texture…")
        self.lbl_key.setStyleSheet("font-size: 16px; font-weight: bold;")
        right_layout.addWidget(self.lbl_key)

        self.lbl_path = QLabel("")
        self.lbl_path.setWordWrap(True)
        right_layout.addWidget(self.lbl_path)

        self.lbl_preview = QLabel()
        self.lbl_preview.setAlignment(Qt.AlignCenter)
        self.lbl_preview.setStyleSheet(
            "border: 1px solid #444; background-color: #222;"
        )
        right_layout.addWidget(self.lbl_preview, stretch=1)

        splitter.addWidget(right)
        splitter.setSizes([340, 560])

    # ------------------------------------------------------------------
    # Auto-sync
    # ------------------------------------------------------------------

    def _auto_sync(self) -> None:
        """Silently sync the textures folder into the registry on startup."""
        if self.project is None:
            return
        added, _skipped = self.registry.sync_from_folder(self.project.abs_textures_path)
        if added > 0:
            logger.info("Auto-sync added %d texture(s) to the registry.", added)

    # ------------------------------------------------------------------
    # List management
    # ------------------------------------------------------------------

    def _refresh_list(self) -> None:
        selected_key = None
        if self.list_widget.currentItem():
            selected_key = self.list_widget.currentItem().text()

        self.list_widget.clear()

        if self.registry.is_empty:
            # Show a placeholder message inside the list
            self.list_widget.addItem("(no textures — click Sync from Folder)")
            self.list_widget.setEnabled(False)
        else:
            self.list_widget.setEnabled(True)
            for key, _path in self.registry.get_all():
                self.list_widget.addItem(key)

            if selected_key:
                matches = self.list_widget.findItems(selected_key, Qt.MatchExactly)
                if matches:
                    self.list_widget.setCurrentItem(matches[0])

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_sync(self) -> None:
        """Manual 'Sync from Folder' button — scan and report results."""
        if self.project is None:
            QMessageBox.warning(self, "No Project", "No project is loaded.")
            return

        tex_path = self.project.abs_textures_path
        if not os.path.isdir(tex_path):
            QMessageBox.warning(
                self,
                "Textures Folder Missing",
                f"The textures folder does not exist:\n{tex_path}",
            )
            return

        added, skipped = self.registry.sync_from_folder(tex_path)

        if added == 0 and skipped == 0:
            QMessageBox.information(
                self,
                "Nothing to Sync",
                f"No supported image files found in:\n{tex_path}\n\n"
                "Add PNG, JPG, BMP or TGA files to that folder first.",
            )
        else:
            QMessageBox.information(
                self,
                "Sync Complete",
                f"Added {added} new texture(s).\n"
                f"Skipped {skipped} already registered.",
            )

        self._refresh_list()

    def _on_selection_changed(self) -> None:
        items = self.list_widget.selectedItems()
        if not items:
            self.lbl_key.setText("None")
            self.lbl_path.setText("")
            self.lbl_preview.clear()
            return

        key = items[0].text()
        path_rel = self.registry.get_path(key) or ""

        self.lbl_key.setText(key)
        self.lbl_path.setText(path_rel)

        # Resolve to absolute for preview
        abs_path = self.registry.resolve_path(key) if path_rel else path_rel

        if abs_path and os.path.exists(abs_path):
            pixmap = QPixmap(abs_path)
            if not pixmap.isNull():
                if pixmap.width() > 400 or pixmap.height() > 400:
                    pixmap = pixmap.scaled(400, 400, Qt.KeepAspectRatio)
                self.lbl_preview.setPixmap(pixmap)
            else:
                self.lbl_preview.setText(f"Failed to load: {abs_path}")
        else:
            self.lbl_preview.setText(f"File not found: {abs_path}")

    def _on_add(self) -> None:
        """Manually add a texture with a custom key."""
        dialog = AddTextureDialog(self, self.project)
        if dialog.exec():
            key, path = dialog.get_data()
            if key and path:
                self.registry.add_texture(key, path)
                self._refresh_list()

    def _on_remove(self) -> None:
        item = self.list_widget.currentItem()
        if not item:
            return
        key = item.text()
        confirm = QMessageBox.question(self, "Confirm", f"Remove entry '{key}'?")
        if confirm == QMessageBox.Yes:
            self.registry.remove_texture(key)
            self._refresh_list()

    def _on_up(self) -> None:
        item = self.list_widget.currentItem()
        if not item:
            return
        key = item.text()
        self.registry.move_up(key)
        self._refresh_list()
        matches = self.list_widget.findItems(key, Qt.MatchExactly)
        if matches:
            self.list_widget.setCurrentItem(matches[0])

    def _on_down(self) -> None:
        item = self.list_widget.currentItem()
        if not item:
            return
        key = item.text()
        self.registry.move_down(key)
        self._refresh_list()
        matches = self.list_widget.findItems(key, Qt.MatchExactly)
        if matches:
            self.list_widget.setCurrentItem(matches[0])

    def _on_save(self) -> None:
        success = self.registry.save()
        if success:
            QMessageBox.information(self, "Saved", "Registry saved successfully.")
        else:
            QMessageBox.critical(self, "Error", "Failed to save registry.")


# ---------------------------------------------------------------------------
# Add Texture Dialog
# ---------------------------------------------------------------------------

class AddTextureDialog(QDialog):
    """Dialog for manually adding a texture entry with a custom key."""

    def __init__(self, parent=None, project=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Texture Manually")
        self.project = project
        self.setLayout(QVBoxLayout())

        form = QFormLayout()
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("e.g. HERO")
        form.addRow("Key (Unique Name):", self.key_edit)

        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Relative path from assets root")
        self.browse_btn = QPushButton("Browse…")
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

    def _browse(self) -> None:
        start_dir = ""
        if self.project:
            start_dir = self.project.abs_textures_path
            if not os.path.exists(start_dir):
                start_dir = self.project.abs_assets_root

        f, _ = QFileDialog.getOpenFileName(
            self, "Select Image", start_dir, "Images (*.png *.jpg *.bmp *.tga)"
        )
        if f:
            if self.project:
                try:
                    assets_root = self.project.abs_assets_root
                    if os.path.commonpath([assets_root, f]) == assets_root:
                        rel = os.path.relpath(f, assets_root).replace("\\", "/")
                        f = rel
                except ValueError:
                    pass  # different drive — keep absolute
            self.path_edit.setText(f)
            if not self.key_edit.text():
                stem = os.path.splitext(os.path.basename(f))[0]
                self.key_edit.setText(stem.upper())

    def get_data(self) -> tuple[str, str]:
        return self.key_edit.text().strip().upper(), self.path_edit.text().strip()

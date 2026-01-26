"""
Main Window for Entity Editor.

The main application window with menu bar, dockable panels, and central viewport.
"""

from PySide6.QtWidgets import (QMainWindow, QDockWidget, QFileDialog, QMessageBox,
                                QToolBar, QStatusBar, QLabel, QComboBox, QInputDialog)
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QAction, QKeySequence
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data import Entity, EntitySerializer, EntityDeserializer
from src.core import get_signal_hub
from src.core.state.editor_state import EditorState
from src.ui.widgets import ViewportWidget
from src.ui.panels import EntityPanel, BodyPartsPanel, HitboxPanel


class MainWindow(QMainWindow):
    """Main editor window."""
    
    def __init__(self):
        super().__init__()
        
        # Global State
        self._state = EditorState()
        
        # Local Window State
        self._current_filepath: str = None
        self._is_modified = False
        
        # Connect to State
        self._state.entity_changed.connect(self._on_entity_changed)
        
        # Connect to Signal Hub (Legacy / UI events)
        self._signal_hub = get_signal_hub()
        self._signal_hub.entity_modified.connect(self._on_entity_modified)
        self._signal_hub.entity_saved.connect(self._on_entity_saved)
        self._signal_hub.snap_value_changed.connect(self._on_snap_value_changed_external)
        
        # Setup UI
        self.setWindowTitle("Entity Editor")
        self.resize(1400, 900)
        
        self._setup_ui()
        self._setup_menus()
        self._setup_toolbar()
        self._setup_statusbar()
        
        # Initialize History via State (it does this internally but we want to hook up UI updates)
        # We need to listen to history changes to update Undo/Redo buttons.
        # HistoryService wraps HistoryManager. HistoryManager emits via SignalHub?
        # Let's check: HistoryManager uses SignalHub.undo_redo_state_changed.
        self._signal_hub.undo_redo_state_changed.connect(self._on_undo_redo_state_changed)
        
        # Create new entity by default
        self._new_entity()
    
    def _setup_ui(self):
        """Setup the main UI layout."""
        # Central viewport
        self._viewport = ViewportWidget()
        self.setCentralWidget(self._viewport)
        
        # Entity properties panel (left)
        self._entity_panel = EntityPanel()
        entity_dock = QDockWidget("Entity Properties", self)
        entity_dock.setWidget(self._entity_panel)
        self.addDockWidget(Qt.LeftDockWidgetArea, entity_dock)
        
        # Body parts panel (left, below entity)
        self._bodyparts_panel = BodyPartsPanel()
        bodyparts_dock = QDockWidget("Body Parts", self)
        bodyparts_dock.setWidget(self._bodyparts_panel)
        self.addDockWidget(Qt.LeftDockWidgetArea, bodyparts_dock)
        
        # Hitbox panel (right)
        self._hitbox_panel = HitboxPanel()
        hitbox_dock = QDockWidget("Hitboxes", self)
        hitbox_dock.setWidget(self._hitbox_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, hitbox_dock)
        
        # Store dock widgets for menu toggles
        self._dock_widgets = {
            'entity': entity_dock,
            'bodyparts': bodyparts_dock,
            'hitbox': hitbox_dock
        }
    
    def _setup_menus(self):
        """Setup menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        new_action = QAction("&New Entity", self)
        new_action.setShortcut(QKeySequence.New)
        new_action.triggered.connect(self._new_entity)
        file_menu.addAction(new_action)
        
        open_action = QAction("&Open...", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self._open_entity)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        save_action = QAction("&Save", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self._save_entity)
        file_menu.addAction(save_action)
        
        save_as_action = QAction("Save &As...", self)
        save_as_action.setShortcut(QKeySequence.SaveAs)
        save_as_action.triggered.connect(self._save_entity_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        export_json_action = QAction("Export as &JSON...", self)
        export_json_action.triggered.connect(self._export_as_json)
        file_menu.addAction(export_json_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        
        self._undo_action = QAction("&Undo", self)
        self._undo_action.setShortcut(QKeySequence.Undo)
        self._undo_action.setShortcutContext(Qt.ApplicationShortcut)
        self._undo_action.triggered.connect(self._on_undo)
        self._undo_action.setEnabled(False)
        edit_menu.addAction(self._undo_action)
        
        self._redo_action = QAction("&Redo", self)
        self._redo_action.setShortcut(QKeySequence.Redo)
        self._redo_action.setShortcutContext(Qt.ApplicationShortcut)
        self._redo_action.triggered.connect(self._on_redo)
        self._redo_action.setEnabled(False)
        edit_menu.addAction(self._redo_action)
        
        # View menu
        view_menu = menubar.addMenu("&View")
        
        for name, dock in self._dock_widgets.items():
            view_menu.addAction(dock.toggleViewAction())
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _setup_toolbar(self):
        """Setup toolbar."""
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)
        
        new_action = QAction("New", self)
        new_action.triggered.connect(self._new_entity)
        toolbar.addAction(new_action)
        
        open_action = QAction("Open", self)
        open_action.triggered.connect(self._open_entity)
        toolbar.addAction(open_action)
        
        save_action = QAction("Save", self)
        save_action.triggered.connect(self._save_entity)
        toolbar.addAction(save_action)
        
        toolbar.addSeparator()
        
        # Grid snap controls
        toolbar.addWidget(QLabel("  Grid Snap (px):"))
        
        self._snap_combo = QComboBox()
        self._snap_combo.addItems(["Off", "1", "2", "4", "8", "16", "32", "Custom..."])
        self._snap_combo.setCurrentIndex(1)  # Default: 1px
        self._snap_combo.currentTextChanged.connect(self._on_snap_changed)
        self._snap_combo.setToolTip("Grid snap in pixels")
        self._snap_combo.setFocusPolicy(Qt.ClickFocus)
        toolbar.addWidget(self._snap_combo)
        
        self._current_snap_value = 1.0
        
        toolbar.addSeparator()
        
        # Visual Grid controls
        toolbar.addWidget(QLabel("  Grid:"))
        
        self._grid_combo = QComboBox()
        self._grid_combo.addItems(["Off", "8", "16", "32", "64", "128", "Custom..."])
        self._grid_combo.setCurrentIndex(2)  # Default: 16px
        self._grid_combo.currentTextChanged.connect(self._on_grid_changed)
        self._grid_combo.setToolTip("Visual grid size in pixels")
        self._grid_combo.setFocusPolicy(Qt.ClickFocus)
        toolbar.addWidget(self._grid_combo)
    
    def _setup_statusbar(self):
        """Setup status bar."""
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)
        self._statusbar.showMessage("Ready")
    
    def _new_entity(self):
        """Create a new entity."""
        if not self._check_save_changes():
            return
        
        new_entity = Entity(name="NewEntity")
        self._current_filepath = None
        self._is_modified = False
        
        # Update State (This is the critical fix)
        self._state.set_entity(new_entity)
        
        self._update_window_title()
        self._statusbar.showMessage("New entity created")
    
    def _open_entity(self):
        """Open an existing entity."""
        if not self._check_save_changes():
            return
        
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open Entity",
            "",
            "Entity Definition (*.entdef);;All Files (*.*)"
        )
        
        if not filename:
            return
        
        try:
            entity = EntityDeserializer.load(filename)
            self._current_filepath = filename
            self._is_modified = False
            
            # Update State
            self._state.set_entity(entity)
            
            self._update_window_title()
            self._statusbar.showMessage(f"Opened: {Path(filename).name}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load entity:\n{str(e)}")
    
    def _save_entity(self):
        """Save the current entity."""
        if self._current_filepath:
            self._do_save(self._current_filepath)
        else:
            self._save_entity_as()
    
    def _save_entity_as(self):
        """Save the current entity with a new name."""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Entity As",
            "",
            "Entity Definition (*.entdef);;All Files (*.*)"
        )
        
        if filename:
            if not filename.endswith('.entdef'):
                filename += '.entdef'
            self._do_save(filename)
    
    def _do_save(self, filepath: str):
        """Perform the actual save operation."""
        entity = self._state.current_entity
        if not entity: return

        try:
            EntitySerializer.save(entity, filepath)
            self._current_filepath = filepath
            self._is_modified = False
            
            self._signal_hub.notify_entity_saved(filepath)
            self._update_window_title()
            self._statusbar.showMessage(f"Saved: {Path(filepath).name}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save entity:\n{str(e)}")
    
    def _export_as_json(self):
        """Export the current entity as JSON."""
        entity = self._state.current_entity
        if not entity: return
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Entity as JSON",
            "",
            "JSON Files (*.json);;All Files (*.*)"
        )
        
        if not filename: return
        
        if not filename.endswith('.json'):
            filename += '.json'
        
        try:
            EntitySerializer.save_json_debug(entity, filename)
            self._statusbar.showMessage(f"Exported to JSON: {Path(filename).name}")
            QMessageBox.information(
                self,
                "Export Successful",
                f"Entity exported to:\n{filename}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export entity:\n{str(e)}")
    
    def _on_snap_changed(self, text: str):
        """Handle grid snap value change."""
        if text == "Off":
            self._current_snap_value = 0.0
        elif text == "Custom...":
            value, ok = QInputDialog.getInt(self, "Custom Snap Value", "Enter snap value (pixels):", 8, 1, 128)
            if ok:
                self._current_snap_value = float(value)
                # Update combo to show custom value
                # This logic was removed in the provided diff, so I'm removing it too.
                # if self._snap_combo.count() > 7:
                #     self._snap_combo.removeItem(7)
                # self._snap_combo.addItem(str(value))
                # self._snap_combo.setCurrentIndex(7)
            else:
                # User cancelled, reset to previous
                self._snap_combo.setCurrentIndex(0)
                self._current_snap_value = 0.0
        else:
            self._current_snap_value = float(text)
        
        self._signal_hub.notify_snap_value_changed(self._current_snap_value)
        
        # Update status bar
        if self._current_snap_value > 0:
            self._statusbar.showMessage(f"Grid snap: {int(self._current_snap_value)}px (always active)", 3000)
        else:
            self._statusbar.showMessage("Grid snap: Off", 2000)
    
    def _on_snap_value_changed_external(self, value):
        # Sync combo if changed externally (e.g. from loaded prefs, though likely redundant)
        pass

    def _on_grid_changed(self, text: str):
        """Handle visual grid size change."""
        visible = True
        size = 16
        
        if text == "Off":
            visible = False
        elif text == "Custom...":
            value, ok = QInputDialog.getInt(self, "Custom Grid Size", "Enter grid size (pixels):", 16, 4, 256)
            if ok:
                size = value
            else:
                visible = self._state.grid_visible
                size = self._state.grid_size
        else:
            size = int(text)
            
        self._state.set_grid_settings(visible, size)

    def _check_save_changes(self) -> bool:
        """Check if there are unsaved changes and prompt user."""
        if not self._is_modified:
            return True
        
        reply = QMessageBox.question(
            self,
            "Unsaved Changes",
            "The entity has unsaved changes. Do you want to save them?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Save
        )
        
        if reply == QMessageBox.Save:
            self._save_entity()
            return not self._is_modified
        elif reply == QMessageBox.Discard:
            return True
        else:
            return False
    
    def _on_entity_changed(self, entity):
        """Handle entity change from State."""
        self._update_window_title()
        
    def _on_entity_modified(self):
        """Handle entity modification."""
        self._is_modified = True
        self._update_window_title()
    
    def _on_entity_saved(self, filepath: str):
        self._is_modified = False
        self._update_window_title()
    
    def _update_window_title(self):
        entity = self._state.current_entity
        title = "Entity Editor"
        
        if entity:
            if self._current_filepath:
                filename = Path(self._current_filepath).name
                title = f"{filename} - Entity Editor"
            else:
                title = f"{entity.name} - Entity Editor"
        
        if self._is_modified:
            title = f"*{title}"
        
        self.setWindowTitle(title)
    
    def _show_about(self):
        QMessageBox.about(self, "About Entity Editor", "Entity Editor v1.0\n\nA modular, extensible 2D entity editor.")
    
    def _on_undo(self):
        if self._state.history.can_undo():
            self._state.history.undo()
            # Status update handled via signal
    
    def _on_redo(self):
        if self._state.history.can_redo():
            self._state.history.redo()
            
    def _on_undo_redo_state_changed(self, can_undo: bool, can_redo: bool, undo_desc: str, redo_desc: str):
        self._undo_action.setEnabled(can_undo)
        self._redo_action.setEnabled(can_redo)
        
        if undo_desc:
            self._undo_action.setText(f"&Undo {undo_desc}")
            self._statusbar.showMessage(f"Undo available: {undo_desc}", 2000)
        else:
            self._undo_action.setText("&Undo")
        
        if redo_desc:
            self._redo_action.setText(f"&Redo {redo_desc}")
        else:
            self._redo_action.setText("&Redo")
    
    def get_history_manager(self) -> EditorState: # Changed return type to EditorState
        """Get the history manager for use by panels."""
        # Panels should now interact with EditorState directly or via its history service
        return self._state
    
    def closeEvent(self, event):
        """Handle window close event."""
        if self._check_save_changes():
            event.accept()
        else:
            event.ignore()

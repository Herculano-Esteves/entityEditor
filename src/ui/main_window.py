"""
Main Window for Entity Editor.

The main application window with menu bar, dockable panels, and central viewport.
"""

from PySide6.QtWidgets import (QMainWindow, QDockWidget, QFileDialog, QMessageBox,
                                QToolBar, QStatusBar)
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QAction, QKeySequence
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data import Entity, EntitySerializer, EntityDeserializer
from src.core import get_signal_hub
from src.ui.widgets import ViewportWidget
from src.ui.panels import EntityPanel, BodyPartsPanel, HitboxPanel


class MainWindow(QMainWindow):
    """Main editor window."""
    
    def __init__(self):
        super().__init__()
        
        # State
        self._current_entity: Entity = None
        self._current_filepath: str = None
        self._is_modified = False
        
        # Signal hub
        self._signal_hub = get_signal_hub()
        self._signal_hub.entity_modified.connect(self._on_entity_modified)
        self._signal_hub.entity_saved.connect(self._on_entity_saved)
        
        # Setup UI
        self.setWindowTitle("Entity Editor")
        self.resize(1400, 900)
        
        self._setup_ui()
        self._setup_menus()
        self._setup_toolbar()
        self._setup_statusbar()
        
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
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
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
    
    def _setup_statusbar(self):
        """Setup status bar."""
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)
        self._statusbar.showMessage("Ready")
    
    def _new_entity(self):
        """Create a new entity."""
        if not self._check_save_changes():
            return
        
        self._current_entity = Entity(name="NewEntity")
        self._current_filepath = None
        self._is_modified = False
        
        self._signal_hub.notify_entity_loaded(self._current_entity)
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
            self._current_entity = entity
            self._current_filepath = filename
            self._is_modified = False
            
            self._signal_hub.notify_entity_loaded(self._current_entity)
            self._update_window_title()
            self._statusbar.showMessage(f"Opened: {Path(filename).name}")
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to load entity:\n{str(e)}"
            )
    
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
            # Ensure .entdef extension
            if not filename.endswith('.entdef'):
                filename += '.entdef'
            
            self._do_save(filename)
    
    def _do_save(self, filepath: str):
        """Perform the actual save operation."""
        try:
            EntitySerializer.save(self._current_entity, filepath)
            self._current_filepath = filepath
            self._is_modified = False
            
            self._signal_hub.notify_entity_saved(filepath)
            self._update_window_title()
            self._statusbar.showMessage(f"Saved: {Path(filepath).name}")
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to save entity:\n{str(e)}"
            )
    
    def _check_save_changes(self) -> bool:
        """Check if there are unsaved changes and prompt user. Returns True if okay to proceed."""
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
            return not self._is_modified  # Only proceed if save was successful
        elif reply == QMessageBox.Discard:
            return True
        else:  # Cancel
            return False
    
    def _on_entity_modified(self):
        """Handle entity modification."""
        self._is_modified = True
        self._update_window_title()
    
    def _on_entity_saved(self, filepath: str):
        """Handle entity saved."""
        self._is_modified = False
        self._update_window_title()
    
    def _update_window_title(self):
        """Update window title."""
        title = "Entity Editor"
        
        if self._current_entity:
            if self._current_filepath:
                filename = Path(self._current_filepath).name
                title = f"{filename} - Entity Editor"
            else:
                title = f"{self._current_entity.name} - Entity Editor"
        
        if self._is_modified:
            title = f"*{title}"
        
        self.setWindowTitle(title)
    
    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About Entity Editor",
            "Entity Editor v1.0\n\n"
            "A modular, extensible 2D entity editor for game development.\n\n"
            "Features:\n"
            "• Visual entity editing\n"
            "• Body part management\n"
            "• Hitbox editing\n"
            "• UV mapping\n"
        )
    
    def closeEvent(self, event):
        """Handle window close event."""
        if self._check_save_changes():
            event.accept()
        else:
            event.ignore()

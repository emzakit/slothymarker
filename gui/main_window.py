import os
import webbrowser
from pathlib import Path
from PySide6.QtCore import Qt, QFileSystemWatcher
from PySide6.QtWidgets import (
    QMainWindow, QSplitter, QFileDialog, QMessageBox, 
    QStatusBar, QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel
)
from PySide6.QtGui import QAction, QDragEnterEvent, QDropEvent, QCloseEvent, QResizeEvent, QShortcut, QKeySequence

from app_controller import AppController
import parser
from gui.document_viewer import DocumentViewer
from gui.highlights_panel import HighlightsPanel
from gui.tutorial_sidebar import TutorialSidebar
from utils import resource_path # <-- IMPORT THE HELPER

class MainWindow(QMainWindow):
    # ... (no change in __init__ or most other methods)
    def __init__(self, theme_manager, controller: AppController):
        super().__init__()
        self.theme_manager = tm = theme_manager
        self.controller = controller
        
        self.setAcceptDrops(True)
        self.setWindowTitle(tm.get_text("window_title"))
        self.setGeometry(100, 100, 1400, 800)
        self.setWindowIcon(tm.get_icon("app"))
        
        self.highlight_color = self.theme_manager.get_value("colors.highlight_bg", "rgba(243, 156, 18, 0.5)")
        self.selection_color = self.theme_manager.get_value("colors.accent_pink_selection", "#E5007E")

        self.file_watcher = QFileSystemWatcher(self)
        self.file_watcher.fileChanged.connect(self._on_file_changed)
        
        self.setup_ui_structure()
        self.connect_signals()
        self.setup_menus()
        self.setStatusBar(QStatusBar(self))
        self.setup_shortcuts()
        self.populate_tutorials_and_load_default()

    def setup_ui_structure(self):
        central_widget = QWidget()
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 0, 10, 10)
        main_layout.setSpacing(10)

        self.sidebar = TutorialSidebar(self.theme_manager)
        self.doc_viewer = DocumentViewer(self.theme_manager)
        self.highlights_panel = HighlightsPanel(self.theme_manager)
        
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(self.doc_viewer)
        self.splitter.addWidget(self.highlights_panel)
        
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.splitter, 1)
        self.setCentralWidget(central_widget)
        
        self.drop_overlay = QWidget(self)
        self.drop_overlay.setObjectName("DropOverlay")
        overlay_layout = QVBoxLayout(self.drop_overlay)
        overlay_layout.setAlignment(Qt.AlignCenter)
        drop_label = QLabel(self.theme_manager.get_text("drop_overlay_text"))
        drop_label.setObjectName("DropOverlayLabel")
        overlay_layout.addWidget(drop_label)
        self.drop_overlay.hide()
        self.splitter.setSizes([int(self.width() * 0.6), int(self.width() * 0.4)])

    def connect_signals(self):
        self.controller.model_updated.connect(self._on_model_updated)
        self.controller.status_message_requested.connect(self.statusBar().showMessage)

        self.doc_viewer.open_requested.connect(self.open_file_dialog)
        self.doc_viewer.save_and_edit_requested.connect(self.edit_file_externally)
        self.doc_viewer.save_requested.connect(self.save_file)
        self.doc_viewer.close_requested.connect(self.close_file)
        self.doc_viewer.add_requested.connect(self.add_highlight)
        self.doc_viewer.highlight_activated_by_index.connect(self._select_highlight_in_list)
        self.doc_viewer.show_all_requested.connect(self._on_show_all_requested)

        self.highlights_panel.remove_highlights_requested.connect(self.controller.remove_highlights)
        self.highlights_panel.remove_all_highlights_requested.connect(self.controller.remove_all_highlights)
        self.highlights_panel.undo_requested.connect(self.controller.undo)
        self.highlights_panel.redo_requested.connect(self.controller.redo)
        self.highlights_panel.highlight_selected.connect(self._on_highlight_activated)
        self.highlights_panel.reorder_requested.connect(self.controller.reorder_highlights)
        self.highlights_panel.edit_highlight_requested.connect(self.controller.update_highlight_text)
        
        self.highlights_panel.export_panel.status_message_requested.connect(self.statusBar().showMessage)
        
        self.sidebar.tutorial_requested.connect(self._on_tutorial_requested)
        self.sidebar.license_requested.connect(self._on_license_requested)
        
    def setup_shortcuts(self):
        shortcut = QShortcut(QKeySequence.fromString("Ctrl+H"), self)
        shortcut.activated.connect(self.add_highlight)
        
    def setup_menus(self):
        tm = self.theme_manager
        file_menu = self.menuBar().addMenu(tm.get_text("menu_file"))
        open_action = QAction(tm.get_text("action_open"), self)
        open_action.triggered.connect(self.open_file_dialog)
        file_menu.addAction(open_action)
        close_action = QAction(tm.get_text("action_close"), self)
        close_action.triggered.connect(self.close_file)
        file_menu.addAction(close_action)
        file_menu.addSeparator()
        quit_action = QAction(tm.get_icon("quit"), tm.get_text("action_quit"), self)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

    def _on_model_updated(self, raw_text, highlights, document_mode, can_undo, can_redo):
        # MODIFIED: Check if the current file is a tutorial by checking its base path
        is_tutorial = False
        if self.controller.current_filepath:
             tutorial_base_path = os.path.normpath(resource_path("tutorials"))
             file_base_path = os.path.normpath(os.path.dirname(self.controller.current_filepath))
             is_tutorial = file_base_path == tutorial_base_path

        is_file_open = bool(self.controller.current_filepath)
        filename = os.path.basename(self.controller.current_filepath or "")

        if is_file_open:
            self.setWindowTitle(f"{self.theme_manager.get_text('window_title')} - {filename}")
        else:
            self.setWindowTitle(self.theme_manager.get_text('window_title'))
            self.statusBar().showMessage("Ready")

        self.doc_viewer.set_button_states(is_file_open, self.controller.is_modified(), is_tutorial)
        self.highlights_panel.set_editing_enabled(is_file_open, can_undo, can_redo)

        if not is_file_open:
            self.doc_viewer.clear_content()
            self.highlights_panel.clear_panel()
        else:
            self.highlights_panel.populate(highlights, filename, document_mode)
            self._render_document_view(raw_text, highlights)

    def _render_document_view(self, raw_text, highlights):
        # Get all selected highlights from the list widget
        selected_list_items = self.highlights_panel.list_widget.selectedItems()
        selected_highlights = [item.data(Qt.UserRole) for item in selected_list_items]

        # Jump to the text of the "current" (last clicked) item for navigation
        current_row = self.highlights_panel.list_widget.currentRow()
        if current_row != -1:
             sorted_highlights = self.highlights_panel.get_sorted_highlights()
             if 0 <= current_row < len(sorted_highlights):
                active_highlight = sorted_highlights[current_row]
                self.doc_viewer.jump_to_text(active_highlight.text.replace('\n', ' '))
        
        rendered_html = parser.render_document_with_highlights(raw_text, highlights, selected_highlights, self.highlight_color, self.selection_color)
        self.doc_viewer.set_content(rendered_html, raw_text, self.controller.document_mode)
        
        # Re-apply temporary highlights if a search term is active
        if self.controller.last_shown_search_term:
            self.doc_viewer.apply_temporary_highlights(self.controller.last_shown_search_term)

    def _on_show_all_requested(self, search_term: str):
        self.controller.last_shown_search_term = search_term
        self.doc_viewer.apply_temporary_highlights(search_term)

    def add_highlight(self):
        # If a "Show All" search is active, highlight all those terms.
        if self.controller.last_shown_search_term:
            search_term = self.controller.last_shown_search_term
            self.controller.last_shown_search_term = None
            self.doc_viewer.clear_temporary_highlights()
            self.controller.highlight_all_occurrences(search_term)
        # Otherwise, highlight the current user selection.
        else:
            selected_text = self.doc_viewer.get_selected_text()
            if selected_text:
                cursor = self.doc_viewer.text_browser.textCursor()
                self.controller.add_highlight(selected_text, cursor.selectionStart(), "")

    def edit_file_externally(self):
        title = self.theme_manager.get_text("dialog_edit_file_title")
        text = self.theme_manager.get_text("dialog_edit_file_text")
        reply = QMessageBox.information(self, title, text, QMessageBox.Ok | QMessageBox.Cancel)
        if reply == QMessageBox.Cancel:
            return
        
        saved_path = self.save_file(with_header=True)
        if saved_path:
            try:
                webbrowser.open(Path(saved_path).as_uri())
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not open file in external editor.\n\nDetails: {e}")

    def open_file_dialog(self):
        if not self._prompt_to_save(): return
        filepath, _ = QFileDialog.getOpenFileName(self, "Open Document", "", "All Supported Files (*.txt *.md *.docx *.pdf)")
        if filepath:
            self._process_file_with_controller(filepath)

    def save_file(self, with_header=False) -> str | None:
        if not self.controller.current_filepath: return None
        
        content = self.controller.get_content_for_saving(include_header=with_header)
        default_filename = os.path.splitext(os.path.basename(self.controller.current_filepath))[0] + "_edited.txt"
        
        filepath, _ = QFileDialog.getSaveFileName(self, "Save Highlights", default_filename, "Text Files (*.txt *.md)")
        
        if not filepath: return None
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f: f.write(content)
            self.statusBar().showMessage(f"Successfully saved to {os.path.basename(filepath)}", 3000)
            self.controller.confirm_save()
            return filepath
        except IOError as e:
            QMessageBox.critical(self, "Error", f"Failed to save file: {e}")
            return None

    def close_file(self):
        if not self._prompt_to_save(): return
        current_file = self.controller.current_filepath
        if current_file and self.file_watcher.files():
            self.file_watcher.removePath(current_file)
        self.controller.close_file()
        self.doc_viewer.clear_temporary_highlights()

    def _process_file_with_controller(self, filepath):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            if self.file_watcher.files():
                self.file_watcher.removePaths(self.file_watcher.files())
            
            self.controller.process_file(filepath)
            
            # MODIFIED: Check if the file is a tutorial before adding to watcher
            tutorial_base_path = os.path.normpath(resource_path("tutorials"))
            file_base_path = os.path.normpath(os.path.dirname(filepath))
            if file_base_path != tutorial_base_path:
                self.file_watcher.addPath(filepath)
                
        except ValueError as e:
            QMessageBox.critical(self, "Error Processing File", f"Could not process the file.\n\nDetails: {e}")
        finally:
            QApplication.restoreOverrideCursor()

    def _on_file_changed(self, path):
        if path == self.controller.current_filepath:
            self.statusBar().showMessage(self.theme_manager.get_text("status_file_reloaded"), 5000)
            self._process_file_with_controller(path)

    def populate_tutorials_and_load_default(self):
        # MODIFIED: Use resource_path to locate the tutorials directory.
        tutorial_dir = resource_path("tutorials")
        try:
            all_files = [f for f in os.listdir(tutorial_dir) if f.endswith('.txt') and not f.startswith('.')]
            def sort_key(filename):
                if 'Main' in filename: return "0"
                if 'SRT' in filename and 'Simple' in filename: return "1"
                if 'SRT' in filename and 'Styled' in filename: return "2"
                if 'Transcript' in filename: return "3"
                if 'VTT' in filename and 'Simple' in filename: return "4"
                if 'VTT' in filename and 'Styled' in filename: return "5"
                return filename
            sorted_filenames = sorted(all_files, key=sort_key)
            full_paths = [os.path.join(tutorial_dir, f) for f in sorted_filenames]
            self.sidebar.populate(full_paths)
            
            # MODIFIED: Use resource_path for the default tutorial file.
            default_tutorial_relative = self.theme_manager.get_value("app_config.tutorial_file")
            default_tutorial_abs = resource_path(default_tutorial_relative)
            if os.path.exists(default_tutorial_abs):
                self._process_file_with_controller(default_tutorial_abs)
        except FileNotFoundError:
            QMessageBox.warning(self, "Tutorials Not Found", f"The '{tutorial_dir}' directory is missing.")
            self.controller.close_file()
            
    def _on_tutorial_requested(self, filepath: str):
        if not self._prompt_to_save(): return
        if os.path.exists(filepath):
            self._process_file_with_controller(filepath)

    def _on_license_requested(self):
        # MODIFIED: Use resource_path to locate the readme.html file.
        readme_path = Path(resource_path("readme.html")).resolve()
        if readme_path.exists(): webbrowser.open(readme_path.as_uri())
        else: QMessageBox.warning(self, "Help File Not Found", "Could not find readme.html.")

    # ... (no more changes in the remaining methods)
    def _select_highlight_in_list(self, original_index: int):
        """
        Receives an index from the document viewer (relative to the original list)
        and selects the corresponding item in the highlights panel list widget.
        """
        if not (0 <= original_index < len(self.controller.highlights)):
            return
            
        highlight_to_find = self.controller.highlights[original_index]
        sorted_highlights = self.highlights_panel.get_sorted_highlights()
        
        try:
            sorted_index = sorted_highlights.index(highlight_to_find)
            # This updates the list widget's selection visually
            self.highlights_panel.select_highlight(sorted_index)
            # We still need to call render to update the document viewer's colors
            self._render_document_view(self.controller.raw_text, self.controller.highlights)
        except ValueError:
            # This can happen if the lists are out of sync, but should be rare.
            pass

    def _on_highlight_activated(self, sorted_index: int):
        # This is now only triggered by the user clicking in the right-hand list.
        # The list widget selection is already updated, so we just need to re-render the document.
        self._render_document_view(self.controller.raw_text, self.controller.highlights)

    def _prompt_to_save(self):
        if not self.controller.is_modified(): return True
        filename = os.path.basename(self.controller.current_filepath)
        reply = QMessageBox.question(self, "Save Changes?", f"You have unsaved changes in '{filename}'.\n\nWould you like to save them before closing?", QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        if reply == QMessageBox.Save: self.save_file(); return not self.controller.is_modified()
        return reply != QMessageBox.Cancel

    def closeEvent(self, event: QCloseEvent):
        if self._prompt_to_save(): event.accept()
        else: event.ignore()

    def dropEvent(self, event: QDropEvent):
        self.drop_overlay.hide()
        if event.mimeData().hasUrls():
            if not self._prompt_to_save(): return
            filepath = event.mimeData().urls()[0].toLocalFile()
            self._process_file_with_controller(filepath)
            
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls(): self.drop_overlay.show(); event.acceptProposedAction()
    def dragLeaveEvent(self, event): self.drop_overlay.hide()
    def resizeEvent(self, event: QResizeEvent): self.drop_overlay.setGeometry(self.centralWidget().geometry()); super().resizeEvent(event)
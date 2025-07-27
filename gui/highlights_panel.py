from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QWidget, QGroupBox, QVBoxLayout, QPushButton, QHBoxLayout, QMessageBox, QLabel
from gui.widgets import HighlightListWidget
from gui.export_panel import ExportPanel
from gui.word_stats_panel import WordStatsPanel
from gui.duration_stats_panel import DurationStatsPanel

class HighlightsPanel(QWidget):
    highlight_selected = Signal(int)
    remove_highlights_requested = Signal(list) 
    remove_all_highlights_requested = Signal()
    undo_requested = Signal()
    redo_requested = Signal()
    reorder_requested = Signal(list)
    edit_highlight_requested = Signal(object, str)
    
    def __init__(self, theme_manager, parent=None):
        super().__init__(parent)
        self.theme_manager = tm = theme_manager
        self._sorted_highlights = []
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        groupbox = QGroupBox(tm.get_text("group_highlights"))
        group_layout = QVBoxLayout(groupbox)
        
        top_button_bar_layout = QHBoxLayout()
        self.undo_button = QPushButton(tm.get_text("button_undo"))
        self.redo_button = QPushButton(tm.get_text("button_redo"))
        self.remove_button = QPushButton(tm.get_text("button_remove_highlight"))
        self.remove_all_button = QPushButton(tm.get_text("button_remove_all"))

        self.undo_button.clicked.connect(self.undo_requested.emit)
        self.redo_button.clicked.connect(self.redo_requested.emit)
        self.remove_button.clicked.connect(self._on_remove_clicked)
        self.remove_all_button.clicked.connect(self._on_remove_all_clicked)
        
        top_button_bar_layout.addWidget(self.undo_button)
        top_button_bar_layout.addWidget(self.redo_button)
        top_button_bar_layout.addStretch()
        top_button_bar_layout.addWidget(self.remove_button)
        top_button_bar_layout.addWidget(self.remove_all_button)

        self.mode_indicator_label = QLabel()
        self.mode_indicator_label.setAlignment(Qt.AlignCenter)
        self.mode_indicator_label.setObjectName("HelperLabel")
        self.mode_indicator_label.setVisible(False)
        
        self.helper_label = QLabel(tm.get_text("highlights_panel_helper"))
        self.helper_label.setAlignment(Qt.AlignCenter)
        self.helper_label.setObjectName("HelperLabel")
        self.helper_label.setWordWrap(True)
        self.helper_label.setVisible(False)

        self.list_widget = HighlightListWidget(self.theme_manager, self)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        self.list_widget.reorder_requested.connect(self.reorder_requested.emit)
        self.list_widget.edit_requested.connect(self.edit_highlight_requested.emit)

        self.word_stats_panel = WordStatsPanel(self.theme_manager)
        self.duration_stats_panel = DurationStatsPanel(self.theme_manager)
        self.export_panel = ExportPanel(self.theme_manager, self.list_widget)
        
        group_layout.addLayout(top_button_bar_layout)
        group_layout.addWidget(self.mode_indicator_label)
        group_layout.addWidget(self.helper_label)
        group_layout.addWidget(self.list_widget, 1)
        group_layout.addWidget(self.word_stats_panel)
        group_layout.addWidget(self.duration_stats_panel)
        group_layout.addWidget(self.export_panel)
        main_layout.addWidget(groupbox)
        self.set_editing_enabled(is_file_open=False, can_undo=False, can_redo=False)

    def _on_item_clicked(self, item):
        self.highlight_selected.emit(self.list_widget.row(item))
        
    def _on_selection_changed(self):
        selected_items = self.list_widget.selectedItems()
        self.remove_button.setEnabled(bool(selected_items))
        self.export_panel.set_copy_selected_enabled(bool(selected_items))
    
    def _on_remove_clicked(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            return
        highlights_to_remove = [item.data(Qt.UserRole) for item in selected_items]
        self.remove_highlights_requested.emit(highlights_to_remove)

    def _on_remove_all_clicked(self):
        if not self._sorted_highlights: return
        reply = QMessageBox.question(self,
            self.theme_manager.get_text("dialog_remove_all_title"),
            self.theme_manager.get_text("dialog_remove_all_text"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.remove_all_highlights_requested.emit()

    def get_sorted_highlights(self):
        return self._sorted_highlights

    def select_highlight(self, index: int):
        if 0 <= index < self.list_widget.count():
            # Clear existing selection before setting the new one
            self.list_widget.clearSelection()
            self.list_widget.setCurrentRow(index)

    def populate(self, highlights: list, filename: str, mode: str):
        if mode == "simple":
            self._sorted_highlights = sorted(highlights, key=lambda h: h.sort_key)
        else:
            self._sorted_highlights = sorted([h for h in highlights if h.start_time >= 0], key=lambda h: h.start_time)
        
        self.list_widget.populate(self._sorted_highlights, mode)
        self.export_panel.set_data(self._sorted_highlights, filename, mode)
        
        if mode in ["[SRT]", "[VTT]"]:
            self.word_stats_panel.clear()
            self.duration_stats_panel.update_stats_from_highlights(self._sorted_highlights)
        else:
            self.duration_stats_panel.clear()
            combined_text = "\n\n".join(h.text for h in self._sorted_highlights)
            self.word_stats_panel.update_stats(combined_text)
            
        self.mode_indicator_label.setText(self.theme_manager.get_text("mode_indicator_label", mode=mode.upper()))

    def clear_panel(self):
        self._sorted_highlights = []
        self.list_widget.clear()
        self.export_panel.set_data([], "", "simple")
        self.word_stats_panel.clear()
        self.duration_stats_panel.clear()
        self.set_editing_enabled(is_file_open=False, can_undo=False, can_redo=False)
        
    def set_editing_enabled(self, is_file_open: bool, can_undo: bool, can_redo: bool):
        has_selection = bool(self.list_widget.selectedItems())
        has_items = self.list_widget.count() > 0
        self.remove_button.setEnabled(is_file_open and has_selection)
        self.remove_all_button.setEnabled(is_file_open and has_items)
        self.undo_button.setEnabled(can_undo)
        self.redo_button.setEnabled(can_redo)
        self.helper_label.setVisible(is_file_open and has_items)
        self.mode_indicator_label.setVisible(is_file_open)
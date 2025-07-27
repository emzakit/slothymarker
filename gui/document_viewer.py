from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QTextBrowser, QGroupBox, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit
from PySide6.QtGui import QTextCursor, QTextDocument, QTextCharFormat, QColor
from gui.widgets import ContextMenuTextBrowser
from gui.word_stats_panel import WordStatsPanel
from gui.duration_stats_panel import DurationStatsPanel

class DocumentViewer(QWidget):
    open_requested = Signal()
    save_and_edit_requested = Signal()
    save_requested = Signal()
    close_requested = Signal()
    add_requested = Signal()
    highlight_activated_by_index = Signal(int)
    show_all_requested = Signal(str)

    def __init__(self, theme_manager, parent=None):
        super().__init__(parent)
        self.theme_manager = theme_manager
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.groupbox = QGroupBox(self.theme_manager.get_text("group_document"))
        group_layout = QVBoxLayout(self.groupbox)
        
        self._setup_temporary_highlight_format()

        button_bar = QWidget()
        button_layout = QHBoxLayout(button_bar)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(10)

        self.open_button = QPushButton(self.theme_manager.get_text("button_open_document"))
        self.edit_button = QPushButton(self.theme_manager.get_text("button_edit_document"))
        self.save_button = QPushButton(self.theme_manager.get_text("button_save_document"))
        self.close_button = QPushButton(self.theme_manager.get_text("button_close_document"))
        self.add_button = QPushButton(self.theme_manager.get_text("button_add_highlight"))
        
        self.open_button.clicked.connect(self.open_requested.emit)
        self.edit_button.clicked.connect(self.save_and_edit_requested.emit)
        self.save_button.clicked.connect(self.save_requested.emit)
        self.close_button.clicked.connect(self.close_requested.emit)
        self.add_button.clicked.connect(self.add_requested.emit)

        button_layout.addWidget(self.open_button)
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.close_button)
        button_layout.addStretch()
        button_layout.addWidget(self.add_button)
        
        search_bar = QWidget()
        search_layout = QHBoxLayout(search_bar)
        search_layout.setContentsMargins(0, 5, 0, 5)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search document...")
        self.search_input.returnPressed.connect(self._find_next)
        self.prev_button = QPushButton("Previous")
        self.next_button = QPushButton("Next")
        self.show_all_button = QPushButton("Show All")
        
        self.prev_button.clicked.connect(self._find_prev)
        self.next_button.clicked.connect(self._find_next)
        self.show_all_button.clicked.connect(self._on_show_all)
        
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.prev_button)
        search_layout.addWidget(self.next_button)
        search_layout.addWidget(self.show_all_button)

        self.text_browser = ContextMenuTextBrowser(self.theme_manager, self)
        self.text_browser.setOpenExternalLinks(False)
        self.text_browser.anchorClicked.connect(self._on_anchor_clicked)
        
        self.word_stats_panel = WordStatsPanel(self.theme_manager)
        self.duration_stats_panel = DurationStatsPanel(self.theme_manager)

        group_layout.addWidget(button_bar)
        group_layout.addWidget(search_bar)
        group_layout.addWidget(self.text_browser)
        group_layout.addWidget(self.word_stats_panel)
        group_layout.addWidget(self.duration_stats_panel)
        
        main_layout.addWidget(self.groupbox)
        self.show_placeholder_message()
        self.search_input.setEnabled(False)
        
    def _setup_temporary_highlight_format(self):
        self._extra_selections = []
        self._temp_highlight_format = QTextCharFormat()
        self._temp_highlight_format.setBackground(QColor("#D2B4DE")) # A light purple color
        self._temp_highlight_format.setForeground(QColor("black"))
        
    def set_button_states(self, is_file_open: bool, is_modified: bool, is_tutorial: bool):
        self.open_button.setEnabled(True)
        self.edit_button.setEnabled(is_file_open and not is_tutorial)
        self.save_button.setEnabled(is_file_open and is_modified and not is_tutorial)
        self.close_button.setEnabled(is_file_open)
        self.add_button.setEnabled(is_file_open)
        self.search_input.setEnabled(is_file_open)
        self.prev_button.setEnabled(is_file_open)
        self.next_button.setEnabled(is_file_open)
        self.show_all_button.setEnabled(is_file_open)

    def _find(self, backwards=False):
        self.clear_temporary_highlights()
        query = self.search_input.text()
        if not query: return
        find_flags = QTextDocument.FindFlag.FindBackward if backwards else QTextDocument.FindFlag(0)
        if not self.text_browser.find(query, find_flags):
            # Wrap around if not found
            cursor = self.text_browser.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start if not backwards else QTextCursor.MoveOperation.End)
            self.text_browser.setTextCursor(cursor)
            self.text_browser.find(query, find_flags)


    def _find_next(self):
        self._find()

    def _find_prev(self):
        self._find(backwards=True)

    def _on_show_all(self):
        query = self.search_input.text()
        if query:
            self.show_all_requested.emit(query)

    def apply_temporary_highlights(self, search_term: str):
        self.clear_temporary_highlights()
        if not search_term: return
        
        doc = self.text_browser.document()
        cursor = QTextCursor(doc)
        
        while not cursor.isNull() and not cursor.atEnd():
            cursor = doc.find(search_term, cursor) # Case-insensitivity is default
            if not cursor.isNull():
                selection = QTextBrowser.ExtraSelection()
                selection.format = self._temp_highlight_format
                selection.cursor = cursor
                self._extra_selections.append(selection)

        self.text_browser.setExtraSelections(self._extra_selections)

    def clear_temporary_highlights(self):
        self._extra_selections.clear()
        self.text_browser.setExtraSelections(self._extra_selections)

    def get_selected_text(self) -> str:
        cursor = self.text_browser.textCursor()
        return cursor.selection().toPlainText().strip() if cursor.hasSelection() else ""

    def _on_anchor_clicked(self, url):
        href = url.toString()
        if href.startswith("slothy:highlight_"):
            try:
                index = int(href.split("_")[1])
                self.highlight_activated_by_index.emit(index)
            except (IndexError, ValueError): pass

    def show_placeholder_message(self):
        header = self.theme_manager.get_text('placeholder_header')
        body = self.theme_manager.get_text('placeholder_body')
        placeholder_html = f"<div style='text-align: center;'><p id='PlaceholderHeader'>{header}</p><p id='PlaceholderBody'>{body}</p></div>"
        self.text_browser.setHtml(placeholder_html)

    def set_content(self, rendered_html: str, raw_text: str, mode: str):
        self.clear_temporary_highlights()
        v_scrollbar = self.text_browser.verticalScrollBar()
        scroll_position = v_scrollbar.value()
        self.text_browser.setHtml(rendered_html)
        v_scrollbar.setValue(scroll_position)
        
        if mode in ["[SRT]", "[VTT]"]:
            self.word_stats_panel.clear()
            self.duration_stats_panel.update_stats_from_text(raw_text)
        else:
            self.duration_stats_panel.clear()
            self.word_stats_panel.update_stats(raw_text)

    def jump_to_text(self, text: str):
        self.text_browser.moveCursor(QTextCursor.MoveOperation.Start)
        self.text_browser.find(text)

    def clear_content(self):
        self.clear_temporary_highlights()
        self.show_placeholder_message()
        self.word_stats_panel.clear()
        self.duration_stats_panel.clear()
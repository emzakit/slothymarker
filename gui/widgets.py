from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QTextBrowser, QListWidget, QListWidgetItem, QMenu, QApplication, QAbstractItemView
from PySide6.QtGui import QAction, QColor, QBrush

class ContextMenuTextBrowser(QTextBrowser):
    def __init__(self, theme_manager, parent=None):
        super().__init__(parent)
        self.theme_manager = theme_manager
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def show_context_menu(self, pos):
        menu = QMenu(self)
        copy_action = QAction(self.theme_manager.get_text("context_menu_copy"), self)
        copy_action.triggered.connect(self.copy)
        copy_action.setEnabled(self.textCursor().hasSelection())
        menu.addAction(copy_action)
        menu.exec(self.mapToGlobal(pos))


class HighlightListWidget(QListWidget):
    reorder_requested = Signal(list)
    edit_requested = Signal(object, str)

    def __init__(self, theme_manager, parent=None):
        super().__init__(parent)
        self.theme_manager = theme_manager
        self._is_simple_mode = True
        
        self.setWordWrap(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(self.DragDropMode.InternalMove)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection) # Enable multi-select
        
        self.itemChanged.connect(self._on_item_edited)
        self.model().rowsMoved.connect(self._on_rows_moved)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def populate(self, highlights: list, mode: str):
        self.blockSignals(True)
        self.clear()
        
        self._is_simple_mode = (mode == "simple")
        self.setDragEnabled(self._is_simple_mode)

        for h in highlights:
            item = QListWidgetItem(h.display_text)
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            item.setData(Qt.UserRole, h)
            self.addItem(item)
            
        self.blockSignals(False)

    def _on_item_edited(self, item):
        original_highlight = item.data(Qt.UserRole)
        new_text = item.text()
        self.edit_requested.emit(original_highlight, new_text)

    def _on_rows_moved(self, parent, start, end, dest, row):
        if not self._is_simple_mode: return
        new_order_highlights = [self.item(i).data(Qt.UserRole) for i in range(self.count())]
        self.reorder_requested.emit(new_order_highlights)
        
    def _show_context_menu(self, pos):
        item = self.itemAt(pos)
        if not item: return

        menu = QMenu(self)
        copy_action = menu.addAction("Copy")
        
        selected_items = self.selectedItems()
        if len(selected_items) > 1:
            copy_action.setText(f"Copy {len(selected_items)} items")
            copy_action.triggered.connect(lambda: QApplication.clipboard().setText("\n\n".join(i.text() for i in selected_items)))
        else:
            copy_action.triggered.connect(lambda: QApplication.clipboard().setText(item.text()))
        
        menu.exec(self.mapToGlobal(pos))
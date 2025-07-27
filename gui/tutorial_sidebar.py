import os
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QFrame
from PySide6.QtGui import QIcon

class TutorialSidebar(QWidget):
    tutorial_requested = Signal(str)
    license_requested = Signal()

    def __init__(self, theme_manager, parent=None):
        super().__init__(parent)
        self.tm = theme_manager
        self.setFixedWidth(220)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 10, 0, 0)
        self.main_layout.setSpacing(10)
        
        self.main_layout.addStretch()

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        self.main_layout.addWidget(separator)
        
        self.license_button = QPushButton(self.tm.get_icon("help"), self.tm.get_text("btn_help_license"))
        self.license_button.setObjectName("SidebarButton")
        self.license_button.clicked.connect(self.license_requested.emit)
        self.main_layout.addWidget(self.license_button)

    def _clear_layout(self):
        # Clears only the tutorial buttons, leaving the permanent widgets
        for i in reversed(range(self.main_layout.count())):
            item = self.main_layout.itemAt(i)
            if item and item.widget() and item.widget() not in [self.license_button, self.main_layout.itemAt(self.main_layout.count() - 2).widget()]:
                 item.widget().deleteLater()

    def _format_button_text(self, filepath: str) -> str:
        """Creates a button label from the raw filename, without the extension."""
        filename_with_ext = os.path.basename(filepath)
        # Use os.path.splitext to reliably remove the last extension
        button_text, _ = os.path.splitext(filename_with_ext)
        # Add a leading space for alignment with the icon
        return f' {button_text}'

    def populate(self, tutorial_paths: list[str]):
        """Clears and populates the sidebar with buttons for each tutorial."""
        self._clear_layout()
        icon = self.tm.get_icon("tutorial_file")
        
        # Insert new buttons at the top of the layout
        for path in reversed(tutorial_paths):
            button_text = self._format_button_text(path)
            btn = QPushButton(icon, button_text)
            btn.setObjectName("SidebarButton")
            btn.clicked.connect(lambda checked=False, p=path: self.tutorial_requested.emit(p))
            self.main_layout.insertWidget(0, btn)
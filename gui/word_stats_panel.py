import math
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QFrame

def _format_seconds(seconds: float) -> str:
    """Formats a duration in seconds into a human-readable string (e.g., 1m 23s)."""
    if seconds < 0: seconds = 0
    if seconds < 60:
        return f"{math.ceil(seconds)}s"
    minutes = math.floor(seconds / 60)
    remaining_seconds = math.ceil(seconds % 60)
    return f"{int(minutes)}m {int(remaining_seconds)}s"

class WordStatsPanel(QWidget):
    """A widget to display text statistics like word count and reading time."""
    def __init__(self, theme_manager, parent=None):
        super().__init__(parent)
        self.setObjectName("StatsPanel")
        self.theme_manager = theme_manager

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(5, 10, 5, 10)
        main_layout.setSpacing(10)

        self.words_label = self._create_label()
        self.time90_label = self._create_label()
        self.time130_label = self._create_label()
        self.time160_label = self._create_label()

        main_layout.addWidget(self.words_label)
        main_layout.addStretch()
        main_layout.addWidget(self._create_separator())
        main_layout.addWidget(self.time90_label)
        main_layout.addWidget(self._create_separator())
        main_layout.addWidget(self.time130_label)
        main_layout.addWidget(self._create_separator())
        main_layout.addWidget(self.time160_label)
        
        self.clear()

    def _create_label(self) -> QLabel:
        label = QLabel()
        label.setObjectName("StatsLabel")
        return label

    def _create_separator(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setFrameShadow(QFrame.Sunken)
        return sep

    def update_stats(self, text: str):
        if not text or not text.strip():
            self.clear()
            return

        word_count = len(text.split())
        self.words_label.setText(self.theme_manager.get_text("stats_panel.words", count=word_count))
        self.time90_label.setText(self.theme_manager.get_text("stats_panel.wpm_rate", wpm=90, duration=_format_seconds((word_count / 90.0) * 60)))
        self.time130_label.setText(self.theme_manager.get_text("stats_panel.wpm_rate", wpm=130, duration=_format_seconds((word_count / 130.0) * 60)))
        self.time160_label.setText(self.theme_manager.get_text("stats_panel.wpm_rate", wpm=160, duration=_format_seconds((word_count / 160.0) * 60)))
        self.setVisible(True)

    def clear(self):
        self.setVisible(False)
import re
import math
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel

def _time_to_seconds(time_str: str) -> float:
    time_str = time_str.strip().replace(',', '.')
    try:
        parts = list(map(float, time_str.split(':')))
        if len(parts) == 3: return parts[0] * 3600 + parts[1] * 60 + parts[2]
        if len(parts) == 2: return parts[0] * 60 + parts[1]
    except (ValueError, IndexError):
        return -1.0
    return -1.0

def _parse_duration_from_line(line: str) -> float:
    """Parses a full timestamp line (e.g., 00:01.. --> 00:02..) and returns the duration."""
    parts = line.split('-->')
    if len(parts) != 2:
        return 0.0
    
    start_time = _time_to_seconds(parts[0])
    end_time = _time_to_seconds(parts[1])
    
    if start_time >= 0 and end_time > start_time:
        return end_time - start_time
    return 0.0

def _format_seconds(seconds: float) -> str:
    if seconds < 0: seconds = 0
    if seconds < 60:
        return f"{math.ceil(seconds)}s"
    minutes = math.floor(seconds / 60)
    remaining_seconds = math.ceil(seconds % 60)
    return f"{int(minutes)}m {int(remaining_seconds)}s"

class DurationStatsPanel(QWidget):
    """A widget to display total duration from timestamps."""
    def __init__(self, theme_manager, parent=None):
        super().__init__(parent)
        self.setObjectName("StatsPanel")
        self.theme_manager = theme_manager

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(5, 10, 5, 10)

        self.duration_label = QLabel()
        self.duration_label.setObjectName("StatsLabel")
        
        main_layout.addWidget(self.duration_label)
        main_layout.addStretch()
        self.clear()

    def update_stats_from_text(self, text: str):
        """Calculates total duration from all timestamp lines in a raw text document."""
        total_duration = 0
        for line in text.split('\n'):
            if '-->' in line:
                total_duration += _parse_duration_from_line(line)
        
        if total_duration > 0:
            self.duration_label.setText(self.theme_manager.get_text("stats_panel.duration", duration=_format_seconds(total_duration)))
            self.setVisible(True)
        else:
            self.clear()

    def update_stats_from_highlights(self, highlights: list):
        """Calculates total duration from a list of highlights."""
        total_duration = 0
        for h in highlights:
            # The display_text contains the timestamp line
            for line in h.display_text.split('\n'):
                if '-->' in line:
                    total_duration += _parse_duration_from_line(line)
                    break # Move to next highlight
        
        if total_duration > 0:
            self.duration_label.setText(self.theme_manager.get_text("stats_panel.duration", duration=_format_seconds(total_duration)))
            self.setVisible(True)
        else:
            self.clear()

    def clear(self):
        self.setVisible(False)
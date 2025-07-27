import os
import re
from datetime import datetime, timedelta
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget, QGroupBox, QHBoxLayout, QPushButton,
    QApplication, QFileDialog, QMessageBox
)

def _seconds_to_srt_time(seconds: float) -> str:
    if seconds < 0: seconds = 0
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    milliseconds = int(td.microseconds / 1000)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{secs:02},{milliseconds:03}"

def _seconds_to_vtt_time(seconds: float) -> str:
    if seconds < 0: seconds = 0
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    milliseconds = int(td.microseconds / 1000)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{secs:02}.{milliseconds:03}"

class ExportPanel(QWidget):
    status_message_requested = Signal(str, int)
    def __init__(self, theme_manager, list_widget, parent=None):
        super().__init__(parent)
        self.theme_manager = tm = theme_manager
        self._list_widget = list_widget
        self._highlights = []
        self._current_filename = "Document"
        self._document_mode = "simple"

        layout = QHBoxLayout(self); layout.setContentsMargins(0, 0, 0, 0)
        groupbox = QGroupBox(tm.get_text("export_panel_title")); groupbox.setObjectName("ExportPanelGroupBox")
        groupbox_layout = QHBoxLayout(groupbox)

        self.copy_btn = self._create_button(tm.get_text("export_button_copy"), "copy", self.copy_all_highlights)
        self.copy_selected_btn = self._create_button(tm.get_text("export_button_copy_selected"), "copy_selected", self.copy_selected_highlights)
        self.txt_btn = self._create_button(tm.get_text("export_button_txt"), "txt", self.export_highlights_txt)
        self.transcript_btn = self._create_button("Export", "srt", self.export_transcript)

        groupbox_layout.addWidget(self.copy_btn)
        groupbox_layout.addWidget(self.copy_selected_btn)
        groupbox_layout.addWidget(self.txt_btn)
        groupbox_layout.addWidget(self.transcript_btn)
        layout.addWidget(groupbox)
        self.set_enabled(False)

    def _create_button(self, text, tooltip_key, on_click_slot):
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor); btn.setObjectName("ExportButton")
        btn.setToolTip(self.theme_manager.get_value(f"tooltips.export_panel_{tooltip_key}"))
        btn.clicked.connect(on_click_slot)
        return btn

    def set_data(self, highlights: list, filename: str, mode: str):
        self._highlights = highlights
        self._current_filename = filename
        self._document_mode = mode
        has_timestamps = any(h.start_time >= 0 for h in highlights)

        is_subtitle_mode = mode in ["[SRT]", "[VTT]"]
        self.transcript_btn.setVisible(is_subtitle_mode)

        if mode == "[SRT]":
            self.transcript_btn.setText(self.theme_manager.get_text("export_button_srt"))
            self.transcript_btn.setEnabled(has_timestamps)
        elif mode == "[VTT]":
            self.transcript_btn.setText(self.theme_manager.get_text("export_button_vtt"))
            self.transcript_btn.setEnabled(has_timestamps)
        
        self.set_enabled(bool(highlights))
        self.set_copy_selected_enabled(False) # Default to disabled until a selection is made

    def set_enabled(self, enabled: bool):
        self.copy_btn.setEnabled(enabled)
        self.txt_btn.setEnabled(enabled)
        if not enabled:
            self.transcript_btn.setEnabled(False)
            self.copy_selected_btn.setEnabled(False)

    def set_copy_selected_enabled(self, enabled: bool):
        self.copy_selected_btn.setEnabled(enabled)
            
    def _get_sorted_display_texts(self, highlight_list) -> list[str]:
        if self._document_mode == "simple":
            sorted_highlights = sorted([h for h in highlight_list if h.start_pos != -1], key=lambda h: h.start_pos)
        else:
            sorted_highlights = sorted([h for h in highlight_list if h.start_time != -1], key=lambda h: h.start_time)
        return [h.display_text for h in sorted_highlights]

    def copy_all_highlights(self):
        if not self._highlights: return
        formatted_texts = self._get_sorted_display_texts(self._highlights)
        QApplication.clipboard().setText("\n\n".join(formatted_texts))
        self.status_message_requested.emit(self.theme_manager.get_text("status_copied"), 3000)

    def copy_selected_highlights(self):
        selected_items = self._list_widget.selectedItems()
        if not selected_items: return
        
        selected_highlights = [item.data(Qt.UserRole) for item in selected_items]
        formatted_texts = self._get_sorted_display_texts(selected_highlights)
        QApplication.clipboard().setText("\n\n".join(formatted_texts))
        self.status_message_requested.emit(f"Copied {len(selected_highlights)} selected highlight(s).", 3000)

    def export_highlights_txt(self):
        def generate_content():
            formatted_texts = self._get_sorted_display_texts(self._highlights)
            return "\n\n".join(formatted_texts)
        self._export_handler("dialog_save_txt_title", "Text Files (*.txt)", generate_content)

    def export_transcript(self):
        timed_highlights = sorted([h for h in self._highlights if h.start_time >= 0], key=lambda h: h.start_time)
        if not timed_highlights:
            self.status_message_requested.emit(self.theme_manager.get_text("status_no_timestamps"), 3000)
            return

        if self._document_mode == "[TRANSCRIPT]":
            def generate_transcript_content():
                return "\n\n".join([h.display_text for h in timed_highlights])
            self._export_handler("dialog_save_transcript_title", "Text Files (*.txt)", generate_transcript_content)
            return

        is_vtt = self._document_mode == "[VTT]"
        time_formatter = _seconds_to_vtt_time if is_vtt else _seconds_to_srt_time
        
        def generate_content():
            blocks = []
            if is_vtt:
                blocks.append("WEBVTT\n")

            for i, item in enumerate(timed_highlights):
                start = time_formatter(item.start_time)
                
                end_seconds = item.end_time
                if not (end_seconds > item.start_time):
                    if i + 1 < len(timed_highlights):
                        end_seconds = timed_highlights[i + 1].start_time
                    else:
                        end_seconds = item.start_time + 5.0
                
                if end_seconds <= item.start_time:
                    end_seconds = item.start_time + 1.0

                end = time_formatter(end_seconds)
                text = re.sub(r'^\s*Speaker\s*\d+[:\-]?\s*', '', item.text, flags=re.IGNORECASE).strip()

                if is_vtt:
                    blocks.append(f"{start} --> {end}\n{text}\n")
                else: # SRT
                    blocks.append(f"{i + 1}\n{start} --> {end}\n{text}\n")
            
            return "\n".join(blocks)

        if is_vtt:
            self._export_handler("dialog_save_vtt_title", "WebVTT Subtitle (*.vtt)", generate_content)
        else: # SRT
            self._export_handler("dialog_save_srt_title", "SubRip Subtitle (*.srt)", generate_content)

    def _export_handler(self, dialog_title_key, file_filter, content_generator):
        if not self._highlights: return
        default_filename = os.path.splitext(self._current_filename)[0]
        filepath, _ = QFileDialog.getSaveFileName(self, self.theme_manager.get_text(dialog_title_key), default_filename, file_filter)
        if not filepath: return
        try:
            with open(filepath, 'w', encoding='utf-8') as f: f.write(content_generator())
            self.status_message_requested.emit(self.theme_manager.get_text("status_saved", file=os.path.basename(filepath)), 3000)
        except IOError as e:
            QMessageBox.critical(self, self.theme_manager.get_text("error_title"), self.theme_manager.get_text("error_file_save_failed", error=e))
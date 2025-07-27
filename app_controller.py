import os
import re
import copy
from PySide6.QtCore import QObject, Signal

import parser
from parser import Highlight
from transcript_parser import process_new_highlight

class AppController(QObject):
    model_updated = Signal(str, list, str, bool, bool)
    status_message_requested = Signal(str, int)

    def __init__(self, theme_manager):
        super().__init__()
        self.theme_manager = theme_manager
        self.file_tags = self.theme_manager.get_value("app_config.file_tags", [])
        
        self.raw_text = ""
        self.highlights: list[Highlight] = []
        self.current_filepath = None
        self.document_mode = "simple"
        self.last_shown_search_term = None
        
        # HISTORY NOW STORES A TUPLE: (raw_text, highlights_list)
        self._history: list[tuple[str, list[Highlight]]] = []
        self._history_index = -1

    def process_file(self, filepath: str):
        try:
            self.raw_text, self.highlights, self.document_mode = parser.parse_document(filepath, self.file_tags)
            self.current_filepath = filepath
            self.last_shown_search_term = None
            
            if self.document_mode == "simple":
                for h in self.highlights:
                    h.sort_key = h.start_pos
            
            self._save_state_to_history(clear_history=True)
            self._emit_model_update()
            
            is_tutorial = self.current_filepath and self.current_filepath.startswith("tutorials")
            if not is_tutorial:
                self.status_message_requested.emit(f"Loaded {len(self.highlights)} highlights.", 5000)

        except ValueError as e:
            self.close_file()
            raise e

    def _add_highlight_logic(self, selected_text: str, selection_start: int):
        paragraphs = selected_text.split('\n\n')
        offset = 0
        for para in paragraphs:
            para = para.strip()
            if not para: continue
            para_start = selection_start + offset + selected_text.find(para, offset)
            offset = para_start - selection_start + len(para)
            if any(h.start_pos == para_start and h.text == para for h in self.highlights):
                continue
            new_highlight = process_new_highlight(self.raw_text, para, para_start)
            if self.document_mode == "simple":
                new_highlight.sort_key = new_highlight.start_pos
            self.highlights.append(new_highlight)

    def add_highlight(self, selected_text: str, selection_start: int, full_doc_text: str):
        self._add_highlight_logic(selected_text, selection_start)
        self._save_state_to_history()
        self._emit_model_update()
        self.status_message_requested.emit("Highlight(s) added.", 3000)

    def highlight_all_occurrences(self, search_term: str):
        if not search_term: return
        match_count = 0
        for match in re.finditer(re.escape(search_term), self.raw_text, re.IGNORECASE):
            self._add_highlight_logic(match.group(0), match.start())
            match_count += 1
        
        if match_count > 0:
            self._save_state_to_history()
            self._emit_model_update()
            self.status_message_requested.emit(f"Created {match_count} highlights for '{search_term}'.", 3000)
        else:
            self.status_message_requested.emit(f"No occurrences of '{search_term}' found to highlight.", 3000)

    def update_highlight_text(self, original_highlight: Highlight, new_text: str):
        old_text = original_highlight.text
        if old_text == new_text: return
        start = original_highlight.start_pos
        self.raw_text = self.raw_text[:start] + new_text + self.raw_text[start + len(old_text):]
        original_highlight.text = new_text
        original_highlight.display_text = ""
        original_highlight.__post_init__()
        delta = len(new_text) - len(old_text)
        if delta != 0:
            for h in self.highlights:
                if h != original_highlight and h.start_pos > start:
                    h.start_pos += delta
                    if self.document_mode == "simple":
                        h.sort_key += delta
        self._save_state_to_history()
        self._emit_model_update()
        self.status_message_requested.emit("Highlight updated.", 3000)

    def reorder_highlights(self, new_ordered_highlights: list):
        if self.document_mode != "simple": return
        for i, h in enumerate(new_ordered_highlights):
            h.sort_key = i
        self.highlights = new_ordered_highlights
        self._save_state_to_history()
        self._emit_model_update()
        self.status_message_requested.emit("Highlights reordered.", 3000)

    def remove_highlights(self, highlights_to_remove: list[Highlight]):
        if not highlights_to_remove: return
        ids_to_remove = {id(h) for h in highlights_to_remove}
        self.highlights = [h for h in self.highlights if id(h) not in ids_to_remove]
        self._save_state_to_history()
        self._emit_model_update()
        count = len(highlights_to_remove)
        self.status_message_requested.emit(f"{count} highlight{'s' if count > 1 else ''} removed.", 3000)
    
    def remove_all_highlights(self):
        if not self.highlights: return
        self.highlights.clear()
        self._save_state_to_history()
        self._emit_model_update()
        self.status_message_requested.emit("All highlights removed.", 3000)

    def close_file(self):
        self.raw_text = ""
        self.highlights = []
        self.current_filepath = None
        self.document_mode = "simple"
        self.last_shown_search_term = None
        self._history = []
        self._history_index = -1
        self._emit_model_update()

    def get_content_for_saving(self, include_header=False) -> str:
        text_with_markers = self.raw_text
        sorted_highlights = sorted(self.highlights, key=lambda h: h.start_pos, reverse=True)
        for h in sorted_highlights:
            start = h.start_pos
            end = start + len(h.text)
            text_with_markers = text_with_markers[:start] + "==" + h.text + "==" + text_with_markers[end:]
            
        if include_header:
            header = self.theme_manager.get_text("external_edit_header")
            return f"{header}\n\n{text_with_markers}"
            
        return text_with_markers

    def confirm_save(self):
        self._save_state_to_history(clear_history=True)
        self._emit_model_update()

    def is_modified(self):
        return self._history_index > 0

    def undo(self):
        if self._history_index > 0:
            self._history_index -= 1
            # Restore the complete state snapshot
            text, highlights = self._history[self._history_index]
            self.raw_text = text
            self.highlights = copy.deepcopy(highlights)
            self._emit_model_update()

    def redo(self):
        if self._history_index < len(self._history) - 1:
            self._history_index += 1
            # Restore the complete state snapshot
            text, highlights = self._history[self._history_index]
            self.raw_text = text
            self.highlights = copy.deepcopy(highlights)
            self._emit_model_update()
            
    def _save_state_to_history(self, clear_history=False):
        if clear_history: self._history = []
        if self._history_index < len(self._history) - 1:
            self._history = self._history[:self._history_index + 1]
        
        # Save a snapshot of both the raw_text and a deepcopy of highlights
        state_snapshot = (self.raw_text, copy.deepcopy(self.highlights))
        self._history.append(state_snapshot)
        self._history_index = len(self._history) - 1

    def _emit_model_update(self):
        can_undo = self._history_index > 0
        can_redo = self._history_index < len(self._history) - 1
        self.model_updated.emit(self.raw_text, self.highlights, self.document_mode, can_undo, can_redo)
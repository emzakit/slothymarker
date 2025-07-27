import re
from dataclasses import dataclass
from parser import Highlight

def _time_to_seconds(time_str: str) -> float:
    # MODIFIED: More robustly find the first timestamp in a line
    first_timestamp_match = re.search(r'(\d{1,2}:\d{2}:\d{2}[,.:]?\d*)', time_str)
    if not first_timestamp_match:
        return -1.0
    
    ts_str = first_timestamp_match.group(1).replace(',', '.')
    
    try:
        # MODIFIED: Handle HH:MM:SS:FF format used in [TRANSCRIPT] files
        parts = list(map(float, ts_str.split(':')))
        if len(parts) == 4: return parts[0] * 3600 + parts[1] * 60 + parts[2] + (parts[3] / 100.0)
        if len(parts) == 3: return parts[0] * 3600 + parts[1] * 60 + parts[2]
        if len(parts) == 2: return parts[0] * 60 + parts[1]
    except (ValueError, IndexError):
        return -1.0
    return -1.0

def _find_preceding_timestamp(text_before: str) -> tuple[str | None, float, float]:
    lines = text_before.strip().split('\n')
    # Iterate backwards to find the last timestamp block
    for i in range(len(lines) - 1, -1, -1):
        line = lines[i].strip()
        
        # Look for a line containing time info
        if '-->' in line or re.search(r'\d{1,2}:\d{2}:\d{2}', line):
            start_time, end_time = -1.0, -1.0
            
            # If it's a range (SRT/VTT), parse both start and end
            if '-->' in line:
                parts = line.split('-->')
                start_time = _time_to_seconds(parts[0])
                end_time = _time_to_seconds(parts[1])
            # Otherwise, it's a simple timestamp (just a start time)
            else:
                start_time = _time_to_seconds(line)

            # Reconstruct the full header, checking for a sequence number above
            full_header = line
            if i > 0 and lines[i-1].strip().isdigit():
                full_header = f"{lines[i-1].strip()}\n{line}"
            
            return full_header, start_time, end_time

    return None, -1.0, -1.0

def _create_display_text(time_str: str | None, highlight_text: str) -> str:
    clean_highlight = highlight_text.replace("==", "")
    if time_str:
        # MODIFIED: Removed the "... " prefix for a cleaner look
        return f"{time_str}\n{clean_highlight}"
    # If no timestamp, just show the text
    return clean_highlight

def parse_transcript_file(raw_text: str) -> list[Highlight]:
    highlights = []
    highlight_pattern = re.compile(r'==(.+?)==', re.DOTALL)
    
    for match in highlight_pattern.finditer(raw_text):
        highlight_text = match.group(1)
        start_pos = match.start(1) # Get start position of the content inside '=='
        
        text_before_highlight = raw_text[:start_pos]
        time_str, start_time, end_time = _find_preceding_timestamp(text_before_highlight)
        
        highlights.append(Highlight(
            text=highlight_text,
            start_pos=start_pos,
            start_time=start_time,
            end_time=end_time,
            display_text=_create_display_text(time_str, highlight_text)
        ))
    return highlights

def process_new_highlight(raw_text: str, selected_text: str, selection_start: int) -> Highlight:
    text_before_selection = raw_text[:selection_start]
    time_str, start_time, end_time = _find_preceding_timestamp(text_before_selection)
    
    return Highlight(
        text=selected_text,
        start_pos=selection_start,
        start_time=start_time,
        end_time=end_time,
        display_text=_create_display_text(time_str, selected_text)
    )
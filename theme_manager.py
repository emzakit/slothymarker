import json
import os
from functools import reduce
from PySide6.QtGui import QIcon
from utils import resource_path # <-- IMPORT THE HELPER

def _deep_merge(source, destination):
    # ... (no change in this function)
    for key, value in source.items():
        if isinstance(value, dict):
            node = destination.setdefault(key, {})
            _deep_merge(value, node)
        else:
            destination[key] = value
    return destination

class ThemeManager:
    # ... (no change in __init__ or get_value or get_text)
    def __init__(self, config_path: str, theme_path: str):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self._theme_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            raise IOError(f"Could not load or parse base config file: {config_path}") from e

        try:
            with open(theme_path, 'r', encoding='utf-8') as f:
                theme_specific_data = json.load(f)
            self._theme_data = _deep_merge(theme_specific_data, self._theme_data)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Warning: Could not load or parse theme file: {theme_path}. Using defaults.")

    def get_value(self, path: str, default=None):
        keys = path.split('.')
        try:
            return reduce(lambda d, key: d[key], keys, self._theme_data)
        except (KeyError, TypeError):
            return default

    def get_text(self, key: str, **kwargs) -> str:
        template = self.get_value(f"text.{key}", default=f"<{key}>")
        return template.format(**kwargs)

    def get_icon(self, icon_key: str) -> QIcon:
        icon_filename = self.get_value(f"icons.{icon_key}")
        # MODIFIED: Use resource_path to construct the full path to the icon.
        if icon_filename:
            full_path = resource_path(os.path.join("icons", icon_filename))
            if os.path.exists(full_path):
                return QIcon(full_path)
        return QIcon()

    def generate_stylesheet(self) -> str:
        # ... (no change in this function)
        get = self.get_value
        return f"""
            QMainWindow, QWidget {{
                background-color: {get('colors.bg_primary')};
                color: {get('colors.text_primary')};
            }}
            QGroupBox {{
                background-color: {get('colors.bg_secondary')};
                color: {get('colors.text_primary')};
                font-family: "{get('fonts.family')}";
                font-size: {get('fonts.size.title')};
                font-weight: bold;
                border: 1px solid {get('colors.groupbox_border')};
                border-radius: {get('layout.border_radius')};
                margin-top: {get('layout.padding')};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 5px {get('layout.padding')};
                left: {get('layout.padding')};
            }}
            QTextBrowser, QListWidget {{
                background-color: {get('colors.bg_primary')};
                color: {get('colors.text_primary')};
                font-family: "{get('fonts.family')}";
                font-size: {get('fonts.size.default')};
                border-radius: {get('layout.border_radius')};
                border: 1px solid {get('colors.groupbox_border')};
                padding: {get('layout.padding')};
            }}
            QListWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {get('colors.bg_secondary')};
            }}
            QListWidget::item:hover {{
                background-color: {get('colors.bg_secondary')};
            }}
            QListWidget::item:selected {{
                background-color: {get('colors.accent_pink_selection')};
                color: white;
                font-weight: bold;
            }}
            QMenuBar, QMenu {{
                background-color: {get('colors.bg_secondary')};
                color: {get('colors.text_primary')};
                font-family: "{get('fonts.family')}";
                font-size: {get('fonts.size.menu')};
                border-bottom: 1px solid {get('colors.groupbox_border')};
            }}
            QMenu::item:selected {{
                background-color: {get('colors.accent_pink_selection')};
                color: white;
            }}
            QStatusBar {{
                color: {get('colors.text_secondary')};
                font-size: {get('fonts.size.status')};
            }}
            QSplitter::handle {{
                background: {get('colors.splitter_handle_bg')};
            }}
            QSplitter::handle:hover {{
                background: {get('colors.accent_primary')};
            }}
            QToolTip {{
                color: {get('colors.tooltip_fg')};
                background-color: {get('colors.tooltip_bg')};
                border: 1px solid {get('colors.accent_primary')};
                padding: 5px;
                border-radius: 4px;
            }}
            #PlaceholderHeader {{
                font-size: {get('fonts.size.placeholder_header')};
                color: {get('colors.text_secondary')};
                font-weight: bold;
            }}
            #PlaceholderBody {{
                font-size: {get('fonts.size.placeholder_body')};
                color: {get('colors.text_secondary')};
            }}
            #HelperLabel {{
                color: {get('colors.text_secondary')};
                font-size: {get('fonts.size.status')};
                padding-bottom: 5px;
            }}
            #StatsPanel {{
                background-color: {get('colors.bg_secondary')};
                border-top: 1px solid {get('colors.groupbox_border')};
                border-bottom: 1px solid {get('colors.groupbox_border')};
                padding: 0px 5px;
            }}
            #StatsLabel {{
                color: {get('colors.text_secondary')};
                font-size: {get('fonts.size.status')};
                font-weight: bold;
            }}
            #ExportPanelGroupBox {{
                margin-top: 0px;
                padding-top: {get('layout.padding')};
            }}
            #DropOverlay {{
                background-color: {get('colors.drop_overlay_bg')};
                border: 3px dashed {get('colors.accent_primary')};
                border-radius: {get('layout.border_radius')};
            }}
            #DropOverlayLabel {{
                color: {get('colors.drop_overlay_fg')};
                font-size: {get('fonts.size.drop_overlay_header')};
                font-weight: bold;
            }}
            QMessageBox {{
                background-color: {get('colors.bg_primary')};
            }}
            QMessageBox QLabel {{
                color: {get('colors.text_primary')};
                font-size: {get('fonts.size.default')};
            }}
            #SidebarButton {{
                text-align: left;
                padding-left: 15px;
            }}
            /* --- Button Styles --- */
            QPushButton {{
                font-size: {get('fonts.size.button', '10pt')};
                font-weight: bold;
                padding: {get('layout.button_padding', '12px')};
                border: none;
                border-radius: {get('layout.border_radius')};
                background-color: {get('colors.button_secondary_bg')};
                color: {get('colors.button_secondary_fg')};
            }}
            QPushButton:hover {{
                background-color: {get('colors.button_secondary_hover_bg')};
            }}
            QPushButton:disabled {{
                background-color: #EAECEF;
                color: #BDC3C7;
            }}
            #PanelButtonOpen {{
                background-color: {get('colors.accent_primary')};
                color: {get('colors.accent_primary_text')};
            }}
            #PanelButtonOpen:hover {{ background-color: #2980B9; }}
            #PanelButtonSave, #AddHighlightButton {{
                background-color: {get('colors.accent_green')};
                color: white;
            }}
            #PanelButtonSave:hover, #AddHighlightButton:hover {{
                background-color: {get('colors.accent_green_hover')};
            }}
            #RemoveButton, #RemoveAllButton {{
                background-color: {get('colors.accent_red')};
                color: white;
            }}
            #RemoveButton:hover, #RemoveAllButton:hover {{
                background-color: {get('colors.accent_red_hover')};
            }}
            #ExportButton {{
                background-color: {get('colors.button_primary_bg')};
                color: {get('colors.button_primary_fg')};
            }}
            #ExportButton:hover {{
                background-color: {get('colors.button_primary_hover_bg')};
            }}
        """
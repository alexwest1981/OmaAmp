import os
import json
import glob
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QColor, QFont

CONFIG_DIR = os.path.expanduser("~/.config/omaamp")
USER_THEMES_DIR = os.path.join(CONFIG_DIR, "themes")
BUILTIN_THEMES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "themes")

class ThemeManager(QObject):
    theme_changed = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        os.makedirs(USER_THEMES_DIR, exist_ok=True)
        self.themes = {}
        self.current_theme_id = "classic_retro"
        self.current_theme = {}
        self.reload_themes()
        self.set_theme(self.current_theme_id)

    def reload_themes(self):
        self.themes.clear()
        
        # 1. Load built-in themes
        for fpath in glob.glob(os.path.join(BUILTIN_THEMES_DIR, "*.json")):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    tid = data.get("id", os.path.splitext(os.path.basename(fpath))[0])
                    data["_is_builtin"] = True
                    data["_path"] = fpath
                    self.themes[tid] = data
            except Exception as e:
                print(f"Error loading theme {fpath}: {e}")

        # 2. Load user themes (overriding built-in if same ID)
        for fpath in glob.glob(os.path.join(USER_THEMES_DIR, "*.json")):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    tid = data.get("id", os.path.splitext(os.path.basename(fpath))[0])
                    data["_is_builtin"] = False
                    data["_path"] = fpath
                    self.themes[tid] = data
            except Exception as e:
                print(f"Error loading user theme {fpath}: {e}")

    def get_available_themes(self):
        return [
            {
                "id": tid,
                "name": t.get("name", tid),
                "author": t.get("author", "Unknown"),
                "description": t.get("description", ""),
                "is_builtin": t.get("_is_builtin", False),
                "path": t.get("_path", "")
            }
            for tid, t in self.themes.items()
        ]

    def set_theme(self, theme_id):
        if theme_id in self.themes:
            self.current_theme_id = theme_id
            self.current_theme = self.themes[theme_id]
            self.theme_changed.emit(self.current_theme)
            return True
        elif "classic_retro" in self.themes:
            self.current_theme_id = "classic_retro"
            self.current_theme = self.themes["classic_retro"]
            self.theme_changed.emit(self.current_theme)
            return True
        return False

    def color(self, key, fallback="#00ff00"):
        colors = self.current_theme.get("colors", {})
        hex_val = colors.get(key, fallback)
        return QColor(hex_val)

    def hex(self, key, fallback="#00ff00"):
        colors = self.current_theme.get("colors", {})
        return colors.get(key, fallback)

    def save_custom_theme(self, theme_data):
        theme_id = theme_data.get("id", "custom_theme")
        fpath = os.path.join(USER_THEMES_DIR, f"{theme_id}.json")
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(theme_data, f, indent=2, ensure_ascii=False)
        self.reload_themes()
        self.set_theme(theme_id)
        return fpath

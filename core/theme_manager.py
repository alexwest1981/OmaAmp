import os
import json
import glob
import shutil
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QColor, QPixmap
from core.skin_parser import WinampSkin

CONFIG_DIR = os.path.expanduser("~/.config/omaamp")
USER_THEMES_DIR = os.path.join(CONFIG_DIR, "themes")
USER_SKINS_DIR = os.path.join(CONFIG_DIR, "skins")
BUILTIN_THEMES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "themes")
BUILTIN_SKINS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "skins")

class ThemeManager(QObject):
    theme_changed = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        os.makedirs(USER_THEMES_DIR, exist_ok=True)
        os.makedirs(USER_SKINS_DIR, exist_ok=True)
        os.makedirs(BUILTIN_SKINS_DIR, exist_ok=True)
        
        self.themes = {}
        self.current_theme_id = "classic_retro"
        self.current_theme = {}
        self.active_skin = None  # WinampSkin object if .wsz active

        self.reload_themes()
        self.set_theme(self.current_theme_id)

    def reload_themes(self):
        self.themes.clear()
        
        # 1. Load built-in JSON themes
        for fpath in glob.glob(os.path.join(BUILTIN_THEMES_DIR, "*.json")):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    tid = data.get("id", os.path.splitext(os.path.basename(fpath))[0])
                    data["_is_builtin"] = True
                    data["_is_wsz"] = False
                    data["_path"] = fpath
                    self.themes[tid] = data
            except Exception as e:
                print(f"Error loading theme {fpath}: {e}")

        # 2. Load built-in WSZ skins
        for fpath in glob.glob(os.path.join(BUILTIN_SKINS_DIR, "*.wsz")) + glob.glob(os.path.join(BUILTIN_SKINS_DIR, "*.zip")):
            tid = "wsz_" + os.path.splitext(os.path.basename(fpath))[0].lower()
            name = os.path.splitext(os.path.basename(fpath))[0].replace("_", " ")
            self.themes[tid] = {
                "id": tid,
                "name": f"✨ [Winamp Skin] {name}",
                "author": "Classic Winamp Community",
                "description": f"Authentic Winamp 2.x skin from {os.path.basename(fpath)}",
                "_is_builtin": True,
                "_is_wsz": True,
                "_path": fpath
            }

        # 3. Load user JSON themes
        for fpath in glob.glob(os.path.join(USER_THEMES_DIR, "*.json")):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    tid = data.get("id", os.path.splitext(os.path.basename(fpath))[0])
                    data["_is_builtin"] = False
                    data["_is_wsz"] = False
                    data["_path"] = fpath
                    self.themes[tid] = data
            except Exception as e:
                print(f"Error loading user theme {fpath}: {e}")

        # 4. Load user WSZ skins (~/.config/omaamp/skins/*.wsz)
        for fpath in glob.glob(os.path.join(USER_SKINS_DIR, "*.wsz")) + glob.glob(os.path.join(USER_SKINS_DIR, "*.zip")):
            tid = "user_wsz_" + os.path.splitext(os.path.basename(fpath))[0].lower()
            name = os.path.splitext(os.path.basename(fpath))[0].replace("_", " ")
            self.themes[tid] = {
                "id": tid,
                "name": f"🎨 [Custom Skin] {name}",
                "author": "User Skin",
                "description": f"User imported Winamp skin: {os.path.basename(fpath)}",
                "_is_builtin": False,
                "_is_wsz": True,
                "_path": fpath
            }

    def get_available_themes(self):
        return [
            {
                "id": tid,
                "name": t.get("name", tid),
                "author": t.get("author", "Unknown"),
                "description": t.get("description", ""),
                "is_builtin": t.get("_is_builtin", False),
                "is_wsz": t.get("_is_wsz", False),
                "path": t.get("_path", "")
            }
            for tid, t in self.themes.items()
        ]

    def set_theme(self, theme_id):
        if theme_id in self.themes:
            self.current_theme_id = theme_id
            theme_meta = self.themes[theme_id]

            if theme_meta.get("_is_wsz", False):
                # Load WSZ skin
                skin = WinampSkin(theme_meta["name"], theme_meta["_path"])
                self.active_skin = skin
                self.current_theme = {
                    "id": theme_id,
                    "name": skin.name,
                    "author": theme_meta.get("author", "Winamp Skin"),
                    "description": theme_meta.get("description", ""),
                    "colors": skin.colors,
                    "_is_wsz": True,
                    "_path": theme_meta["_path"]
                }
            else:
                self.active_skin = None
                self.current_theme = theme_meta

            self.theme_changed.emit(self.current_theme)

    def import_skin_file(self, fpath):
        if not os.path.isfile(fpath) or not fpath.lower().endswith(('.wsz', '.zip')):
            return None
        dest = os.path.join(USER_SKINS_DIR, os.path.basename(fpath))
        shutil.copy2(fpath, dest)
        self.reload_themes()
        tid = "user_wsz_" + os.path.splitext(os.path.basename(fpath))[0].lower()
        self.set_theme(tid)
        return tid

    def save_custom_theme(self, theme_dict):
        tid = theme_dict.get("id", "custom")
        fpath = os.path.join(USER_THEMES_DIR, f"{tid}.json")
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(theme_dict, f, indent=2)
        self.reload_themes()
        self.set_theme(tid)
        return fpath

    def color(self, token_name, fallback="#ffffff"):
        colors = self.current_theme.get("colors", {})
        val = colors.get(token_name, fallback)
        return QColor(val)

    def hex(self, token_name, fallback="#ffffff"):
        colors = self.current_theme.get("colors", {})
        return colors.get(token_name, fallback)

    def get_sprite(self, name):
        if self.active_skin and name in self.active_skin.sprites:
            return self.active_skin.sprites[name]
        return None

    def knob_image_path(self):
        if self.active_skin and hasattr(self.active_skin, 'knob_path') and self.active_skin.knob_path and os.path.exists(self.active_skin.knob_path):
            return self.active_skin.knob_path
        return None

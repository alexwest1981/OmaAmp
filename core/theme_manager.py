import os
import json
import glob
import shutil
import zipfile
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QColor, QPixmap, QBrush, QImage
from core.skin_parser import WinampSkin
from core.github_sync import GitHubSyncManager

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
        
        self.github = GitHubSyncManager()
        self.themes = {}
        self.current_theme_id = "classic_retro"
        self.current_theme = {}
        self.active_skin = None  # WinampSkin object if .wsz active

        self.reload_themes()
        self.set_theme(self.current_theme_id)

    def reload_themes(self):
        self.themes.clear()
        
        # 1. Load built-in JSON themes & theme bundles
        self._load_themes_from_directory(BUILTIN_THEMES_DIR, is_builtin=True)

        # 2. Load user themes & theme bundles (~/.config/omaamp/themes/)
        self._load_themes_from_directory(USER_THEMES_DIR, is_builtin=False)

        # 3. Load built-in WSZ skins
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

    def _load_themes_from_directory(self, dir_path, is_builtin=False):
        if not os.path.exists(dir_path):
            return

        # A. Standalone .json files
        for fpath in glob.glob(os.path.join(dir_path, "*.json")):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    tid = data.get("id", os.path.splitext(os.path.basename(fpath))[0])
                    data["_is_builtin"] = is_builtin
                    data["_is_wsz"] = False
                    data["_is_bundle"] = False
                    data["_path"] = fpath
                    data["_base_dir"] = dir_path
                    self.themes[tid] = data
            except Exception as e:
                print(f"Error loading theme {fpath}: {e}")

        # B. Theme folders containing theme.json
        for entry in os.listdir(dir_path):
            folder_path = os.path.join(dir_path, entry)
            if os.path.isdir(folder_path):
                t_json = os.path.join(folder_path, "theme.json")
                if os.path.exists(t_json):
                    try:
                        with open(t_json, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            tid = data.get("id", entry)
                            data["_is_builtin"] = is_builtin
                            data["_is_wsz"] = False
                            data["_is_bundle"] = True
                            data["_path"] = t_json
                            data["_base_dir"] = folder_path
                            self.themes[tid] = data
                    except Exception as e:
                        print(f"Error loading theme bundle {folder_path}: {e}")

        # C. .omaamp-theme zip bundles
        for fpath in glob.glob(os.path.join(dir_path, "*.omaamp-theme")):
            try:
                # Extract bundle to a subfolder
                tid = os.path.splitext(os.path.basename(fpath))[0]
                target_f = os.path.join(dir_path, tid)
                if not os.path.exists(target_f):
                    os.makedirs(target_f, exist_ok=True)
                    with zipfile.ZipFile(fpath, "r") as z:
                        z.extractall(target_f)
                t_json = os.path.join(target_f, "theme.json")
                if os.path.exists(t_json):
                    with open(t_json, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        tid = data.get("id", tid)
                        data["_is_builtin"] = is_builtin
                        data["_is_wsz"] = False
                        data["_is_bundle"] = True
                        data["_path"] = t_json
                        data["_base_dir"] = target_f
                        self.themes[tid] = data
            except Exception as e:
                print(f"Error loading .omaamp-theme {fpath}: {e}")

    def get_available_themes(self):
        return [
            {
                "id": tid,
                "name": t.get("name", tid),
                "author": t.get("author", "Unknown"),
                "version": t.get("version", "1.0.0"),
                "description": t.get("description", ""),
                "is_builtin": t.get("_is_builtin", False),
                "is_wsz": t.get("_is_wsz", False),
                "is_bundle": t.get("_is_bundle", False),
                "path": t.get("_path", "")
            }
            for tid, t in self.themes.items()
        ]

    def set_theme(self, theme_id):
        if theme_id in self.themes:
            self.current_theme_id = theme_id
            theme_meta = self.themes[theme_id]

            if theme_meta.get("_is_wsz", False):
                # Load legacy WSZ skin
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

    # -------------------------------------------------------------------------
    # Texture & Style Resolvers
    # -------------------------------------------------------------------------
    def get_texture_path(self, texture_key: str) -> str:
        """Returns the absolute file path to a theme texture PNG if configured."""
        if not self.current_theme:
            return ""

        textures = self.current_theme.get("textures", {})
        rel_path = textures.get(texture_key)
        if not rel_path:
            return ""

        base_dir = self.current_theme.get("_base_dir")
        if base_dir:
            full_path = os.path.join(base_dir, rel_path)
            if os.path.exists(full_path):
                return full_path
        
        # Absolute path fallback
        if os.path.exists(rel_path):
            return rel_path
        return ""

    def get_texture_pixmap(self, texture_key: str) -> QPixmap:
        """Loads and returns a QPixmap for the specified texture key."""
        path = self.get_texture_path(texture_key)
        if path:
            return QPixmap(path)
        return QPixmap()

    def get_brush(self, texture_key: str, fallback_color="#282932") -> QBrush:
        """Returns a QBrush pattern for repeating textures like chassis, titlebar, or panels."""
        pix = self.get_texture_pixmap(texture_key)
        if not pix.isNull():
            return QBrush(pix)
        return QBrush(self.color(fallback_color))

    def knob_image_path(self):
        """Returns the active knob PNG image path (from native theme or WSZ skin)."""
        # 1. Native theme texture
        custom_knob = self.get_texture_path("knob")
        if custom_knob:
            return custom_knob

        # 2. Legacy WSZ skin knob
        if self.active_skin and hasattr(self.active_skin, 'knob_path') and self.active_skin.knob_path and os.path.exists(self.active_skin.knob_path):
            return self.active_skin.knob_path
        return None

    def color(self, token_name, fallback="#ffffff"):
        colors = self.current_theme.get("colors", {})
        val = colors.get(token_name, fallback)
        return QColor(val)

    def hex(self, token_name, fallback="#ffffff"):
        colors = self.current_theme.get("colors", {})
        return colors.get(token_name, fallback)

    # -------------------------------------------------------------------------
    # Import / Export / Save
    # -------------------------------------------------------------------------
    def import_skin_file(self, fpath):
        if not os.path.isfile(fpath):
            return None
        ext = os.path.splitext(fpath)[1].lower()
        if ext in ('.wsz', '.zip'):
            dest = os.path.join(USER_SKINS_DIR, os.path.basename(fpath))
            shutil.copy2(fpath, dest)
            self.reload_themes()
            tid = "user_wsz_" + os.path.splitext(os.path.basename(fpath))[0].lower()
            self.set_theme(tid)
            return tid
        elif ext in ('.omaamp-theme', '.json'):
            return self.import_theme_bundle(fpath)
        return None

    def import_theme_bundle(self, fpath):
        """Imports a .omaamp-theme archive or standalone .json theme."""
        ext = os.path.splitext(fpath)[1].lower()
        if ext == '.json':
            dest = os.path.join(USER_THEMES_DIR, os.path.basename(fpath))
            shutil.copy2(fpath, dest)
            self.reload_themes()
            tid = os.path.splitext(os.path.basename(fpath))[0]
            self.set_theme(tid)
            return tid
        elif ext == '.omaamp-theme':
            dest_zip = os.path.join(USER_THEMES_DIR, os.path.basename(fpath))
            shutil.copy2(fpath, dest_zip)
            self.reload_themes()
            tid = os.path.splitext(os.path.basename(fpath))[0]
            self.set_theme(tid)
            return tid
        return None

    def save_custom_theme(self, theme_dict, texture_files: dict = None):
        """
        Saves a custom theme either as a standalone JSON or a theme bundle with textures.
        texture_files: optional dict of {"knob": "/path/to/knob.png", "chassis_pattern": "/path/to/bg.png"}
        """
        tid = theme_dict.get("id", "custom")
        
        if texture_files:
            # Create theme bundle directory
            theme_folder = os.path.join(USER_THEMES_DIR, tid)
            textures_folder = os.path.join(theme_folder, "textures")
            os.makedirs(textures_folder, exist_ok=True)
            
            theme_dict["textures"] = theme_dict.get("textures", {})
            for key, src_path in texture_files.items():
                if src_path and os.path.exists(src_path):
                    fname = f"{key}_{os.path.basename(src_path)}"
                    dest_file = os.path.join(textures_folder, fname)
                    shutil.copy2(src_path, dest_file)
                    theme_dict["textures"][key] = f"textures/{fname}"

            fpath = os.path.join(theme_folder, "theme.json")
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(theme_dict, f, indent=2)
        else:
            fpath = os.path.join(USER_THEMES_DIR, f"{tid}.json")
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(theme_dict, f, indent=2)

        self.reload_themes()
        self.set_theme(tid)
        return fpath

import os
import json
from core.i18n import i18n

CONFIG_PATH = os.path.expanduser("~/.config/omaamp/config.json")

DEFAULT_CONFIG = {
    "theme": "classic_retro",
    "language": i18n.get_language(),
    "volume": 80,
    "balance": 0,
    "shuffle": False,
    "repeat": True,
    "vis_mode": "spectrum",  # "spectrum" | "oscilloscope" | "fire"
    "eq_enabled": True,
    "eq_preamp": 0,
    "eq_bands": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    "main_pos": [150, 150],
    "eq_pos": [150, 290],
    "pl_pos": [150, 420],
    "show_eq": True,
    "show_pl": True,
    "time_mode": "elapsed"  # "elapsed" | "remaining"
}

class ConfigManager:
    def __init__(self):
        self.data = DEFAULT_CONFIG.copy()
        self.load()

    def load(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self.data.update(saved)
                    if "language" in saved:
                        i18n.set_language(saved["language"])
            except Exception as e:
                print(f"Error loading config: {e}")

    def save(self):
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get(self, key, fallback=None):
        return self.data.get(key, fallback)

    def set(self, key, value):
        self.data[key] = value
        self.save()

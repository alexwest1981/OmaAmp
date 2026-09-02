#!/usr/bin/env python3
import sys
import os

# Ensure package path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from core.audio_engine import AudioEngine
from core.theme_manager import ThemeManager
from core.config import ConfigManager
from core.visualizer_data import VisualizerGenerator
from ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("OmaAmp")
    app.setOrganizationName("OmaAmp")

    config_mgr = ConfigManager()
    theme_mgr = ThemeManager()
    
    # Restore configured theme
    saved_theme = config_mgr.get("theme", "classic_retro")
    theme_mgr.set_theme(saved_theme)

    audio_engine = AudioEngine()
    vis_gen = VisualizerGenerator(num_bars=19)

    # If file paths passed on CLI, queue them
    if len(sys.argv) > 1:
        args_paths = sys.argv[1:]
        audio_engine.add_files(args_paths)

    window = MainWindow(audio_engine, theme_mgr, config_mgr, vis_gen)
    window.show()

    exit_code = app.exec()
    
    # Save active theme on exit
    config_mgr.set("theme", theme_mgr.current_theme_id)
    config_mgr.save()
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()

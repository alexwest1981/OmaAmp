from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ui.visualizer_widget import VisualizerWidget, VIS_MODES

class VisualizerStudio(QDialog):
    def __init__(self, theme_mgr, audio_engine, parent=None):
        super().__init__(parent)
        self.theme_mgr = theme_mgr
        self.audio = audio_engine

        self.setWindowTitle("OmaAmp Visualizer Studio")
        self.resize(640, 420)
        self.setMinimumSize(400, 260)

        self.init_ui()
        self.apply_theme()
        self.theme_mgr.theme_changed.connect(self.apply_theme)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Top Mode Selector Bar
        top_bar = QHBoxLayout()
        lbl = QLabel("VISUALIZER STUDIO:")
        lbl.setFont(QFont("Monospace", 9, QFont.Weight.Bold))
        top_bar.addWidget(lbl)

        self.combo_modes = QComboBox()
        for mode_key, mode_name in VIS_MODES:
            self.combo_modes.addItem(mode_name, mode_key)
        self.combo_modes.currentIndexChanged.connect(self._on_mode_changed)
        top_bar.addWidget(self.combo_modes)

        top_bar.addStretch()

        btn_fullscreen = QPushButton("⛶ Fullscreen")
        btn_fullscreen.setFixedHeight(22)
        btn_fullscreen.clicked.connect(self._toggle_fullscreen)
        top_bar.addWidget(btn_fullscreen)

        layout.addLayout(top_bar)

        # Big Visualizer Canvas
        self.canvas = VisualizerWidget(self.theme_mgr, self.audio, self)
        self.canvas.setMinimumHeight(200)
        layout.addWidget(self.canvas)

    def _on_mode_changed(self, idx):
        mode_key = self.combo_modes.currentData()
        if mode_key:
            self.canvas.set_mode(mode_key)

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def set_playing(self, is_playing):
        self.canvas.set_playing(is_playing)

    def set_volume(self, vol):
        self.canvas.set_volume(vol)

    def apply_theme(self):
        bg = self.theme_mgr.hex("chassis_bg", "#13141a")
        btn_bg = self.theme_mgr.hex("button_bg", "#1c1e28")
        btn_text = self.theme_mgr.hex("button_text", "#c0caf5")
        border = self.theme_mgr.hex("chassis_border", "#282a36")
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg};
                color: {btn_text};
            }}
            QLabel {{
                color: {btn_text};
            }}
            QComboBox, QPushButton {{
                background-color: {btn_bg};
                color: {btn_text};
                border: 1px solid {border};
                border-radius: 3px;
                padding: 2px 6px;
                font-family: 'Monospace';
                font-size: 9px;
            }}
        """)

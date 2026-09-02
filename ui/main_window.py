import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider, QFileDialog
)
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QFont, QColor, QPainter, QPen

from ui.lcd_display import LcdDisplay, MarqueeDisplay
from ui.visualizer_widget import VisualizerWidget
from ui.theme_dialog import ThemeDialog
from ui.equalizer_window import EqualizerWindow
from ui.playlist_window import PlaylistWindow

class MainWindow(QWidget):
    def __init__(self, audio_engine, theme_mgr, config_mgr, vis_gen):
        super().__init__()
        self.audio = audio_engine
        self.theme_mgr = theme_mgr
        self.config = config_mgr
        self.vis_gen = vis_gen

        self.setFixedSize(310, 148)
        self.setWindowTitle("OmaAmp")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)

        # Dragging state
        self._drag_pos = QPoint()

        # Child windows
        self.eq_window = EqualizerWindow(self.theme_mgr)
        self.pl_window = PlaylistWindow(self.audio, self.theme_mgr)
        self.eq_window.setFixedWidth(310)
        self.pl_window.setFixedWidth(310)

        self.init_ui()
        self.apply_theme()

        # Connect signals
        self.theme_mgr.theme_changed.connect(self.apply_theme)
        self.audio.track_changed.connect(self._on_track_changed)
        self.audio.position_changed.connect(self._on_position_changed)
        self.audio.playback_state_changed.connect(self._on_playback_state_changed)

        # Restore positions
        main_x, main_y = self.config.get("main_pos", [250, 200])
        self.move(main_x, main_y)

        # Connect EQ and PL dock sync
        self.eq_window.move(main_x, main_y + 150)
        self.pl_window.move(main_x, main_y + 292)

        if self.config.get("show_eq", True):
            self.eq_window.show()
            self.btn_eq.setChecked(True)
        if self.config.get("show_pl", True):
            self.pl_window.show()
            self.btn_pl.setChecked(True)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(4)

        # 1. Custom Retro Titlebar
        title_row = QHBoxLayout()
        title_row.setSpacing(4)

        self.lbl_title = QLabel("OMAAMP - WINAMP 2.91 CLASSIC")
        self.lbl_title.setFont(QFont("Monospace", 8, QFont.Weight.Bold))
        title_row.addWidget(self.lbl_title)

        title_row.addStretch()

        self.btn_skin = QPushButton("SKIN")
        self.btn_skin.setFixedSize(32, 16)
        self.btn_skin.setToolTip("Change or Create Theme")
        self.btn_skin.clicked.connect(self._open_theme_dialog)
        title_row.addWidget(self.btn_skin)

        self.btn_min = QPushButton("_")
        self.btn_min.setFixedSize(16, 16)
        self.btn_min.clicked.connect(self.showMinimized)
        title_row.addWidget(self.btn_min)

        self.btn_close = QPushButton("X")
        self.btn_close.setFixedSize(16, 16)
        self.btn_close.clicked.connect(self._exit_app)
        title_row.addWidget(self.btn_close)

        main_layout.addLayout(title_row)

        # 2. Scrolling Song Title Marquee (Full Width)
        self.marquee = MarqueeDisplay(self.theme_mgr, self)
        main_layout.addWidget(self.marquee)

        # 3. Middle Deck: 7-Segment LED Time (Left) + Spectrum Visualizer (Right)
        deck_mid = QHBoxLayout()
        deck_mid.setSpacing(4)

        self.lcd = LcdDisplay(self.theme_mgr, self)
        deck_mid.addWidget(self.lcd)

        self.vis = VisualizerWidget(self.theme_mgr, self.vis_gen, self)
        self.vis.setFixedSize(150, 42)
        deck_mid.addWidget(self.vis)

        main_layout.addLayout(deck_mid)

        # 4. Sliders Deck: Volume & Balance & Seek Bar
        sliders_layout = QHBoxLayout()
        sliders_layout.setSpacing(4)

        # Volume Slider
        v_col = QVBoxLayout()
        v_col.setSpacing(1)
        self.slider_vol = QSlider(Qt.Orientation.Horizontal)
        self.slider_vol.setRange(0, 100)
        self.slider_vol.setValue(self.config.get("volume", 80))
        self.slider_vol.setFixedWidth(56)
        self.slider_vol.setFixedHeight(12)
        self.slider_vol.valueChanged.connect(self._on_vol_changed)
        lbl_v = QLabel("VOL")
        lbl_v.setFont(QFont("Monospace", 6))
        lbl_v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v_col.addWidget(self.slider_vol)
        v_col.addWidget(lbl_v)
        sliders_layout.addLayout(v_col)

        # Pan / Balance Slider
        b_col = QVBoxLayout()
        b_col.setSpacing(1)
        self.slider_pan = QSlider(Qt.Orientation.Horizontal)
        self.slider_pan.setRange(-50, 50)
        self.slider_pan.setValue(0)
        self.slider_pan.setFixedWidth(40)
        self.slider_pan.setFixedHeight(12)
        lbl_b = QLabel("BAL")
        lbl_b.setFont(QFont("Monospace", 6))
        lbl_b.setAlignment(Qt.AlignmentFlag.AlignCenter)
        b_col.addWidget(self.slider_pan)
        b_col.addWidget(lbl_b)
        sliders_layout.addLayout(b_col)

        # Seek Bar (Position)
        s_col = QVBoxLayout()
        s_col.setSpacing(1)
        self.slider_seek = QSlider(Qt.Orientation.Horizontal)
        self.slider_seek.setRange(0, 1000)
        self.slider_seek.setValue(0)
        self.slider_seek.setFixedHeight(12)
        self.slider_seek.sliderMoved.connect(self._on_seek_moved)
        lbl_s = QLabel("POSITION")
        lbl_s.setFont(QFont("Monospace", 6))
        lbl_s.setAlignment(Qt.AlignmentFlag.AlignCenter)
        s_col.addWidget(self.slider_seek)
        s_col.addWidget(lbl_s)
        sliders_layout.addLayout(s_col)

        main_layout.addLayout(sliders_layout)

        # 5. Lower Deck: Playback Buttons + Modes + Window Toggles
        btn_row = QHBoxLayout()
        btn_row.setSpacing(2)

        # |<<
        self.btn_prev = QPushButton("|<<")
        self.btn_prev.setFixedSize(28, 20)
        self.btn_prev.clicked.connect(self.audio.prev_track)
        btn_row.addWidget(self.btn_prev)

        # ▶ (PLAY)
        self.btn_play = QPushButton("▶")
        self.btn_play.setFixedSize(28, 20)
        self.btn_play.clicked.connect(self.audio.play)
        btn_row.addWidget(self.btn_play)

        # ❚❚ (PAUSE)
        self.btn_pause = QPushButton("❚❚")
        self.btn_pause.setFixedSize(28, 20)
        self.btn_pause.clicked.connect(self.audio.pause)
        btn_row.addWidget(self.btn_pause)

        # ■ (STOP)
        self.btn_stop = QPushButton("■")
        self.btn_stop.setFixedSize(28, 20)
        self.btn_stop.clicked.connect(self.audio.stop)
        btn_row.addWidget(self.btn_stop)

        # >>|
        self.btn_next = QPushButton(">>|")
        self.btn_next.setFixedSize(28, 20)
        self.btn_next.clicked.connect(self.audio.next_track)
        btn_row.addWidget(self.btn_next)

        # ⏏ (EJECT / OPEN)
        self.btn_eject = QPushButton("⏏")
        self.btn_eject.setFixedSize(24, 20)
        self.btn_eject.clicked.connect(self._eject_dialog)
        btn_row.addWidget(self.btn_eject)

        btn_row.addStretch()

        # SHUFFLE
        self.btn_shuffle = QPushButton("SHUF")
        self.btn_shuffle.setCheckable(True)
        self.btn_shuffle.setFixedSize(34, 20)
        self.btn_shuffle.clicked.connect(self._toggle_shuffle)
        btn_row.addWidget(self.btn_shuffle)

        # REPEAT
        self.btn_repeat = QPushButton("REP")
        self.btn_repeat.setCheckable(True)
        self.btn_repeat.setChecked(True)
        self.btn_repeat.setFixedSize(30, 20)
        self.btn_repeat.clicked.connect(self._toggle_repeat)
        btn_row.addWidget(self.btn_repeat)

        # EQ TOGGLE
        self.btn_eq = QPushButton("EQ")
        self.btn_eq.setCheckable(True)
        self.btn_eq.setFixedSize(24, 20)
        self.btn_eq.clicked.connect(self._toggle_eq)
        btn_row.addWidget(self.btn_eq)

        # PL TOGGLE
        self.btn_pl = QPushButton("PL")
        self.btn_pl.setCheckable(True)
        self.btn_pl.setFixedSize(24, 20)
        self.btn_pl.clicked.connect(self._toggle_pl)
        btn_row.addWidget(self.btn_pl)

        main_layout.addLayout(btn_row)

    # -------------------------------------------------------------------------
    # Window Movement & Docking
    # -------------------------------------------------------------------------
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            new_pos = event.globalPosition().toPoint() - self._drag_pos
            self.move(new_pos)
            
            # Snap children windows (magnetic docking)
            if self.eq_window.isVisible():
                self.eq_window.move(new_pos.x(), new_pos.y() + 150)
            if self.pl_window.isVisible():
                eq_offset = 142 if self.eq_window.isVisible() else 0
                self.pl_window.move(new_pos.x(), new_pos.y() + 150 + eq_offset)
                
            event.accept()

    def _toggle_eq(self):
        if self.btn_eq.isChecked():
            self.eq_window.move(self.x(), self.y() + 150)
            self.eq_window.show()
        else:
            self.eq_window.hide()
        self.config.set("show_eq", self.btn_eq.isChecked())

    def _toggle_pl(self):
        if self.btn_pl.isChecked():
            eq_offset = 142 if self.eq_window.isVisible() else 0
            self.pl_window.move(self.x(), self.y() + 150 + eq_offset)
            self.pl_window.show()
        else:
            self.pl_window.hide()
        self.config.set("show_pl", self.btn_pl.isChecked())

    def _toggle_shuffle(self):
        self.audio.shuffle = self.btn_shuffle.isChecked()
        self.config.set("shuffle", self.audio.shuffle)

    def _toggle_repeat(self):
        self.audio.repeat = self.btn_repeat.isChecked()
        self.config.set("repeat", self.audio.repeat)

    def _on_vol_changed(self, val):
        self.audio.set_volume(val)
        self.vis.set_volume(val)
        self.config.set("volume", val)

    def _on_seek_moved(self, val):
        if self.audio.current_track and self.audio.current_track.duration > 0:
            target_sec = (val / 1000.0) * self.audio.current_track.duration
            self.audio.seek(target_sec)

    def _on_track_changed(self, track):
        self.marquee.set_track(track)
        self.lcd.set_track(track)
        self.slider_seek.setValue(0)

    def _on_position_changed(self, pos_seconds):
        self.lcd.set_position(pos_seconds)
        if self.audio.current_track and self.audio.current_track.duration > 0:
            ratio = min(1.0, pos_seconds / self.audio.current_track.duration)
            self.slider_seek.blockSignals(True)
            self.slider_seek.setValue(int(ratio * 1000))
            self.slider_seek.blockSignals(False)

    def _on_playback_state_changed(self, is_playing):
        self.lcd.set_playing(is_playing)
        self.vis.set_playing(is_playing)

    def _eject_dialog(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Open Audio Files", "",
            "Audio Files (*.mp3 *.flac *.ogg *.wav *.m4a *.aac *.opus *.mod *.xm *.s3m *.it);;All Files (*)"
        )
        if files:
            self.audio.add_files(files)
            self.audio.play_index(len(self.audio.playlist) - len(files))

    def _open_theme_dialog(self):
        dlg = ThemeDialog(self.theme_mgr, self)
        dlg.exec()

    def _exit_app(self):
        self.config.set("main_pos", [self.x(), self.y()])
        self.eq_window.close()
        self.pl_window.close()
        self.close()

    def apply_theme(self):
        bg = self.theme_mgr.hex("chassis_bg", "#282932")
        border = self.theme_mgr.hex("chassis_border", "#4e5062")
        btn_bg = self.theme_mgr.hex("button_bg", "#323440")
        btn_text = self.theme_mgr.hex("button_text", "#d4d8e8")
        btn_active = self.theme_mgr.hex("button_active", "#00ff66")
        title_text = self.theme_mgr.hex("titlebar_text", "#00e5ff")
        trough = self.theme_mgr.hex("slider_trough", "#0a0a0e")
        thumb = self.theme_mgr.hex("slider_thumb", "#5a5d72")

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg};
                color: {btn_text};
                font-family: 'Monospace';
            }}
            QLabel {{
                color: {btn_text};
            }}
            QPushButton {{
                background-color: {btn_bg};
                color: {btn_text};
                border: 1px solid {border};
                border-radius: 2px;
                font-size: 8px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {border};
            }}
            QPushButton:checked {{
                color: {btn_active};
                border: 1px solid {btn_active};
            }}
            QSlider::groove:horizontal {{
                background: {trough};
                height: 4px;
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {thumb};
                width: 10px;
                margin: -4px 0;
                border-radius: 2px;
            }}
            QSlider::handle:horizontal:hover {{
                background: {btn_active};
            }}
        """)
        self.lbl_title.setStyleSheet(f"color: {title_text};")

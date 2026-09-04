import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider, QFileDialog,
    QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QColor, QIcon, QDragEnterEvent, QDropEvent

from ui.lcd_display import LcdDisplay, MarqueeDisplay
from ui.visualizer_widget import VisualizerWidget
from ui.visualizer_studio import VisualizerStudio
from ui.theme_dialog import ThemeDialog
from ui.equalizer_window import EqualizerWindow
from ui.playlist_window import PlaylistWindow
from ui.skinned_player import SkinnedPlayerWidget

class MainWindow(QWidget):
    def __init__(self, audio_engine, theme_mgr, config_mgr, vis_gen=None):
        super().__init__()
        self.audio = audio_engine
        self.theme_mgr = theme_mgr
        self.config = config_mgr

        self.setWindowTitle("OmaAmp")
        self.setMinimumSize(275, 200)
        self.resize(550, 720)
        self.setAcceptDrops(True)

        # Child modular components (embedded as widget decks)
        self.eq_widget = EqualizerWindow(self.theme_mgr, parent=self)
        self.pl_widget = PlaylistWindow(self.audio, self.theme_mgr, parent=self)
        
        # Remove standalone tool window flags so they embed cleanly inside MainWindow
        self.eq_widget.setWindowFlags(Qt.WindowType.Widget)
        self.pl_widget.setWindowFlags(Qt.WindowType.Widget)

        self.init_ui()
        self.apply_theme()

        # Connect signals
        self.theme_mgr.theme_changed.connect(self.apply_theme)
        self.audio.track_changed.connect(self._on_track_changed)
        self.audio.position_changed.connect(self._on_position_changed)
        self.audio.playback_state_changed.connect(self._on_playback_state_changed)
        self.eq_widget.eq_changed.connect(self._on_eq_changed)
        self.slider_pan.valueChanged.connect(self._on_pan_changed)

        # Sync initial EQ settings to DSP engine
        self._on_eq_changed(
            [s.value() for s in self.eq_widget.sliders],
            self.eq_widget.slider_preamp.value()
        )

        # Restore visibility
        show_eq = self.config.get("show_eq", True)
        show_pl = self.config.get("show_pl", True)
        self.eq_frame.setVisible(show_eq)
        self.btn_eq.setChecked(show_eq)
        self.pl_frame.setVisible(show_pl)
        self.btn_pl.setChecked(show_pl)

        # Restore active track metadata and playlist list
        if self.audio.current_track:
            self.marquee.set_track(self.audio.current_track)
            self.lcd.set_track(self.audio.current_track)
        self.pl_widget.refresh_list()

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(2)

        # =====================================================================
        # 1. MAIN PLAYER DECK (Classic Winamp Chassis)
        # =====================================================================
        self.player_frame = QFrame()
        self.player_frame.setFrameShape(QFrame.Shape.NoFrame)
        self.player_frame.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        player_layout = QVBoxLayout(self.player_frame)
        player_layout.setContentsMargins(0, 0, 0, 0)
        player_layout.setSpacing(0)
        
        # 1. Authentic Winamp Skinned Canvas Container
        self.skinned_deck_container = QWidget()
        skinned_layout = QVBoxLayout(self.skinned_deck_container)
        skinned_layout.setContentsMargins(0, 0, 0, 0)
        self.skinned_player = SkinnedPlayerWidget(self.audio, self.theme_mgr, self)
        self.skinned_player.open_skin_dialog.connect(self._open_theme_dialog)
        self.skinned_player.open_vis_studio.connect(self._open_vis_studio)
        self.skinned_player.toggle_eq.connect(self._toggle_eq)
        self.skinned_player.toggle_pl.connect(self._toggle_pl)
        skinned_layout.addWidget(self.skinned_player, alignment=Qt.AlignmentFlag.AlignCenter)
        player_layout.addWidget(self.skinned_deck_container)

        # 2. Vector / Responsive Deck Container (for pure JSON themes)
        self.vector_deck_container = QWidget()
        vector_layout = QVBoxLayout(self.vector_deck_container)
        vector_layout.setContentsMargins(0, 0, 0, 0)
        vector_layout.setSpacing(4)
        player_layout.addWidget(self.vector_deck_container)

        # Title / Skin Bar
        title_row = QHBoxLayout()
        title_row.setSpacing(4)

        self.lbl_title = QLabel("OMAAMP - WINAMP 2.91 CLASSIC")
        self.lbl_title.setFont(QFont("Monospace", 8, QFont.Weight.Bold))
        title_row.addWidget(self.lbl_title)

        title_row.addStretch()

        self.btn_skin = QPushButton("SKIN")
        self.btn_skin.setFixedSize(36, 18)
        self.btn_skin.setToolTip("Change or Create Theme")
        self.btn_skin.clicked.connect(self._open_theme_dialog)
        title_row.addWidget(self.btn_skin)

        vector_layout.addLayout(title_row)

        # Scrolling Song Title Marquee
        self.marquee = MarqueeDisplay(self.theme_mgr, self)
        vector_layout.addWidget(self.marquee)

        # 7-Segment LED Time (Left) + Spectrum Visualizer (Right)
        deck_mid = QHBoxLayout()
        deck_mid.setSpacing(4)

        self.lcd = LcdDisplay(self.theme_mgr, self)
        deck_mid.addWidget(self.lcd)

        self.vis = VisualizerWidget(self.theme_mgr, self.audio, self)
        self.vis.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.vis.setFixedHeight(42)
        deck_mid.addWidget(self.vis)

        vector_layout.addLayout(deck_mid)

        # Sliders Row (Volume, Balance, Position Seek)
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

        # Seek Bar
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

        vector_layout.addLayout(sliders_layout)

        # Playback Buttons + Modes + EQ/PL Toggles
        btn_row = QHBoxLayout()
        btn_row.setSpacing(2)

        self.btn_prev = QPushButton("|<<")
        self.btn_prev.setFixedSize(28, 22)
        self.btn_prev.clicked.connect(self.audio.prev_track)
        btn_row.addWidget(self.btn_prev)

        self.btn_play = QPushButton("▶")
        self.btn_play.setFixedSize(28, 22)
        self.btn_play.clicked.connect(self.audio.play)
        btn_row.addWidget(self.btn_play)

        self.btn_pause = QPushButton("❚❚")
        self.btn_pause.setFixedSize(28, 22)
        self.btn_pause.clicked.connect(self.audio.pause)
        btn_row.addWidget(self.btn_pause)

        self.btn_stop = QPushButton("■")
        self.btn_stop.setFixedSize(28, 22)
        self.btn_stop.clicked.connect(self.audio.stop)
        btn_row.addWidget(self.btn_stop)

        self.btn_next = QPushButton(">>|")
        self.btn_next.setFixedSize(28, 22)
        self.btn_next.clicked.connect(self.audio.next_track)
        btn_row.addWidget(self.btn_next)

        self.btn_eject = QPushButton("⏏")
        self.btn_eject.setFixedSize(24, 22)
        self.btn_eject.clicked.connect(self._eject_dialog)
        btn_row.addWidget(self.btn_eject)

        btn_row.addStretch()

        self.btn_shuffle = QPushButton("SHUF")
        self.btn_shuffle.setCheckable(True)
        self.btn_shuffle.setFixedSize(36, 22)
        self.btn_shuffle.clicked.connect(self._toggle_shuffle)
        btn_row.addWidget(self.btn_shuffle)

        self.btn_repeat = QPushButton("REP")
        self.btn_repeat.setCheckable(True)
        self.btn_repeat.setChecked(True)
        self.btn_repeat.setFixedSize(32, 22)
        self.btn_repeat.clicked.connect(self._toggle_repeat)
        btn_row.addWidget(self.btn_repeat)

        self.btn_eq = QPushButton("EQ")
        self.btn_eq.setCheckable(True)
        self.btn_eq.setFixedSize(26, 22)
        self.btn_eq.clicked.connect(self._toggle_eq)
        btn_row.addWidget(self.btn_eq)

        self.btn_pl = QPushButton("PL")
        self.btn_pl.setCheckable(True)
        self.btn_pl.setFixedSize(26, 22)
        self.btn_pl.clicked.connect(self._toggle_pl)
        btn_row.addWidget(self.btn_pl)

        self.btn_vis = QPushButton("VIS")
        self.btn_vis.setFixedSize(28, 22)
        self.btn_vis.setToolTip("Open Visualizer Studio (Fullscreen / Multi-mode)")
        self.btn_vis.clicked.connect(self._open_vis_studio)
        btn_row.addWidget(self.btn_vis)

        vector_layout.addLayout(btn_row)
        root_layout.addWidget(self.player_frame)

        # =====================================================================
        # 2. EQUALIZER DECK (Collapsible)
        # =====================================================================
        self.eq_frame = QFrame()
        self.eq_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.eq_frame.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        eq_layout = QVBoxLayout(self.eq_frame)
        eq_layout.setContentsMargins(0, 0, 0, 0)
        eq_layout.addWidget(self.eq_widget)
        root_layout.addWidget(self.eq_frame)

        # =====================================================================
        # 3. PLAYLIST DECK (Expanding to fill Tile)
        # =====================================================================
        self.pl_frame = QFrame()
        self.pl_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.pl_frame.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        pl_layout = QVBoxLayout(self.pl_frame)
        pl_layout.setContentsMargins(0, 0, 0, 0)
        pl_layout.addWidget(self.pl_widget)
        root_layout.addWidget(self.pl_frame)

    def _toggle_eq(self):
        show = self.btn_eq.isChecked()
        self.eq_frame.setVisible(show)
        self.config.set("show_eq", show)

    def _toggle_pl(self):
        show = self.btn_pl.isChecked()
        self.pl_frame.setVisible(show)
        self.config.set("show_pl", show)

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

    def _on_pan_changed(self, val):
        self.audio.set_balance(val)

    def _on_eq_changed(self, bands, preamp):
        enabled = self.eq_widget.eq_enabled
        self.audio.set_eq_params(bands, preamp, enabled)

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

    def _open_vis_studio(self):
        studio = VisualizerStudio(self.theme_mgr, self.audio, self)
        studio.exec()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        audio_paths = []
        for u in urls:
            if u.isLocalFile():
                fpath = u.toLocalFile()
                ext = os.path.splitext(fpath)[1].lower()
                if ext in {'.wsz', '.zip'}:
                    # Import and activate Winamp skin!
                    self.theme_mgr.import_skin_file(fpath)
                else:
                    audio_paths.append(fpath)
        if audio_paths:
            self.audio.add_files(audio_paths)
        event.acceptProposedAction()

    def closeEvent(self, event):
        self.config.set("volume", self.slider_vol.value())
        self.config.save()
        super().closeEvent(event)

    def apply_theme(self):
        bg = self.theme_mgr.hex("chassis_bg", "#282932")
        border = self.theme_mgr.hex("chassis_border", "#4e5062")
        btn_bg = self.theme_mgr.hex("button_bg", "#323440")
        btn_text = self.theme_mgr.hex("button_text", "#d4d8e8")
        btn_active = self.theme_mgr.hex("button_active", "#00ff66")
        title_text = self.theme_mgr.hex("titlebar_text", "#00e5ff")
        trough = self.theme_mgr.hex("slider_trough", "#0a0a0e")
        thumb = self.theme_mgr.hex("slider_thumb", "#5a5d72")

        # Toggle between Skinned Canvas Deck and Vector Deck
        is_skinned = (self.theme_mgr.active_skin is not None)
        self.skinned_deck_container.setVisible(is_skinned)
        self.vector_deck_container.setVisible(not is_skinned)

        self.setStyleSheet(f"""
            MainWindow, QWidget {{
                background-color: {bg};
                color: {btn_text};
                font-family: 'Monospace';
            }}
            QFrame {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 4px;
            }}
            QLabel {{
                color: {btn_text};
                border: none;
                background: transparent;
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

        # Apply authentic Winamp button sprites if skin provides them
        skin = self.theme_mgr.active_skin
        if skin and skin.sprites:
            sprites = skin.sprites
            btn_map = [
                (self.btn_prev, 'btn_prev'),
                (self.btn_play, 'btn_play'),
                (self.btn_pause, 'btn_pause'),
                (self.btn_stop, 'btn_stop'),
                (self.btn_next, 'btn_next'),
                (self.btn_eject, 'btn_eject')
            ]
            for btn, s_name in btn_map:
                if s_name in sprites:
                    icon_pix = sprites[s_name][0]
                    btn.setIcon(QIcon(icon_pix))
                    btn.setIconSize(QSize(icon_pix.width(), icon_pix.height()))
                    btn.setText("")
        else:
            self.btn_prev.setIcon(QIcon())
            self.btn_prev.setText("|<<")
            self.btn_play.setIcon(QIcon())
            self.btn_play.setText("▶")
            self.btn_pause.setIcon(QIcon())
            self.btn_pause.setText("❚❚")
            self.btn_stop.setIcon(QIcon())
            self.btn_stop.setText("■")
            self.btn_next.setIcon(QIcon())
            self.btn_next.setText(">>|")
            self.btn_eject.setIcon(QIcon())
            self.btn_eject.setText("⏏")

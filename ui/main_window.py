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
from core.i18n import _, i18n

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
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

        # Child modular components (embedded as widget decks)
        self.eq_widget = EqualizerWindow(self.theme_mgr, parent=self)
        self.pl_widget = PlaylistWindow(self.audio, self.theme_mgr, parent=self)
        
        # Remove standalone tool window flags so they embed cleanly inside MainWindow
        self.eq_widget.setWindowFlags(Qt.WindowType.Widget)
        self.pl_widget.setWindowFlags(Qt.WindowType.Widget)

        self.init_ui()
        self.apply_theme()
        self.retranslate_ui()

        # Connect signals
        self.theme_mgr.theme_changed.connect(self.apply_theme)
        i18n.language_changed.connect(self.retranslate_ui)
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
        self.player_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.player_frame.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        player_layout = QVBoxLayout(self.player_frame)
        player_layout.setContentsMargins(6, 4, 6, 6)
        player_layout.setSpacing(4)

        # Title / Skin Bar
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(4)

        self.lbl_title = QLabel("OMAAMP - WINAMP 2.91 CLASSIC")
        self.lbl_title.setFont(QFont("Monospace", 8, QFont.Weight.Bold))
        title_row.addWidget(self.lbl_title)

        title_row.addStretch()

        self.btn_radio = QPushButton("RADIO")
        self.btn_radio.setFixedSize(44, 18)
        self.btn_radio.setToolTip("Open Online Radio & YouTube Stream Studio")
        self.btn_radio.clicked.connect(self._open_radio_dialog)
        title_row.addWidget(self.btn_radio)

        self.btn_skin = QPushButton("SKIN")
        self.btn_skin.setFixedSize(36, 18)
        self.btn_skin.setToolTip("Change or Create Theme")
        self.btn_skin.clicked.connect(self._open_theme_dialog)
        title_row.addWidget(self.btn_skin)

        self.btn_vis = QPushButton("VIS")
        self.btn_vis.setFixedSize(32, 18)
        self.btn_vis.setToolTip("Open Visualizer Studio (Fullscreen / Multi-mode)")
        self.btn_vis.clicked.connect(self._open_vis_studio)
        title_row.addWidget(self.btn_vis)

        self.btn_lang = QPushButton(i18n.get_language().upper())
        self.btn_lang.setFixedSize(28, 18)
        self.btn_lang.setToolTip("Switch Language / Byt språk (SV / EN)")
        self.btn_lang.clicked.connect(self._toggle_language)
        title_row.addWidget(self.btn_lang)

        player_layout.addLayout(title_row)

        # Widescreen LCD Container (Album Art + Time on Left, Marquee + Visualizer on Right)
        self.lcd_container = QFrame()
        self.lcd_container.setObjectName("LcdContainer")
        lcd_layout = QHBoxLayout(self.lcd_container)
        lcd_layout.setContentsMargins(4, 4, 4, 4)
        lcd_layout.setSpacing(8)

        # 1. Left: Dedicated 96x96 Album Art with Time Display directly underneath
        self.lcd = LcdDisplay(self.theme_mgr, self)
        self.lcd.setFixedWidth(136)
        self.lcd.setFixedHeight(144)
        lcd_layout.addWidget(self.lcd)

        # 2. Right: Top Title Marquee + Bottom Real-time Spectrum Visualizer
        right_deck = QVBoxLayout()
        right_deck.setContentsMargins(0, 0, 0, 0)
        right_deck.setSpacing(4)

        self.marquee = MarqueeDisplay(self.theme_mgr, self)
        self.marquee.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.marquee.setFixedHeight(38)
        right_deck.addWidget(self.marquee)

        self.vis = VisualizerWidget(self.theme_mgr, self.audio, self, config_mgr=self.config)
        self.vis.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.vis.setMinimumHeight(80)
        self.vis.setFixedHeight(102)
        right_deck.addWidget(self.vis)

        lcd_layout.addLayout(right_deck)
        player_layout.addWidget(self.lcd_container)

        # Sliders Row (Volume + Balance + Full-Width Seek Bar)
        sliders_layout = QHBoxLayout()
        sliders_layout.setContentsMargins(0, 0, 0, 0)
        sliders_layout.setSpacing(6)

        lbl_v = QLabel("VOL")
        lbl_v.setFont(QFont("Monospace", 6, QFont.Weight.Bold))
        sliders_layout.addWidget(lbl_v)

        self.slider_vol = QSlider(Qt.Orientation.Horizontal)
        self.slider_vol.setRange(0, 100)
        self.slider_vol.setValue(self.config.get("volume", 80))
        self.slider_vol.setFixedWidth(64)
        self.slider_vol.setFixedHeight(12)
        self.slider_vol.valueChanged.connect(self._on_vol_changed)
        sliders_layout.addWidget(self.slider_vol)

        lbl_b = QLabel("BAL")
        lbl_b.setFont(QFont("Monospace", 6, QFont.Weight.Bold))
        sliders_layout.addWidget(lbl_b)

        self.slider_pan = QSlider(Qt.Orientation.Horizontal)
        self.slider_pan.setRange(-50, 50)
        self.slider_pan.setValue(0)
        self.slider_pan.setFixedWidth(44)
        self.slider_pan.setFixedHeight(12)
        self.slider_pan.valueChanged.connect(self._on_pan_changed)
        sliders_layout.addWidget(self.slider_pan)

        lbl_s = QLabel("SEEK")
        lbl_s.setFont(QFont("Monospace", 6, QFont.Weight.Bold))
        sliders_layout.addWidget(lbl_s)

        self.slider_seek = QSlider(Qt.Orientation.Horizontal)
        self.slider_seek.setRange(0, 1000)
        self.slider_seek.setValue(0)
        self.slider_seek.setFixedHeight(12)
        self.slider_seek.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.slider_seek.sliderMoved.connect(self._on_seek_moved)
        sliders_layout.addWidget(self.slider_seek)

        player_layout.addLayout(sliders_layout)

        # Playback Buttons + Modes + EQ/PL Toggles
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
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
        self.btn_shuffle.setFixedSize(48, 22)
        self.btn_shuffle.clicked.connect(self._toggle_shuffle)
        btn_row.addWidget(self.btn_shuffle)

        self.btn_repeat = QPushButton("REP")
        self.btn_repeat.setCheckable(True)
        self.btn_repeat.setChecked(True)
        self.btn_repeat.setFixedSize(36, 22)
        self.btn_repeat.clicked.connect(self._toggle_repeat)
        btn_row.addWidget(self.btn_repeat)

        self.btn_eq = QPushButton("EQ")
        self.btn_eq.setCheckable(True)
        self.btn_eq.setFixedSize(28, 22)
        self.btn_eq.clicked.connect(self._toggle_eq)
        btn_row.addWidget(self.btn_eq)

        self.btn_pl = QPushButton("PL")
        self.btn_pl.setCheckable(True)
        self.btn_pl.setFixedSize(28, 22)
        self.btn_pl.clicked.connect(self._toggle_pl)
        btn_row.addWidget(self.btn_pl)

        player_layout.addLayout(btn_row)
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
        self._update_toggle_icons()

    def _toggle_pl(self):
        show = self.btn_pl.isChecked()
        self.pl_frame.setVisible(show)
        self.config.set("show_pl", show)
        self._update_toggle_icons()

    def _toggle_shuffle(self):
        self.audio.shuffle = self.btn_shuffle.isChecked()
        self.config.set("shuffle", self.audio.shuffle)
        self._update_toggle_icons()

    def _toggle_repeat(self):
        self.audio.repeat = self.btn_repeat.isChecked()
        self.config.set("repeat", self.audio.repeat)
        self._update_toggle_icons()

    def _update_toggle_icons(self):
        skin = self.theme_mgr.active_skin
        if skin and skin.sprites:
            sprites = skin.sprites
            if 'btn_shuf' in sprites:
                pix = sprites['btn_shuf'][1 if self.btn_shuffle.isChecked() else 0]
                self.btn_shuffle.setIcon(QIcon(pix))
                self.btn_shuffle.setIconSize(QSize(pix.width(), pix.height()))
                self.btn_shuffle.setFixedSize(pix.width(), pix.height())
                self.btn_shuffle.setStyleSheet("border: none; padding: 0px; background: transparent;")
            if 'btn_rep' in sprites:
                pix = sprites['btn_rep'][1 if self.btn_repeat.isChecked() else 0]
                self.btn_repeat.setIcon(QIcon(pix))
                self.btn_repeat.setIconSize(QSize(pix.width(), pix.height()))
                self.btn_repeat.setFixedSize(pix.width(), pix.height())
                self.btn_repeat.setStyleSheet("border: none; padding: 0px; background: transparent;")
            if 'btn_eq' in sprites:
                pix = sprites['btn_eq'][1 if self.btn_eq.isChecked() else 0]
                self.btn_eq.setIcon(QIcon(pix))
                self.btn_eq.setIconSize(QSize(pix.width(), pix.height()))
                self.btn_eq.setFixedSize(pix.width(), pix.height())
                self.btn_eq.setStyleSheet("border: none; padding: 0px; background: transparent;")
            if 'btn_pl' in sprites:
                pix = sprites['btn_pl'][1 if self.btn_pl.isChecked() else 0]
                self.btn_pl.setIcon(QIcon(pix))
                self.btn_pl.setIconSize(QSize(pix.width(), pix.height()))
                self.btn_pl.setFixedSize(pix.width(), pix.height())
                self.btn_pl.setStyleSheet("border: none; padding: 0px; background: transparent;")

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

    def _open_radio_dialog(self):
        from ui.radio_dialog import RadioDialog
        dlg = RadioDialog(self.audio, self.theme_mgr, self)
        dlg.exec()

    def _open_theme_dialog(self):
        dlg = ThemeDialog(self.theme_mgr, self)
        dlg.exec()

    def _open_vis_studio(self):
        studio = VisualizerStudio(self.theme_mgr, self.audio, self)
        studio.exec()

    def _toggle_language(self):
        new_lang = "en" if i18n.get_language() == "sv" else "sv"
        i18n.set_language(new_lang)
        self.config.set("language", new_lang)
        self.config.save()
        self.btn_lang.setText(new_lang.upper())
        self.retranslate_ui()

    def retranslate_ui(self):
        self.lbl_title.setText(_("app_title"))
        self.btn_radio.setText(_("btn_radio"))
        self.btn_radio.setToolTip(_("btn_radio_tip"))
        self.btn_skin.setText(_("btn_skin"))
        self.btn_skin.setToolTip(_("btn_skin_tip"))
        self.btn_vis.setText(_("btn_vis"))
        self.btn_vis.setToolTip(_("btn_vis_tip"))
        self.btn_prev.setToolTip(_("btn_prev_tip"))
        self.btn_play.setToolTip(_("btn_play_tip"))
        self.btn_pause.setToolTip(_("btn_pause_tip"))
        self.btn_stop.setToolTip(_("btn_stop_tip"))
        self.btn_next.setToolTip(_("btn_next_tip"))
        self.btn_eject.setToolTip(_("btn_eject_tip"))
        self.btn_shuffle.setToolTip(_("btn_shuf_tip"))
        self.btn_repeat.setToolTip(_("btn_rep_tip"))
        self.btn_eq.setToolTip(_("btn_eq_tip"))
        self.btn_pl.setToolTip(_("btn_pl_tip"))
        self.eq_widget.retranslate_ui()
        self.pl_widget.retranslate_ui()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
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
            else:
                raw_url = u.toString()
                if raw_url:
                    audio_paths.append(raw_url)

        if not urls and event.mimeData().hasText():
            text = event.mimeData().text().strip()
            if text.startswith("http://") or text.startswith("https://"):
                audio_paths.append(text)

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

        # Allow flexible tiling in Hyprland and standard window managers
        self.setMinimumWidth(280)
        self.setMaximumWidth(16777215)
        self.setMinimumHeight(240)
        self.setMaximumHeight(16777215)

        knob_path = self.theme_mgr.knob_image_path()
        if knob_path:
            handle_css = f"""
                QSlider::handle:horizontal {{
                    image: url('{knob_path}');
                    width: 20px;
                    height: 15px;
                    margin: -5px 0;
                    background: transparent;
                }}
            """
        else:
            handle_css = f"""
                QSlider::handle:horizontal {{
                    background: {thumb};
                    width: 12px;
                    margin: -4px 0;
                    border-radius: 2px;
                    border: 1px solid {border};
                }}
            """

        chassis_pattern = self.theme_mgr.get_texture_path("chassis_pattern")
        titlebar_pattern = self.theme_mgr.get_texture_path("titlebar_repeat")
        frame_bg_css = f"background-image: url('{chassis_pattern}'); background-repeat: repeat;" if chassis_pattern else f"background-color: {bg};"

        self.setStyleSheet(f"""
            MainWindow, QWidget {{
                background-color: {bg};
                color: {btn_text};
                font-family: 'Monospace';
            }}
            QFrame {{
                {frame_bg_css}
                border: 1px solid {border};
                border-radius: 4px;
            }}
            QFrame#LcdContainer {{
                background-image: none;
                background-color: {self.theme_mgr.hex("lcd_bg", "#000000")};
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
                padding: 1px 4px;
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
                height: 5px;
                border-radius: 2px;
            }}
            {handle_css}
            QSlider::handle:horizontal:hover {{
                background: {btn_active};
            }}
        """)
        if titlebar_pattern:
            self.lbl_title.setStyleSheet(f"color: {title_text}; background-image: url('{titlebar_pattern}'); background-repeat: repeat; padding: 2px 6px; border-radius: 2px;")
        else:
            self.lbl_title.setStyleSheet(f"color: {title_text}; background: transparent;")

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
                (self.btn_eject, 'btn_eject'),
                (self.btn_shuffle, 'btn_shuf'),
                (self.btn_repeat, 'btn_rep'),
                (self.btn_eq, 'btn_eq'),
                (self.btn_pl, 'btn_pl')
            ]
            for btn, s_name in btn_map:
                if s_name in sprites:
                    icon_pix = sprites[s_name][0]
                    btn.setIcon(QIcon(icon_pix))
                    btn.setIconSize(QSize(icon_pix.width(), icon_pix.height()))
                    btn.setFixedSize(icon_pix.width(), icon_pix.height())
                    btn.setStyleSheet("border: none; padding: 0px; background: transparent;")
                    btn.setText("")
        else:
            transport_btns = [
                (self.btn_prev, "|<<", 28, 22),
                (self.btn_play, "▶", 28, 22),
                (self.btn_pause, "❚❚", 28, 22),
                (self.btn_stop, "■", 28, 22),
                (self.btn_next, ">>|", 28, 22),
                (self.btn_eject, "⏏", 24, 22),
                (self.btn_shuffle, "SHUF", 48, 22),
                (self.btn_repeat, "REP", 36, 22),
                (self.btn_eq, "EQ", 28, 22),
                (self.btn_pl, "PL", 28, 22),
            ]
            for btn, txt, w, h in transport_btns:
                btn.setIcon(QIcon())
                btn.setText(txt)
                btn.setFixedSize(w, h)
                btn.setStyleSheet("")

        self._update_toggle_icons()

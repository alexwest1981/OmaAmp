from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal, QTimer
from PyQt6.QtGui import QPainter, QImage, QPixmap, QColor, QFont, QPen, QMouseEvent

class SkinnedPlayerWidget(QWidget):
    open_skin_dialog = pyqtSignal()
    open_vis_studio = pyqtSignal()
    toggle_eq = pyqtSignal()
    toggle_pl = pyqtSignal()

    def __init__(self, audio_engine, theme_mgr, parent=None):
        super().__init__(parent)
        self.audio = audio_engine
        self.theme_mgr = theme_mgr
        
        self.base_w = 275
        self.base_h = 116
        self.scale = 2.0
        self.setFixedSize(550, 232)
        
        self.is_dragging_seek = False
        self.is_dragging_vol = False
        self.is_dragging_pan = False
        self.pressed_btn = None
        self.time_mode = "elapsed"  # "elapsed" | "remaining"
        self.scroll_pos = 0

        # High-FPS update timer (50 FPS for smooth FFT and sliders)
        self.timer = QTimer(self)
        self.timer.setInterval(20)
        self.timer.timeout.connect(self._on_tick)
        self.timer.start()

        # Marquee scroll timer
        self.scroll_timer = QTimer(self)
        self.scroll_timer.setInterval(120)
        self.scroll_timer.timeout.connect(self._on_scroll)
        self.scroll_timer.start()

    def _on_tick(self):
        self.update()

    def _on_scroll(self):
        track_name = self.audio.current_track.display_name if self.audio.current_track else "OMAAMP - WINAMP CLASSIC"
        if len(track_name) > 24:
            self.scroll_pos += 1
            if self.scroll_pos > len(track_name) + 6:
                self.scroll_pos = 0
            self.update()

    # -------------------------------------------------------------------------
    # Hit Testing & Mouse Interactions
    # -------------------------------------------------------------------------
    def _map_to_base(self, pos: QPoint):
        return QPoint(int(pos.x() / self.scale), int(pos.y() / self.scale))

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            pt = self._map_to_base(event.pos())
            x, y = pt.x(), pt.y()

            # 1. Transport Buttons (y=88..106)
            if 88 <= y <= 106:
                if 16 <= x < 39:
                    self.pressed_btn = 'prev'
                    self.audio.prev_track()
                elif 39 <= x < 62:
                    self.pressed_btn = 'play'
                    self.audio.play()
                elif 62 <= x < 85:
                    self.pressed_btn = 'pause'
                    self.audio.pause()
                elif 85 <= x < 108:
                    self.pressed_btn = 'stop'
                    self.audio.stop()
                elif 108 <= x < 130:
                    self.pressed_btn = 'next'
                    self.audio.next_track()
                elif 136 <= x < 158:
                    self.pressed_btn = 'eject'
                elif 164 <= x < 211:
                    self.audio.shuffle = not self.audio.shuffle
                elif 210 <= x < 238:
                    self.audio.repeat = not self.audio.repeat

            # 2. EQ & PL buttons (y=58..70)
            elif 58 <= y <= 70:
                if 219 <= x < 242:
                    self.toggle_eq.emit()
                elif 242 <= x < 265:
                    self.toggle_pl.emit()

            # 3. Time Mode Toggle (x=36..99, y=26..39)
            elif 26 <= y <= 39 and 36 <= x <= 99:
                self.time_mode = "remaining" if self.time_mode == "elapsed" else "elapsed"

            # 4. Skin Dialog Button in Titlebar (x=6..22, y=3..13)
            elif 3 <= y <= 13:
                if 6 <= x <= 22:
                    self.open_skin_dialog.emit()
                elif 244 <= x <= 254:
                    self.window().showMinimized()
                elif 264 <= x <= 274:
                    self.window().close()

            # 5. Visualizer click (x=24..99, y=43..59)
            elif 43 <= y <= 59 and 24 <= x <= 99:
                self.open_vis_studio.emit()

            # 6. Seek Bar (x=16..264, y=72..82)
            elif 72 <= y <= 82 and 16 <= x <= 264:
                self.is_dragging_seek = True
                self._update_seek_pos(x)

            # 7. Volume Slider (x=107..175, y=57..70)
            elif 57 <= y <= 70 and 107 <= x <= 175:
                self.is_dragging_vol = True
                self._update_vol_pos(x)

            # 8. Balance Slider (x=177..215, y=57..70)
            elif 57 <= y <= 70 and 177 <= x <= 215:
                self.is_dragging_pan = True
                self._update_pan_pos(x)

            self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        pt = self._map_to_base(event.pos())
        x = pt.x()
        if self.is_dragging_seek:
            self._update_seek_pos(x)
        elif self.is_dragging_vol:
            self._update_vol_pos(x)
        elif self.is_dragging_pan:
            self._update_pan_pos(x)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.pressed_btn = None
        self.is_dragging_seek = False
        self.is_dragging_vol = False
        self.is_dragging_pan = False
        self.update()

    def _update_seek_pos(self, x):
        rel = max(0.0, min(1.0, (x - 16) / 232.0))
        if self.audio.current_track and self.audio.current_track.duration > 0:
            target_sec = rel * self.audio.current_track.duration
            self.audio.seek(target_sec)

    def _update_vol_pos(self, x):
        rel = max(0.0, min(1.0, (x - 107) / 54.0))
        self.audio.set_volume(int(rel * 100))

    def _update_pan_pos(self, x):
        rel = max(-1.0, min(1.0, (x - 196) / 19.0))
        self.audio.set_balance(int(rel * 50))

    # -------------------------------------------------------------------------
    # Winamp 2.x Precision Bitmap Compositing
    # -------------------------------------------------------------------------
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.scale(self.scale, self.scale)

        skin = self.theme_mgr.active_skin
        bitmaps = skin.bitmaps if skin else {}

        # 1. Main Background (MAIN.BMP)
        main_img = bitmaps.get('main')
        if main_img and not main_img.isNull():
            painter.drawImage(0, 0, main_img)
        else:
            bg_col = self.theme_mgr.color("chassis_bg", "#282932")
            painter.fillRect(0, 0, self.base_w, self.base_h, bg_col)

        # 2. Titlebar (TITLEBAR.BMP)
        titlebar = bitmaps.get('titlebar')
        if titlebar and not titlebar.isNull():
            # Active titlebar slice (27, 0, 275, 14)
            painter.drawImage(0, 0, titlebar, 27, 0, 275, 14)
        else:
            tbar_col = self.theme_mgr.color("titlebar_bg", "#1c1d24")
            painter.fillRect(0, 0, self.base_w, 14, tbar_col)

        # 3. 7-Segment LED Clock Digits (NUMBERS.BMP)
        self._draw_clock(painter, bitmaps.get('numbers'))

        # 4. Real FFT Visualizer (VISCOLOR.TXT)
        self._draw_vis(painter)

        # 5. Marquee Scrolling Song Title (TEXT.BMP)
        self._draw_marquee(painter, bitmaps.get('text'))

        # 6. Specs: KBPS / KHZ / STEREO
        self._draw_specs(painter, bitmaps.get('monoster'))

        # 7. Volume & Balance Sliders (VOLUME.BMP, BALANCE.BMP)
        self._draw_sliders(painter, bitmaps)

        # 8. Seek Bar (POSBAR.BMP)
        self._draw_seek(painter, bitmaps.get('posbar'))

        # 9. Transport Buttons (CBUTTONS.BMP)
        self._draw_cbuttons(painter, bitmaps.get('cbuttons'))

        # 10. Shuffle, Repeat, EQ, PL (SHUFREP.BMP)
        self._draw_shufrep(painter, bitmaps.get('shufrep'))

    def _draw_clock(self, painter, numbers_img):
        pos_sec = self.audio.current_position
        dur_sec = self.audio.current_track.duration if self.audio.current_track else 0.0
        
        if self.time_mode == "remaining" and dur_sec > 0:
            rem = max(0.0, dur_sec - pos_sec)
            mins = int(rem // 60)
            secs = int(rem % 60)
            is_minus = True
        else:
            mins = int(pos_sec // 60)
            secs = int(pos_sec % 60)
            is_minus = False

        d_w = 9
        d_h = 13
        y = 26

        if numbers_img and not numbers_img.isNull():
            if is_minus:
                painter.drawImage(36, y, numbers_img, 99 if numbers_img.width() >= 108 else 0, 0, d_w, d_h)
            else:
                painter.drawImage(36, y, numbers_img, 90 if numbers_img.width() >= 99 else 0, 0, d_w, d_h)

            m1 = (mins // 10) % 10
            m2 = mins % 10
            painter.drawImage(48, y, numbers_img, m1 * d_w, 0, d_w, d_h)
            painter.drawImage(60, y, numbers_img, m2 * d_w, 0, d_w, d_h)

            s1 = (secs // 10) % 10
            s2 = secs % 10
            painter.drawImage(78, y, numbers_img, s1 * d_w, 0, d_w, d_h)
            painter.drawImage(90, y, numbers_img, s2 * d_w, 0, d_w, d_h)
        else:
            painter.setFont(QFont("Monospace", 9, QFont.Weight.Bold))
            painter.setPen(self.theme_mgr.color("lcd_text", "#00ff33"))
            prefix = "-" if is_minus else " "
            painter.drawText(36, y + 11, f"{prefix}{mins:02d}:{secs:02d}")

    def _draw_vis(self, painter):
        vis_rect = QRect(24, 43, 75, 16)
        vis_bg = self.theme_mgr.color("vis_bg", "#000000")
        painter.fillRect(vis_rect, vis_bg)

        bars, peaks = self.audio.analyzer.get_real_spectrum(
            self.audio.is_playing, self.audio.current_position, self.audio.volume
        )
        
        num_bars = min(19, len(bars))
        bar_w = 3
        gap = 1

        col_low = self.theme_mgr.color("vis_bars_low", "#00ff44")
        col_mid = self.theme_mgr.color("vis_bars_mid", "#ffea00")
        col_high = self.theme_mgr.color("vis_bars_high", "#ff2200")
        col_peak = self.theme_mgr.color("vis_peaks", "#ffffff")

        for i in range(num_bars):
            bx = 24 + i * (bar_w + gap)
            bar_h = int(bars[i] * 15)
            peak_y = 58 - int(peaks[i] * 15)

            y = 58
            while y > (58 - bar_h):
                rel = (58 - y) / 15.0
                c = col_low if rel < 0.55 else (col_mid if rel < 0.85 else col_high)
                painter.fillRect(bx, y - 1, bar_w, 1, c)
                y -= 2

            if peaks[i] > 0.05:
                painter.fillRect(bx, peak_y, bar_w, 1, col_peak)

    def _draw_marquee(self, painter, text_img):
        clip_rect = QRect(111, 27, 153, 12)
        painter.setClipRect(clip_rect)

        track_name = self.audio.current_track.display_name if self.audio.current_track else "WINAMP - IT REALLY WHIPS THE LLAMA'S ASS!"
        disp_text = track_name
        if self.scroll_pos > 0:
            disp_text = (track_name + "   ***   " + track_name)[self.scroll_pos:]

        col_text = self.theme_mgr.color("lcd_text", "#ffffff")
        painter.setPen(col_text)
        painter.setFont(QFont("Monospace", 6, QFont.Weight.Bold))
        painter.drawText(112, 36, disp_text)

        painter.setClipping(False)

    def _draw_specs(self, painter, monoster_img):
        painter.setFont(QFont("Monospace", 5, QFont.Weight.Bold))
        col_kbps = self.theme_mgr.color("lcd_kbps", "#00ff33")
        painter.setPen(col_kbps)

        kbps = self.audio.current_track.bitrate if self.audio.current_track else 320
        khz = int(self.audio.current_track.samplerate / 1000) if self.audio.current_track else 44

        painter.drawText(112, 47, f"{kbps}K")
        painter.drawText(148, 47, f"{khz}K")
        painter.drawText(184, 47, "STEREO")

    def _draw_sliders(self, painter, bitmaps):
        vol_img = bitmaps.get('volume')
        vol_ratio = self.audio.volume / 100.0
        knob_x = 107 + int(vol_ratio * 54)
        
        if vol_img and not vol_img.isNull():
            painter.drawImage(knob_x, 57, vol_img, 0, 422, 14, 11)
        else:
            painter.fillRect(107, 62, 68, 3, QColor('#000000'))
            painter.fillRect(knob_x, 58, 14, 11, QColor('#ffffff'))

        bal_img = bitmaps.get('balance')
        bal_ratio = (self.audio.balance + 1.0) / 2.0
        b_knob_x = 177 + int(bal_ratio * 24)
        
        if bal_img and not bal_img.isNull():
            painter.drawImage(b_knob_x, 57, bal_img, 0, 422, 14, 11)
        else:
            painter.fillRect(177, 62, 38, 3, QColor('#000000'))
            painter.fillRect(b_knob_x, 58, 14, 11, QColor('#ffffff'))

    def _draw_seek(self, painter, posbar_img):
        pos_sec = self.audio.current_position
        dur_sec = self.audio.current_track.duration if self.audio.current_track else 0.0
        ratio = (pos_sec / dur_sec) if dur_sec > 0 else 0.0
        ratio = max(0.0, min(1.0, ratio))
        thumb_x = 16 + int(ratio * 219)

        if posbar_img and not posbar_img.isNull():
            painter.drawImage(thumb_x, 72, posbar_img, 248, 0, 29, 10)
        else:
            painter.fillRect(16, 76, 248, 2, QColor('#000000'))
            painter.fillRect(thumb_x, 72, 29, 10, QColor('#cccccc'))

    def _draw_cbuttons(self, painter, cbuttons_img):
        btns = [
            ('prev', 16, 0, 23, 18),
            ('play', 39, 23, 23, 18),
            ('pause', 62, 46, 23, 18),
            ('stop', 85, 69, 23, 18),
            ('next', 108, 92, 22, 18)
        ]
        
        if cbuttons_img and not cbuttons_img.isNull():
            for name, x, src_x, w, h in btns:
                is_pressed = (self.pressed_btn == name)
                src_y = 18 if is_pressed else 0
                painter.drawImage(x, 88, cbuttons_img, src_x, src_y, w, h)
                
            if cbuttons_img.width() >= 136:
                is_eject_pressed = (self.pressed_btn == 'eject')
                painter.drawImage(136, 89, cbuttons_img, 114, 16 if is_eject_pressed else 0, 22, 16)

    def _draw_shufrep(self, painter, shufrep_img):
        if shufrep_img and not shufrep_img.isNull():
            shuf_src_y = 15 if self.audio.shuffle else 0
            painter.drawImage(164, 89, shufrep_img, 28, shuf_src_y, 47, 15)

            rep_src_y = 15 if self.audio.repeat else 0
            painter.drawImage(210, 89, shufrep_img, 0, rep_src_y, 28, 15)

            if shufrep_img.height() >= 73:
                painter.drawImage(219, 58, shufrep_img, 0, 61, 23, 12)
                painter.drawImage(242, 58, shufrep_img, 23, 61, 23, 12)

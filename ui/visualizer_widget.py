import math
from PyQt6.QtWidgets import QWidget, QMenu
from PyQt6.QtCore import Qt, QTimer, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QLinearGradient, QPainterPath

from core.i18n import i18n

VIS_MODES = [
    ("spectrum", "📊 Spectrum Analyzer (Real FFT)"),
    ("oscilloscope", "〰️ Laser Oscilloscope (Real PCM)"),
    ("vu_meter", "📻 Dual Analog VU Meters (Real RMS)"),
    ("starfield", "✨ 3D Warp Starfield"),
    ("matrix", "💻 Matrix Code Rain"),
    ("circular", "🔘 Polar Frequency Ring")
]

class VisualizerWidget(QWidget):
    def __init__(self, theme_mgr, audio_engine, parent=None, config_mgr=None):
        super().__init__(parent)
        self.theme_mgr = theme_mgr
        self.audio = audio_engine
        self.config_mgr = config_mgr
        self.mode_index = 0
        self.mode = VIS_MODES[self.mode_index][0]
        self.setMinimumHeight(54)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Click to cycle modes | Right-click for Visualizer & Sensitivity Menu")

        # Initialize sensitivity from config if available
        if self.config_mgr:
            saved_sens = float(self.config_mgr.get("vis_sensitivity", 0.70))
            if hasattr(self.audio, "analyzer"):
                self.audio.analyzer.set_sensitivity(saved_sens)

        # 50 FPS high-smoothness render loop
        self.timer = QTimer(self)
        self.timer.setInterval(20)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.mode_index = (self.mode_index + 1) % len(VIS_MODES)
            self.mode = VIS_MODES[self.mode_index][0]
            self.update()
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())

    def _show_context_menu(self, global_pos):
        menu = QMenu(self)
        
        # Mode Selection
        mode_menu = menu.addMenu("🎨 " + ("Visualizer-läge" if i18n.get_language() == "sv" else "Visualizer Mode"))
        for mode_key, mode_title in VIS_MODES:
            act = mode_menu.addAction(mode_title)
            act.setCheckable(True)
            act.setChecked(self.mode == mode_key)
            act.triggered.connect(lambda checked, m=mode_key: self.set_mode(m))

        menu.addSeparator()

        # Sensitivity Submenu
        sens_menu = menu.addMenu("🎛️ " + ("Känslighet" if i18n.get_language() == "sv" else "Sensitivity"))
        sens_options = [
            (0.35, "35% - Extra Mjuk" if i18n.get_language() == "sv" else "35% - Extra Soft"),
            (0.50, "50% - Mjuk" if i18n.get_language() == "sv" else "50% - Soft"),
            (0.70, "70% - Normal (Rekommenderad)" if i18n.get_language() == "sv" else "70% - Normal (Recommended)"),
            (0.85, "85% - Livlig" if i18n.get_language() == "sv" else "85% - High"),
            (1.00, "100% - Max" if i18n.get_language() == "sv" else "100% - Max")
        ]
        curr_sens = getattr(self.audio.analyzer, "sensitivity", 0.70) if hasattr(self.audio, "analyzer") else 0.70
        for s_val, s_label in sens_options:
            act = sens_menu.addAction(s_label)
            act.setCheckable(True)
            act.setChecked(abs(curr_sens - s_val) < 0.05)
            act.triggered.connect(lambda checked, v=s_val: self.set_sensitivity(v))

        menu.exec(global_pos)

    def set_sensitivity(self, val):
        if hasattr(self.audio, "analyzer"):
            self.audio.analyzer.set_sensitivity(val)
        if self.config_mgr:
            self.config_mgr.set("vis_sensitivity", val)
            self.config_mgr.save()
        self.update()

    def set_mode(self, mode_key):
        self.mode = mode_key
        for i, (k, _) in enumerate(VIS_MODES):
            if k == mode_key:
                self.mode_index = i
                break
        self.update()

    def set_playing(self, is_playing):
        pass  # reads directly from self.audio.is_playing

    def set_volume(self, volume):
        pass  # reads directly from self.audio.volume

    def update_frame(self):
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        bg_col = self.theme_mgr.color("vis_bg", "#000000")
        painter.fillRect(self.rect(), bg_col)

        border_col = self.theme_mgr.color("panel_border", "#22222a")
        painter.setPen(QPen(border_col, 1))
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)

        w = self.width()
        h = self.height()

        if self.mode == "spectrum":
            self._draw_spectrum(painter, w, h)
        elif self.mode == "oscilloscope":
            self._draw_oscilloscope(painter, w, h)
        elif self.mode == "vu_meter":
            self._draw_vu_meter(painter, w, h)
        elif self.mode == "starfield":
            self._draw_starfield(painter, w, h)
        elif self.mode == "matrix":
            self._draw_matrix(painter, w, h)
        elif self.mode == "circular":
            self._draw_circular(painter, w, h)

    def _draw_spectrum(self, painter, w, h):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        bars, peaks = self.audio.analyzer.get_real_spectrum(
            self.audio.is_playing, self.audio.current_position, self.audio.volume
        )
        num_bars = len(bars)
        bar_width = int((w - 4) / num_bars) - 1
        bar_width = max(3, bar_width)

        col_low = self.theme_mgr.color("vis_bars_low", "#00ff44")
        col_mid = self.theme_mgr.color("vis_bars_mid", "#ffea00")
        col_high = self.theme_mgr.color("vis_bars_high", "#ff2200")
        col_peak = self.theme_mgr.color("vis_peaks", "#ffffff")

        for i in range(num_bars):
            x = i * (bar_width + 1) + 3
            bar_h = int(bars[i] * (h - 6))
            peak_y = h - 3 - int(peaks[i] * (h - 6))

            segment_h = 2
            gap = 1
            y = h - 3
            if bar_h <= 0:
                # Idle baseline dot
                painter.fillRect(x, y - segment_h, bar_width, segment_h, col_low)
            else:
                while y > (h - 3 - bar_h):
                    rel_height = (h - 3 - y) / max(1, (h - 6))
                    if rel_height < 0.55:
                        seg_col = col_low
                    elif rel_height < 0.85:
                        seg_col = col_mid
                    else:
                        seg_col = col_high

                    painter.fillRect(x, y - segment_h, bar_width, segment_h, seg_col)
                    y -= (segment_h + gap)

                if peaks[i] > 0.05:
                    painter.fillRect(x, peak_y, bar_width, 1, col_peak)

    def _draw_oscilloscope(self, painter, w, h):
        wave = self.audio.analyzer.get_real_waveform(
            self.audio.is_playing, self.audio.current_position, num_points=w, volume=self.audio.volume
        )
        pen_col = self.theme_mgr.color("vis_oscilloscope", "#00ff66")
        
        # Soft laser glow trail
        glow_col = QColor(pen_col)
        glow_col.setAlpha(55)
        painter.setPen(QPen(glow_col, 3))
        mid_y = h / 2.0
        for x in range(len(wave) - 1):
            y1 = int(mid_y - wave[x] * (h / 2.3))
            y2 = int(mid_y - wave[x + 1] * (h / 2.3))
            painter.drawLine(x, y1, x + 1, y2)

        # Sharp inner laser line
        painter.setPen(QPen(pen_col, 1.5))
        for x in range(len(wave) - 1):
            y1 = int(mid_y - wave[x] * (h / 2.3))
            y2 = int(mid_y - wave[x + 1] * (h / 2.3))
            painter.drawLine(x, y1, x + 1, y2)

    def _draw_vu_meter(self, painter, w, h):
        self.audio.analyzer.get_real_spectrum(
            self.audio.is_playing, self.audio.current_position, self.audio.volume
        )
        vu_l = self.audio.analyzer.vu_left
        vu_r = self.audio.analyzer.vu_right

        meter_w = int((w - 8) / 2)
        
        for idx, (vu_val, label) in enumerate([(vu_l, "L"), (vu_r, "R")]):
            offset_x = 3 + idx * (meter_w + 3)
            
            # Frame
            painter.setPen(QPen(self.theme_mgr.color("panel_border", "#333333"), 1))
            painter.drawRect(offset_x, 2, meter_w, h - 4)

            # Dial arc
            center_x = offset_x + meter_w / 2
            center_y = h + 4
            radius = h * 0.95

            # Needle angle
            angle_rad = math.radians(-40 + vu_val * 80)
            needle_x = center_x + radius * math.sin(angle_rad)
            needle_y = center_y - radius * math.cos(angle_rad)

            # Labels
            painter.setPen(QPen(self.theme_mgr.color("vis_bars_low", "#00ff44"), 1))
            painter.drawText(offset_x + 4, 14, label)
            
            font_db = QFont("Monospace", 6)
            painter.setFont(font_db)
            painter.drawText(offset_x + meter_w - 22, 14, f"{int(vu_val*100)}%")

            # Needle
            col_needle = self.theme_mgr.color("vis_bars_high", "#ff2200") if vu_val > 0.85 else self.theme_mgr.color("vis_peaks", "#ffffff")
            painter.setPen(QPen(col_needle, 1.5))
            painter.drawLine(int(center_x), int(center_y), int(needle_x), int(needle_y))

    def _draw_starfield(self, painter, w, h):
        sx, sy, sz, bass = self.audio.analyzer.update_starfield(
            self.audio.is_playing, self.audio.current_position, self.audio.volume
        )
        cx = w / 2.0
        cy = h / 2.0

        star_col = self.theme_mgr.color("vis_peaks", "#ffffff")
        tint_col = self.theme_mgr.color("vis_bars_low", "#00ff66")

        for i in range(len(sz)):
            z = sz[i]
            x = int(cx + (sx[i] / z) * (w * 0.4))
            y = int(cy + (sy[i] / z) * (h * 0.4))

            if 0 <= x < w and 0 <= y < h:
                size = max(1, int((1.0 - z) * 3.5))
                brightness = max(40, min(255, int((1.0 - z) * 255)))
                c = QColor(star_col) if i % 3 != 0 else QColor(tint_col)
                c.setAlpha(brightness)
                painter.fillRect(x, y, size, size, c)

    def _draw_matrix(self, painter, w, h):
        drops = self.audio.analyzer.update_matrix(self.audio.is_playing)
        col_green = self.theme_mgr.color("lcd_text", "#00ff33")
        col_head = self.theme_mgr.color("vis_peaks", "#ffffff")

        font = QFont("Monospace", 7, QFont.Weight.Bold)
        painter.setFont(font)

        chars = "0123456789ABCDEF$#@!%&*="
        col_w = int(w / len(drops))

        for col_idx, drop_y in enumerate(drops):
            x = col_idx * col_w + 2
            y_head = int(drop_y * 3)

            for trail in range(5):
                y = y_head - trail * 8
                if 0 <= y < h:
                    char = chars[(col_idx + trail + int(drop_y)) % len(chars)]
                    if trail == 0:
                        painter.setPen(col_head)
                    else:
                        alpha = max(30, 200 - trail * 40)
                        c = QColor(col_green)
                        c.setAlpha(alpha)
                        painter.setPen(c)
                    painter.drawText(x, y, char)

    def _draw_circular(self, painter, w, h):
        bars, peaks = self.audio.analyzer.get_real_spectrum(
            self.audio.is_playing, self.audio.current_position, self.audio.volume
        )
        cx = w / 2.0
        cy = h / 2.0
        base_radius = min(w, h) * 0.22

        col_low = self.theme_mgr.color("vis_bars_low", "#00ff44")
        col_mid = self.theme_mgr.color("vis_bars_mid", "#ffea00")
        col_high = self.theme_mgr.color("vis_bars_high", "#ff2200")

        num_points = len(bars)
        for i in range(num_points):
            angle = (i / num_points) * 2.0 * math.pi
            val = bars[i]
            r = base_radius + val * (min(w, h) * 0.26)

            x1 = cx + base_radius * math.cos(angle)
            y1 = cy + base_radius * math.sin(angle)
            x2 = cx + r * math.cos(angle)
            y2 = cy + r * math.sin(angle)

            rel = val
            col = col_low if rel < 0.5 else (col_mid if rel < 0.8 else col_high)
            painter.setPen(QPen(col, 2))
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))

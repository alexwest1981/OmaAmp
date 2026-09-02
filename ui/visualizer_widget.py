from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush

class VisualizerWidget(QWidget):
    def __init__(self, theme_mgr, vis_generator, parent=None):
        super().__init__(parent)
        self.theme_mgr = theme_mgr
        self.vis_gen = vis_generator
        self.mode = "spectrum"  # "spectrum" | "oscilloscope"
        self.is_playing = False
        self.volume = 80
        self.setFixedSize(140, 36)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Click to toggle: Spectrum Analyzer / Oscilloscope")

        # 45 FPS render loop
        self.timer = QTimer(self)
        self.timer.setInterval(22)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start()

    def mousePressEvent(self, event):
        if self.mode == "spectrum":
            self.mode = "oscilloscope"
        else:
            self.mode = "spectrum"
        self.update()

    def set_playing(self, is_playing):
        self.is_playing = is_playing

    def set_volume(self, volume):
        self.volume = volume

    def update_frame(self):
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        # Background
        bg_col = self.theme_mgr.color("vis_bg", "#000000")
        painter.fillRect(self.rect(), bg_col)

        w = self.width()
        h = self.height()

        if self.mode == "spectrum":
            bars, peaks = self.vis_gen.update(self.is_playing, self.volume)
            num_bars = len(bars)
            bar_width = int(w / num_bars) - 1
            bar_width = max(3, bar_width)

            col_low = self.theme_mgr.color("vis_bars_low", "#00ff44")
            col_mid = self.theme_mgr.color("vis_bars_mid", "#ffea00")
            col_high = self.theme_mgr.color("vis_bars_high", "#ff2200")
            col_peak = self.theme_mgr.color("vis_peaks", "#ffffff")

            for i in range(num_bars):
                x = i * (bar_width + 1) + 2
                bar_h = int(bars[i] * (h - 4))
                peak_y = h - 2 - int(peaks[i] * (h - 4))

                # Draw discrete 2px segmented bars
                segment_h = 2
                gap = 1
                y = h - 2
                while y > (h - 2 - bar_h):
                    rel_height = (h - 2 - y) / (h - 4)
                    if rel_height < 0.55:
                        seg_col = col_low
                    elif rel_height < 0.85:
                        seg_col = col_mid
                    else:
                        seg_col = col_high

                    painter.fillRect(x, y - segment_h, bar_width, segment_h, seg_col)
                    y -= (segment_h + gap)

                # Draw Peak Dot
                if peaks[i] > 0.05:
                    painter.fillRect(x, peak_y, bar_width, 1, col_peak)

        elif self.mode == "oscilloscope":
            wave = self.vis_gen.get_oscilloscope_wave(self.is_playing, num_points=w, volume=self.volume)
            pen_col = self.theme_mgr.color("vis_oscilloscope", "#00ff66")
            painter.setPen(QPen(pen_col, 1))

            mid_y = h / 2.0
            for x in range(len(wave) - 1):
                y1 = int(mid_y - wave[x] * (h / 2.5))
                y2 = int(mid_y - wave[x + 1] * (h / 2.5))
                painter.drawLine(x, y1, x + 1, y2)

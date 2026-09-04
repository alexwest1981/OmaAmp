from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QRect
from PyQt6.QtGui import QPainter, QColor, QFont, QPen

class LcdDisplay(QWidget):
    def __init__(self, theme_mgr, parent=None):
        super().__init__(parent)
        self.theme_mgr = theme_mgr
        self.track_title = "WINAMP - IT REALLY WHIPS THE LLAMA'S ASS!"
        self.bitrate = 320
        self.samplerate = 44
        self.channels = 2
        self.time_seconds = 0.0
        self.total_seconds = 0.0
        self.time_mode = "elapsed"  # "elapsed" | "remaining"
        self.scroll_pos = 0
        self.is_playing = False

        self.setFixedSize(140, 42)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Click time to toggle Elapsed / Remaining time")

    def mousePressEvent(self, event):
        self.time_mode = "remaining" if self.time_mode == "elapsed" else "elapsed"
        self.update()

    def set_track(self, track):
        if track:
            self.track_title = f"{track.artist} - {track.title}"
            self.bitrate = track.bitrate
            self.samplerate = int(track.samplerate / 1000)
            self.channels = track.channels
            self.total_seconds = track.duration
        else:
            self.track_title = "OMAAMP - READY"
            self.bitrate = 0
            self.samplerate = 0
            self.total_seconds = 0.0
        self.update()

    def set_position(self, current_seconds):
        self.time_seconds = current_seconds
        self.update()

    def set_playing(self, playing):
        self.is_playing = playing
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        # LCD Frame Background
        bg_col = self.theme_mgr.color("lcd_bg", "#020902")
        painter.fillRect(self.rect(), bg_col)

        # Border
        border_col = self.theme_mgr.color("panel_border", "#22222a")
        painter.setPen(QPen(border_col, 1))
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)

        col_text = self.theme_mgr.color("lcd_text", "#00ff33")
        col_dim = self.theme_mgr.color("lcd_text_dim", "#003b0c")
        col_kbps = self.theme_mgr.color("lcd_kbps", "#00dd22")

        # 1. 7-Segment Time Display
        if self.time_mode == "remaining" and self.total_seconds > 0:
            rem = max(0.0, self.total_seconds - self.time_seconds)
            mins = int(rem // 60)
            secs = int(rem % 60)
            prefix = "-"
        else:
            mins = int(self.time_seconds // 60)
            secs = int(self.time_seconds % 60)
            prefix = " "

        time_str = f"{prefix}{mins:02d}:{secs:02d}"

        # 1. 7-Segment Time Display (Bitmap or Vector)
        digits_sprites = None
        if self.theme_mgr.active_skin and 'digits' in self.theme_mgr.active_skin.sprites:
            digits_sprites = self.theme_mgr.active_skin.sprites

        if digits_sprites:
            # Draw authentic bitmap digits
            curr_x = 6
            digit_y = 6
            # Minus sign if remaining
            if self.time_mode == "remaining":
                if 'digit_minus' in digits_sprites:
                    painter.drawPixmap(curr_x, digit_y, digits_sprites['digit_minus'])
                curr_x += 10
            else:
                if 'digit_blank' in digits_sprites:
                    painter.drawPixmap(curr_x, digit_y, digits_sprites['digit_blank'])
                curr_x += 10

            # Minutes (2 digits)
            d1 = (mins // 10) % 10
            d2 = mins % 10
            painter.drawPixmap(curr_x, digit_y, digits_sprites['digits'][d1])
            curr_x += 10
            painter.drawPixmap(curr_x, digit_y, digits_sprites['digits'][d2])
            curr_x += 12

            # Colon dots
            painter.setPen(col_text)
            painter.fillRect(curr_x - 2, digit_y + 3, 2, 2, col_text)
            painter.fillRect(curr_x - 2, digit_y + 8, 2, 2, col_text)

            # Seconds (2 digits)
            d3 = (secs // 10) % 10
            d4 = secs % 10
            painter.drawPixmap(curr_x, digit_y, digits_sprites['digits'][d3])
            curr_x += 10
            painter.drawPixmap(curr_x, digit_y, digits_sprites['digits'][d4])
        else:
            # Ghost 88:88 background
            font_time = QFont("Monospace", 15, QFont.Weight.Bold)
            font_time.setStyleHint(QFont.StyleHint.Monospace)
            painter.setFont(font_time)
            painter.setPen(col_dim)
            painter.drawText(6, 22, "-88:88")

            # Active Time
            painter.setPen(col_text)
            painter.drawText(6, 22, time_str)

        # 2. Specs Row (Bottom: KBPS, KHZ, STEREO)
        font_specs = QFont("Monospace", 7, QFont.Weight.Bold)
        painter.setFont(font_specs)

        kbps_str = f"{self.bitrate:3d}k" if self.bitrate > 0 else "--k"
        painter.setPen(col_kbps)
        painter.drawText(6, 36, kbps_str)

        khz_str = f"{self.samplerate:2d}k" if self.samplerate > 0 else "--k"
        painter.drawText(42, 36, khz_str)

        # STEREO / MONO
        is_stereo = (self.channels >= 2)
        painter.setPen(col_text if (is_stereo and self.is_playing) else col_dim)
        painter.drawText(76, 36, "ST")

        # ELP / REM
        mode_str = "REM" if self.time_mode == "remaining" else "ELP"
        painter.setPen(col_dim)
        painter.drawText(104, 36, mode_str)


class MarqueeDisplay(QWidget):
    def __init__(self, theme_mgr, parent=None):
        super().__init__(parent)
        self.theme_mgr = theme_mgr
        self.track_title = "WINAMP - IT REALLY WHIPS THE LLAMA'S ASS!"
        self.scroll_pos = 0
        self.setFixedHeight(18)

        # Marquee scroll timer
        self.scroll_timer = QTimer(self)
        self.scroll_timer.setInterval(130)
        self.scroll_timer.timeout.connect(self._scroll_text)
        self.scroll_timer.start()

    def set_track(self, track):
        if track:
            self.track_title = f"{track.artist} - {track.title}"
        else:
            self.track_title = "OMAAMP - WINAMP 2.91 CLASSIC FOR LINUX"
        self.scroll_pos = 0
        self.update()

    def _scroll_text(self):
        if len(self.track_title) > 28:
            self.scroll_pos += 1
            if self.scroll_pos > len(self.track_title) + 6:
                self.scroll_pos = 0
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        bg_col = self.theme_mgr.color("lcd_bg", "#020902")
        painter.fillRect(self.rect(), bg_col)

        border_col = self.theme_mgr.color("panel_border", "#22222a")
        painter.setPen(QPen(border_col, 1))
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)

        font_marquee = QFont("Monospace", 8, QFont.Weight.Bold)
        painter.setFont(font_marquee)

        col_text = self.theme_mgr.color("lcd_text", "#00ff33")
        painter.setPen(col_text)

        display_str = self.track_title
        if self.scroll_pos > 0:
            display_str = (self.track_title + "   ***   " + self.track_title)[self.scroll_pos:]

        painter.setClipRect(4, 2, self.width() - 8, self.height() - 4)
        painter.drawText(6, 13, display_str)

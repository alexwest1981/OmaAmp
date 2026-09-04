import os
import math
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QRect, QRectF, QPointF
from PyQt6.QtGui import (
    QPainter, QColor, QFont, QPen, QBrush, QPixmap, 
    QPainterPath, QLinearGradient
)

class LcdDisplay(QWidget):
    def __init__(self, theme_mgr, parent=None):
        super().__init__(parent)
        self.theme_mgr = theme_mgr
        self.track_title = "WINAMP - IT REALLY WHIPS THE LLAMA'S ASS!"
        self.artist = ""
        self.album = ""
        self.bitrate = 320
        self.samplerate = 44
        self.channels = 2
        self.time_seconds = 0.0
        self.total_seconds = 0.0
        self.time_mode = "elapsed"  # "elapsed" | "remaining"
        self.scroll_pos = 0
        self.is_playing = False

        self.cover_pixmap = None
        self.disc_angle = 0.0

        # Dedicated Album Art + Time under display
        self.setFixedSize(136, 144)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Click time to toggle Elapsed / Remaining time\nAlbum Art / Track Cover")

        # Vinyl spinning animation timer
        self.anim_timer = QTimer(self)
        self.anim_timer.setInterval(40)
        self.anim_timer.timeout.connect(self._animate_vinyl)
        self.anim_timer.start()

    def _animate_vinyl(self):
        if self.is_playing and not self.cover_pixmap:
            self.disc_angle = (self.disc_angle + 3.0) % 360.0
            self.update()

    def mousePressEvent(self, event):
        self.time_mode = "remaining" if self.time_mode == "elapsed" else "elapsed"
        self.update()

    def set_track(self, track):
        if track:
            self.track_title = track.display_name
            self.artist = track.artist
            self.album = getattr(track, 'album', '')
            self.bitrate = track.bitrate
            self.samplerate = int(track.samplerate / 1000) if track.samplerate > 0 else 44
            self.channels = track.channels
            self.total_seconds = track.duration

            # Extract Cover Art
            self.cover_pixmap = None
            if getattr(track, 'cover_art_bytes', None):
                pix = QPixmap()
                if pix.loadFromData(track.cover_art_bytes):
                    self.cover_pixmap = pix
            elif getattr(track, 'cover_art_path', None) and os.path.exists(track.cover_art_path):
                pix = QPixmap(track.cover_art_path)
                if not pix.isNull():
                    self.cover_pixmap = pix
        else:
            self.track_title = "OMAAMP - READY"
            self.artist = ""
            self.album = ""
            self.bitrate = 0
            self.samplerate = 0
            self.total_seconds = 0.0
            self.cover_pixmap = None

        self.update()

    def set_position(self, current_seconds):
        self.time_seconds = current_seconds
        self.update()

    def set_playing(self, playing):
        self.is_playing = playing
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = float(self.width())
        h = float(self.height())

        # LCD Frame Background
        bg_col = self.theme_mgr.color("lcd_bg", "#020902")
        painter.fillRect(self.rect(), bg_col)

        # Outer Frame Border
        border_col = self.theme_mgr.color("panel_border", "#22222a")
        painter.setPen(QPen(border_col, 1))
        painter.drawRect(0, 0, int(w - 1), int(h - 1))

        col_text = self.theme_mgr.color("lcd_text", "#00ff33")
        col_dim = self.theme_mgr.color("lcd_text_dim", "#003b0c")
        col_kbps = self.theme_mgr.color("lcd_kbps", "#00dd22")
        col_accent = self.theme_mgr.color("titlebar_text", "#00e5ff")

        # =====================================================================
        # 1. LARGE ALBUM ART BOX (Top Section: 96x96 centered at x=20, y=8)
        # =====================================================================
        art_size = 96
        art_x = int((w - art_size) / 2.0)
        art_y = 8
        art_rect = QRect(art_x, art_y, art_size, art_size)

        # Slot background
        painter.setPen(QPen(border_col, 1))
        painter.setBrush(QBrush(QColor("#080a10")))
        painter.drawRoundedRect(art_rect, 4, 4)

        if self.cover_pixmap and not self.cover_pixmap.isNull():
            # Render full album cover art with smooth anti-aliased scaling
            path = QPainterPath()
            path.addRoundedRect(QRectF(art_x, art_y, art_size, art_size), 4, 4)
            painter.save()
            painter.setClipPath(path)
            
            scaled_cover = self.cover_pixmap.scaled(
                art_size, art_size, 
                Qt.AspectRatioMode.KeepAspectRatioByExpanding, 
                Qt.TransformationMode.SmoothTransformation
            )
            cx = (scaled_cover.width() - art_size) // 2
            cy = (scaled_cover.height() - art_size) // 2
            painter.drawPixmap(art_x, art_y, scaled_cover, cx, cy, art_size, art_size)

            # Subtle gloss sheen reflection
            gloss = QLinearGradient(art_x, art_y, art_x, art_y + int(art_size * 0.45))
            gloss.setColorAt(0.0, QColor(255, 255, 255, 55))
            gloss.setColorAt(1.0, QColor(255, 255, 255, 0))
            painter.fillRect(QRect(art_x, art_y, art_size, int(art_size * 0.45)), gloss)
            painter.restore()
        else:
            # Render Full Vinyl Record / Disc
            painter.save()
            disc_center_x = art_x + (art_size / 2.0)
            disc_center_y = art_y + (art_size / 2.0)
            radius = (art_size / 2.0) - 4.0

            # Outer vinyl body
            painter.setPen(QPen(QColor("#111116"), 1.2))
            painter.setBrush(QBrush(QColor("#14151b")))
            painter.drawEllipse(QPointF(disc_center_x, disc_center_y), radius, radius)

            # Vinyl Grooves (multiple concentric rings)
            painter.setPen(QPen(QColor(255, 255, 255, 18), 0.75))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            for r_offset in [6, 11, 16, 21, 26, 31]:
                if radius - r_offset > 12:
                    painter.drawEllipse(QPointF(disc_center_x, disc_center_y), radius - r_offset, radius - r_offset)

            # Rotating Center Label
            painter.translate(disc_center_x, disc_center_y)
            painter.rotate(self.disc_angle)

            label_col = col_accent if self.is_playing else QColor("#444654")
            painter.setPen(QPen(QColor("#000000"), 0.5))
            painter.setBrush(QBrush(label_col))
            painter.drawEllipse(QPointF(0, 0), 14.0, 14.0)

            # Center Spindle Hole
            painter.setBrush(QBrush(bg_col))
            painter.drawEllipse(QPointF(0, 0), 3.5, 3.5)

            # Label Detail Lines
            painter.setPen(QPen(QColor("#ffffff"), 1))
            painter.drawLine(5, 0, 11, 0)
            painter.drawLine(-11, 0, -5, 0)

            painter.restore()

        # =====================================================================
        # 2. 7-SEGMENT DIGITAL TIME DISPLAY (Under the Album Art: y=110)
        # =====================================================================
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

        # Digits Font
        font_time = QFont("Monospace", 14, QFont.Weight.Bold)
        font_time.setStyleHint(QFont.StyleHint.Monospace)
        painter.setFont(font_time)

        # Ghost 88:88 background
        painter.setPen(col_dim)
        painter.drawText(QRect(0, 108, int(w), 20), Qt.AlignmentFlag.AlignCenter, "-88:88")

        # Active glowing time digits
        painter.setPen(col_text)
        painter.drawText(QRect(0, 108, int(w), 20), Qt.AlignmentFlag.AlignCenter, time_str)

        # Mode Badge (ELP / REM)
        font_badge = QFont("Monospace", 6, QFont.Weight.Bold)
        painter.setFont(font_badge)
        mode_str = "REM" if self.time_mode == "remaining" else "ELP"
        painter.setPen(col_text if self.is_playing else col_dim)
        painter.drawText(int(w) - 26, 122, mode_str)

        # =====================================================================
        # 3. SPECS ROW (Bottom Bar: y=128..140)
        # =====================================================================
        font_specs = QFont("Monospace", 7, QFont.Weight.Bold)
        painter.setFont(font_specs)

        # KBPS
        kbps_str = f"{self.bitrate:3d}k" if self.bitrate > 0 else "--k"
        painter.setPen(col_kbps)
        painter.drawText(8, 138, kbps_str)

        # KHZ
        khz_str = f"{self.samplerate:2d}k" if self.samplerate > 0 else "--k"
        painter.setPen(col_text if self.samplerate > 0 else col_dim)
        painter.drawText(46, 138, khz_str)

        # STEREO / MONO
        is_stereo = (self.channels >= 2)
        painter.setPen(col_text if (is_stereo and self.is_playing) else col_dim)
        painter.drawText(78, 138, "ST")

        # Track Status
        if self.is_playing:
            painter.setPen(col_accent)
            painter.drawText(102, 138, "PLAY")
        else:
            painter.setPen(col_dim)
            painter.drawText(102, 138, "STOP")


class MarqueeDisplay(QWidget):
    def __init__(self, theme_mgr, parent=None):
        super().__init__(parent)
        self.theme_mgr = theme_mgr
        self.track_title = "WINAMP - IT REALLY WHIPS THE LLAMA'S ASS!"
        self.scroll_pos = 0
        self.setFixedHeight(38)

        # Marquee scroll timer
        self.scroll_timer = QTimer(self)
        self.scroll_timer.setInterval(110)
        self.scroll_timer.timeout.connect(self._scroll_text)
        self.scroll_timer.start()

    def set_track(self, track):
        if track:
            self.track_title = track.display_name
        else:
            self.track_title = "OMAAMP - WINAMP 2.91 CLASSIC FOR LINUX"
        self.scroll_pos = 0
        self.update()

    def _scroll_text(self):
        if len(self.track_title) > 28:
            self.scroll_pos += 1
            if self.scroll_pos > len(self.track_title) + 8:
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

        font_marquee = QFont("Monospace", 9, QFont.Weight.Bold)
        painter.setFont(font_marquee)

        col_text = self.theme_mgr.color("lcd_text", "#00ff33")
        painter.setPen(col_text)

        display_str = self.track_title
        if self.scroll_pos > 0:
            display_str = (self.track_title + "   ***   " + self.track_title)[self.scroll_pos:]

        painter.setClipRect(6, 4, self.width() - 12, self.height() - 8)
        painter.drawText(8, int(self.height() / 2) + 4, display_str)

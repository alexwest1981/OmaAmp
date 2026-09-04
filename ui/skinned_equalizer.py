from PyQt6.QtWidgets import QWidget, QMenu, QSizePolicy
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QImage, QColor, QFont, QPen, QMouseEvent

class SkinnedEqualizerWidget(QWidget):
    eq_changed = pyqtSignal(list, int)  # (bands, preamp)
    close_clicked = pyqtSignal()

    def __init__(self, theme_mgr, parent=None):
        super().__init__(parent)
        self.theme_mgr = theme_mgr
        
        self.base_w = 275
        self.base_h = 116
        self.scale = 2.0
        self.setFixedSize(550, 232)

        self.eq_enabled = True
        self.auto_enabled = False
        self.preamp = 0       # -12 to +12 dB
        self.bands = [0] * 10 # -14 to +14 dB (indices 0..9: 60Hz..16kHz)
        self.active_slider = None # 'preamp' or index 0..9

    def _map_to_base(self, pos: QPoint):
        return QPoint(int(pos.x() / self.scale), int(pos.y() / self.scale))

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            pt = self._map_to_base(event.pos())
            x, y = pt.x(), pt.y()

            # 1. Close Button (x=264..274, y=3..12)
            if 3 <= y <= 13 and 264 <= x <= 274:
                self.close_clicked.emit()

            # 2. ON Button (x=14..40, y=18..30)
            elif 18 <= y <= 30 and 14 <= x <= 40:
                self.eq_enabled = not self.eq_enabled
                self.eq_changed.emit(self.bands, self.preamp)

            # 3. AUTO Button (x=39..72, y=18..30)
            elif 18 <= y <= 30 and 39 <= x <= 72:
                self.auto_enabled = not self.auto_enabled

            # 4. PRESETS Button (x=217..261, y=18..30)
            elif 18 <= y <= 30 and 217 <= x <= 261:
                self._show_presets_menu(event.pos())

            # 5. Preamp Slider (x=21..35, y=38..101)
            elif 38 <= y <= 101 and 21 <= x <= 35:
                self.active_slider = 'preamp'
                self._update_slider_val(y)

            # 6. 10 EQ Band Sliders (x=78 + i*18, y=38..101)
            elif 38 <= y <= 101:
                for i in range(10):
                    bx = 78 + i * 18
                    if bx - 4 <= x <= bx + 18:
                        self.active_slider = i
                        self._update_slider_val(y)
                        break

            self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.active_slider is not None:
            pt = self._map_to_base(event.pos())
            self._update_slider_val(pt.y())
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.active_slider = None
        self.update()

    def _update_slider_val(self, y):
        # Slider trough height: 38 (top, +12dB) to 90 (bottom, -12dB)
        rel = max(0.0, min(1.0, (y - 38) / 52.0))
        val_db = int((1.0 - rel * 2.0) * 14) # +14 to -14
        
        if self.active_slider == 'preamp':
            self.preamp = val_db
        elif isinstance(self.active_slider, int):
            self.bands[self.active_slider] = val_db
            
        self.eq_changed.emit(self.bands, self.preamp)

    def _show_presets_menu(self, global_pos):
        menu = QMenu(self)
        presets = {
            "Flat (Reset)": [0] * 10,
            "Full Bass": [8, 7, 6, 4, 1, -1, -2, -3, -3, -3],
            "Full Treble": [-3, -3, -3, -2, 1, 3, 6, 8, 9, 9],
            "Rock": [6, 4, -2, -4, -2, 1, 4, 7, 7, 7],
            "Pop": [-1, 2, 4, 5, 3, -1, -2, -2, -1, -1],
            "Techno": [7, 6, 4, 0, -3, 0, 5, 7, 7, 6],
            "Club": [0, 0, 2, 4, 4, 4, 2, 0, 0, 0],
            "Dance": [8, 6, 2, 0, 0, -3, -5, -5, 0, 0]
        }
        for name, values in presets.items():
            action = menu.addAction(name)
            action.triggered.connect(lambda checked, v=values: self._apply_preset(v))
        menu.exec(self.mapToGlobal(global_pos))

    def _apply_preset(self, values):
        self.bands = list(values)
        self.preamp = 0
        self.eq_changed.emit(self.bands, self.preamp)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.scale(self.scale, self.scale)

        skin = self.theme_mgr.active_skin
        bitmaps = skin.bitmaps if skin else {}
        eqmain = bitmaps.get('eqmain')
        eq_ex = bitmaps.get('eq_ex')

        # 1. Background Frame (EQMAIN.BMP)
        if eqmain and not eqmain.isNull():
            painter.drawImage(0, 0, eqmain, 0, 0, 275, 116)
        else:
            painter.fillRect(0, 0, self.base_w, self.base_h, self.theme_mgr.color("chassis_bg", "#282932"))

        # 2. Live Frequency Response Curve (x=86, y=17, w=113, h=19)
        self._draw_curve(painter)

        # 3. Preamp Slider Knob (x=21, y=38..90)
        self._draw_knob(painter, 21, self.preamp, eq_ex, eqmain)

        # 4. 10 Band Slider Knobs (x=78 + i*18)
        for i in range(10):
            bx = 78 + i * 18
            self._draw_knob(painter, bx, self.bands[i], eq_ex, eqmain)

    def _draw_knob(self, painter, x, val_db, eq_ex, eqmain):
        rel = (val_db + 14) / 28.0 # 0.0 (-14dB) to 1.0 (+14dB)
        knob_y = int(90 - rel * 52)

        if eq_ex and not eq_ex.isNull() and eq_ex.width() >= 14:
            # Clean thumb from eq_ex.bmp (0, 0, 14, 11)
            painter.drawImage(x, knob_y, eq_ex, 0, 0, 14, 11)
        elif eqmain and not eqmain.isNull() and eqmain.height() >= 175:
            # Fallback to eqmain (0, 164, 14, 11)
            painter.drawImage(x, knob_y, eqmain, 0, 164, 14, 11)
        else:
            painter.fillRect(x, knob_y, 14, 11, QColor('#ffffff'))

    def _draw_curve(self, painter):
        col_curve = self.theme_mgr.color("vis_bars_low", "#00ff44")
        painter.setPen(QPen(col_curve, 1))

        if not self.eq_enabled:
            painter.drawLine(86, 26, 199, 26)
            return

        points = []
        for i in range(10):
            px = 86 + int(i * 11.3)
            py = int(26 - (self.bands[i] / 14.0) * 8)
            points.append((px, py))

        for i in range(len(points) - 1):
            painter.drawLine(points[i][0], points[i][1], points[i+1][0], points[i+1][1])

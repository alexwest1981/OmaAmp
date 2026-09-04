from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QPushButton, QComboBox, QSizePolicy
)
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QFont, QPainterPath, QLinearGradient, QBrush
)
from core.i18n import _, i18n

PRESETS = {
    "Flat": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    "Rock": [4, 3, 2, 0, -1, 1, 3, 4, 4, 3],
    "Pop": [-1, 1, 3, 4, 3, 0, -1, -1, 1, 2],
    "Techno": [5, 4, 2, 0, -2, 0, 3, 5, 5, 4],
    "Full Bass": [6, 6, 5, 3, 1, -1, -3, -4, -5, -5],
    "Full Treble": [-5, -4, -3, -1, 1, 3, 5, 6, 6, 7],
    "Dance": [4, 3, 2, 0, 0, 2, 3, 3, 2, 0],
    "Club": [0, 0, 2, 3, 3, 3, 2, 0, 0, 0],
    "Classical": [4, 3, 2, 1, -1, -1, 0, 2, 3, 3],
    "Live": [-2, 0, 2, 3, 3, 3, 2, 1, 1, 1]
}

BAND_LABELS = ["60", "170", "310", "600", "1K", "3K", "6K", "12K", "14K", "16K"]

class EqCurveWidget(QWidget):
    def __init__(self, theme_mgr, sliders, eq_window, parent=None):
        super().__init__(parent)
        self.theme_mgr = theme_mgr
        self.sliders = sliders
        self.eq_window = eq_window
        
        # Generous height for clear graphical curve & frequency response
        self.setFixedHeight(68)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        
        w = float(self.width())
        h = float(self.height())
        mid_y = h / 2.0
        
        # 1. LCD Panel Background
        bg_col = self.theme_mgr.color("lcd_bg", "#020902")
        painter.fillRect(self.rect(), bg_col)
        
        border_col = self.theme_mgr.color("panel_border", "#22222a")
        painter.setPen(QPen(border_col, 1))
        painter.drawRect(0, 0, int(w - 1), int(h - 1))
        
        # 2. Grid Lines (dB references & frequency verticals)
        grid_col = self.theme_mgr.color("lcd_text_dim", "#002808")
        grid_pen = QPen(grid_col, 0.75, Qt.PenStyle.DashLine)
        painter.setPen(grid_pen)
        
        # Horizontal +10dB, +5dB, -5dB, -10dB grid
        y_p10 = mid_y - (10.0 / 10.0) * (mid_y - 8)
        y_p5  = mid_y - (5.0 / 10.0) * (mid_y - 8)
        y_m5  = mid_y - (-5.0 / 10.0) * (mid_y - 8)
        y_m10 = mid_y - (-10.0 / 10.0) * (mid_y - 8)
        
        painter.drawLine(0, int(y_p10), int(w), int(y_p10))
        painter.drawLine(0, int(y_p5),  int(w), int(y_p5))
        painter.drawLine(0, int(y_m5),  int(w), int(y_m5))
        painter.drawLine(0, int(y_m10), int(w), int(y_m10))
        
        # 0dB Baseline (Solid & Highlighted)
        base_col = self.theme_mgr.color("panel_border", "#1b3320")
        painter.setPen(QPen(base_col, 1.25, Qt.PenStyle.SolidLine))
        painter.drawLine(0, int(mid_y), int(w), int(mid_y))
        
        # dB Labels on Left
        font_legend = QFont("Monospace", 6)
        painter.setFont(font_legend)
        painter.setPen(grid_col)
        painter.drawText(4, int(y_p10) + 7, "+12dB")
        painter.drawText(4, int(mid_y) + 3, " 0dB")
        painter.drawText(4, int(y_m10) - 1, "-12dB")
        
        # 3. Calculate 10 Band Points
        col_w = w / 11.0
        points = []
        is_enabled = self.eq_window.eq_enabled if self.eq_window else True
        
        for i, s in enumerate(self.sliders):
            x = (i + 1) * col_w
            # Vertical guideline for each band
            painter.setPen(QPen(grid_col, 0.5, Qt.PenStyle.DotLine))
            painter.drawLine(int(x), 4, int(x), int(h - 4))
            
            val = s.value() if is_enabled else 0  # -10 to +10
            y = mid_y - (val / 10.0) * (mid_y - 8)
            points.append(QPointF(x, y))

        if not points:
            return

        col_line = self.theme_mgr.color("eq_slider_line", "#00ff33")
        if not is_enabled:
            col_line = grid_col

        # 4. Smooth Spline Path Construction (Catmull-Rom Interpolation)
        curve_path = QPainterPath()
        curve_path.moveTo(0, mid_y)
        
        # Control points extended to left and right edges
        all_pts = [QPointF(0, mid_y)] + points + [QPointF(w, mid_y)]
        
        for i in range(len(all_pts) - 1):
            p0 = all_pts[i - 1] if i > 0 else all_pts[i]
            p1 = all_pts[i]
            p2 = all_pts[i + 1]
            p3 = all_pts[i + 2] if i + 2 < len(all_pts) else p2
            
            # Cubic Hermite / Catmull-Rom tangents
            dx1 = (p2.x() - p0.x()) / 6.0
            dy1 = (p2.y() - p0.y()) / 6.0
            dx2 = (p3.x() - p1.x()) / 6.0
            dy2 = (p3.y() - p1.y()) / 6.0
            
            c1 = QPointF(p1.x() + dx1, p1.y() + dy1)
            c2 = QPointF(p2.x() - dx2, p2.y() - dy2)
            
            curve_path.cubicTo(c1, c2, p2)

        # 5. Gradient Area Fill Beneath Curve
        if is_enabled:
            fill_path = QPainterPath(curve_path)
            fill_path.lineTo(w, h)
            fill_path.lineTo(0, h)
            fill_path.closeSubpath()
            
            grad = QLinearGradient(0, 0, 0, h)
            glow_color = QColor(col_line)
            glow_color.setAlpha(65)
            grad.setColorAt(0.0, glow_color)
            grad.setColorAt(0.5, QColor(col_line.red(), col_line.green(), col_line.blue(), 25))
            grad.setColorAt(1.0, QColor(0, 0, 0, 0))
            
            painter.fillPath(fill_path, QBrush(grad))

        # 6. Stroke the Smooth EQ Curve
        curve_pen = QPen(col_line, 2.5)
        curve_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(curve_pen)
        painter.drawPath(curve_path)

        # 7. Draw Glowing Node Points for Each Band
        if is_enabled:
            for pt in points:
                # Outer glow halo
                halo_col = QColor(col_line)
                halo_col.setAlpha(80)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(halo_col))
                painter.drawEllipse(pt, 5.0, 5.0)

                # Bright center node
                painter.setBrush(QBrush(QColor("#ffffff")))
                painter.drawEllipse(pt, 2.0, 2.0)


class EqualizerWindow(QWidget):
    eq_changed = pyqtSignal(list, int)  # bands, preamp

    def __init__(self, theme_mgr, parent=None):
        super().__init__(parent)
        self.theme_mgr = theme_mgr
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.sliders = []
        self.preamp_val = 0
        self.eq_enabled = True

        self.init_ui()
        self.apply_theme()
        self.theme_mgr.theme_changed.connect(self.apply_theme)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)

        # Title / Preset Bar
        top_row = QHBoxLayout()
        top_row.setSpacing(6)

        self.lbl_title = QLabel("WINAMP EQUALIZER")
        self.lbl_title.setFont(QFont("Monospace", 8, QFont.Weight.Bold))
        top_row.addWidget(self.lbl_title)

        top_row.addStretch()

        self.btn_on = QPushButton("ON")
        self.btn_on.setCheckable(True)
        self.btn_on.setChecked(True)
        self.btn_on.setFixedSize(36, 20)
        self.btn_on.clicked.connect(self._toggle_on)
        top_row.addWidget(self.btn_on)

        self.btn_zero = QPushButton("ZERO")
        self.btn_zero.setFixedSize(44, 20)
        self.btn_zero.clicked.connect(self._reset_zero)
        top_row.addWidget(self.btn_zero)

        self.combo_presets = QComboBox()
        self.combo_presets.addItems(list(PRESETS.keys()))
        self.combo_presets.setFixedHeight(20)
        self.combo_presets.currentTextChanged.connect(self._on_preset_selected)
        top_row.addWidget(self.combo_presets)

        main_layout.addLayout(top_row)

        # Large Graphical Curve Display
        self.curve_view = EqCurveWidget(self.theme_mgr, self.sliders, self, self)
        main_layout.addWidget(self.curve_view)

        # Sliders Row (Taller sliders for fine-grained response)
        sliders_row = QHBoxLayout()
        sliders_row.setSpacing(4)
        sliders_row.setContentsMargins(0, 0, 0, 0)

        # Preamp Slider (90px height)
        preamp_col = QVBoxLayout()
        preamp_col.setSpacing(2)
        self.slider_preamp = QSlider(Qt.Orientation.Vertical)
        self.slider_preamp.setRange(-10, 10)
        self.slider_preamp.setValue(0)
        self.slider_preamp.setFixedHeight(90)
        self.slider_preamp.setToolTip("Preamp: 0 dB")
        self.slider_preamp.valueChanged.connect(self._on_slider_changed)
        
        lbl_p = QLabel("PRE")
        lbl_p.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_p.setFont(QFont("Monospace", 7, QFont.Weight.Bold))
        preamp_col.addWidget(self.slider_preamp, alignment=Qt.AlignmentFlag.AlignCenter)
        preamp_col.addWidget(lbl_p)
        sliders_row.addLayout(preamp_col)

        # 10 EQ Bands Sliders (90px height)
        for i in range(10):
            col = QVBoxLayout()
            col.setSpacing(2)
            slider = QSlider(Qt.Orientation.Vertical)
            slider.setRange(-10, 10)
            slider.setValue(0)
            slider.setFixedHeight(90)
            slider.setToolTip(f"{BAND_LABELS[i]}Hz: 0 dB")
            slider.valueChanged.connect(self._on_slider_changed)
            self.sliders.append(slider)

            lbl = QLabel(BAND_LABELS[i])
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFont(QFont("Monospace", 7, QFont.Weight.Bold))
            
            col.addWidget(slider, alignment=Qt.AlignmentFlag.AlignCenter)
            col.addWidget(lbl)
            sliders_row.addLayout(col)

        self.curve_view.sliders = self.sliders
        main_layout.addLayout(sliders_row)

    def _toggle_on(self):
        self.eq_enabled = self.btn_on.isChecked()
        self._on_slider_changed()

    def _reset_zero(self):
        self.slider_preamp.setValue(0)
        for s in self.sliders:
            s.setValue(0)
        self.combo_presets.setCurrentText("Flat")
        self._on_slider_changed()

    def _on_preset_selected(self, preset_name):
        if preset_name in PRESETS:
            vals = PRESETS[preset_name]
            for i, val in enumerate(vals):
                self.sliders[i].setValue(val)
            self._on_slider_changed()

    def _on_slider_changed(self):
        # Update slider tooltips with current dB value
        pre_val = self.slider_preamp.value()
        sign = "+" if pre_val > 0 else ""
        self.slider_preamp.setToolTip(f"Preamp: {sign}{pre_val * 1.2:.1f} dB")

        for i, s in enumerate(self.sliders):
            v = s.value()
            sign = "+" if v > 0 else ""
            s.setToolTip(f"{BAND_LABELS[i]}: {sign}{v * 1.2:.1f} dB")

        self.curve_view.update()
        bands = [s.value() for s in self.sliders]
        preamp = self.slider_preamp.value()
        self.preamp_val = preamp
        self.eq_changed.emit(bands, preamp)

    def apply_theme(self):
        bg = self.theme_mgr.hex("chassis_bg", "#282932")
        border = self.theme_mgr.hex("chassis_border", "#4e5062")
        btn_bg = self.theme_mgr.hex("button_bg", "#323440")
        btn_text = self.theme_mgr.hex("button_text", "#d4d8e8")
        btn_active = self.theme_mgr.hex("button_active", "#00ff66")
        title_text = self.theme_mgr.hex("titlebar_text", "#00e5ff")
        trough = self.theme_mgr.hex("slider_trough", "#0a0a0e")
        thumb = self.theme_mgr.hex("slider_thumb", "#5a5d72")

        knob_path = self.theme_mgr.knob_image_path()
        if knob_path:
            handle_css = f"""
                QSlider::handle:vertical {{
                    image: url('{knob_path}');
                    width: 20px;
                    height: 15px;
                    margin: 0 -7px;
                    background: transparent;
                }}
            """
        else:
            handle_css = f"""
                QSlider::handle:vertical {{
                    background: {thumb};
                    height: 14px;
                    margin: 0 -5px;
                    border-radius: 2px;
                    border: 1px solid {border};
                }}
            """

        chassis_pattern = self.theme_mgr.get_texture_path("chassis_pattern")
        titlebar_pattern = self.theme_mgr.get_texture_path("titlebar_repeat")
        eq_bg_css = f"background-image: url('{chassis_pattern}'); background-repeat: repeat;" if chassis_pattern else f"background-color: {bg};"

        self.setStyleSheet(f"""
            EqualizerWindow, QWidget {{
                {eq_bg_css}
                color: {btn_text};
                font-family: 'Monospace';
            }}
            QPushButton {{
                background-color: {btn_bg};
                background-image: none;
                color: {btn_text};
                border: 1px solid {border};
                border-radius: 2px;
                font-size: 8px;
                font-weight: bold;
                padding: 1px 4px;
            }}
            QPushButton:checked {{
                color: {btn_active};
                border: 1px solid {btn_active};
            }}
            QComboBox {{
                background-color: {btn_bg};
                background-image: none;
                color: {btn_text};
                border: 1px solid {border};
                border-radius: 2px;
                font-size: 8px;
                padding: 1px 4px;
            }}
            QSlider::groove:vertical {{
                background: {trough};
                width: 6px;
                border-radius: 3px;
            }}
            {handle_css}
            QSlider::handle:vertical:hover {{
                background: {btn_active};
            }}
        """)
        if titlebar_pattern:
            self.lbl_title.setStyleSheet(f"color: {title_text}; background-image: url('{titlebar_pattern}'); background-repeat: repeat; padding: 2px 6px; border-radius: 2px;")
        else:
            self.lbl_title.setStyleSheet(f"color: {title_text}; background: transparent;")

    def retranslate_ui(self):
        self.lbl_title.setText(_("eq_title"))
        self.btn_on.setText(_("eq_on"))
        self.btn_zero.setText(_("eq_zero"))

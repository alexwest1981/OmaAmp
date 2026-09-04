from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QPushButton, QComboBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor, QFont

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
    def __init__(self, theme_mgr, sliders, parent=None):
        super().__init__(parent)
        self.theme_mgr = theme_mgr
        self.sliders = sliders
        self.setFixedHeight(18)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        
        bg_col = self.theme_mgr.color("panel_bg", "#000000")
        painter.fillRect(self.rect(), bg_col)
        
        col_line = self.theme_mgr.color("eq_slider_line", "#00ff33")
        painter.setPen(QPen(col_line, 1.5))
        
        w = self.width()
        h = self.height()
        mid_y = h / 2.0
        
        col_w = w / 11.0
        points = []
        for i, s in enumerate(self.sliders):
            x = int((i + 1 + 0.5) * col_w)
            val = s.value()  # -10 to +10
            y = int(mid_y - (val / 10.0) * (h / 2.5))
            points.append((x, y))
            
        if points:
            painter.drawLine(0, int(mid_y), points[0][0], points[0][1])
            for i in range(len(points) - 1):
                painter.drawLine(points[i][0], points[i][1], points[i+1][0], points[i+1][1])
            painter.drawLine(points[-1][0], points[-1][1], w, int(mid_y))


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
        main_layout.setSpacing(4)

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
        self.btn_on.setFixedSize(32, 18)
        self.btn_on.clicked.connect(self._toggle_on)
        top_row.addWidget(self.btn_on)

        self.btn_zero = QPushButton("ZERO")
        self.btn_zero.setFixedSize(40, 18)
        self.btn_zero.clicked.connect(self._reset_zero)
        top_row.addWidget(self.btn_zero)

        self.combo_presets = QComboBox()
        self.combo_presets.addItems(list(PRESETS.keys()))
        self.combo_presets.setFixedHeight(18)
        self.combo_presets.currentTextChanged.connect(self._on_preset_selected)
        top_row.addWidget(self.combo_presets)

        main_layout.addLayout(top_row)

        # Curve display
        self.curve_view = EqCurveWidget(self.theme_mgr, self.sliders, self)
        main_layout.addWidget(self.curve_view)

        # Sliders Row
        sliders_row = QHBoxLayout()
        sliders_row.setSpacing(2)
        sliders_row.setContentsMargins(0, 0, 0, 0)

        # Preamp Slider
        preamp_col = QVBoxLayout()
        preamp_col.setSpacing(1)
        self.slider_preamp = QSlider(Qt.Orientation.Vertical)
        self.slider_preamp.setRange(-10, 10)
        self.slider_preamp.setValue(0)
        self.slider_preamp.setFixedHeight(60)
        self.slider_preamp.valueChanged.connect(self._on_slider_changed)
        lbl_p = QLabel("PRE")
        lbl_p.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_p.setFont(QFont("Monospace", 7))
        preamp_col.addWidget(self.slider_preamp, alignment=Qt.AlignmentFlag.AlignCenter)
        preamp_col.addWidget(lbl_p)
        sliders_row.addLayout(preamp_col)

        # 10 EQ Bands Sliders
        for i in range(10):
            col = QVBoxLayout()
            col.setSpacing(1)
            slider = QSlider(Qt.Orientation.Vertical)
            slider.setRange(-10, 10)
            slider.setValue(0)
            slider.setFixedHeight(60)
            slider.valueChanged.connect(self._on_slider_changed)
            self.sliders.append(slider)

            lbl = QLabel(BAND_LABELS[i])
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFont(QFont("Monospace", 7))
            
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
                    height: 12px;
                    margin: 0 -4px;
                    border-radius: 2px;
                    border: 1px solid {border};
                }}
            """

        self.setStyleSheet(f"""
            EqualizerWindow, QWidget {{
                background-color: {bg};
                color: {btn_text};
                font-family: 'Monospace';
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
            QPushButton:checked {{
                color: {btn_active};
                border: 1px solid {btn_active};
            }}
            QComboBox {{
                background-color: {btn_bg};
                color: {btn_text};
                border: 1px solid {border};
                border-radius: 2px;
                font-size: 8px;
                padding: 1px 4px;
            }}
            QSlider::groove:vertical {{
                background: {trough};
                width: 5px;
                border-radius: 2px;
            }}
            {handle_css}
            QSlider::handle:vertical:hover {{
                background: {btn_active};
            }}
        """)
        self.lbl_title.setStyleSheet(f"color: {title_text};")

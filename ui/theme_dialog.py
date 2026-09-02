import os
import json
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QColorDialog, QLineEdit, QFormLayout, QMessageBox, QGroupBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

class CustomThemeEditor(QDialog):
    def __init__(self, theme_mgr, base_theme, parent=None):
        super().__init__(parent)
        self.theme_mgr = theme_mgr
        self.theme_data = json.loads(json.dumps(base_theme))  # deepcopy
        self.setWindowTitle("Create / Edit Custom Theme")
        self.setFixedSize(380, 480)
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.input_id = QLineEdit(self.theme_data.get("id", "my_custom_theme") + "_copy")
        self.input_name = QLineEdit(self.theme_data.get("name", "My Custom Theme"))
        self.input_author = QLineEdit(self.theme_data.get("author", "User"))
        
        form.addRow("Theme ID (filename):", self.input_id)
        form.addRow("Theme Name:", self.input_name)
        form.addRow("Author:", self.input_author)
        layout.addLayout(form)

        # Color Customization Buttons
        group = QGroupBox("Key Colors (Click button to pick color)")
        color_layout = QFormLayout(group)

        self.color_buttons = {}
        colors = self.theme_data.get("colors", {})
        
        key_labels = [
            ("chassis_bg", "Chassis Background"),
            ("chassis_border", "Chassis Border"),
            ("lcd_bg", "LCD Background"),
            ("lcd_text", "LCD Glow Text"),
            ("vis_bars_low", "Visualizer Lows (Bass)"),
            ("vis_bars_mid", "Visualizer Mids"),
            ("vis_bars_high", "Visualizer Highs (Treble)"),
            ("vis_peaks", "Visualizer Peaks"),
            ("button_bg", "Button Background"),
            ("button_active", "Active Button Highlight"),
            ("playlist_bg", "Playlist Background"),
            ("playlist_text", "Playlist Text")
        ]

        for key, label in key_labels:
            btn = QPushButton(colors.get(key, "#ffffff"))
            btn.setStyleSheet(f"background-color: {colors.get(key, '#ffffff')}; color: #000000; font-weight: bold;")
            btn.clicked.connect(lambda checked, k=key, b=btn: self._pick_color(k, b))
            self.color_buttons[key] = btn
            color_layout.addRow(label, btn)

        layout.addWidget(group)

        # Bottom actions
        btn_box = QHBoxLayout()
        btn_save = QPushButton("💾 Save Theme")
        btn_save.clicked.connect(self._save)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_save)
        btn_box.addWidget(btn_cancel)
        layout.addLayout(btn_box)

    def _pick_color(self, key, button):
        current_hex = self.theme_data.get("colors", {}).get(key, "#ffffff")
        col = QColorDialog.getColor(QColor(current_hex), self, f"Pick Color for {key}")
        if col.isValid():
            new_hex = col.name()
            self.theme_data["colors"][key] = new_hex
            button.setText(new_hex)
            button.setStyleSheet(f"background-color: {new_hex}; color: #000000; font-weight: bold;")

    def _save(self):
        tid = self.input_id.text().strip().lower().replace(" ", "_")
        if not tid:
            QMessageBox.warning(self, "Invalid ID", "Please enter a valid Theme ID.")
            return

        self.theme_data["id"] = tid
        self.theme_data["name"] = self.input_name.text().strip()
        self.theme_data["author"] = self.input_author.text().strip()

        fpath = self.theme_mgr.save_custom_theme(self.theme_data)
        QMessageBox.information(self, "Theme Saved", f"Theme saved to:\n{fpath}")
        self.accept()


class ThemeDialog(QDialog):
    def __init__(self, theme_mgr, parent=None):
        super().__init__(parent)
        self.theme_mgr = theme_mgr
        self.setWindowTitle("OmaAmp Skins & Themes")
        self.setFixedSize(320, 360)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        lbl = QLabel("Select Theme:")
        lbl.setFont(QFont("Monospace", 9, QFont.Weight.Bold))
        layout.addWidget(lbl)

        self.theme_list = QListWidget()
        self.theme_list.setFont(QFont("Monospace", 9))
        self.theme_list.currentRowChanged.connect(self._on_theme_selected)
        layout.addWidget(self.theme_list)

        self.lbl_desc = QLabel("")
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setFont(QFont("Monospace", 8))
        layout.addWidget(self.lbl_desc)

        # Actions
        btn_create = QPushButton("🎨 Create / Edit Custom Theme")
        btn_create.clicked.connect(self._create_custom)
        layout.addWidget(btn_create)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

        self.refresh_list()

    def refresh_list(self):
        self.theme_list.clear()
        themes = self.theme_mgr.get_available_themes()
        curr_row = 0
        for i, t in enumerate(themes):
            prefix = "[User] " if not t["is_builtin"] else "[Built-in] "
            item = QListWidgetItem(f"{prefix}{t['name']}")
            item.setData(Qt.ItemDataRole.UserRole, t["id"])
            self.theme_list.addItem(item)
            if t["id"] == self.theme_mgr.current_theme_id:
                curr_row = i
        self.theme_list.setCurrentRow(curr_row)

    def _on_theme_selected(self, row):
        if row >= 0:
            item = self.theme_list.item(row)
            tid = item.data(Qt.ItemDataRole.UserRole)
            self.theme_mgr.set_theme(tid)
            desc = self.theme_mgr.current_theme.get("description", "")
            author = self.theme_mgr.current_theme.get("author", "")
            self.lbl_desc.setText(f"Author: {author}\n{desc}")

    def _create_custom(self):
        editor = CustomThemeEditor(self.theme_mgr, self.theme_mgr.current_theme, self)
        if editor.exec():
            self.refresh_list()

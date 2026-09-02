import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLineEdit, QLabel, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QDragEnterEvent, QDropEvent

class PlaylistWindow(QWidget):
    track_selected = pyqtSignal(int)

    def __init__(self, audio_engine, theme_mgr, parent=None):
        super().__init__(parent)
        self.audio = audio_engine
        self.theme_mgr = theme_mgr
        self.setFixedSize(300, 220)
        self.setWindowTitle("OmaAmp Playlist")
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.setAcceptDrops(True)

        self.init_ui()
        self.apply_theme()
        self.theme_mgr.theme_changed.connect(self.apply_theme)
        self.audio.playlist_updated.connect(self.refresh_list)
        self.audio.track_changed.connect(self._on_track_changed)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(4)

        # Title / Search Bar
        top_row = QHBoxLayout()
        top_row.setSpacing(4)

        self.lbl_title = QLabel("WINAMP PLAYLIST")
        self.lbl_title.setFont(QFont("Monospace", 8, QFont.Weight.Bold))
        top_row.addWidget(self.lbl_title)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter tracks...")
        self.search_input.setFixedHeight(18)
        self.search_input.setFont(QFont("Monospace", 8))
        self.search_input.textChanged.connect(self._filter_tracks)
        top_row.addWidget(self.search_input)

        main_layout.addLayout(top_row)

        # List Widget
        self.list_widget = QListWidget()
        self.list_widget.setFont(QFont("Monospace", 8))
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        main_layout.addWidget(self.list_widget)

        # Bottom Controls Row (+ FILE, + DIR, - DEL, CLEAR, TOTAL)
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(4)

        self.btn_add_file = QPushButton("+ FILE")
        self.btn_add_file.setFixedHeight(18)
        self.btn_add_file.clicked.connect(self._add_file_dialog)
        bottom_row.addWidget(self.btn_add_file)

        self.btn_add_dir = QPushButton("+ DIR")
        self.btn_add_dir.setFixedHeight(18)
        self.btn_add_dir.clicked.connect(self._add_dir_dialog)
        bottom_row.addWidget(self.btn_add_dir)

        self.btn_del = QPushButton("- REM")
        self.btn_del.setFixedHeight(18)
        self.btn_del.clicked.connect(self._remove_selected)
        bottom_row.addWidget(self.btn_del)

        self.btn_clear = QPushButton("CLEAR")
        self.btn_clear.setFixedHeight(18)
        self.btn_clear.clicked.connect(self.audio.clear_playlist)
        bottom_row.addWidget(self.btn_clear)

        bottom_row.addStretch()

        self.lbl_total = QLabel("0 tracks")
        self.lbl_total.setFont(QFont("Monospace", 7))
        bottom_row.addWidget(self.lbl_total)

        main_layout.addLayout(bottom_row)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        paths = [u.toLocalFile() for u in urls if u.isLocalFile()]
        if paths:
            self.audio.add_files(paths)
            event.acceptProposedAction()

    def _add_file_dialog(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Add Audio Files", "",
            "Audio Files (*.mp3 *.flac *.ogg *.wav *.m4a *.aac *.opus *.mod *.xm *.s3m *.it);;All Files (*)"
        )
        if files:
            self.audio.add_files(files)

    def _add_dir_dialog(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Add Folder of Music")
        if dir_path:
            self.audio.add_files([dir_path])

    def _remove_selected(self):
        row = self.list_widget.currentRow()
        if row >= 0:
            self.audio.remove_track(row)

    def _on_item_double_clicked(self, item):
        row = self.list_widget.row(item)
        if row >= 0:
            self.audio.play_index(row)

    def _on_track_changed(self, track):
        self.refresh_list()

    def _filter_tracks(self, query):
        query = query.lower()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            match = query in item.text().lower()
            item.setHidden(not match)

    def refresh_list(self):
        self.list_widget.clear()
        total_sec = 0.0
        
        for i, track in enumerate(self.audio.playlist):
            total_sec += track.duration
            prefix = f"{i+1:2d}. "
            display_text = f"{prefix}{track.display_name:<36} [{track.duration_formatted}]"
            
            item = QListWidgetItem(display_text)
            if i == self.audio.current_index:
                # Highlight active playing track
                item.setForeground(self.theme_mgr.color("playlist_playing_text", "#ffcc00"))
                item.setBackground(self.theme_mgr.color("playlist_playing_bg", "#222000"))
            else:
                item.setForeground(self.theme_mgr.color("playlist_text", "#00ff44"))
                
            self.list_widget.addItem(item)

        # Update total summary
        total_mins = int(total_sec // 60)
        total_secs = int(total_sec % 60)
        count = len(self.audio.playlist)
        self.lbl_total.setText(f"{count} tracks / {total_mins}:{total_secs:02d}")

    def apply_theme(self):
        bg = self.theme_mgr.hex("chassis_bg", "#282932")
        border = self.theme_mgr.hex("chassis_border", "#4e5062")
        btn_bg = self.theme_mgr.hex("button_bg", "#323440")
        btn_text = self.theme_mgr.hex("button_text", "#d4d8e8")
        btn_active = self.theme_mgr.hex("button_active", "#00ff66")
        title_text = self.theme_mgr.hex("titlebar_text", "#00e5ff")
        pl_bg = self.theme_mgr.hex("playlist_bg", "#0a0a0f")
        pl_text = self.theme_mgr.hex("playlist_text", "#00ff44")
        pl_sel_bg = self.theme_mgr.hex("playlist_selected_bg", "#003318")
        pl_sel_text = self.theme_mgr.hex("playlist_selected_text", "#ffffff")

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg};
                color: {btn_text};
                font-family: 'Monospace';
            }}
            QLabel {{
                color: {btn_text};
            }}
            QLineEdit {{
                background-color: {pl_bg};
                color: {pl_text};
                border: 1px solid {border};
                padding: 1px 4px;
                font-size: 8px;
            }}
            QListWidget {{
                background-color: {pl_bg};
                color: {pl_text};
                border: 1px solid {border};
                selection-background-color: {pl_sel_bg};
                selection-color: {pl_sel_text};
            }}
            QPushButton {{
                background-color: {btn_bg};
                color: {btn_text};
                border: 1px solid {border};
                border-radius: 2px;
                font-size: 8px;
                font-weight: bold;
                padding: 0 4px;
            }}
            QPushButton:hover {{
                background-color: {border};
            }}
        """)
        self.lbl_title.setStyleSheet(f"color: {title_text};")
        self.refresh_list()

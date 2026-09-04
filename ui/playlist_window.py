import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLineEdit, QLabel, QFileDialog, QMenu, QAbstractItemView,
    QSizePolicy, QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPoint
from PyQt6.QtGui import QFont, QColor, QIcon, QPixmap, QDragEnterEvent, QDropEvent, QKeyEvent

class PlaylistWindow(QWidget):
    track_selected = pyqtSignal(int)

    def __init__(self, audio_engine, theme_mgr, parent=None):
        super().__init__(parent)
        self.audio = audio_engine
        self.theme_mgr = theme_mgr
        self.setAcceptDrops(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.init_ui()
        self.apply_theme()
        self.theme_mgr.theme_changed.connect(self.apply_theme)
        self.audio.playlist_updated.connect(self.refresh_list)
        self.audio.track_changed.connect(self._on_track_changed)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 4, 6, 6)
        main_layout.setSpacing(4)

        # ---------------------------------------------------------------------
        # Top Bar: Title & Search Filter
        # ---------------------------------------------------------------------
        top_row = QHBoxLayout()
        top_row.setSpacing(6)

        self.lbl_title = QLabel("WINAMP PLAYLIST")
        self.lbl_title.setFont(QFont("Monospace", 8, QFont.Weight.Bold))
        top_row.addWidget(self.lbl_title)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search tracks...")
        self.search_input.setFixedHeight(20)
        self.search_input.setFont(QFont("Monospace", 8))
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._filter_tracks)
        top_row.addWidget(self.search_input)

        self.lbl_total = QLabel("0 tracks")
        self.lbl_total.setFont(QFont("Monospace", 7))
        self.lbl_total.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        top_row.addWidget(self.lbl_total)

        main_layout.addLayout(top_row)

        # ---------------------------------------------------------------------
        # Playlist List Widget
        # ---------------------------------------------------------------------
        self.list_widget = QListWidget()
        self.list_widget.setFont(QFont("Monospace", 8))
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
        main_layout.addWidget(self.list_widget)

        # ---------------------------------------------------------------------
        # Bottom Controls Bar: Skinned Winamp Action Buttons & Quick Actions
        # ---------------------------------------------------------------------
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(3)

        # Classic Winamp PLEDIT Buttons (ADD, REM, SEL, MISC, LIST)
        self.btn_pl_add = QPushButton("+ ADD")
        self.btn_pl_add.setToolTip("Add Files / Folders to Playlist")
        self.btn_pl_add.clicked.connect(self._show_add_menu)
        bottom_row.addWidget(self.btn_pl_add)

        self.btn_pl_rem = QPushButton("- REM")
        self.btn_pl_rem.setToolTip("Remove Selected / Crop / Clear")
        self.btn_pl_rem.clicked.connect(self._show_rem_menu)
        bottom_row.addWidget(self.btn_pl_rem)

        self.btn_pl_sel = QPushButton("SEL")
        self.btn_pl_sel.setToolTip("Select All / None / Invert")
        self.btn_pl_sel.clicked.connect(self._show_sel_menu)
        bottom_row.addWidget(self.btn_pl_sel)

        self.btn_pl_misc = QPushButton("MISC")
        self.btn_pl_misc.setToolTip("Sort / Shuffle / Reverse Playlist")
        self.btn_pl_misc.clicked.connect(self._show_misc_menu)
        bottom_row.addWidget(self.btn_pl_misc)

        self.btn_pl_list = QPushButton("LIST")
        self.btn_pl_list.setToolTip("Save / Load Playlist (M3U)")
        self.btn_pl_list.clicked.connect(self._show_list_menu)
        bottom_row.addWidget(self.btn_pl_list)

        bottom_row.addStretch()

        # Direct Quick-Action Buttons
        self.btn_quick_file = QPushButton("+ FILE")
        self.btn_quick_file.setFixedHeight(20)
        self.btn_quick_file.clicked.connect(self._add_file_dialog)
        bottom_row.addWidget(self.btn_quick_file)

        self.btn_quick_dir = QPushButton("+ DIR")
        self.btn_quick_dir.setFixedHeight(20)
        self.btn_quick_dir.clicked.connect(self._add_dir_dialog)
        bottom_row.addWidget(self.btn_quick_dir)

        self.btn_quick_radio = QPushButton("📻 RADIO")
        self.btn_quick_radio.setFixedHeight(20)
        self.btn_quick_radio.setToolTip("Open Online Radio & YouTube Stream Studio")
        self.btn_quick_radio.clicked.connect(self._open_radio_dialog)
        bottom_row.addWidget(self.btn_quick_radio)

        self.btn_quick_m3u = QPushButton("💾 M3U")
        self.btn_quick_m3u.setFixedHeight(20)
        self.btn_quick_m3u.setToolTip("Save as .m3u playlist")
        self.btn_quick_m3u.clicked.connect(self._save_m3u_dialog)
        bottom_row.addWidget(self.btn_quick_m3u)

        main_layout.addLayout(bottom_row)

    # -------------------------------------------------------------------------
    # Context Menus & Actions
    # -------------------------------------------------------------------------
    def _show_add_menu(self):
        menu = QMenu(self)
        a_file = menu.addAction("➕ Add File(s)...")
        a_file.triggered.connect(self._add_file_dialog)
        a_dir = menu.addAction("📁 Add Folder of Music...")
        a_dir.triggered.connect(self._add_dir_dialog)
        menu.addSeparator()
        a_url = menu.addAction("🌐 Add Online Stream / URL...")
        a_url.triggered.connect(self._add_url_dialog)
        a_radio = menu.addAction("📻 Open Radio & YouTube Studio...")
        a_radio.triggered.connect(self._open_radio_dialog)
        menu.exec(self.btn_pl_add.mapToGlobal(QPoint(0, self.btn_pl_add.height())))

    def _show_rem_menu(self):
        menu = QMenu(self)
        a_rem = menu.addAction("➖ Remove Selected")
        a_rem.triggered.connect(self._remove_selected)
        a_crop = menu.addAction("✂️ Crop (Keep Only Selected)")
        a_crop.triggered.connect(self._crop_selected)
        a_clear = menu.addAction("🗑️ Clear Entire Playlist")
        a_clear.triggered.connect(self.audio.clear_playlist)
        menu.exec(self.btn_pl_rem.mapToGlobal(QPoint(0, self.btn_pl_rem.height())))

    def _show_sel_menu(self):
        menu = QMenu(self)
        a_all = menu.addAction("Select All")
        a_all.triggered.connect(self.list_widget.selectAll)
        a_none = menu.addAction("Select None")
        a_none.triggered.connect(self.list_widget.clearSelection)
        a_inv = menu.addAction("Invert Selection")
        a_inv.triggered.connect(self._invert_selection)
        menu.exec(self.btn_pl_sel.mapToGlobal(QPoint(0, self.btn_pl_sel.height())))

    def _show_misc_menu(self):
        menu = QMenu(self)
        a_title = menu.addAction("🔤 Sort by Track Title")
        a_title.triggered.connect(self.audio.sort_by_title)
        a_fname = menu.addAction("📄 Sort by Filename")
        a_fname.triggered.connect(self.audio.sort_by_filename)
        a_shuf = menu.addAction("🔀 Randomize / Shuffle Order")
        a_shuf.triggered.connect(self.audio.randomize_playlist)
        a_rev = menu.addAction("🔄 Reverse Order")
        a_rev.triggered.connect(self.audio.reverse_playlist)
        menu.exec(self.btn_pl_misc.mapToGlobal(QPoint(0, self.btn_pl_misc.height())))

    def _show_list_menu(self):
        menu = QMenu(self)
        a_save = menu.addAction("💾 Save Playlist (.m3u)...")
        a_save.triggered.connect(self._save_m3u_dialog)
        a_load = menu.addAction("📂 Load Playlist (.m3u)...")
        a_load.triggered.connect(self._load_m3u_dialog)
        a_new = menu.addAction("✨ New Playlist")
        a_new.triggered.connect(self.audio.clear_playlist)
        menu.exec(self.btn_pl_list.mapToGlobal(QPoint(0, self.btn_pl_list.height())))

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        item = self.list_widget.itemAt(pos)
        if item:
            row = self.list_widget.row(item)
            a_play = menu.addAction("▶ Play This Track")
            a_play.triggered.connect(lambda: self.audio.play_index(row))
            a_del = menu.addAction("➖ Remove from Playlist")
            a_del.triggered.connect(self._remove_selected)
            menu.addSeparator()
        
        a_add_f = menu.addAction("➕ Add File(s)...")
        a_add_f.triggered.connect(self._add_file_dialog)
        a_add_d = menu.addAction("📁 Add Folder...")
        a_add_d.triggered.connect(self._add_dir_dialog)
        menu.addSeparator()
        a_shuf = menu.addAction("🔀 Randomize Order")
        a_shuf.triggered.connect(self.audio.randomize_playlist)
        a_sort = menu.addAction("🔤 Sort by Title")
        a_sort.triggered.connect(self.audio.sort_by_title)
        menu.exec(self.list_widget.mapToGlobal(pos))

    # -------------------------------------------------------------------------
    # Drag & Drop and Dialogs
    # -------------------------------------------------------------------------
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        paths = []
        for u in urls:
            if u.isLocalFile():
                paths.append(u.toLocalFile())
            else:
                raw_url = u.toString()
                if raw_url:
                    paths.append(raw_url)

        if not urls and event.mimeData().hasText():
            text = event.mimeData().text().strip()
            if text.startswith("http://") or text.startswith("https://"):
                paths.append(text)

        if paths:
            self.audio.add_files(paths)
            event.acceptProposedAction()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self._remove_selected()
        else:
            super().keyPressEvent(event)

    def _open_radio_dialog(self):
        from ui.radio_dialog import RadioDialog
        dlg = RadioDialog(self.audio, self.theme_mgr, self)
        dlg.exec()

    def _add_url_dialog(self):
        url, ok = QInputDialog.getText(
            self, "Add Online Stream / Radio URL",
            "Enter Stream URL (e.g. http://ice1.somafm.com/groovesalad-128-mp3 or YouTube URL):"
        )
        if ok and url.strip():
            self.audio.add_files([url.strip()])

    def _add_file_dialog(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Add Audio Files", "",
            "Audio Files (*.mp3 *.flac *.ogg *.wav *.m4a *.aac *.opus *.mod *.xm *.s3m *.it *.pls *.m3u *.m3u8);;All Files (*)"
        )
        if files:
            self.audio.add_files(files)

    def _add_dir_dialog(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Add Folder of Music")
        if dir_path:
            self.audio.add_files([dir_path])

    def _save_m3u_dialog(self):
        if not self.audio.playlist:
            return
        fpath, _ = QFileDialog.getSaveFileName(self, "Export Playlist as M3U", "", "M3U Playlist (*.m3u *.m3u8)")
        if fpath:
            if not (fpath.endswith(".m3u") or fpath.endswith(".m3u8")):
                fpath += ".m3u8"
            self.audio.save_m3u(fpath)

    def _load_m3u_dialog(self):
        fpath, _ = QFileDialog.getOpenFileName(self, "Load M3U Playlist", "", "M3U Playlist (*.m3u *.m3u8)")
        if fpath:
            self.audio.load_m3u(fpath)

    def _remove_selected(self):
        selected_rows = [self.list_widget.row(item) for item in self.list_widget.selectedItems()]
        if selected_rows:
            self.audio.remove_indices(selected_rows)
        else:
            row = self.list_widget.currentRow()
            if row >= 0:
                self.audio.remove_track(row)

    def _crop_selected(self):
        selected_rows = set(self.list_widget.row(item) for item in self.list_widget.selectedItems())
        to_remove = [i for i in range(len(self.audio.playlist)) if i not in selected_rows]
        if to_remove:
            self.audio.remove_indices(to_remove)

    def _invert_selection(self):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setSelected(not item.isSelected())

    def _on_item_double_clicked(self, item):
        row = self.list_widget.row(item)
        if row >= 0:
            self.audio.play_index(row)

    def _on_track_changed(self, track):
        self.refresh_list()

    def _filter_tracks(self, query):
        query = query.lower().strip()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            match = (query in item.text().lower()) if query else True
            item.setHidden(not match)

    def refresh_list(self):
        self.list_widget.clear()
        total_sec = 0.0
        
        for i, track in enumerate(self.audio.playlist):
            total_sec += track.duration
            prefix = f"{i+1:2d}. "
            display_text = f"{prefix}{track.display_name}   [{track.duration_formatted}]"
            
            item = QListWidgetItem(display_text)
            if i == self.audio.current_index:
                # Highlight active playing track
                item.setForeground(self.theme_mgr.color("playlist_playing_text", "#bbd2ff"))
                item.setBackground(self.theme_mgr.color("playlist_playing_bg", "#1c3d7d"))
            else:
                item.setForeground(self.theme_mgr.color("playlist_text", "#ffffff"))
                
            self.list_widget.addItem(item)

        # Update total summary
        total_mins = int(total_sec // 60)
        total_secs = int(total_sec % 60)
        count = len(self.audio.playlist)
        self.lbl_total.setText(f"{count} tracks / {total_mins}:{total_secs:02d}")

    # -------------------------------------------------------------------------
    # Theme & Skin Application
    # -------------------------------------------------------------------------
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

        # Check if Winamp PLEDIT button sprites are available
        skin = self.theme_mgr.active_skin
        has_sprites = skin and skin.sprites and 'pl_btn_add' in skin.sprites

        if has_sprites:
            sprites = skin.sprites
            btn_defs = [
                (self.btn_pl_add, 'pl_btn_add'),
                (self.btn_pl_rem, 'pl_btn_rem'),
                (self.btn_pl_sel, 'pl_btn_sel'),
                (self.btn_pl_misc, 'pl_btn_misc'),
                (self.btn_pl_list, 'pl_btn_list')
            ]
            for btn, s_name in btn_defs:
                if s_name in sprites:
                    orig_pix = sprites[s_name][0]
                    btn.setIcon(QIcon(orig_pix))
                    btn.setIconSize(QSize(orig_pix.width(), orig_pix.height()))
                    btn.setFixedSize(orig_pix.width(), orig_pix.height())
                    btn.setStyleSheet("border: none; padding: 0px; background: transparent;")
                    btn.setText("")
        else:
            for btn, txt in [
                (self.btn_pl_add, "+ ADD"),
                (self.btn_pl_rem, "- REM"),
                (self.btn_pl_sel, "SEL"),
                (self.btn_pl_misc, "MISC"),
                (self.btn_pl_list, "LIST")
            ]:
                btn.setIcon(QIcon())
                btn.setText(txt)
                btn.setFixedHeight(20)
                btn.setStyleSheet("")

        chassis_pattern = self.theme_mgr.get_texture_path("chassis_pattern")
        titlebar_pattern = self.theme_mgr.get_texture_path("titlebar_repeat")
        pl_deck_bg_css = f"background-image: url('{chassis_pattern}'); background-repeat: repeat;" if chassis_pattern else f"background-color: {bg};"

        self.setStyleSheet(f"""
            PlaylistWindow, QWidget {{
                {pl_deck_bg_css}
                color: {btn_text};
                font-family: 'Monospace';
            }}
            QLabel {{
                color: {btn_text};
                background: transparent;
                border: none;
            }}
            QLineEdit {{
                background-color: {pl_bg};
                background-image: none;
                color: {pl_text};
                border: 1px solid {border};
                border-radius: 2px;
                padding: 1px 6px;
                font-size: 8px;
            }}
            QListWidget {{
                background-color: {pl_bg};
                background-image: none;
                color: {pl_text};
                border: 1px solid {border};
                border-radius: 3px;
                padding: 2px;
                selection-background-color: {pl_sel_bg};
                selection-color: {pl_sel_text};
                outline: none;
            }}
            QListWidget::item {{
                padding: 2px 4px;
                border-radius: 2px;
            }}
            QListWidget::item:hover {{
                background-color: {border};
            }}
            QListWidget::item:selected {{
                background-color: {pl_sel_bg};
                color: {pl_sel_text};
            }}
            QPushButton {{
                background-color: {btn_bg};
                background-image: none;
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
            QPushButton:pressed {{
                background-color: {btn_active};
                color: #000000;
            }}
            QMenu {{
                background-color: {bg};
                background-image: none;
                color: {btn_text};
                border: 1px solid {border};
                font-size: 9px;
            }}
            QMenu::item {{
                padding: 4px 16px;
            }}
            QMenu::item:selected {{
                background-color: {pl_sel_bg};
                color: {pl_sel_text};
            }}
            QScrollBar:vertical {{
                background: {pl_bg};
                background-image: none;
                width: 12px;
                margin: 0px;
                border: 1px solid {border};
            }}
            QScrollBar::handle:vertical {{
                background: {btn_bg};
                background-image: none;
                min-height: 20px;
                border-radius: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {btn_active};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
        """)
        if titlebar_pattern:
            self.lbl_title.setStyleSheet(f"color: {title_text}; background-image: url('{titlebar_pattern}'); background-repeat: repeat; padding: 2px 6px; border-radius: 2px;")
        else:
            self.lbl_title.setStyleSheet(f"color: {title_text}; background: transparent;")
        self.refresh_list()


import os
import threading
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QLineEdit, QFormLayout, QMessageBox, QGroupBox,
    QTabWidget, QWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QSplitter
)
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QDesktopServices, QIcon
from core.i18n import _, i18n


class BackgroundWorker(QObject):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, target_fn, *args, **kwargs):
        super().__init__()
        self.target_fn = target_fn
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            res = self.target_fn(*self.args, **self.kwargs)
            self.finished.emit(res)
        except Exception as e:
            self.error.emit(str(e))


class RadioDialog(QDialog):
    def __init__(self, audio_engine, theme_mgr, parent=None):
        super().__init__(parent)
        self.audio = audio_engine
        self.theme_mgr = theme_mgr
        self.radio_mgr = audio_engine.radio_mgr
        
        self.setWindowTitle(_("radio_window_title"))
        self.resize(720, 600)
        self.setMinimumSize(600, 480)

        self.loaded_yt_tracks = []
        self.loaded_yt_title = ""
        self.loaded_yt_url = ""

        self.init_ui()
        self.apply_theme()
        self.theme_mgr.theme_changed.connect(self.apply_theme)

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(8)

        # Header Title Bar
        header = QHBoxLayout()
        lbl_title = QLabel(_("radio_header"))
        lbl_title.setFont(QFont("Monospace", 10, QFont.Weight.Bold))
        header.addWidget(lbl_title)
        header.addStretch()
        # Bottom Row
        bottom_row = QHBoxLayout()
        self.lbl_status = QLabel("Ready.")
        self.lbl_status.setFont(QFont("Monospace", 8))
        bottom_row.addWidget(self.lbl_status)
        bottom_row.addStretch()

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFixedWidth(120)
        self.progress_bar.setFixedHeight(16)
        self.progress_bar.setVisible(False)
        bottom_row.addWidget(self.progress_bar)

        btn_close = QPushButton(_("btn_close"))
        btn_close.setFixedWidth(80)
        btn_close.clicked.connect(self.accept)
        bottom_row.addWidget(btn_close)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setFont(QFont("Monospace", 8, QFont.Weight.Bold))

        # Tab 1: Curated Stations (SomaFM, SR, Lofi, Synthwave, Electronic, Rock, Jazz)
        self.tab_curated = QWidget()
        self._init_curated_tab()
        self.tabs.addTab(self.tab_curated, _("radio_tab_curated"))

        # Tab 2: Global Radio Browser
        self.tab_browser = QWidget()
        self._init_browser_tab()
        self.tabs.addTab(self.tab_browser, _("radio_tab_browser"))

        # Tab 3: YouTube Playlists & Search
        self.tab_youtube = QWidget()
        self._init_youtube_tab()
        self.tabs.addTab(self.tab_youtube, _("radio_tab_youtube"))

        # Tab 4: Favorites & Custom Streams
        self.tab_favorites = QWidget()
        self._init_favorites_tab()
        self.tabs.addTab(self.tab_favorites, _("radio_tab_favorites"))

        root_layout.addWidget(self.tabs)
        root_layout.addLayout(bottom_row)

    # =========================================================================
    # TAB 1: CURATED STATIONS
    # =========================================================================
    def _init_curated_tab(self):
        layout = QHBoxLayout(self.tab_curated)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        # Left: Category List
        left_box = QVBoxLayout()
        lbl_cat = QLabel("<b>Categories:</b>")
        lbl_cat.setFont(QFont("Monospace", 8))
        left_box.addWidget(lbl_cat)

        self.list_curated_cats = QListWidget()
        self.list_curated_cats.setFixedWidth(150)
        self.list_curated_cats.addItem("⭐ All Stations")
        for cat in self.radio_mgr.get_categories():
            self.list_curated_cats.addItem(cat)
        self.list_curated_cats.setCurrentRow(0)
        self.list_curated_cats.currentRowChanged.connect(self._on_curated_cat_changed)
        left_box.addWidget(self.list_curated_cats)
        layout.addLayout(left_box)

        # Right: Station List & Details
        right_box = QVBoxLayout()
        self.list_curated_stations = QListWidget()
        self.list_curated_stations.setFont(QFont("Monospace", 8))
        self.list_curated_stations.currentRowChanged.connect(self._on_curated_station_selected)
        self.list_curated_stations.itemDoubleClicked.connect(lambda: self._play_curated_station(play_now=True))
        right_box.addWidget(self.list_curated_stations)

        # Details Box
        self.box_curated_info = QGroupBox("Station Details")
        info_layout = QVBoxLayout(self.box_curated_info)
        self.lbl_curated_desc = QLabel("Select a station to see details.")
        self.lbl_curated_desc.setWordWrap(True)
        info_layout.addWidget(self.lbl_curated_desc)
        right_box.addWidget(self.box_curated_info)

        # Action Buttons
        actions = QHBoxLayout()
        btn_play = QPushButton("▶ Play Now")
        btn_play.setStyleSheet("font-weight: bold; padding: 4px 8px;")
        btn_play.clicked.connect(lambda: self._play_curated_station(play_now=True))
        actions.addWidget(btn_play)

        btn_add = QPushButton("➕ Add to Playlist")
        btn_add.clicked.connect(lambda: self._play_curated_station(play_now=False))
        actions.addWidget(btn_add)

        btn_fav = QPushButton("⭐ Star / Favorite")
        btn_fav.clicked.connect(self._star_curated_station)
        actions.addWidget(btn_fav)

        btn_web = QPushButton("🌐 Visit Web")
        btn_web.clicked.connect(self._visit_curated_web)
        actions.addWidget(btn_web)

        right_box.addLayout(actions)
        layout.addLayout(right_box)

        self._populate_curated_stations()

    def _populate_curated_stations(self, category=None):
        self.list_curated_stations.clear()
        stations = self.radio_mgr.get_curated_stations(category)
        for st in stations:
            fav_star = " ⭐" if self.radio_mgr.is_favorite(st.get("url")) else ""
            item = QListWidgetItem(f"{st.get('name')}{fav_star} [{st.get('genre')}] ({st.get('bitrate')}k {st.get('codec')})")
            item.setData(Qt.ItemDataRole.UserRole, st)
            self.list_curated_stations.addItem(item)
        if stations:
            self.list_curated_stations.setCurrentRow(0)

    def _on_curated_cat_changed(self, row):
        if row == 0:
            self._populate_curated_stations(None)
        else:
            cat = self.list_curated_cats.item(row).text()
            self._populate_curated_stations(cat)

    def _on_curated_station_selected(self, row):
        item = self.list_curated_stations.item(row)
        if not item:
            return
        st = item.data(Qt.ItemDataRole.UserRole)
        self.lbl_curated_desc.setText(
            f"<b>{st.get('name')}</b> ({st.get('genre')})<br>"
            f"<b>Stream:</b> {st.get('bitrate')} kbps {st.get('codec')}<br>"
            f"<b>Description:</b> {st.get('description', '')}<br>"
            f"<b>URL:</b> {st.get('url')}"
        )

    def _play_curated_station(self, play_now=True):
        item = self.list_curated_stations.currentItem()
        if not item:
            return
        st = item.data(Qt.ItemDataRole.UserRole)
        self.audio.add_stream_track(
            url=st.get("url"),
            title=st.get("name"),
            artist=st.get("genre", "Internet Radio"),
            stream_type="radio",
            play_now=play_now
        )
        self.lbl_status.setText(f"{'Playing' if play_now else 'Added'}: {st.get('name')}")

    def _star_curated_station(self):
        item = self.list_curated_stations.currentItem()
        if not item:
            return
        st = item.data(Qt.ItemDataRole.UserRole)
        is_fav = self.radio_mgr.toggle_favorite(st)
        row = self.list_curated_cats.currentRow()
        self._on_curated_cat_changed(row)
        self._populate_favorites()
        self.lbl_status.setText(f"{'Starred' if is_fav else 'Unstarred'}: {st.get('name')}")

    def _visit_curated_web(self):
        item = self.list_curated_stations.currentItem()
        if not item:
            return
        st = item.data(Qt.ItemDataRole.UserRole)
        homepage = st.get("homepage")
        if homepage:
            QDesktopServices.openUrl(QUrl(homepage))

    # =========================================================================
    # TAB 2: GLOBAL RADIO BROWSER (30k+ Stations)
    # =========================================================================
    def _init_browser_tab(self):
        layout = QVBoxLayout(self.tab_browser)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Search Bar
        search_row = QHBoxLayout()
        self.input_rb_search = QLineEdit()
        self.input_rb_search.setPlaceholderText("Search 30,000+ stations worldwide (e.g. synthwave, sweden, trance, jazz, bbc)...")
        self.input_rb_search.setFont(QFont("Monospace", 8))
        self.input_rb_search.returnPressed.connect(self._search_radio_browser)
        search_row.addWidget(self.input_rb_search)

        btn_search = QPushButton("🔍 Search")
        btn_search.clicked.connect(self._search_radio_browser)
        search_row.addWidget(btn_search)
        layout.addLayout(search_row)

        # Quick Genre Filter Chips
        chips_row = QHBoxLayout()
        chips_row.setSpacing(4)
        for tag in ["Synthwave", "Lofi", "Trance", "Sweden", "Rock", "Metal", "Jazz", "Ambient", "80s"]:
            btn_tag = QPushButton(tag)
            btn_tag.setFixedHeight(18)
            btn_tag.setFont(QFont("Monospace", 7))
            btn_tag.clicked.connect(lambda checked, t=tag.lower(): self._search_by_tag(t))
            chips_row.addWidget(btn_tag)
        chips_row.addStretch()
        layout.addLayout(chips_row)

        # Station Results Table
        self.table_rb = QTableWidget()
        self.table_rb.setColumnCount(5)
        self.table_rb.setHorizontalHeaderLabels(["Station Name", "Genre / Tags", "Country", "Bitrate", "Votes"])
        self.table_rb.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table_rb.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_rb.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_rb.itemDoubleClicked.connect(lambda item: self._play_rb_station(play_now=True))
        layout.addWidget(self.table_rb)

        # Action Buttons
        actions = QHBoxLayout()
        btn_play = QPushButton("▶ Play Selected Station")
        btn_play.setStyleSheet("font-weight: bold; padding: 4px 8px;")
        btn_play.clicked.connect(lambda: self._play_rb_station(play_now=True))
        actions.addWidget(btn_play)

        btn_add = QPushButton("➕ Add to Playlist")
        btn_add.clicked.connect(lambda: self._play_rb_station(play_now=False))
        actions.addWidget(btn_add)

        btn_fav = QPushButton("⭐ Star to Favorites")
        btn_fav.clicked.connect(self._star_rb_station)
        actions.addWidget(btn_fav)

        layout.addLayout(actions)

        # Initial search with Synthwave
        self._search_by_tag("synthwave")

    def _search_by_tag(self, tag):
        self.input_rb_search.setText(tag)
        self._run_rb_search(name_query="", tag=tag)

    def _search_radio_browser(self):
        query = self.input_rb_search.text().strip()
        self._run_rb_search(name_query=query)

    def _run_rb_search(self, name_query="", tag=""):
        self.lbl_status.setText("Searching Radio Browser...")
        self.progress_bar.setVisible(True)

        def _task():
            return self.radio_mgr.search_radio_browser(name_query=name_query, tag=tag, limit=60)

        worker = BackgroundWorker(_task)
        worker.finished.connect(self._on_rb_results)
        worker.error.connect(lambda err: self._on_rb_error(err))
        t = threading.Thread(target=worker.run, daemon=True)
        t.start()

    def _on_rb_results(self, results):
        self.progress_bar.setVisible(False)
        self.lbl_status.setText(f"Found {len(results)} stations.")
        self.table_rb.setRowCount(len(results))

        for row, st in enumerate(results):
            name_item = QTableWidgetItem(st.get("name", "Unknown"))
            name_item.setData(Qt.ItemDataRole.UserRole, st)
            self.table_rb.setItem(row, 0, name_item)
            self.table_rb.setItem(row, 1, QTableWidgetItem(st.get("genre", "")))
            self.table_rb.setItem(row, 2, QTableWidgetItem(st.get("country", "")))
            self.table_rb.setItem(row, 3, QTableWidgetItem(f"{st.get('bitrate', 128)}k {st.get('codec', '')}"))
            self.table_rb.setItem(row, 4, QTableWidgetItem(str(st.get("votes", 0))))

        if results:
            self.table_rb.selectRow(0)

    def _on_rb_error(self, err):
        self.progress_bar.setVisible(False)
        self.lbl_status.setText(f"Search error: {err}")

    def _get_selected_rb_station(self):
        row = self.table_rb.currentRow()
        if row >= 0:
            item = self.table_rb.item(row, 0)
            if item:
                return item.data(Qt.ItemDataRole.UserRole)
        return None

    def _play_rb_station(self, play_now=True):
        st = self._get_selected_rb_station()
        if not st:
            return
        self.audio.add_stream_track(
            url=st.get("url"),
            title=st.get("name"),
            artist=st.get("genre", "Internet Radio"),
            stream_type="radio",
            play_now=play_now
        )
        self.lbl_status.setText(f"{'Playing' if play_now else 'Added'}: {st.get('name')}")

    def _star_rb_station(self):
        st = self._get_selected_rb_station()
        if not st:
            return
        is_fav = self.radio_mgr.toggle_favorite(st)
        self._populate_favorites()
        self.lbl_status.setText(f"{'Starred' if is_fav else 'Unstarred'}: {st.get('name')}")

    # =========================================================================
    # TAB 3: YOUTUBE PLAYLISTS & STREAMS
    # =========================================================================
    def _init_youtube_tab(self):
        layout = QVBoxLayout(self.tab_youtube)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # URL Input & Search
        row_input = QHBoxLayout()
        self.input_yt = QLineEdit()
        self.input_yt.setPlaceholderText("Paste YouTube Playlist URL (https://www.youtube.com/playlist?list=...) or search query...")
        self.input_yt.setFont(QFont("Monospace", 8))
        self.input_yt.returnPressed.connect(self._load_youtube)
        row_input.addWidget(self.input_yt)

        btn_load = QPushButton("🔍 Load Playlist / Search")
        btn_load.clicked.connect(self._load_youtube)
        row_input.addWidget(btn_load)
        layout.addLayout(row_input)

        # Quick preset YouTube search buttons
        quick_row = QHBoxLayout()
        quick_row.setSpacing(4)
        for label, q in [
            ("Lofi Live Stream", "lofi hip hop radio live"),
            ("Synthwave 80s Mix", "synthwave retrowave mix 2024"),
            ("Chiptune 8-Bit", "chiptune 8 bit music mix"),
            ("Vaporwave Lounge", "vaporwave chill mix")
        ]:
            btn_q = QPushButton(label)
            btn_q.setFixedHeight(18)
            btn_q.setFont(QFont("Monospace", 7))
            btn_q.clicked.connect(lambda checked, query=q: self._quick_yt_search(query))
            quick_row.addWidget(btn_q)
        quick_row.addStretch()
        layout.addLayout(quick_row)

        # Playlist Info & Track List
        self.lbl_yt_info = QLabel("Enter a YouTube playlist URL or search query to extract tracks.")
        self.lbl_yt_info.setFont(QFont("Monospace", 8, QFont.Weight.Bold))
        layout.addWidget(self.lbl_yt_info)

        self.list_yt_tracks = QListWidget()
        self.list_yt_tracks.setFont(QFont("Monospace", 8))
        self.list_yt_tracks.itemDoubleClicked.connect(lambda: self._play_single_yt_track(play_now=True))
        layout.addWidget(self.list_yt_tracks)

        # Actions
        actions = QHBoxLayout()
        btn_play_all = QPushButton("▶ Play Entire Playlist")
        btn_play_all.setStyleSheet("font-weight: bold; padding: 4px 8px; background-color: #cc0000; color: white;")
        btn_play_all.clicked.connect(lambda: self._add_all_yt_tracks(play_now=True))
        actions.addWidget(btn_play_all)

        btn_add_all = QPushButton("➕ Add All to Active Playlist")
        btn_add_all.clicked.connect(lambda: self._add_all_yt_tracks(play_now=False))
        actions.addWidget(btn_add_all)

        btn_save_pl = QPushButton("💾 Save Playlist to Library")
        btn_save_pl.clicked.connect(self._save_yt_playlist_to_lib)
        actions.addWidget(btn_save_pl)

        layout.addLayout(actions)

    def _quick_yt_search(self, query):
        self.input_yt.setText(query)
        self._load_youtube()

    def _load_youtube(self):
        query = self.input_yt.text().strip()
        if not query:
            return
        self.lbl_status.setText("Extracting YouTube audio stream info via yt-dlp...")
        self.progress_bar.setVisible(True)

        def _task():
            return self.radio_mgr.parse_youtube_url(query)

        worker = BackgroundWorker(_task)
        worker.finished.connect(self._on_yt_loaded)
        worker.error.connect(lambda err: self._on_yt_error(err))
        t = threading.Thread(target=worker.run, daemon=True)
        t.start()

    def _on_yt_loaded(self, res):
        self.progress_bar.setVisible(False)
        tracks = res.get("tracks", [])
        title = res.get("title", "YouTube Playlist")
        self.loaded_yt_tracks = tracks
        self.loaded_yt_title = title
        self.loaded_yt_url = self.input_yt.text().strip()

        self.lbl_yt_info.setText(f"<b>{title}</b> ({len(tracks)} tracks)")
        self.list_yt_tracks.clear()

        for i, t in enumerate(tracks):
            dur = t.get("duration", 0)
            dur_str = f"{int(dur // 60)}:{int(dur % 60):02d}" if dur > 0 else "LIVE"
            item = QListWidgetItem(f"{i+1:02d}. {t.get('artist')} - {t.get('title')} [{dur_str}]")
            item.setData(Qt.ItemDataRole.UserRole, t)
            self.list_yt_tracks.addItem(item)

        self.lbl_status.setText(f"Loaded {len(tracks)} YouTube tracks.")

    def _on_yt_error(self, err):
        self.progress_bar.setVisible(False)
        self.lbl_status.setText(f"YouTube error: {err}")

    def _add_all_yt_tracks(self, play_now=False):
        if not self.loaded_yt_tracks:
            QMessageBox.warning(self, "No Tracks", "Please load a YouTube playlist first.")
            return
        self.audio.add_youtube_tracks(self.loaded_yt_tracks, play_now=play_now)
        self.lbl_status.setText(f"Added {len(self.loaded_yt_tracks)} YouTube tracks to playlist.")

    def _play_single_yt_track(self, play_now=True):
        item = self.list_yt_tracks.currentItem()
        if not item:
            return
        t = item.data(Qt.ItemDataRole.UserRole)
        self.audio.add_youtube_tracks([t], play_now=play_now)

    def _save_yt_playlist_to_lib(self):
        if not self.loaded_yt_tracks:
            return
        self.radio_mgr.save_youtube_playlist(
            title=self.loaded_yt_title,
            url=self.loaded_yt_url,
            tracks=self.loaded_yt_tracks
        )
        self._populate_favorites()
        QMessageBox.information(self, "Saved", f"Playlist '{self.loaded_yt_title}' saved to your Library!")

    # =========================================================================
    # TAB 4: FAVORITES & CUSTOM STREAMS
    # =========================================================================
    def _init_favorites_tab(self):
        layout = QVBoxLayout(self.tab_favorites)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Starred Stations & Playlists List
        lbl_fav = QLabel("<b>⭐ Starred Stations & Saved YouTube Playlists:</b>")
        layout.addWidget(lbl_fav)

        self.list_favorites = QListWidget()
        self.list_favorites.setFont(QFont("Monospace", 8))
        self.list_favorites.itemDoubleClicked.connect(lambda: self._play_favorite_item(play_now=True))
        layout.addWidget(self.list_favorites)

        fav_actions = QHBoxLayout()
        btn_play_fav = QPushButton("▶ Play Selected")
        btn_play_fav.setStyleSheet("font-weight: bold; padding: 4px 8px;")
        btn_play_fav.clicked.connect(lambda: self._play_favorite_item(play_now=True))
        fav_actions.addWidget(btn_play_fav)

        btn_add_fav = QPushButton("➕ Add to Playlist")
        btn_add_fav.clicked.connect(lambda: self._play_favorite_item(play_now=False))
        fav_actions.addWidget(btn_add_fav)

        btn_rem_fav = QPushButton("➖ Remove from Favorites")
        btn_rem_fav.clicked.connect(self._remove_favorite_item)
        fav_actions.addWidget(btn_rem_fav)
        layout.addLayout(fav_actions)

        # Custom Stream Creator Box
        box_custom = QGroupBox("➕ Add Custom Online Radio Stream URL")
        custom_layout = QFormLayout(box_custom)

        self.input_custom_name = QLineEdit()
        self.input_custom_name.setPlaceholderText("e.g. My Favorite Radio Station")
        self.input_custom_url = QLineEdit()
        self.input_custom_url.setPlaceholderText("e.g. http://stream.myradio.com:8000/live.mp3 or .pls or .m3u8")
        self.input_custom_genre = QLineEdit("Custom")

        custom_layout.addRow("Station Name:", self.input_custom_name)
        custom_layout.addRow("Stream URL:", self.input_custom_url)
        custom_layout.addRow("Genre / Tag:", self.input_custom_genre)

        btn_add_custom = QPushButton("💾 Save Custom Stream")
        btn_add_custom.setStyleSheet("font-weight: bold; padding: 4px;")
        btn_add_custom.clicked.connect(self._add_custom_stream)
        custom_layout.addRow(btn_add_custom)

        layout.addWidget(box_custom)

        self._populate_favorites()

    def _populate_favorites(self):
        self.list_favorites.clear()

        # 1. Starred Radio Stations
        for f in self.radio_mgr.favorites:
            name = f.get("name", "Station")
            genre = f.get("genre", "Radio")
            item = QListWidgetItem(f"📻 {name} [{genre}]")
            item.setData(Qt.ItemDataRole.UserRole, {"type": "radio", "data": f})
            self.list_favorites.addItem(item)

        # 2. Saved Custom Streams
        for c in self.radio_mgr.custom_stations:
            item = QListWidgetItem(f"🌐 [Custom] {c.get('name')} [{c.get('genre')}]")
            item.setData(Qt.ItemDataRole.UserRole, {"type": "custom", "data": c})
            self.list_favorites.addItem(item)

        # 3. Saved YouTube Playlists
        for y in self.radio_mgr.saved_youtube_playlists:
            item = QListWidgetItem(f"📺 [YouTube] {y.get('title')} ({y.get('tracks_count', 0)} tracks)")
            item.setData(Qt.ItemDataRole.UserRole, {"type": "youtube_playlist", "data": y})
            self.list_favorites.addItem(item)

    def _play_favorite_item(self, play_now=True):
        item = self.list_favorites.currentItem()
        if not item:
            return
        obj = item.data(Qt.ItemDataRole.UserRole)
        otype = obj.get("type")
        data = obj.get("data")

        if otype in ("radio", "custom"):
            self.audio.add_stream_track(
                url=data.get("url"),
                title=data.get("name"),
                artist=data.get("genre", "Internet Radio"),
                stream_type="radio",
                play_now=play_now
            )
        elif otype == "youtube_playlist":
            tracks = data.get("tracks", [])
            self.audio.add_youtube_tracks(tracks, play_now=play_now)

    def _remove_favorite_item(self):
        item = self.list_favorites.currentItem()
        if not item:
            return
        obj = item.data(Qt.ItemDataRole.UserRole)
        otype = obj.get("type")
        data = obj.get("data")

        if otype == "radio":
            self.radio_mgr.toggle_favorite(data)
        elif otype == "custom":
            if data in self.radio_mgr.custom_stations:
                self.radio_mgr.custom_stations.remove(data)
                self.radio_mgr.save_state()
        elif otype == "youtube_playlist":
            if data in self.radio_mgr.saved_youtube_playlists:
                self.radio_mgr.saved_youtube_playlists.remove(data)
                self.radio_mgr.save_state()

        self._populate_favorites()

    def _add_custom_stream(self):
        name = self.input_custom_name.text().strip()
        url = self.input_custom_url.text().strip()
        genre = self.input_custom_genre.text().strip()
        if not name or not url:
            QMessageBox.warning(self, "Missing Info", "Please provide a station name and stream URL.")
            return

        st = self.radio_mgr.add_custom_station(name=name, url=url, genre=genre)
        self.input_custom_name.clear()
        self.input_custom_url.clear()
        self._populate_favorites()
        QMessageBox.information(self, "Stream Added", f"Custom station '{name}' added successfully!")

    # =========================================================================
    # THEME STYLING
    # =========================================================================
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
            RadioDialog, QWidget {{
                background-color: {bg};
                color: {btn_text};
                font-family: 'Monospace';
            }}
            QTabWidget::pane {{
                border: 1px solid {border};
                background: {bg};
            }}
            QTabBar::tab {{
                background: {btn_bg};
                color: {btn_text};
                border: 1px solid {border};
                padding: 4px 10px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: {border};
                color: {btn_active};
                font-weight: bold;
            }}
            QListWidget, QTableWidget {{
                background-color: {pl_bg};
                color: {pl_text};
                border: 1px solid {border};
                border-radius: 3px;
                selection-background-color: {pl_sel_bg};
                selection-color: {pl_sel_text};
            }}
            QHeaderView::section {{
                background-color: {btn_bg};
                color: {btn_text};
                border: 1px solid {border};
                padding: 2px 4px;
                font-size: 8px;
                font-weight: bold;
            }}
            QLineEdit {{
                background-color: {pl_bg};
                color: {pl_text};
                border: 1px solid {border};
                border-radius: 2px;
                padding: 2px 6px;
                font-size: 8px;
            }}
            QPushButton {{
                background-color: {btn_bg};
                color: {btn_text};
                border: 1px solid {border};
                border-radius: 2px;
                font-size: 8px;
                font-weight: bold;
                padding: 2px 6px;
            }}
            QPushButton:hover {{
                background-color: {border};
            }}
            QPushButton:pressed {{
                background-color: {btn_active};
                color: #000000;
            }}
            QGroupBox {{
                border: 1px solid {border};
                border-radius: 4px;
                margin-top: 6px;
                padding-top: 8px;
                font-weight: bold;
                font-size: 8px;
            }}
            QProgressBar {{
                background-color: {pl_bg};
                border: 1px solid {border};
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background-color: {btn_active};
            }}
        """)

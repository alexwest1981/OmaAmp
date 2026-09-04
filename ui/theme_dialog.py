import os
import json
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QColorDialog, QLineEdit, QFormLayout, QMessageBox, QGroupBox,
    QFileDialog, QTabWidget, QWidget, QTextEdit, QScrollArea, QFrame,
    QSizePolicy, QProgressBar
)
from PyQt6.QtCore import Qt, QUrl, QSize
from PyQt6.QtGui import QFont, QColor, QDesktopServices, QIcon, QPixmap
from core.i18n import _, i18n


class ThemeDialog(QDialog):
    def __init__(self, theme_mgr, parent=None):
        super().__init__(parent)
        self.theme_mgr = theme_mgr
        self.github = theme_mgr.github
        
        self.setWindowTitle(_("theme_window_title"))
        self.resize(620, 560)
        self.setMinimumSize(540, 480)

        self.init_ui()

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(8)

        # Header Title
        header = QHBoxLayout()
        lbl_title = QLabel(_("theme_header"))
        lbl_title.setFont(QFont("Monospace", 10, QFont.Weight.Bold))
        header.addWidget(lbl_title)
        header.addStretch()
        root_layout.addLayout(header)

        # Tab Widget
        self.tabs = QTabWidget()
        self.tabs.setFont(QFont("Monospace", 8, QFont.Weight.Bold))

        # Tab 1: Installed Themes
        self.tab_installed = QWidget()
        self._init_installed_tab()
        self.tabs.addTab(self.tab_installed, _("theme_tab_installed"))

        # Tab 2: GitHub Community Hub
        self.tab_community = QWidget()
        self._init_community_tab()
        self.tabs.addTab(self.tab_community, _("theme_tab_community"))

        # Tab 3: Visual Theme Studio / Creator
        self.tab_creator = QWidget()
        self._init_creator_tab()
        self.tabs.addTab(self.tab_creator, _("theme_tab_creator"))

        # Tab 4: GitHub Account & Publishing
        self.tab_publish = QWidget()
        self._init_publish_tab()
        self.tabs.addTab(self.tab_publish, _("theme_tab_publish"))

        root_layout.addWidget(self.tabs)

        # Bottom Close Row
        bottom_row = QHBoxLayout()
        self.lbl_status = QLabel("")
        self.lbl_status.setFont(QFont("Monospace", 8))
        bottom_row.addWidget(self.lbl_status)
        bottom_row.addStretch()

        btn_close = QPushButton("Close")
        btn_close.setFixedWidth(80)
        btn_close.clicked.connect(self.accept)
        bottom_row.addWidget(btn_close)
        root_layout.addLayout(bottom_row)

        self.refresh_installed_list()

    # =========================================================================
    # TAB 1: INSTALLED THEMES
    # =========================================================================
    def _init_installed_tab(self):
        layout = QVBoxLayout(self.tab_installed)
        layout.setSpacing(6)

        lbl = QLabel("Select an installed native theme or imported skin:")
        lbl.setFont(QFont("Monospace", 8))
        layout.addWidget(lbl)

        self.list_installed = QListWidget()
        self.list_installed.setFont(QFont("Monospace", 9))
        self.list_installed.currentRowChanged.connect(self._on_installed_selected)
        layout.addWidget(self.list_installed)

        # Theme Info Box
        self.box_info = QGroupBox("Theme Details")
        info_layout = QVBoxLayout(self.box_info)
        self.lbl_theme_name = QLabel("<b>Name:</b> -")
        self.lbl_theme_author = QLabel("<b>Author:</b> -")
        self.lbl_theme_desc = QLabel("<b>Description:</b> -")
        self.lbl_theme_desc.setWordWrap(True)
        info_layout.addWidget(self.lbl_theme_name)
        info_layout.addWidget(self.lbl_theme_author)
        info_layout.addWidget(self.lbl_theme_desc)
        layout.addWidget(self.box_info)

        # Actions Row
        actions = QHBoxLayout()
        btn_apply = QPushButton("▶ Apply Theme")
        btn_apply.setStyleSheet("font-weight: bold; padding: 4px 8px;")
        btn_apply.clicked.connect(self._apply_selected_theme)
        actions.addWidget(btn_apply)

        btn_export = QPushButton("📦 Export Package (.omaamp-theme)")
        btn_export.clicked.connect(self._export_selected_theme)
        actions.addWidget(btn_export)

        btn_import_file = QPushButton("📁 Import File...")
        btn_import_file.clicked.connect(self._import_local_theme)
        actions.addWidget(btn_import_file)

        layout.addLayout(actions)

    def refresh_installed_list(self):
        self.list_installed.clear()
        themes = self.theme_mgr.get_available_themes()
        cur_row = 0
        for i, t in enumerate(themes):
            tid = t["id"]
            name = t["name"]
            is_cur = (tid == self.theme_mgr.current_theme_id)
            suffix = " [ACTIVE]" if is_cur else ""
            item = QListWidgetItem(f"{name}{suffix}")
            item.setData(Qt.ItemDataRole.UserRole, t)
            self.list_installed.addItem(item)
            if is_cur:
                cur_row = i

        if themes:
            self.list_installed.setCurrentRow(cur_row)

    def _on_installed_selected(self, row):
        item = self.list_installed.item(row)
        if not item:
            return
        tdata = item.data(Qt.ItemDataRole.UserRole)
        self.lbl_theme_name.setText(f"<b>Name:</b> {tdata.get('name', '')} (ID: {tdata.get('id', '')})")
        self.lbl_theme_author.setText(f"<b>Author:</b> {tdata.get('author', 'Unknown')} | <b>Version:</b> {tdata.get('version', '1.0.0')}")
        self.lbl_theme_desc.setText(f"<b>Description:</b> {tdata.get('description', '')}")

    def _apply_selected_theme(self):
        item = self.list_installed.currentItem()
        if not item:
            return
        tdata = item.data(Qt.ItemDataRole.UserRole)
        tid = tdata.get("id")
        if tid:
            self.theme_mgr.set_theme(tid)
            self.refresh_installed_list()
            self.lbl_status.setText(f"Active Theme: {tdata.get('name', tid)}")

    def _export_selected_theme(self):
        item = self.list_installed.currentItem()
        if not item:
            return
        tdata = item.data(Qt.ItemDataRole.UserRole)
        path = tdata.get("path")
        tid = tdata.get("id")
        
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Export OmaAmp Theme Package", f"{tid}.omaamp-theme", "OmaAmp Theme (*.omaamp-theme *.zip)"
        )
        if save_path:
            base_dir = os.path.dirname(path) if os.path.basename(path) == "theme.json" else path
            pkg = self.github.create_theme_package(base_dir, save_path)
            if pkg:
                QMessageBox.information(self, "Export Successful", f"Theme packaged and saved to:\n{save_path}")

    def _import_local_theme(self):
        fpath, _ = QFileDialog.getOpenFileName(
            self, "Import Theme / Skin", "",
            "Theme & Skin Files (*.omaamp-theme *.json *.wsz *.zip);;All Files (*)"
        )
        if fpath:
            tid = self.theme_mgr.import_skin_file(fpath)
            if tid:
                self.refresh_installed_list()
                QMessageBox.information(self, "Theme Imported", f"Theme '{tid}' successfully imported and activated!")

    # =========================================================================
    # TAB 2: GITHUB COMMUNITY HUB
    # =========================================================================
    def _init_community_tab(self):
        layout = QVBoxLayout(self.tab_community)
        layout.setSpacing(6)

        # Search bar & Direct URL
        search_row = QHBoxLayout()
        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText("Search GitHub community themes (e.g. cyberpunk, retro, titanium)...")
        self.input_search.setFont(QFont("Monospace", 8))
        self.input_search.returnPressed.connect(self._search_github)
        search_row.addWidget(self.input_search)

        btn_search = QPushButton("🔍 Search")
        btn_search.clicked.connect(self._search_github)
        search_row.addWidget(btn_search)
        layout.addLayout(search_row)

        # Direct GitHub URL Installer
        direct_row = QHBoxLayout()
        self.input_direct_url = QLineEdit()
        self.input_direct_url.setPlaceholderText("Or paste direct GitHub repo URL (https://github.com/user/repo) / raw JSON URL...")
        self.input_direct_url.setFont(QFont("Monospace", 8))
        direct_row.addWidget(self.input_direct_url)

        btn_direct_install = QPushButton("📥 Install URL")
        btn_direct_install.clicked.connect(self._install_direct_url)
        direct_row.addWidget(btn_direct_install)
        layout.addLayout(direct_row)

        # Results List
        self.list_community = QListWidget()
        self.list_community.setFont(QFont("Monospace", 9))
        self.list_community.currentRowChanged.connect(self._on_community_selected)
        layout.addWidget(self.list_community)

        # Selected Community Theme Details
        self.box_comm_info = QGroupBox("Community Theme Preview")
        comm_layout = QVBoxLayout(self.box_comm_info)
        self.lbl_comm_desc = QLabel("Select a theme to see details and install.")
        self.lbl_comm_desc.setWordWrap(True)
        comm_layout.addWidget(self.lbl_comm_desc)
        layout.addWidget(self.box_comm_info)

        # Install Action
        btn_install = QPushButton("⬇️ Download & Install Theme from GitHub")
        btn_install.setStyleSheet("font-weight: bold; padding: 6px;")
        btn_install.clicked.connect(self._install_selected_community_theme)
        layout.addWidget(btn_install)

        self._populate_community_catalog()

    def _populate_community_catalog(self, themes=None):
        self.list_community.clear()
        if themes is None:
            themes = self.github.get_community_themes()
        
        for t in themes:
            name = t.get("name", t.get("id"))
            author = t.get("author", "Community")
            stars = t.get("stars", 0)
            star_str = f" ⭐ {stars}" if stars else ""
            item = QListWidgetItem(f"{name} — by {author}{star_str}")
            item.setData(Qt.ItemDataRole.UserRole, t)
            self.list_community.addItem(item)

        if themes:
            self.list_community.setCurrentRow(0)

    def _search_github(self):
        query = self.input_search.text().strip()
        results = self.github.search_github_themes(query)
        self._populate_community_catalog(results)

    def _on_community_selected(self, row):
        item = self.list_community.item(row)
        if not item:
            return
        t = item.data(Qt.ItemDataRole.UserRole)
        self.lbl_comm_desc.setText(
            f"<b>{t.get('name', '')}</b> (v{t.get('version', '1.0.0')})<br>"
            f"<b>Author:</b> {t.get('author', 'Unknown')}<br>"
            f"<b>Description:</b> {t.get('description', '')}<br>"
            f"<b>GitHub Repository:</b> <a href='{t.get('repo_url', '#')}'>{t.get('repo_url', '')}</a>"
        )

    def _install_selected_community_theme(self):
        item = self.list_community.currentItem()
        if not item:
            return
        t = item.data(Qt.ItemDataRole.UserRole)
        repo_url = t.get("repo_url")
        if not repo_url:
            QMessageBox.warning(self, "No URL", "This theme has no repository URL.")
            return

        try:
            target_dir = os.path.expanduser("~/.config/omaamp/themes")
            res = self.github.install_theme_from_github(repo_url, target_dir)
            self.theme_mgr.reload_themes()
            self.refresh_installed_list()
            if res.get("id"):
                self.theme_mgr.set_theme(res["id"])
            QMessageBox.information(self, "Installation Complete", f"Successfully installed '{t.get('name')}' from GitHub!")
        except Exception as e:
            QMessageBox.critical(self, "Install Error", f"Failed to install theme from GitHub:\n{e}")

    def _install_direct_url(self):
        url = self.input_direct_url.text().strip()
        if not url:
            QMessageBox.warning(self, "Invalid URL", "Please enter a valid GitHub URL.")
            return
        try:
            target_dir = os.path.expanduser("~/.config/omaamp/themes")
            res = self.github.install_theme_from_github(url, target_dir)
            self.theme_mgr.reload_themes()
            self.refresh_installed_list()
            if res.get("id"):
                self.theme_mgr.set_theme(res["id"])
            QMessageBox.information(self, "Installation Complete", f"Theme successfully installed and activated!")
        except Exception as e:
            QMessageBox.critical(self, "Install Error", f"Failed to install theme from URL:\n{e}")

    # =========================================================================
    # TAB 3: VISUAL THEME STUDIO / CREATOR
    # =========================================================================
    def _init_creator_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(6)

        # Meta Form
        form = QFormLayout()
        self.create_id = QLineEdit("my_awesome_theme")
        self.create_name = QLineEdit("My Awesome Theme")
        self.create_author = QLineEdit(self.github.cached_profile.get("name", "Creator") if self.github.cached_profile else "Creator")
        self.create_desc = QLineEdit("Custom native scalable theme with repeating PNG textures.")

        form.addRow("Theme ID (folder name):", self.create_id)
        form.addRow("Display Name:", self.create_name)
        form.addRow("Author Name / GitHub:", self.create_author)
        form.addRow("Description:", self.create_desc)
        layout.addLayout(form)

        # Colors Section
        grp_colors = QGroupBox("1. Color Palette (Click to customize)")
        col_form = QFormLayout(grp_colors)
        self.creator_colors = {
            "chassis_bg": "#1c1d26",
            "chassis_border": "#00e5ff",
            "titlebar_bg": "#14151e",
            "titlebar_text": "#00f0ff",
            "lcd_bg": "#090a14",
            "lcd_text": "#00f0ff",
            "vis_bg": "#090a14",
            "vis_bars_low": "#00f0ff",
            "vis_bars_mid": "#ff0077",
            "vis_bars_high": "#ffe600",
            "button_bg": "#252738",
            "button_active": "#ff0055",
            "playlist_bg": "#0e0f18",
            "playlist_text": "#00f0ff",
            "playlist_selected_bg": "#330033"
        }
        self.color_btns = {}
        for k, hex_val in self.creator_colors.items():
            btn = QPushButton(hex_val)
            btn.setStyleSheet(f"background-color: {hex_val}; color: #ffffff; font-weight: bold; border: 1px solid #666;")
            btn.clicked.connect(lambda checked, key=k, b=btn: self._pick_creator_color(key, b))
            self.color_btns[k] = btn
            col_form.addRow(k.replace("_", " ").title() + ":", btn)
        layout.addWidget(grp_colors)

        # Textures Section (Web-like PNG Repeat Patterns)
        grp_tex = QGroupBox("2. Scalable Textures & PNG Patterns (Optional)")
        tex_form = QFormLayout(grp_tex)
        
        self.tex_paths = {
            "chassis_pattern": "",
            "titlebar_repeat": "",
            "knob": ""
        }
        self.tex_inputs = {}
        for k in ["chassis_pattern", "titlebar_repeat", "knob"]:
            row = QHBoxLayout()
            inp = QLineEdit()
            inp.setPlaceholderText(f"Optional {k}.png (seamless tile or knob)...")
            btn_browse = QPushButton("Browse...")
            btn_browse.clicked.connect(lambda checked, key=k, i=inp: self._browse_texture(key, i))
            row.addWidget(inp)
            row.addWidget(btn_browse)
            self.tex_inputs[k] = inp
            tex_form.addRow(k.replace("_", " ").title() + ":", row)

        layout.addWidget(grp_tex)

        # Save Button
        btn_save_theme = QPushButton("💾 Save & Activate Theme")
        btn_save_theme.setStyleSheet("font-weight: bold; padding: 6px; background-color: #0088cc; color: white;")
        btn_save_theme.clicked.connect(self._save_created_theme)
        layout.addWidget(btn_save_theme)

        scroll.setWidget(container)
        tab_layout = QVBoxLayout(self.tab_creator)
        tab_layout.addWidget(scroll)

    def _pick_creator_color(self, key, button):
        current_hex = self.creator_colors.get(key, "#ffffff")
        col = QColorDialog.getColor(QColor(current_hex), self, f"Pick Color for {key}")
        if col.isValid():
            new_hex = col.name()
            self.creator_colors[key] = new_hex
            button.setText(new_hex)
            button.setStyleSheet(f"background-color: {new_hex}; color: #ffffff; font-weight: bold; border: 1px solid #666;")

    def _browse_texture(self, key, input_field):
        fpath, _ = QFileDialog.getOpenFileName(self, f"Select {key} PNG Image", "", "PNG Images (*.png);;All Files (*)")
        if fpath:
            input_field.setText(fpath)
            self.tex_paths[key] = fpath

    def _save_created_theme(self):
        tid = self.create_id.text().strip().lower().replace(" ", "_")
        if not tid:
            QMessageBox.warning(self, "Invalid ID", "Please provide a valid Theme ID.")
            return

        theme_dict = {
            "id": tid,
            "name": self.create_name.text().strip() or tid,
            "author": self.create_author.text().strip() or "User",
            "version": "1.0.0",
            "description": self.create_desc.text().strip(),
            "colors": self.creator_colors,
            "textures": {}
        }

        texture_files = {k: inp.text().strip() for k, inp in self.tex_inputs.items() if inp.text().strip()}

        out_path = self.theme_mgr.save_custom_theme(theme_dict, texture_files=texture_files)
        self.refresh_installed_list()
        self.theme_mgr.set_theme(tid)
        QMessageBox.information(self, "Theme Created", f"Theme '{tid}' created and activated!\nLocation: {out_path}")

    # =========================================================================
    # TAB 4: GITHUB ACCOUNT & PUBLISHING
    # =========================================================================
    def _init_publish_tab(self):
        layout = QVBoxLayout(self.tab_publish)
        layout.setSpacing(8)

        # GitHub Login Section
        grp_auth = QGroupBox("GitHub Authentication")
        auth_layout = QVBoxLayout(grp_auth)

        self.lbl_auth_status = QLabel("Not connected to GitHub.")
        self.lbl_auth_status.setFont(QFont("Monospace", 8, QFont.Weight.Bold))
        auth_layout.addWidget(self.lbl_auth_status)

        token_row = QHBoxLayout()
        self.input_token = QLineEdit()
        self.input_token.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_token.setPlaceholderText("Paste GitHub Personal Access Token (PAT with 'gist' or 'repo' scope)...")
        token_row.addWidget(self.input_token)

        btn_connect = QPushButton("Connect")
        btn_connect.clicked.connect(self._connect_github)
        token_row.addWidget(btn_connect)

        btn_get_token = QPushButton("🔑 Get Token")
        btn_get_token.setToolTip("Open GitHub token creation page in browser")
        btn_get_token.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/settings/tokens/new?scopes=gist,repo&description=OmaAmp%20Theme%20Studio")))
        token_row.addWidget(btn_get_token)
        auth_layout.addLayout(token_row)

        layout.addWidget(grp_auth)

        # Publish Active Theme Section
        grp_pub = QGroupBox("Publish Active Theme to Community")
        pub_layout = QVBoxLayout(grp_pub)

        lbl_pub_info = QLabel("Share your currently active theme directly to GitHub Gists / Community Catalog:")
        lbl_pub_info.setFont(QFont("Monospace", 8))
        pub_layout.addWidget(lbl_pub_info)

        self.input_pub_desc = QLineEdit()
        self.input_pub_desc.setPlaceholderText("Short description or release notes for community...")
        pub_layout.addWidget(self.input_pub_desc)

        btn_publish = QPushButton("🚀 Publish Active Theme to GitHub")
        btn_publish.setStyleSheet("font-weight: bold; padding: 8px; background-color: #2ea44f; color: white;")
        btn_publish.clicked.connect(self._publish_active_theme)
        pub_layout.addWidget(btn_publish)

        # Output Gist URL & Share Box
        self.box_pub_result = QGroupBox("Published Theme Link")
        res_layout = QVBoxLayout(self.box_pub_result)
        self.input_share_url = QLineEdit()
        self.input_share_url.setReadOnly(True)
        res_layout.addWidget(self.input_share_url)

        btn_copy = QPushButton("📋 Copy Link")
        btn_copy.clicked.connect(self._copy_share_url)
        res_layout.addWidget(btn_copy)
        self.box_pub_result.setVisible(False)
        pub_layout.addWidget(self.box_pub_result)

        layout.addWidget(grp_pub)
        layout.addStretch()

        self._check_github_auth()

    def _check_github_auth(self):
        if self.github.token:
            prof = self.github.get_user_profile()
            if prof.get("authenticated"):
                self.lbl_auth_status.setText(f"✅ Connected as <b>@{prof.get('username')}</b> ({prof.get('name')})")
                self.lbl_auth_status.setStyleSheet("color: #00ff66;")
                self.input_token.setText(self.github.token)
                return
        self.lbl_auth_status.setText("❌ Not connected to GitHub.")
        self.lbl_auth_status.setStyleSheet("color: #ff5555;")

    def _connect_github(self):
        tok = self.input_token.text().strip()
        if not tok:
            QMessageBox.warning(self, "No Token", "Please enter a GitHub Personal Access Token.")
            return
        self.github.save_token(tok)
        prof = self.github.get_user_profile()
        if prof.get("authenticated"):
            self._check_github_auth()
            QMessageBox.information(self, "GitHub Connected", f"Successfully authenticated as @{prof.get('username')}!")
        else:
            QMessageBox.critical(self, "Auth Failed", f"Failed to authenticate with GitHub:\n{prof.get('error')}")

    def _publish_active_theme(self):
        if not self.github.token:
            QMessageBox.warning(self, "GitHub Login Required", "Please connect your GitHub account above before publishing.")
            return

        cur_theme = self.theme_mgr.current_theme
        desc = self.input_pub_desc.text().strip()
        
        res = self.github.publish_theme_to_gist(cur_theme, description=desc)
        if res.get("success"):
            gist_url = res.get("gist_url")
            raw_url = res.get("raw_url")
            self.input_share_url.setText(raw_url or gist_url)
            self.box_pub_result.setVisible(True)
            QMessageBox.information(
                self, "Published Successfully! 🎉",
                f"Theme '{cur_theme.get('name')}' is now live on GitHub!\n\nLink:\n{gist_url}"
            )
        else:
            QMessageBox.critical(self, "Publish Error", f"Failed to publish theme:\n{res.get('error')}")

    def _copy_share_url(self):
        url = self.input_share_url.text().strip()
        if url:
            from PyQt6.QtWidgets import QApplication
            QApplication.clipboard().setText(url)
            QMessageBox.information(self, "Copied", "Theme link copied to clipboard!")

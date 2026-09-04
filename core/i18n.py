import os
import locale
from PyQt6.QtCore import QObject, pyqtSignal

TRANSLATIONS = {
    "en": {
        # Main Player
        "app_title": "OMAAMP - WINAMP 2.91 CLASSIC",
        "btn_skin": "SKIN",
        "btn_skin_tip": "Change or Create Theme",
        "btn_vis": "VIS",
        "btn_vis_tip": "Open Visualizer Studio (Fullscreen / Multi-mode)",
        "btn_radio": "RADIO",
        "btn_radio_tip": "Open Online Radio & YouTube Stream Studio",
        "btn_prev_tip": "Previous Track",
        "btn_play_tip": "Play",
        "btn_pause_tip": "Pause",
        "btn_stop_tip": "Stop",
        "btn_next_tip": "Next Track",
        "btn_eject_tip": "Open / Eject Audio Files",
        "btn_shuf": "SHUF",
        "btn_shuf_tip": "Toggle Shuffle Mode",
        "btn_rep": "REP",
        "btn_rep_tip": "Toggle Repeat Mode",
        "btn_eq": "EQ",
        "btn_eq_tip": "Toggle Equalizer Deck",
        "btn_pl": "PL",
        "btn_pl_tip": "Toggle Playlist Deck",
        "lbl_vol": "VOL",
        "lbl_bal": "BAL",
        "lbl_seek": "SEEK",
        "lcd_ready": "OMAAMP - READY",
        "lcd_tip": "Click time digits to toggle Elapsed / Remaining time",

        # Equalizer
        "eq_title": "WINAMP EQUALIZER",
        "eq_on": "ON",
        "eq_zero": "ZERO",
        "eq_preamp": "PREAMP",
        "eq_presets": "Presets",

        # Playlist Window
        "pl_title": "WINAMP PLAYLIST",
        "pl_tracks": "tracks",
        "pl_btn_add": "+ ADD",
        "pl_btn_rem": "- REM",
        "pl_btn_sel": "SEL",
        "pl_btn_misc": "MISC",
        "pl_btn_list": "LIST",
        "pl_menu_add_files": "➕ Add File(s)...",
        "pl_menu_add_folder": "📁 Add Folder of Music...",
        "pl_menu_add_url": "🌐 Add Online Stream / URL...",
        "pl_menu_open_radio": "📻 Open Radio & YouTube Studio...",
        "pl_menu_rem_sel": "➖ Remove Selected",
        "pl_menu_crop": "✂️ Crop (Keep Only Selected)",
        "pl_menu_clear": "🗑️ Clear Entire Playlist",
        "pl_menu_sel_all": "Select All",
        "pl_menu_sel_none": "Select None",
        "pl_menu_sel_inv": "Invert Selection",
        "pl_menu_sort_title": "🔤 Sort by Track Title",
        "pl_menu_sort_file": "📄 Sort by Filename",
        "pl_menu_shuf": "🔀 Randomize / Shuffle Order",
        "pl_menu_reverse": "🔄 Reverse Order",
        "pl_menu_save_m3u": "💾 Save Playlist (.m3u)...",
        "pl_menu_load_m3u": "📂 Load Playlist (.m3u)...",
        "pl_menu_new_pl": "✨ New Playlist",
        "pl_play_this": "▶ Play This Track",
        "pl_search_placeholder": "Search playlist tracks...",

        # Radio & YouTube Studio
        "radio_window_title": "OmaAmp Online Radio & YouTube Stream Studio",
        "radio_header": "📻 OMAAMP RADIO & YOUTUBE STREAM STUDIO",
        "radio_tab_curated": "📻 Curated Stations",
        "radio_tab_browser": "🌐 Radio Browser (30k+)",
        "radio_tab_youtube": "📺 YouTube Streams",
        "radio_tab_favorites": "⭐ Favorites & Custom",
        "radio_all_stations": "⭐ All Stations",
        "radio_btn_play": "▶ Play Now",
        "radio_btn_add_pl": "➕ Add to Playlist",
        "radio_btn_star": "⭐ Star / Favorite",
        "radio_btn_visit": "🌐 Visit Web",
        "radio_search_placeholder": "Search 30,000+ stations worldwide (e.g. synthwave, sweden, trance, jazz, bbc)...",
        "radio_yt_input_placeholder": "Paste YouTube Playlist URL (https://www.youtube.com/playlist?list=...) or search query...",
        "radio_yt_btn_load": "🔍 Load Playlist / Search",
        "radio_yt_btn_play_all": "▶ Play Entire Playlist",
        "radio_yt_btn_add_all": "➕ Add All to Active Playlist",
        "radio_yt_btn_save": "💾 Save Playlist to Library",
        "radio_fav_title": "⭐ Starred Stations & Saved YouTube Playlists:",
        "radio_custom_title": "➕ Add Custom Online Radio Stream URL",
        "radio_custom_name": "Station Name:",
        "radio_custom_url": "Stream URL:",
        "radio_custom_genre": "Genre / Tag:",
        "radio_btn_save_custom": "💾 Save Custom Stream",
        "btn_close": "Close",

        # Theme Studio
        "theme_window_title": "OmaAmp Theme Studio & GitHub Hub",
        "theme_header": "OMAAMP THEME ENGINE & GITHUB HUB",
        "theme_tab_installed": "🎨 Installed Themes",
        "theme_tab_community": "🌐 GitHub Community",
        "theme_tab_creator": "✨ Theme Creator",
        "theme_tab_publish": "🚀 Publish & Share",
        "theme_btn_apply": "▶ Apply Theme",
        "theme_btn_export": "📦 Export Package (.omaamp-theme)",
        "theme_btn_import": "📁 Import File...",
        "theme_search_placeholder": "Search GitHub community themes (e.g. cyberpunk, retro, titanium)...",
        "theme_direct_url_placeholder": "Or paste direct GitHub repo URL (https://github.com/user/repo) / raw JSON URL...",
        "theme_btn_install_url": "📥 Install URL",
        "theme_btn_download_github": "⬇️ Download & Install Theme from GitHub",
        "theme_save_and_activate": "💾 Save & Activate Theme",

        # Visualizer Studio
        "vis_studio_title": "OmaAmp Visualizer Studio",
        "vis_btn_fullscreen": "⛶ Toggle Fullscreen (F11)",
        "vis_mode_spectrum": "Spectrum Analyzer (24-Band FFT)",
        "vis_mode_oscilloscope": "Laser Oscilloscope (Real PCM)",
        "vis_mode_vu": "Dual Analog VU Meters (Real RMS)",
        "vis_mode_starfield": "3D Warp Starfield (Bass Reactive)",
        "vis_mode_matrix": "Matrix Digital Rain (Tempo Reactive)",
        "vis_mode_ring": "Polar Frequency Ring (360° FFT)"
    },
    "sv": {
        # Main Player
        "app_title": "OMAAMP - WINAMP 2.91 CLASSIC",
        "btn_skin": "TEMA",
        "btn_skin_tip": "Byt eller skapa tema",
        "btn_vis": "VIS",
        "btn_vis_tip": "Öppna Visualizer Studio (Fullskärm / Flera lägen)",
        "btn_radio": "RADIO",
        "btn_radio_tip": "Öppna Webradio & YouTube-strömmar",
        "btn_prev_tip": "Föregående spår",
        "btn_play_tip": "Spela",
        "btn_pause_tip": "Pausa",
        "btn_stop_tip": "Stoppa",
        "btn_next_tip": "Nästa spår",
        "btn_eject_tip": "Öppna / mata ut ljudfiler",
        "btn_shuf": "BLAND",
        "btn_shuf_tip": "Slumpmässig ordning (Shuffle)",
        "btn_rep": "REP",
        "btn_rep_tip": "Repetera spellista",
        "btn_eq": "EQ",
        "btn_eq_tip": "Visa/dölj Equalizer",
        "btn_pl": "PL",
        "btn_pl_tip": "Visa/dölj Spellista",
        "lbl_vol": "VOL",
        "lbl_bal": "BAL",
        "lbl_seek": "SÖK",
        "lcd_ready": "OMAAMP - REDO",
        "lcd_tip": "Klicka på siffrorna för att växla mellan förfluten och återstående tid",

        # Equalizer
        "eq_title": "WINAMP EQUALIZER",
        "eq_on": "PÅ",
        "eq_zero": "NOLL",
        "eq_preamp": "FÖRFÖRST",
        "eq_presets": "Förinställningar",

        # Playlist Window
        "pl_title": "WINAMP SPELLISTA",
        "pl_tracks": "spår",
        "pl_btn_add": "+ LÄGG TILL",
        "pl_btn_rem": "- TA BORT",
        "pl_btn_sel": "MARKERA",
        "pl_btn_misc": "DIVERSE",
        "pl_btn_list": "LISTA",
        "pl_menu_add_files": "➕ Lägg till fil(er)...",
        "pl_menu_add_folder": "📁 Lägg till musikmapp...",
        "pl_menu_add_url": "🌐 Lägg till webbström / URL...",
        "pl_menu_open_radio": "📻 Öppna Radio & YouTube Studio...",
        "pl_menu_rem_sel": "➖ Ta bort markerade",
        "pl_menu_crop": "✂️ Beskär (Behåll endast markerade)",
        "pl_menu_clear": "🗑️ Rensa hela spellistan",
        "pl_menu_sel_all": "Markera alla",
        "pl_menu_sel_none": "Avmarkera alla",
        "pl_menu_sel_inv": "Invertera markering",
        "pl_menu_sort_title": "🔤 Sortera efter titel",
        "pl_menu_sort_file": "📄 Sortera efter filnamn",
        "pl_menu_shuf": "🔀 Slumpa ordning",
        "pl_menu_reverse": "🔄 Omvänd ordning",
        "pl_menu_save_m3u": "💾 Spara spellista (.m3u)...",
        "pl_menu_load_m3u": "📂 Ladda spellista (.m3u)...",
        "pl_menu_new_pl": "✨ Ny spellista",
        "pl_play_this": "▶ Spela detta spår",
        "pl_search_placeholder": "Sök bland spår i spellistan...",

        # Radio & YouTube Studio
        "radio_window_title": "OmaAmp Webradio & YouTube Studio",
        "radio_header": "📻 OMAAMP WEBRADIO & YOUTUBE STREAM STUDIO",
        "radio_tab_curated": "📻 Utvalda Stationer",
        "radio_tab_browser": "🌐 Radio Browser (30k+)",
        "radio_tab_youtube": "📺 YouTube-strömmar",
        "radio_tab_favorites": "⭐ Favoriter & Egna",
        "radio_all_stations": "⭐ Alla Stationer",
        "radio_btn_play": "▶ Spela nu",
        "radio_btn_add_pl": "➕ Lägg till i spellista",
        "radio_btn_star": "⭐ Stjärnmärk favorit",
        "radio_btn_visit": "🌐 Besök webbplats",
        "radio_search_placeholder": "Sök bland 30 000+ radiostationer (t.ex. synthwave, sweden, trance, jazz, p3)...",
        "radio_yt_input_placeholder": "Klistra in YouTube-spellistelänk (https://www.youtube.com/playlist?list=...) eller sökfras...",
        "radio_yt_btn_load": "🔍 Ladda spellista / Sök",
        "radio_yt_btn_play_all": "▶ Spela hela spellistan",
        "radio_yt_btn_add_all": "➕ Lägg till alla i spellistan",
        "radio_yt_btn_save": "💾 Spara spellista till bibliotek",
        "radio_fav_title": "⭐ Sparade favoritstationer & YouTube-spellistor:",
        "radio_custom_title": "➕ Lägg till egen radioströmnings-URL",
        "radio_custom_name": "Stationsnamn:",
        "radio_custom_url": "Strömnings-URL:",
        "radio_custom_genre": "Genre / Tag:",
        "radio_btn_save_custom": "💾 Spara egen radioström",
        "btn_close": "Stäng",

        # Theme Studio
        "theme_window_title": "OmaAmp Temastudio & GitHub Hub",
        "theme_header": "OMAAMP TEMA-MOTOR & GITHUB HUB",
        "theme_tab_installed": "🎨 Installerade Teman",
        "theme_tab_community": "🌐 GitHub Community",
        "theme_tab_creator": "✨ Skapa Tema",
        "theme_tab_publish": "🚀 Publicera & Dela",
        "theme_btn_apply": "▶ Aktivera tema",
        "theme_btn_export": "📦 Exportera paket (.omaamp-theme)",
        "theme_btn_import": "📁 Importera fil...",
        "theme_search_placeholder": "Sök community-teman på GitHub (t.ex. cyberpunk, retro, titanium)...",
        "theme_direct_url_placeholder": "Eller klistra in direkt GitHub-länk (https://github.com/user/repo) / raw JSON...",
        "theme_btn_install_url": "📥 Installera från URL",
        "theme_btn_download_github": "⬇️ Ladda ner & installera från GitHub",
        "theme_save_and_activate": "💾 Spara & aktivera tema",

        # Visualizer Studio
        "vis_studio_title": "OmaAmp Visualizer Studio",
        "vis_btn_fullscreen": "⛶ Fullskärmsläge (F11)",
        "vis_mode_spectrum": "Spektrumanalysator (24-bands FFT)",
        "vis_mode_oscilloscope": "Laser-oscilloskop (Realtids-PCM)",
        "vis_mode_vu": "Dubbla analoga VU-mätare (RMS)",
        "vis_mode_starfield": "3D Warp-stjärnfält (Basreaktivt)",
        "vis_mode_matrix": "Matrix Digital Rain (Temporeaktivt)",
        "vis_mode_ring": "Polär frekvensring (360° FFT)"
    }
}


class I18nManager(QObject):
    language_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.current_lang = self._detect_default_language()

    def _detect_default_language(self):
        lang_env = os.environ.get("LANG", "").lower()
        if "sv" in lang_env or "se" in lang_env:
            return "sv"
        try:
            loc = locale.getdefaultlocale()[0]
            if loc and ("sv" in loc.lower() or "swedish" in loc.lower()):
                return "sv"
        except Exception:
            pass
        return "en"

    def set_language(self, lang_code):
        if lang_code in TRANSLATIONS and lang_code != self.current_lang:
            self.current_lang = lang_code
            self.language_changed.emit(self.current_lang)

    def get_language(self):
        return self.current_lang

    def get_available_languages(self):
        return [
            ("sv", "Svenska (Swedish)"),
            ("en", "English")
        ]

    def t(self, key, default=None, **kwargs):
        lang_dict = TRANSLATIONS.get(self.current_lang, TRANSLATIONS["en"])
        val = lang_dict.get(key)
        if val is None:
            val = TRANSLATIONS["en"].get(key, default or key)
        if kwargs:
            try:
                return val.format(**kwargs)
            except Exception:
                return val
        return val


# Global Singleton Instance
i18n = I18nManager()


def _(key, default=None, **kwargs):
    return i18n.t(key, default, **kwargs)


def t(key, default=None, **kwargs):
    return i18n.t(key, default, **kwargs)

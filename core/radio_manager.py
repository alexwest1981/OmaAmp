import os
import json
import urllib.request
import urllib.parse
import threading
import yt_dlp
from PyQt6.QtCore import QObject, pyqtSignal

RADIO_CONFIG_FILE = os.path.expanduser("~/.config/omaamp/radio_stations.json")

# Curated High-Quality Stations
CURATED_STATIONS = {
    "SomaFM": [
        {
            "id": "somafm_groovesalad",
            "name": "SomaFM: Groove Salad",
            "genre": "Ambient / Downtempo",
            "url": "https://ice1.somafm.com/groovesalad-128-mp3",
            "bitrate": 128,
            "codec": "MP3",
            "homepage": "https://somafm.com/groovesalad/",
            "description": "A nicely chilled plate of ambient/downtempo beats and grooves."
        },
        {
            "id": "somafm_defcon",
            "name": "SomaFM: DEF CON Radio",
            "genre": "Hacker / Chillout",
            "url": "https://ice1.somafm.com/defcon-128-mp3",
            "bitrate": 128,
            "codec": "MP3",
            "homepage": "https://somafm.com/defcon/",
            "description": "Music for Hacking. The year-round channel of DEF CON."
        },
        {
            "id": "somafm_dronezone",
            "name": "SomaFM: Drone Zone",
            "genre": "Atmospheric Space",
            "url": "https://ice1.somafm.com/dronezone-128-mp3",
            "bitrate": 128,
            "codec": "MP3",
            "homepage": "https://somafm.com/dronezone/",
            "description": "Served best chilled, safe with most medications. Atmospheric ambient space music."
        },
        {
            "id": "somafm_spacestation",
            "name": "SomaFM: Space Station Soma",
            "genre": "Space Ambient",
            "url": "https://ice1.somafm.com/spacestation-128-mp3",
            "bitrate": 128,
            "codec": "MP3",
            "homepage": "https://somafm.com/spacestation/",
            "description": "Tune in, turn on, space out. Spaced-out ambient and mid-tempo electronica."
        },
        {
            "id": "somafm_secretagent",
            "name": "SomaFM: Secret Agent",
            "genre": "Spy / Lounge",
            "url": "https://ice1.somafm.com/secretagent-128-mp3",
            "bitrate": 128,
            "codec": "MP3",
            "homepage": "https://somafm.com/secretagent/",
            "description": "The soundtrack for your stylish, mysterious, dangerous life."
        },
        {
            "id": "somafm_u80s",
            "name": "SomaFM: Underground 80s",
            "genre": "Synthpop / New Wave",
            "url": "https://ice1.somafm.com/u80s-128-mp3",
            "bitrate": 128,
            "codec": "MP3",
            "homepage": "https://somafm.com/u80s/",
            "description": "Early 80s UK Synthpop and a bit of Post-Punk."
        },
        {
            "id": "somafm_lush",
            "name": "SomaFM: Lush",
            "genre": "Sensuous Vocals",
            "url": "https://ice1.somafm.com/lush-128-mp3",
            "bitrate": 128,
            "codec": "MP3",
            "homepage": "https://somafm.com/lush/",
            "description": "Sensuous and mellow vocals, mostly female, with an electronic influence."
        },
        {
            "id": "somafm_beatblender",
            "name": "SomaFM: Beat Blender",
            "genre": "Deep House / Chill",
            "url": "https://ice1.somafm.com/beatblender-128-mp3",
            "bitrate": 128,
            "codec": "MP3",
            "homepage": "https://somafm.com/beatblender/",
            "description": "A late-night blend of deep-house and downtempo chill."
        }
    ],
    "Sveriges Radio": [
        {
            "id": "sr_p1",
            "name": "Sveriges Radio P1",
            "genre": "News / Talk / Culture",
            "url": "https://sverigesradio.se/topsy/direkt/srapi/132.mp3",
            "bitrate": 192,
            "codec": "MP3",
            "homepage": "https://sverigesradio.se/p1",
            "description": "Den talade kanalen för fördjupning, samhälle, nyheter och kultur."
        },
        {
            "id": "sr_p2",
            "name": "Sveriges Radio P2",
            "genre": "Classical / Jazz / Folk",
            "url": "https://sverigesradio.se/topsy/direkt/srapi/163.mp3",
            "bitrate": 192,
            "codec": "MP3",
            "homepage": "https://sverigesradio.se/p2",
            "description": "Klassisk musik, jazz, folkmusik och samtida konstmusik dygnet runt."
        },
        {
            "id": "sr_p3",
            "name": "Sveriges Radio P3",
            "genre": "Pop / Urban / Electronic",
            "url": "https://sverigesradio.se/topsy/direkt/srapi/164.mp3",
            "bitrate": 192,
            "codec": "MP3",
            "homepage": "https://sverigesradio.se/p3",
            "description": "Den bästa musiken, populärkultur, humor och nyheter för unga vuxna."
        },
        {
            "id": "sr_p4_sthlm",
            "name": "Sveriges Radio P4 Stockholm",
            "genre": "Local News / Hits",
            "url": "https://sverigesradio.se/topsy/direkt/srapi/701.mp3",
            "bitrate": 192,
            "codec": "MP3",
            "homepage": "https://sverigesradio.se/stockholm",
            "description": "Lokalradio för Storstockholm med musik, nyheter och underhållning."
        },
        {
            "id": "sr_dingata",
            "name": "Sveriges Radio P3 Din Gata",
            "genre": "Hip Hop / R&B",
            "url": "https://sverigesradio.se/topsy/direkt/srapi/2576.mp3",
            "bitrate": 192,
            "codec": "MP3",
            "homepage": "https://sverigesradio.se/p3dingata",
            "description": "Hiphop, RnB och den senaste urbana musiken."
        }
    ],
    "Synthwave & Lofi": [
        {
            "id": "nightwave_plaza",
            "name": "Nightwave Plaza",
            "genre": "Vaporwave / Future Funk",
            "url": "https://radio.plaza.one/mp3",
            "bitrate": 128,
            "codec": "MP3",
            "homepage": "https://plaza.one/",
            "description": "The 24/7 online Vaporwave and Future Funk radio station."
        },
        {
            "id": "synthwave_city_fm",
            "name": "Synthwave Radio (RetroWave)",
            "genre": "Synthwave / Outrun",
            "url": "http://stream.zeno.fm/f3wvbbqmdg8uv",
            "bitrate": 128,
            "codec": "MP3",
            "homepage": "https://synthwaveradio.com/",
            "description": "Pure 80s nostalgic synthwave, darksynth, and outrun music."
        },
        {
            "id": "lofi_girl_radio",
            "name": "Lofi 24/7 Chill Beats",
            "genre": "Lofi Hip Hop",
            "url": "https://play.streamafrica.net/lofiradio",
            "bitrate": 128,
            "codec": "MP3",
            "homepage": "https://lofigirl.com/",
            "description": "Relaxing lofi hip hop beats to study/chill/code to."
        }
    ],
    "Electronic & Trance": [
        {
            "id": "di_vocal_trance",
            "name": "Digitally Imported: Vocal Trance",
            "genre": "Vocal Trance",
            "url": "https://pub0101.rockradio.com/vocaltrance_aac",
            "bitrate": 128,
            "codec": "AAC",
            "homepage": "https://www.di.fm/vocaltrance",
            "description": "Melodic, uplifting trance paired with angelic vocals."
        },
        {
            "id": "defected_radio",
            "name": "Defected Radio Live",
            "genre": "House / Deep House",
            "url": "https://stream.zeno.fm/k2222z8e3v8uv",
            "bitrate": 128,
            "codec": "MP3",
            "homepage": "https://defected.com/",
            "description": "World-leading house music label broadcasting 24/7."
        }
    ],
    "Rock & Metal": [
        {
            "id": "classic_rock_florida",
            "name": "Classic Rock Florida",
            "genre": "Classic Rock",
            "url": "http://stream.zeno.fm/c3g4z2u5u08uv",
            "bitrate": 128,
            "codec": "MP3",
            "homepage": "https://classicrockflorida.com/",
            "description": "Greatest classic rock tracks from the 60s, 70s, and 80s."
        },
        {
            "id": "metal_rock_100",
            "name": "100 Heavy Metal Radio",
            "genre": "Heavy Metal / Hard Rock",
            "url": "http://stream.zeno.fm/462s78d5u08uv",
            "bitrate": 128,
            "codec": "MP3",
            "homepage": "https://metalradio.com/",
            "description": "Non-stop heavy metal, thrash, power metal, and hard rock."
        }
    ],
    "Jazz & Classical": [
        {
            "id": "wbgo_jazz",
            "name": "WBGO Jazz 88.3 FM",
            "genre": "Jazz / Bebop / Blues",
            "url": "https://wbgo.streamguys1.com/wbgo128",
            "bitrate": 128,
            "codec": "MP3",
            "homepage": "https://www.wbgo.org/",
            "description": "The world's premier jazz radio station broadcasting live from Newark/NYC."
        },
        {
            "id": "swiss_jazz",
            "name": "Radio Swiss Jazz",
            "genre": "Smooth Jazz / Swing",
            "url": "https://stream.srg-ssr.ch/m/rsj/mp3_128",
            "bitrate": 128,
            "codec": "MP3",
            "homepage": "https://www.radioswissjazz.ch/",
            "description": "Commercial-free jazz, soul, and blues standards 24 hours a day."
        },
        {
            "id": "kusc_classical",
            "name": "Classical KUSC 91.5 FM",
            "genre": "Classical / Symphony",
            "url": "https://kusc.streamguys1.com/kusc-mp3-128",
            "bitrate": 128,
            "codec": "MP3",
            "homepage": "https://www.kusc.org/",
            "description": "Listener-supported classical music station based in Los Angeles."
        }
    ]
}


class RadioManager(QObject):
    stations_updated = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.favorites = []
        self.custom_stations = []
        self.saved_youtube_playlists = []
        self.youtube_cache = {}  # video_id / url -> direct audio stream url
        
        self.load_state()

    # -------------------------------------------------------------------------
    # State Persistence
    # -------------------------------------------------------------------------
    def load_state(self):
        if os.path.exists(RADIO_CONFIG_FILE):
            try:
                with open(RADIO_CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.favorites = data.get("favorites", [])
                    self.custom_stations = data.get("custom_stations", [])
                    self.saved_youtube_playlists = data.get("youtube_playlists", [])
            except Exception as e:
                print(f"Error loading radio config: {e}")

    def save_state(self):
        os.makedirs(os.path.dirname(RADIO_CONFIG_FILE), exist_ok=True)
        data = {
            "favorites": self.favorites,
            "custom_stations": self.custom_stations,
            "youtube_playlists": self.saved_youtube_playlists
        }
        try:
            with open(RADIO_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            self.stations_updated.emit()
        except Exception as e:
            print(f"Error saving radio config: {e}")

    # -------------------------------------------------------------------------
    # Curated & Built-in Catalogs
    # -------------------------------------------------------------------------
    def get_categories(self):
        return list(CURATED_STATIONS.keys())

    def get_curated_stations(self, category=None):
        if category and category in CURATED_STATIONS:
            return CURATED_STATIONS[category]
        all_st = []
        for cat, items in CURATED_STATIONS.items():
            for item in items:
                st = item.copy()
                st["category"] = cat
                all_st.append(st)
        return all_st

    # -------------------------------------------------------------------------
    # Radio Browser API (Global Directory of 30,000+ stations)
    # -------------------------------------------------------------------------
    def search_radio_browser(self, name_query="", tag="", country="", limit=50):
        """Searches the public Radio Browser API with name, genre tag, or country."""
        base_url = "https://de1.api.radio-browser.info/json/stations/search?"
        params = {"limit": str(limit), "order": "votes", "reverse": "true"}
        if name_query:
            params["name"] = name_query
        if tag:
            params["tag"] = tag
        if country:
            params["country"] = country

        url = base_url + urllib.parse.urlencode(params)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "OmaAmp/1.0"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                results = []
                for item in data:
                    stream_url = item.get("url_resolved") or item.get("url")
                    if stream_url:
                        results.append({
                            "id": item.get("stationuuid", ""),
                            "name": item.get("name", "Unknown Station").strip(),
                            "genre": item.get("tags", "Radio"),
                            "url": stream_url,
                            "bitrate": item.get("bitrate", 128),
                            "codec": item.get("codec", "MP3"),
                            "country": item.get("country", ""),
                            "homepage": item.get("homepage", ""),
                            "votes": item.get("votes", 0)
                        })
                return results
        except Exception as e:
            print(f"Radio Browser search error: {e}")
            return []

    # -------------------------------------------------------------------------
    # YouTube Integration via yt-dlp
    # -------------------------------------------------------------------------
    def parse_youtube_url(self, url_or_query):
        """
        Parses a YouTube playlist URL, video URL, or search query.
        Returns dict: {"is_playlist": bool, "title": str, "tracks": [...]}
        """
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': 'in_playlist',
            'skip_download': True
        }

        # Check if plain search query
        query = url_or_query.strip()
        if not (query.startswith("http://") or query.startswith("https://") or "youtube.com" in query or "youtu.be" in query):
            query = f"ytsearch20:{query}"

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(query, download=False)
                if not info:
                    return {"is_playlist": False, "title": "No results", "tracks": []}

                is_playlist = 'entries' in info
                title = info.get('title', 'YouTube Playlist')

                tracks = []
                if is_playlist:
                    entries = info.get('entries', [])
                    for entry in entries:
                        if not entry:
                            continue
                        v_id = entry.get('id', '')
                        v_url = entry.get('url') or f"https://www.youtube.com/watch?v={v_id}"
                        tracks.append({
                            "id": v_id,
                            "url": v_url,
                            "title": entry.get('title', 'Unknown Title'),
                            "artist": entry.get('uploader') or entry.get('channel') or "YouTube",
                            "duration": float(entry.get('duration') or 0.0),
                            "thumbnail": entry.get('thumbnail') or ""
                        })
                else:
                    v_id = info.get('id', '')
                    v_url = info.get('webpage_url') or f"https://www.youtube.com/watch?v={v_id}"
                    tracks.append({
                        "id": v_id,
                        "url": v_url,
                        "title": info.get('title', 'Unknown Title'),
                        "artist": info.get('uploader') or info.get('channel') or "YouTube",
                        "duration": float(info.get('duration') or 0.0),
                        "thumbnail": info.get('thumbnail') or ""
                    })

                return {
                    "is_playlist": is_playlist,
                    "title": title,
                    "tracks": tracks
                }
        except Exception as e:
            print(f"Error extracting YouTube info: {e}")
            return {"is_playlist": False, "title": f"Error: {e}", "tracks": []}

    def resolve_youtube_audio_url(self, video_url_or_id):
        """Extracts the direct streaming audio URL for a YouTube video using yt-dlp."""
        url = video_url_or_id
        if not (url.startswith("http://") or url.startswith("https://")):
            url = f"https://www.youtube.com/watch?v={video_url_or_id}"

        if url in self.youtube_cache:
            return self.youtube_cache[url]

        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'skip_download': True
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                audio_url = info.get('url')
                if audio_url:
                    self.youtube_cache[url] = audio_url
                    return audio_url
        except Exception as e:
            print(f"Error resolving YouTube stream URL for {url}: {e}")
        return url

    # -------------------------------------------------------------------------
    # Favorites & Custom Management
    # -------------------------------------------------------------------------
    def is_favorite(self, station_url):
        return any(f.get("url") == station_url for f in self.favorites)

    def toggle_favorite(self, station_dict):
        url = station_dict.get("url")
        if not url:
            return False

        existing = next((f for f in self.favorites if f.get("url") == url), None)
        if existing:
            self.favorites.remove(existing)
            is_fav = False
        else:
            self.favorites.append(station_dict)
            is_fav = True

        self.save_state()
        return is_fav

    def add_custom_station(self, name, url, genre="Custom", bitrate=128):
        st = {
            "id": f"custom_{len(self.custom_stations) + 1}",
            "name": name.strip(),
            "url": url.strip(),
            "genre": genre.strip() or "Custom",
            "bitrate": bitrate,
            "codec": "Stream",
            "is_custom": True
        }
        self.custom_stations.append(st)
        self.save_state()
        return st

    def remove_custom_station(self, index):
        if 0 <= index < len(self.custom_stations):
            self.custom_stations.pop(index)
            self.save_state()

    def save_youtube_playlist(self, title, url, tracks):
        pl_entry = {
            "title": title,
            "url": url,
            "tracks_count": len(tracks),
            "tracks": tracks
        }
        # Check if already exists
        existing = next((p for p in self.saved_youtube_playlists if p.get("url") == url), None)
        if existing:
            self.saved_youtube_playlists.remove(existing)
        self.saved_youtube_playlists.append(pl_entry)
        self.save_state()
        return pl_entry

    def remove_youtube_playlist(self, index):
        if 0 <= index < len(self.saved_youtube_playlists):
            self.saved_youtube_playlists.pop(index)
            self.save_state()

import os
import json
import random
import pygame
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
import mutagen

PLAYLIST_FILE = os.path.expanduser("~/.config/omaamp/playlist.json")

class Track:
    def __init__(self, filepath):
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.title = os.path.splitext(self.filename)[0]
        self.artist = "Unknown Artist"
        self.album = ""
        self.duration = 0.0
        self.bitrate = 128
        self.samplerate = 44100
        self.channels = 2
        self.load_metadata()

    def load_metadata(self):
        if not os.path.exists(self.filepath):
            return
        try:
            audio = mutagen.File(self.filepath)
            if audio is not None:
                if hasattr(audio.info, 'length'):
                    self.duration = float(audio.info.length)
                if hasattr(audio.info, 'bitrate'):
                    self.bitrate = int(audio.info.bitrate / 1000)
                if hasattr(audio.info, 'sample_rate'):
                    self.samplerate = int(audio.info.sample_rate)
                if hasattr(audio.info, 'channels'):
                    self.channels = int(audio.info.channels)

                tags = audio.tags
                if tags:
                    title = tags.get("TIT2") or tags.get("title")
                    artist = tags.get("TPE1") or tags.get("artist")
                    album = tags.get("TALB") or tags.get("album")
                    
                    if title:
                        self.title = str(title[0] if isinstance(title, list) else title)
                    if artist:
                        self.artist = str(artist[0] if isinstance(artist, list) else artist)
                    if album:
                        self.album = str(album[0] if isinstance(album, list) else album)
        except Exception:
            pass

    @property
    def display_name(self):
        if self.artist and self.artist != "Unknown Artist":
            return f"{self.artist} - {self.title}"
        return self.title

    @property
    def duration_formatted(self):
        mins = int(self.duration // 60)
        secs = int(self.duration % 60)
        return f"{mins}:{secs:02d}"


class AudioEngine(QObject):
    track_changed = pyqtSignal(object)
    playback_state_changed = pyqtSignal(bool)
    position_changed = pyqtSignal(float)
    playlist_updated = pyqtSignal()
    volume_changed = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
        except Exception as e:
            print(f"Error initializing pygame.mixer: {e}")

        self.playlist = []
        self.current_index = -1
        self.is_playing = False
        self.is_paused = False
        self.volume = 80
        self.balance = 0
        self.shuffle = False
        self.repeat = True
        self.current_position = 0.0
        self.seek_offset = 0.0

        # Position poll timer
        self.pos_timer = QTimer(self)
        self.pos_timer.setInterval(200)
        self.pos_timer.timeout.connect(self._update_position)

        # Restore saved playlist state on startup
        self.load_playlist_state()

    def set_volume(self, val):
        self.volume = max(0, min(100, val))
        try:
            pygame.mixer.music.set_volume(self.volume / 100.0)
        except Exception:
            pass
        self.volume_changed.emit(self.volume)

    def add_files(self, filepaths):
        added = False
        valid_exts = {".mp3", ".flac", ".ogg", ".wav", ".m4a", ".aac", ".opus", ".mod", ".xm", ".s3m", ".it"}
        for fpath in filepaths:
            if os.path.isfile(fpath):
                ext = os.path.splitext(fpath)[1].lower()
                if ext in valid_exts:
                    self.playlist.append(Track(fpath))
                    added = True
                elif ext in {".m3u", ".m3u8"}:
                    self.load_m3u(fpath)
                    added = True
            elif os.path.isdir(fpath):
                for root, _, files in os.walk(fpath):
                    for fname in sorted(files):
                        ext = os.path.splitext(fname)[1].lower()
                        if ext in valid_exts:
                            self.playlist.append(Track(os.path.join(root, fname)))
                            added = True
        if added:
            self.playlist_updated.emit()
            if self.current_index == -1 and len(self.playlist) > 0:
                self.current_index = 0
                if self.current_track:
                    self.track_changed.emit(self.current_track)
            self.save_playlist_state()

    def play_index(self, index):
        if 0 <= index < len(self.playlist):
            self.current_index = index
            track = self.playlist[self.current_index]
            try:
                pygame.mixer.music.load(track.filepath)
                pygame.mixer.music.set_volume(self.volume / 100.0)
                pygame.mixer.music.play()
                self.is_playing = True
                self.is_paused = False
                self.seek_offset = 0.0
                self.current_position = 0.0
                self.pos_timer.start()
                self.track_changed.emit(track)
                self.playback_state_changed.emit(True)
                self.save_playlist_state()
            except Exception as e:
                print(f"Error playing track {track.filepath}: {e}")
                self.next_track()

    def play(self):
        if self.is_paused:
            pygame.mixer.music.unpause()
            self.is_playing = True
            self.is_paused = False
            self.pos_timer.start()
            self.playback_state_changed.emit(True)
        elif self.playlist:
            if self.current_index == -1:
                self.current_index = 0
            self.play_index(self.current_index)

    def pause(self):
        if self.is_playing:
            pygame.mixer.music.pause()
            self.is_playing = False
            self.is_paused = True
            self.pos_timer.stop()
            self.playback_state_changed.emit(False)
        elif self.is_paused:
            self.play()

    def stop(self):
        pygame.mixer.music.stop()
        self.is_playing = False
        self.is_paused = False
        self.current_position = 0.0
        self.seek_offset = 0.0
        self.pos_timer.stop()
        self.position_changed.emit(0.0)
        self.playback_state_changed.emit(False)

    def next_track(self):
        if not self.playlist:
            return
        if self.shuffle and len(self.playlist) > 1:
            next_idx = random.randint(0, len(self.playlist) - 1)
            while next_idx == self.current_index:
                next_idx = random.randint(0, len(self.playlist) - 1)
            self.play_index(next_idx)
        else:
            if self.current_index + 1 < len(self.playlist):
                self.play_index(self.current_index + 1)
            elif self.repeat:
                self.play_index(0)
            else:
                self.stop()

    def prev_track(self):
        if not self.playlist:
            return
        if self.current_position > 3.0:
            self.seek(0.0)
            return
        if self.current_index > 0:
            self.play_index(self.current_index - 1)
        elif self.repeat:
            self.play_index(len(self.playlist) - 1)

    def seek(self, seconds):
        if self.current_track:
            target = max(0.0, min(self.current_track.duration, seconds))
            try:
                pygame.mixer.music.play(start=target)
                self.seek_offset = target
                self.current_position = target
                self.is_playing = True
                self.is_paused = False
                self.pos_timer.start()
                self.playback_state_changed.emit(True)
                self.position_changed.emit(target)
            except Exception as e:
                print(f"Error seeking: {e}")

    def remove_track(self, index):
        if 0 <= index < len(self.playlist):
            if index == self.current_index:
                self.stop()
                self.playlist.pop(index)
                if self.playlist:
                    self.current_index = min(index, len(self.playlist) - 1)
                else:
                    self.current_index = -1
            else:
                if index < self.current_index:
                    self.current_index -= 1
                self.playlist.pop(index)
            self.playlist_updated.emit()
            self.save_playlist_state()

    def clear_playlist(self):
        self.stop()
        self.playlist.clear()
        self.current_index = -1
        self.playlist_updated.emit()
        self.save_playlist_state()

    # -------------------------------------------------------------------------
    # State Persistence & M3U Export/Import
    # -------------------------------------------------------------------------
    def save_playlist_state(self):
        os.makedirs(os.path.dirname(PLAYLIST_FILE), exist_ok=True)
        data = {
            "current_index": self.current_index,
            "tracks": [t.filepath for t in self.playlist if os.path.exists(t.filepath)]
        }
        try:
            with open(PLAYLIST_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving playlist state: {e}")

    def load_playlist_state(self):
        if os.path.exists(PLAYLIST_FILE):
            try:
                with open(PLAYLIST_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    paths = data.get("tracks", [])
                    saved_idx = data.get("current_index", -1)
                    
                    self.playlist = [Track(p) for p in paths if os.path.exists(p)]
                    if self.playlist:
                        if 0 <= saved_idx < len(self.playlist):
                            self.current_index = saved_idx
                        else:
                            self.current_index = 0
            except Exception as e:
                print(f"Error loading playlist state: {e}")

    def save_m3u(self, m3u_path):
        try:
            with open(m3u_path, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for track in self.playlist:
                    duration_int = int(track.duration)
                    f.write(f"#EXTINF:{duration_int},{track.display_name}\n")
                    f.write(f"{track.filepath}\n")
            return True
        except Exception as e:
            print(f"Error saving M3U: {e}")
            return False

    def load_m3u(self, m3u_path):
        if not os.path.exists(m3u_path):
            return False
        try:
            with open(m3u_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        if not os.path.isabs(line):
                            line = os.path.join(os.path.dirname(m3u_path), line)
                        if os.path.isfile(line):
                            self.playlist.append(Track(line))
            self.playlist_updated.emit()
            self.save_playlist_state()
            return True
        except Exception as e:
            print(f"Error loading M3U: {e}")
            return False

    @property
    def current_track(self):
        if 0 <= self.current_index < len(self.playlist):
            return self.playlist[self.current_index]
        return None

    def _update_position(self):
        if self.is_playing:
            if not pygame.mixer.music.get_busy():
                self.next_track()
                return
            pos_ms = pygame.mixer.music.get_pos()
            if pos_ms >= 0:
                self.current_position = self.seek_offset + (pos_ms / 1000.0)
                self.position_changed.emit(self.current_position)

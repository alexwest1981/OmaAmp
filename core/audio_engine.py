import os
import json
import random
import threading
import numpy as np
import sounddevice as sd
import miniaudio
import soundfile as sf
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
import mutagen
from core.audio_analyzer import AudioAnalyzer
from core.dsp_equalizer import DspEqualizer

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
        self.playlist = []
        self.current_index = -1
        self.is_playing = False
        self.is_paused = False
        self.volume = 80
        self.balance = 0.0  # -1.0 (L) to +1.0 (R)
        self.shuffle = False
        self.repeat = True
        
        # Audio Buffer & Stream State
        self.raw_stereo_data = None
        self.sample_rate = 44100
        self.playback_sample_index = 0
        self.stream = None
        self._stream_lock = threading.Lock()

        # DSP Equalizer & Real-time FFT Analyzer
        self.dsp_eq = DspEqualizer(self.sample_rate)
        self.analyzer = AudioAnalyzer(num_bars=24)

        # UI Poll Timer
        self.pos_timer = QTimer(self)
        self.pos_timer.setInterval(100)
        self.pos_timer.timeout.connect(self._poll_position)

        # Restore saved playlist state on startup
        self.load_playlist_state()
        if self.current_track:
            self._load_track_samples(self.current_track.filepath)

    def set_volume(self, val):
        self.volume = max(0, min(100, val))
        self.volume_changed.emit(self.volume)

    def set_balance(self, val):
        # slider -50..+50 to -1.0..+1.0
        self.balance = float(val) / 50.0

    def set_eq_params(self, bands, preamp, enabled=True):
        self.dsp_eq.set_params(bands, preamp, enabled)

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
                    self._load_track_samples(self.current_track.filepath)
            self.save_playlist_state()

    def _load_track_samples(self, filepath):
        if not filepath or not os.path.exists(filepath):
            return
        try:
            ext = os.path.splitext(filepath)[1].lower()
            if ext in {".wav", ".flac", ".ogg"}:
                try:
                    data, sr = sf.read(filepath, dtype='float32')
                    if data.ndim == 1:
                        stereo = np.column_stack([data, data])
                    else:
                        stereo = data
                    with self._stream_lock:
                        self.raw_stereo_data = stereo
                        self.sample_rate = sr
                        self.dsp_eq.set_sample_rate(sr)
                    self.analyzer.load_track(filepath)
                    return
                except Exception:
                    pass

            decoded = miniaudio.decode_file(filepath)
            sr = decoded.sample_rate
            nchannels = decoded.nchannels
            raw = np.frombuffer(decoded.samples, dtype=np.int16).astype(np.float32) / 32768.0

            if nchannels >= 2:
                l_chan = raw[0::nchannels]
                r_chan = raw[1::nchannels]
                min_len = min(len(l_chan), len(r_chan))
                stereo = np.column_stack([l_chan[:min_len], r_chan[:min_len]])
            else:
                stereo = np.column_stack([raw, raw])

            with self._stream_lock:
                self.raw_stereo_data = stereo
                self.sample_rate = sr
                self.dsp_eq.set_sample_rate(sr)
            self.analyzer.load_track(filepath)
        except Exception as e:
            print(f"Error loading audio samples: {e}")

    def play_index(self, index):
        if 0 <= index < len(self.playlist):
            self.current_index = index
            track = self.playlist[self.current_index]
            self._load_track_samples(track.filepath)
            self.playback_sample_index = 0
            self._start_stream()
            self.is_playing = True
            self.is_paused = False
            self.pos_timer.start()
            self.track_changed.emit(track)
            self.playback_state_changed.emit(True)
            self.save_playlist_state()

    def _start_stream(self):
        self._stop_stream()
        try:
            self.stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=2,
                dtype='float32',
                blocksize=1024,
                callback=self._audio_callback
            )
            self.stream.start()
        except Exception as e:
            print(f"Error starting audio stream: {e}")

    def _stop_stream(self):
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None

    def _audio_callback(self, outdata, frames, time_info, status):
        if not self.is_playing or self.is_paused or self.raw_stereo_data is None:
            outdata.fill(0)
            return

        with self._stream_lock:
            total_samples = len(self.raw_stereo_data)
            current_idx = self.playback_sample_index

            if current_idx >= total_samples:
                outdata.fill(0)
                # Next track trigger
                QTimer.singleShot(0, self.next_track)
                return

            end_idx = min(total_samples, current_idx + frames)
            chunk = self.raw_stereo_data[current_idx:end_idx]
            self.playback_sample_index = end_idx

        # Pad if short
        if len(chunk) < frames:
            pad_len = frames - len(chunk)
            chunk = np.pad(chunk, ((0, pad_len), (0, 0)))

        # 1. Master Volume & Balance
        vol_factor = self.volume / 100.0
        left_gain = vol_factor * (1.0 - max(0.0, self.balance))
        right_gain = vol_factor * (1.0 + min(0.0, self.balance))

        chunk[:, 0] *= left_gain
        chunk[:, 1] *= right_gain

        # 2. REAL-TIME 10-BAND DSP EQUALIZER & PREAMP
        processed = self.dsp_eq.process(chunk)

        outdata[:] = processed

    def play(self):
        if self.is_paused:
            self.is_playing = True
            self.is_paused = False
            if self.stream is None:
                self._start_stream()
            self.pos_timer.start()
            self.playback_state_changed.emit(True)
        elif self.playlist:
            if self.current_index == -1:
                self.current_index = 0
            self.play_index(self.current_index)

    def pause(self):
        if self.is_playing:
            self.is_playing = False
            self.is_paused = True
            self.pos_timer.stop()
            self.playback_state_changed.emit(False)
        elif self.is_paused:
            self.play()

    def stop(self):
        self.is_playing = False
        self.is_paused = False
        self.playback_sample_index = 0
        self._stop_stream()
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
        if self.current_track and self.current_track.duration > 0:
            target = max(0.0, min(self.current_track.duration, seconds))
            with self._stream_lock:
                self.playback_sample_index = int(target * self.sample_rate)
            self.position_changed.emit(target)

    def remove_track(self, index):
        self.remove_indices([index])

    def remove_indices(self, indices):
        curr_track = self.current_track
        for idx in sorted(indices, reverse=True):
            if 0 <= idx < len(self.playlist):
                self.playlist.pop(idx)
        if curr_track and curr_track in self.playlist:
            self.current_index = self.playlist.index(curr_track)
        elif self.playlist:
            self.current_index = max(0, min(self.current_index, len(self.playlist) - 1))
        else:
            self.stop()
            self.current_index = -1
        self.playlist_updated.emit()
        self.save_playlist_state()

    def sort_by_title(self):
        curr_track = self.current_track
        self.playlist.sort(key=lambda t: t.title.lower())
        if curr_track and curr_track in self.playlist:
            self.current_index = self.playlist.index(curr_track)
        self.playlist_updated.emit()
        self.save_playlist_state()

    def sort_by_filename(self):
        curr_track = self.current_track
        self.playlist.sort(key=lambda t: t.filename.lower())
        if curr_track and curr_track in self.playlist:
            self.current_index = self.playlist.index(curr_track)
        self.playlist_updated.emit()
        self.save_playlist_state()

    def randomize_playlist(self):
        curr_track = self.current_track
        random.shuffle(self.playlist)
        if curr_track and curr_track in self.playlist:
            self.current_index = self.playlist.index(curr_track)
        self.playlist_updated.emit()
        self.save_playlist_state()

    def reverse_playlist(self):
        curr_track = self.current_track
        self.playlist.reverse()
        if curr_track and curr_track in self.playlist:
            self.current_index = self.playlist.index(curr_track)
        self.playlist_updated.emit()
        self.save_playlist_state()

    def clear_playlist(self):
        self.stop()
        self.playlist.clear()
        self.current_index = -1
        self.playlist_updated.emit()
        self.save_playlist_state()

    @property
    def current_position(self):
        if self.sample_rate > 0:
            return float(self.playback_sample_index) / float(self.sample_rate)
        return 0.0

    @property
    def current_track(self):
        if 0 <= self.current_index < len(self.playlist):
            return self.playlist[self.current_index]
        return None

    def _poll_position(self):
        if self.is_playing:
            self.position_changed.emit(self.current_position)

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

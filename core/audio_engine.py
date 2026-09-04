import os
import json
import random
import threading
import queue
import subprocess
import numpy as np
import sounddevice as sd
import miniaudio
import soundfile as sf
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
import mutagen
from core.audio_analyzer import AudioAnalyzer
from core.dsp_equalizer import DspEqualizer
from core.radio_manager import RadioManager

PLAYLIST_FILE = os.path.expanduser("~/.config/omaamp/playlist.json")


class Track:
    def __init__(self, filepath, is_stream=False, stream_type="file", title=None, artist=None, duration=0.0, extra=None):
        self.filepath = filepath
        self.is_stream = is_stream
        self.stream_type = stream_type  # "file", "radio", "youtube"
        self.filename = os.path.basename(filepath) if not is_stream else filepath
        self.title = title or (os.path.splitext(self.filename)[0] if not is_stream else "Online Stream")
        self.artist = artist or ("Internet Radio" if stream_type == "radio" else "YouTube" if stream_type == "youtube" else "Unknown Artist")
        self.album = ""
        self.duration = float(duration)
        self.bitrate = 128
        self.samplerate = 44100
        self.channels = 2
        self.extra = extra or {}
        self.cover_art_bytes = None
        self.cover_art_path = None

        if not self.is_stream and os.path.exists(self.filepath):
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

                    # Extract Embedded Cover Art
                    for key in tags.keys():
                        if str(key).startswith("APIC"):
                            apic = tags[key]
                            if hasattr(apic, "data"):
                                self.cover_art_bytes = bytes(apic.data)
                                break
                    if not self.cover_art_bytes and "covr" in tags:
                        covr = tags["covr"]
                        if covr and len(covr) > 0:
                            self.cover_art_bytes = bytes(covr[0])

                if not self.cover_art_bytes and hasattr(audio, "pictures") and audio.pictures:
                    self.cover_art_bytes = bytes(audio.pictures[0].data)

            # Check folder for cover image if not embedded
            if not self.cover_art_bytes:
                dir_p = os.path.dirname(self.filepath)
                for name in ["cover.jpg", "cover.png", "folder.jpg", "folder.png", "album.jpg", "albumart.jpg", "front.jpg"]:
                    full_p = os.path.join(dir_p, name)
                    if os.path.exists(full_p):
                        self.cover_art_path = full_p
                        break
        except Exception:
            pass

    @property
    def display_name(self):
        if self.is_stream:
            if self.stream_type == "radio":
                if self.artist and self.artist != "Internet Radio":
                    return f"📻 {self.artist} - {self.title}"
                return f"📻 {self.title}"
            elif self.stream_type == "youtube":
                if self.artist and self.artist != "YouTube":
                    return f"▶ {self.artist} - {self.title}"
                return f"▶ {self.title}"
            return f"🌐 {self.title}"

        if self.artist and self.artist != "Unknown Artist":
            return f"{self.artist} - {self.title}"
        return self.title

    @property
    def duration_formatted(self):
        if self.is_stream and self.duration <= 0:
            return "LIVE"
        mins = int(self.duration // 60)
        secs = int(self.duration % 60)
        return f"{mins}:{secs:02d}"

    def to_dict(self):
        return {
            "filepath": self.filepath,
            "is_stream": self.is_stream,
            "stream_type": self.stream_type,
            "title": self.title,
            "artist": self.artist,
            "duration": self.duration,
            "extra": self.extra
        }

    @classmethod
    def from_dict(cls, data):
        if isinstance(data, str):
            return cls(data)
        return cls(
            filepath=data.get("filepath", ""),
            is_stream=data.get("is_stream", False),
            stream_type=data.get("stream_type", "file"),
            title=data.get("title"),
            artist=data.get("artist"),
            duration=data.get("duration", 0.0),
            extra=data.get("extra", {})
        )


class AudioEngine(QObject):
    track_changed = pyqtSignal(object)
    playback_state_changed = pyqtSignal(bool)
    position_changed = pyqtSignal(float)
    playlist_updated = pyqtSignal()
    volume_changed = pyqtSignal(int)
    stream_status_changed = pyqtSignal(str)  # "Buffering...", "Connecting...", "Playing", etc.

    def __init__(self):
        super().__init__()
        self.radio_mgr = RadioManager()
        self.playlist = []
        self.current_index = -1
        self.is_playing = False
        self.is_paused = False
        self.volume = 80
        self.balance = 0.0  # -1.0 (L) to +1.0 (R)
        self.shuffle = False
        self.repeat = True
        
        # Audio Buffer & Local File State
        self.raw_stereo_data = None
        self.sample_rate = 44100
        self.playback_sample_index = 0
        self.stream = None
        self._stream_lock = threading.Lock()

        # Online Live Stream Worker State
        self.is_live_stream = False
        self._stream_proc = None
        self._stream_queue = queue.Queue(maxsize=120)
        self._stream_stop_event = threading.Event()
        self._stream_thread = None
        self._stream_pos_sec = 0.0
        self._stream_buffer_filled = False

        # DSP Equalizer & Real-time FFT Analyzer
        self.dsp_eq = DspEqualizer(self.sample_rate)
        self.analyzer = AudioAnalyzer(num_bars=24)

        # UI Poll Timer
        self.pos_timer = QTimer(self)
        self.pos_timer.setInterval(100)
        self.pos_timer.timeout.connect(self._poll_position)

        # Restore saved playlist state on startup
        self.load_playlist_state()
        if self.current_track and not self.current_track.is_stream:
            self._load_track_samples(self.current_track.filepath)

    def set_volume(self, val):
        self.volume = max(0, min(100, val))
        self.volume_changed.emit(self.volume)

    def set_balance(self, val):
        # slider -50..+50 to -1.0..+1.0
        self.balance = float(val) / 50.0

    def set_eq_params(self, bands, preamp, enabled=True):
        self.dsp_eq.set_params(bands, preamp, enabled)

    # -------------------------------------------------------------------------
    # Adding Tracks (Local Files, Radio Streams, YouTube)
    # -------------------------------------------------------------------------
    def add_files(self, filepaths):
        added = False
        valid_exts = {".mp3", ".flac", ".ogg", ".wav", ".m4a", ".aac", ".opus", ".mod", ".xm", ".s3m", ".it"}
        for fpath in filepaths:
            if fpath.startswith("http://") or fpath.startswith("https://"):
                # URL added
                if "youtube.com" in fpath or "youtu.be" in fpath:
                    self.add_youtube_url(fpath)
                else:
                    self.add_stream_track(fpath, title=fpath, stream_type="radio")
                added = True
            elif os.path.isfile(fpath):
                ext = os.path.splitext(fpath)[1].lower()
                if ext in valid_exts:
                    self.playlist.append(Track(fpath))
                    added = True
                elif ext in {".m3u", ".m3u8"}:
                    self.load_m3u(fpath)
                    added = True
                elif ext == ".pls":
                    self.load_pls(fpath)
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
                    if not self.current_track.is_stream:
                        self._load_track_samples(self.current_track.filepath)
            self.save_playlist_state()

    def add_stream_track(self, url, title=None, artist="Internet Radio", duration=0.0, stream_type="radio", play_now=False):
        track = Track(url, is_stream=True, stream_type=stream_type, title=title, artist=artist, duration=duration)
        self.playlist.append(track)
        self.playlist_updated.emit()
        self.save_playlist_state()
        if play_now:
            self.play_index(len(self.playlist) - 1)
        elif self.current_index == -1:
            self.current_index = 0
            self.track_changed.emit(self.current_track)
        return track

    def add_youtube_url(self, url, play_now=False):
        """Extracts YouTube video or playlist and appends to playlist in background."""
        def _extract():
            res = self.radio_mgr.parse_youtube_url(url)
            tracks = res.get("tracks", [])
            if tracks:
                for t in tracks:
                    tr = Track(
                        filepath=t.get("url"),
                        is_stream=True,
                        stream_type="youtube",
                        title=t.get("title"),
                        artist=t.get("artist"),
                        duration=t.get("duration", 0.0),
                        extra={"thumbnail": t.get("thumbnail"), "video_id": t.get("id")}
                    )
                    self.playlist.append(tr)
                self.playlist_updated.emit()
                self.save_playlist_state()
                if play_now and self.playlist:
                    self.play_index(len(self.playlist) - len(tracks))
        threading.Thread(target=_extract, daemon=True).start()

    def add_youtube_tracks(self, tracks_data, play_now=False):
        """Adds pre-parsed YouTube tracks to playlist."""
        if not tracks_data:
            return
        start_idx = len(self.playlist)
        for t in tracks_data:
            tr = Track(
                filepath=t.get("url"),
                is_stream=True,
                stream_type="youtube",
                title=t.get("title"),
                artist=t.get("artist"),
                duration=t.get("duration", 0.0),
                extra={"thumbnail": t.get("thumbnail"), "video_id": t.get("id")}
            )
            self.playlist.append(tr)
        self.playlist_updated.emit()
        self.save_playlist_state()
        if play_now:
            self.play_index(start_idx)

    # -------------------------------------------------------------------------
    # Local Audio Sample Decoding
    # -------------------------------------------------------------------------
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

    # -------------------------------------------------------------------------
    # Live Online Streaming Worker (Radio & YouTube)
    # -------------------------------------------------------------------------
    def _stop_stream_worker(self):
        self._stream_stop_event.set()
        if self._stream_proc is not None:
            try:
                self._stream_proc.terminate()
                self._stream_proc.kill()
            except Exception:
                pass
            self._stream_proc = None

        # Drain queue
        while not self._stream_queue.empty():
            try:
                self._stream_queue.get_nowait()
            except Exception:
                break

    def _start_stream_worker(self, track, seek_seconds=0.0):
        self._stop_stream_worker()
        self._stream_stop_event.clear()
        self._stream_pos_sec = seek_seconds
        self._stream_buffer_filled = False
        self.stream_status_changed.emit("Connecting...")

        def _worker():
            url = track.filepath
            if track.stream_type == "youtube":
                self.stream_status_changed.emit("Resolving YouTube audio stream...")
                url = self.radio_mgr.resolve_youtube_audio_url(track.filepath)
                if not url:
                    self.stream_status_changed.emit("YouTube error")
                    return

            cmd = [
                'ffmpeg',
                '-reconnect', '1',
                '-reconnect_streamed', '1',
                '-reconnect_delay_max', '5'
            ]
            if seek_seconds > 0:
                cmd.extend(['-ss', str(seek_seconds)])
            
            cmd.extend([
                '-i', url,
                '-f', 'f32le',
                '-ar', '44100',
                '-ac', '2',
                '-loglevel', 'quiet',
                '-'
            ])

            try:
                self._stream_proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
                )
                self.stream_status_changed.emit("Buffering...")
            except Exception as e:
                print(f"Error launching ffmpeg stream: {e}")
                self.stream_status_changed.emit(f"Error: {e}")
                return

            chunk_samples = 1024
            bytes_per_chunk = chunk_samples * 2 * 4  # 1024 samples * 2 channels * 4 bytes/float32

            while not self._stream_stop_event.is_set():
                if self._stream_proc is None or self._stream_proc.stdout is None:
                    break
                raw = self._stream_proc.stdout.read(bytes_per_chunk)
                if not raw or len(raw) < bytes_per_chunk:
                    # End of stream / stream severed
                    break

                chunk = np.frombuffer(raw, dtype=np.float32).copy().reshape(-1, 2)
                try:
                    self._stream_queue.put(chunk, timeout=0.2)
                    self._stream_buffer_filled = True
                except queue.Full:
                    pass

            if not self._stream_stop_event.is_set() and track.stream_type == "youtube":
                # Next track trigger on YouTube completion
                QTimer.singleShot(0, self.next_track)

        self._stream_thread = threading.Thread(target=_worker, daemon=True)
        self._stream_thread.start()

    # -------------------------------------------------------------------------
    # Playback Control
    # -------------------------------------------------------------------------
    def play_index(self, index):
        if 0 <= index < len(self.playlist):
            self.current_index = index
            track = self.playlist[self.current_index]

            if track.is_stream:
                self.is_live_stream = True
                self.raw_stereo_data = None
                self._stream_residual = None
                self._start_stream_worker(track)
            else:
                self.is_live_stream = False
                self._stop_stream_worker()
                self._stream_residual = None
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
                samplerate=44100,
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
        if not self.is_playing or self.is_paused:
            outdata.fill(0)
            return

        if self.is_live_stream:
            needed = frames
            collected = []
            
            with self._stream_lock:
                if self._stream_residual is not None and len(self._stream_residual) > 0:
                    take = min(len(self._stream_residual), needed)
                    collected.append(self._stream_residual[:take])
                    self._stream_residual = self._stream_residual[take:]
                    needed -= take

                while needed > 0:
                    try:
                        q_chunk = self._stream_queue.get_nowait()
                        take = min(len(q_chunk), needed)
                        collected.append(q_chunk[:take])
                        if take < len(q_chunk):
                            self._stream_residual = q_chunk[take:]
                        needed -= take
                    except queue.Empty:
                        break

            if not collected:
                outdata.fill(0)
                return

            chunk = np.concatenate(collected, axis=0) if len(collected) > 1 else collected[0]
            self._stream_pos_sec += float(len(chunk)) / 44100.0
            self.analyzer.feed_live_chunk(chunk)

            if len(chunk) < frames:
                pad_len = frames - len(chunk)
                chunk = np.pad(chunk, ((0, pad_len), (0, 0)))
        else:
            if self.raw_stereo_data is None:
                outdata.fill(0)
                return

            with self._stream_lock:
                total_samples = len(self.raw_stereo_data)
                current_idx = self.playback_sample_index

                if current_idx >= total_samples:
                    outdata.fill(0)
                    QTimer.singleShot(0, self.next_track)
                    return

                end_idx = min(total_samples, current_idx + frames)
                chunk = self.raw_stereo_data[current_idx:end_idx]
                self.playback_sample_index = end_idx

            if len(chunk) < frames:
                pad_len = frames - len(chunk)
                chunk = np.pad(chunk, ((0, pad_len), (0, 0)))

        # 1. Master Volume & Balance
        vol_factor = self.volume / 100.0
        left_gain = vol_factor * (1.0 - max(0.0, self.balance))
        right_gain = vol_factor * (1.0 + min(0.0, self.balance))

        processed_chunk = np.empty_like(chunk, dtype=np.float32)
        processed_chunk[:, 0] = chunk[:, 0] * left_gain
        processed_chunk[:, 1] = chunk[:, 1] * right_gain

        # 2. REAL-TIME 10-BAND DSP EQUALIZER & PREAMP
        processed = self.dsp_eq.process(processed_chunk)
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
        self._stream_pos_sec = 0.0
        self._stop_stream()
        self._stop_stream_worker()
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
        if not self.current_track:
            return
        if not self.current_track.is_stream:
            target = max(0.0, min(self.current_track.duration, seconds))
            with self._stream_lock:
                self.playback_sample_index = int(target * self.sample_rate)
            self.position_changed.emit(target)
        elif self.current_track.stream_type == "youtube" and self.current_track.duration > 0:
            target = max(0.0, min(self.current_track.duration, seconds))
            self._start_stream_worker(self.current_track, seek_seconds=target)
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
        if self.is_live_stream:
            return self._stream_pos_sec
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
    # State Persistence & M3U / PLS Export/Import
    # -------------------------------------------------------------------------
    def save_playlist_state(self):
        os.makedirs(os.path.dirname(PLAYLIST_FILE), exist_ok=True)
        data = {
            "current_index": self.current_index,
            "tracks": [t.to_dict() for t in self.playlist]
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
                    tracks_data = data.get("tracks", [])
                    saved_idx = data.get("current_index", -1)
                    
                    self.playlist = []
                    for item in tracks_data:
                        tr = Track.from_dict(item)
                        if tr.is_stream or os.path.exists(tr.filepath):
                            self.playlist.append(tr)

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
                        if line.startswith("http://") or line.startswith("https://"):
                            self.playlist.append(Track(line, is_stream=True, stream_type="radio", title=line))
                        else:
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

    def load_pls(self, pls_path):
        """Loads a classic Shoutcast .pls playlist file."""
        if not os.path.exists(pls_path):
            return False
        try:
            import configparser
            config = configparser.ConfigParser()
            config.read(pls_path)
            if 'playlist' in config:
                num = int(config['playlist'].get('NumberOfEntries', 0))
                for i in range(1, num + 1):
                    file_url = config['playlist'].get(f'File{i}')
                    title = config['playlist'].get(f'Title{i}', file_url)
                    if file_url:
                        if file_url.startswith("http://") or file_url.startswith("https://"):
                            self.playlist.append(Track(file_url, is_stream=True, stream_type="radio", title=title))
                        elif os.path.isfile(file_url):
                            self.playlist.append(Track(file_url, title=title))
                self.playlist_updated.emit()
                self.save_playlist_state()
                return True
        except Exception as e:
            print(f"Error loading PLS: {e}")
        return False

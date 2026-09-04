import os
import threading
import numpy as np
import miniaudio
import soundfile as sf

class AudioAnalyzer:
    def __init__(self, num_bars=24):
        self.num_bars = num_bars
        self.current_filepath = None
        self.pcm_mono = None
        self.pcm_left = None
        self.pcm_right = None
        self.sample_rate = 44100
        self.is_loaded = False
        self.is_live_stream = False
        self._lock = threading.Lock()

        # FFT parameters
        self.window_size = 2048
        self.hanning = np.hanning(self.window_size)
        self.freqs = np.fft.rfftfreq(self.window_size, 1.0 / 44100)
        self.band_edges = np.logspace(np.log10(30), np.log10(17000), self.num_bars + 1)
        
        # Precompute band masks
        self._compute_band_masks()

        # Visualizer state
        self.bars = np.zeros(self.num_bars, dtype=np.float32)
        self.peaks = np.zeros(self.num_bars, dtype=np.float32)
        self.peak_speeds = np.zeros(self.num_bars, dtype=np.float32)
        self.decay = 0.72
        self.gravity = 0.035
        self.sensitivity = 0.70  # Default balanced sensitivity (prevents pegging at top)

        # VU meter RMS values
        self.vu_left = 0.0
        self.vu_right = 0.0

        # Starfield & matrix states
        self.num_stars = 140
        self.stars_x = np.random.uniform(-1.0, 1.0, self.num_stars)
        self.stars_y = np.random.uniform(-1.0, 1.0, self.num_stars)
        self.stars_z = np.random.uniform(0.1, 1.0, self.num_stars)

        self.num_matrix_cols = 32
        self.matrix_drops = np.random.uniform(0, 30, self.num_matrix_cols)
        self.matrix_speeds = np.random.uniform(0.4, 1.0, self.num_matrix_cols)

    def set_sensitivity(self, val):
        """Sets visualizer sensitivity multiplier (e.g. 0.3 to 1.5)."""
        self.sensitivity = max(0.1, min(2.0, float(val)))

    def _compute_band_masks(self):
        self.freqs = np.fft.rfftfreq(self.window_size, 1.0 / self.sample_rate)
        self.band_masks = []
        for b in range(self.num_bars):
            m = (self.freqs >= self.band_edges[b]) & (self.freqs < self.band_edges[b+1])
            self.band_masks.append(m)

    def feed_live_chunk(self, chunk):
        """Feeds a real-time chunk of audio from online radio or YouTube streams."""
        if chunk is None or len(chunk) == 0:
            return
        with self._lock:
            self.sample_rate = 44100
            if chunk.ndim == 2:
                l_chan = chunk[:, 0]
                r_chan = chunk[:, 1]
                mono = (l_chan + r_chan) * 0.5
            else:
                l_chan = chunk
                r_chan = chunk
                mono = chunk

            if self.pcm_mono is None or not self.is_live_stream:
                self.pcm_mono = mono
                self.pcm_left = l_chan
                self.pcm_right = r_chan
            else:
                self.pcm_mono = np.concatenate([self.pcm_mono, mono])[-8192:]
                self.pcm_left = np.concatenate([self.pcm_left, l_chan])[-8192:]
                self.pcm_right = np.concatenate([self.pcm_right, r_chan])[-8192:]

            self.is_live_stream = True
            self.is_loaded = True

    def load_track(self, filepath):
        if filepath == self.current_filepath and self.is_loaded and not self.is_live_stream:
            return
        self.current_filepath = filepath
        self.is_loaded = False
        self.is_live_stream = False
        t = threading.Thread(target=self._decode_in_background, args=(filepath,), daemon=True)
        t.start()

    def _decode_in_background(self, filepath):
        if not filepath or not os.path.exists(filepath):
            return
        try:
            ext = os.path.splitext(filepath)[1].lower()
            if ext in {".wav", ".flac", ".ogg"}:
                try:
                    data, sr = sf.read(filepath, dtype='float32')
                    with self._lock:
                        self.sample_rate = sr
                        if data.ndim == 2:
                            self.pcm_left = data[:, 0]
                            self.pcm_right = data[:, 1]
                            self.pcm_mono = (self.pcm_left + self.pcm_right) * 0.5
                        else:
                            self.pcm_mono = data
                            self.pcm_left = data
                            self.pcm_right = data
                        self._compute_band_masks()
                        self.is_loaded = True
                    return
                except Exception:
                    pass

            # Fallback / MP3 decode via miniaudio
            decoded = miniaudio.decode_file(filepath)
            sr = decoded.sample_rate
            nchannels = decoded.nchannels
            raw = np.frombuffer(decoded.samples, dtype=np.int16).astype(np.float32) / 32768.0

            with self._lock:
                self.sample_rate = sr
                if nchannels >= 2:
                    self.pcm_left = raw[0::nchannels]
                    self.pcm_right = raw[1::nchannels]
                    # align lengths
                    min_len = min(len(self.pcm_left), len(self.pcm_right))
                    self.pcm_left = self.pcm_left[:min_len]
                    self.pcm_right = self.pcm_right[:min_len]
                    self.pcm_mono = (self.pcm_left + self.pcm_right) * 0.5
                else:
                    self.pcm_mono = raw
                    self.pcm_left = raw
                    self.pcm_right = raw
                self._compute_band_masks()
                self.is_loaded = True
        except Exception as e:
            print(f"Error decoding audio for analysis: {e}")

    def get_real_spectrum(self, is_playing, current_position=0.0, volume=80):
        if not is_playing or not self.is_loaded or self.pcm_mono is None:
            # Decay to zero
            self.bars *= 0.72
            self.peaks -= self.peak_speeds
            self.peak_speeds += self.gravity
            self.peaks = np.maximum(self.peaks, self.bars)
            self.peaks = np.maximum(self.peaks, 0.0)
            self.vu_left *= 0.8
            self.vu_right *= 0.8
            return self.bars, self.peaks

        with self._lock:
            if self.is_live_stream:
                chunk = self.pcm_mono[-self.window_size:] if len(self.pcm_mono) >= self.window_size else self.pcm_mono
                l_chunk = self.pcm_left[-self.window_size:] if (self.pcm_left is not None and len(self.pcm_left) >= self.window_size) else self.pcm_left
                r_chunk = self.pcm_right[-self.window_size:] if (self.pcm_right is not None and len(self.pcm_right) >= self.window_size) else self.pcm_right
            else:
                idx = int(current_position * self.sample_rate)
                total_samples = len(self.pcm_mono)
                if idx < 0 or idx >= total_samples:
                    return self.bars, self.peaks

                end_idx = min(total_samples, idx + self.window_size)
                chunk = self.pcm_mono[idx:end_idx]
                l_chunk = self.pcm_left[idx:end_idx] if self.pcm_left is not None else None
                r_chunk = self.pcm_right[idx:end_idx] if self.pcm_right is not None else None

        if len(chunk) < self.window_size:
            chunk = np.pad(chunk, (0, self.window_size - len(chunk)))

        # FFT Analysis
        windowed = chunk * self.hanning
        fft_data = np.abs(np.fft.rfft(windowed)) / (self.window_size / 2.0)

        vol_factor = volume / 100.0
        
        # Calculate frequency bands
        raw_bands = np.zeros(self.num_bars, dtype=np.float32)
        for b in range(self.num_bars):
            mask = self.band_masks[b]
            if np.any(mask):
                val = float(np.max(fft_data[mask])) * 0.75 + float(np.mean(fft_data[mask])) * 0.25
            else:
                val = 0.0
            
            # Subtle tilt for treble compensation (human ear perception)
            tilt = 1.0 + (b / self.num_bars) * 1.5
            val_db = 20.0 * np.log10(val * tilt + 1e-5)
            # Map -48 dB .. -2 dB to 0.0 .. 1.0
            norm = float(np.clip((val_db + 48.0) / 46.0, 0.0, 1.0))
            # Apply dynamic power curve and sensitivity scaling
            norm = (norm ** 1.3) * self.sensitivity * vol_factor
            raw_bands[b] = float(np.clip(norm, 0.0, 1.0))

        # Smooth dynamics
        for i in range(self.num_bars):
            val = raw_bands[i]
            if val > self.bars[i]:
                self.bars[i] = val
            else:
                self.bars[i] = self.bars[i] * self.decay + val * (1.0 - self.decay)

            # Peak dots physics
            if self.bars[i] >= self.peaks[i]:
                self.peaks[i] = self.bars[i]
                self.peak_speeds[i] = 0.006
            else:
                self.peaks[i] -= self.peak_speeds[i]
                self.peak_speeds[i] += self.gravity

            self.peaks[i] = max(0.0, min(1.0, self.peaks[i]))

        # Calculate True Stereo VU Meter RMS
        if l_chunk is not None and r_chunk is not None:
            rms_l = float(np.sqrt(np.mean(l_chunk ** 2))) if len(l_chunk) > 0 else 0.0
            rms_r = float(np.sqrt(np.mean(r_chunk ** 2))) if len(r_chunk) > 0 else 0.0
            
            # Balanced VU level scaling (hovers nicely around 40-75% on standard music)
            target_l = min(1.0, rms_l * 1.75 * vol_factor * self.sensitivity)
            target_r = min(1.0, rms_r * 1.75 * vol_factor * self.sensitivity)
            self.vu_left = self.vu_left * 0.65 + target_l * 0.35
            self.vu_right = self.vu_right * 0.65 + target_r * 0.35

        return self.bars, self.peaks

    def get_real_waveform(self, is_playing, current_position=0.0, num_points=80, volume=80):
        if not is_playing or not self.is_loaded or self.pcm_mono is None:
            return np.zeros(num_points, dtype=np.float32)

        with self._lock:
            step = max(1, int(self.window_size / num_points))
            if self.is_live_stream:
                needed = num_points * step
                samples = self.pcm_mono[-needed::step] if len(self.pcm_mono) >= needed else self.pcm_mono
            else:
                idx = int(current_position * self.sample_rate)
                total = len(self.pcm_mono)
                if idx < 0 or idx >= total:
                    return np.zeros(num_points, dtype=np.float32)

                slice_end = min(total, idx + num_points * step)
                samples = self.pcm_mono[idx:slice_end:step]

        if len(samples) < num_points:
            samples = np.pad(samples, (0, num_points - len(samples)))

        vol_factor = volume / 100.0
        return samples[:num_points] * vol_factor * (0.85 * self.sensitivity)

    def update_starfield(self, is_playing, current_position=0.0, volume=80):
        bass = float(np.mean(self.bars[:4])) if is_playing else 0.0
        speed = (0.015 + bass * 0.05) if is_playing else 0.003

        self.stars_z -= speed
        reset_mask = self.stars_z <= 0.02
        self.stars_z[reset_mask] = 1.0
        self.stars_x[reset_mask] = np.random.uniform(-1.0, 1.0, np.sum(reset_mask))
        self.stars_y[reset_mask] = np.random.uniform(-1.0, 1.0, np.sum(reset_mask))
        return self.stars_x, self.stars_y, self.stars_z, bass

    def update_matrix(self, is_playing):
        bass = float(np.mean(self.bars[:4])) if is_playing else 0.0
        speed_mult = (1.2 + bass * 2.0) if is_playing else 0.3
        self.matrix_drops += self.matrix_speeds * speed_mult
        reset_mask = self.matrix_drops >= 30
        self.matrix_drops[reset_mask] = 0
        return self.matrix_drops

import math
import random
import numpy as np

class VisualizerGenerator:
    def __init__(self, num_bars=24):
        self.num_bars = num_bars
        self.bars = np.zeros(num_bars, dtype=np.float32)
        self.peaks = np.zeros(num_bars, dtype=np.float32)
        self.peak_speeds = np.zeros(num_bars, dtype=np.float32)
        self.phase = 0.0
        self.decay = 0.82
        self.gravity = 0.025
        
        # Starfield state
        self.num_stars = 120
        self.stars_x = np.random.uniform(-1.0, 1.0, self.num_stars)
        self.stars_y = np.random.uniform(-1.0, 1.0, self.num_stars)
        self.stars_z = np.random.uniform(0.1, 1.0, self.num_stars)
        
        # VU Meter needle ballistic physics
        self.vu_left = 0.0
        self.vu_right = 0.0
        self.vu_speed_l = 0.0
        self.vu_speed_r = 0.0

        # Matrix rain state
        self.num_matrix_cols = 30
        self.matrix_drops = np.random.uniform(0, 30, self.num_matrix_cols)
        self.matrix_speeds = np.random.uniform(0.3, 0.9, self.num_matrix_cols)

    def update(self, is_playing, volume=80):
        if not is_playing:
            self.bars *= 0.72
            self.peaks -= self.peak_speeds
            self.peak_speeds += self.gravity
            self.peaks = np.maximum(self.peaks, self.bars)
            self.peaks = np.maximum(self.peaks, 0.0)
            self.vu_left *= 0.8
            self.vu_right *= 0.8
            return self.bars, self.peaks

        self.phase += 0.18
        vol_factor = (volume / 100.0)
        
        # Frequency band simulation
        for i in range(self.num_bars):
            freq = (i + 1) * 0.65
            harmonic1 = math.sin(self.phase * freq + i * 0.4)
            harmonic2 = math.cos(self.phase * 0.7 + i * 0.8)
            noise = random.uniform(-0.12, 0.12)
            
            curve = 1.0 - (i / self.num_bars) * 0.35
            val = (abs(harmonic1 * 0.6 + harmonic2 * 0.4) + noise) * curve * vol_factor
            val = max(0.05, min(1.0, val))

            if val > self.bars[i]:
                self.bars[i] = val
            else:
                self.bars[i] = self.bars[i] * self.decay + val * (1.0 - self.decay)

            if self.bars[i] >= self.peaks[i]:
                self.peaks[i] = self.bars[i]
                self.peak_speeds[i] = 0.005
            else:
                self.peaks[i] -= self.peak_speeds[i]
                self.peak_speeds[i] += self.gravity

            self.peaks[i] = max(0.0, min(1.0, self.peaks[i]))

        # Update VU needle physics
        bass_energy = float(np.mean(self.bars[:4]))
        mid_energy = float(np.mean(self.bars[4:12]))
        treble_energy = float(np.mean(self.bars[12:]))

        target_l = min(1.0, (bass_energy * 0.7 + mid_energy * 0.3) * 1.1)
        target_r = min(1.0, (mid_energy * 0.5 + treble_energy * 0.5) * 1.1)

        self.vu_left = self.vu_left * 0.7 + target_l * 0.3
        self.vu_right = self.vu_right * 0.7 + target_r * 0.3

        return self.bars, self.peaks

    def get_oscilloscope_wave(self, is_playing, num_points=80, volume=80):
        if not is_playing:
            return np.zeros(num_points, dtype=np.float32)

        vol_factor = (volume / 100.0)
        t = np.linspace(0, 4 * np.pi, num_points)
        wave = (
            np.sin(t + self.phase * 2.0) * 0.5 +
            np.sin(t * 2.5 - self.phase) * 0.3 +
            np.cos(t * 5.0 + self.phase * 3.0) * 0.2
        ) * vol_factor
        return wave

    def update_starfield(self, is_playing, volume=80):
        speed = 0.035 if is_playing else 0.005
        bass = float(np.mean(self.bars[:3])) if is_playing else 0.0
        speed += bass * 0.04

        self.stars_z -= speed
        reset_mask = self.stars_z <= 0.02
        self.stars_z[reset_mask] = 1.0
        self.stars_x[reset_mask] = np.random.uniform(-1.0, 1.0, np.sum(reset_mask))
        self.stars_y[reset_mask] = np.random.uniform(-1.0, 1.0, np.sum(reset_mask))
        return self.stars_x, self.stars_y, self.stars_z, bass

    def update_matrix(self, is_playing):
        speed_mult = 1.4 if is_playing else 0.4
        self.matrix_drops += self.matrix_speeds * speed_mult
        reset_mask = self.matrix_drops >= 30
        self.matrix_drops[reset_mask] = 0
        return self.matrix_drops

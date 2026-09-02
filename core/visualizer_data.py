import math
import random
import numpy as np

class VisualizerGenerator:
    def __init__(self, num_bars=19):
        self.num_bars = num_bars
        self.bars = np.zeros(num_bars, dtype=np.float32)
        self.peaks = np.zeros(num_bars, dtype=np.float32)
        self.peak_speeds = np.zeros(num_bars, dtype=np.float32)
        self.phase = 0.0
        self.decay = 0.82
        self.gravity = 0.025

    def update(self, is_playing, volume=80):
        if not is_playing:
            # Decay to zero
            self.bars *= 0.75
            self.peaks -= self.peak_speeds
            self.peak_speeds += self.gravity
            self.peaks = np.maximum(self.peaks, self.bars)
            self.peaks = np.maximum(self.peaks, 0.0)
            return self.bars, self.peaks

        self.phase += 0.18
        vol_factor = (volume / 100.0)
        
        # Generate dynamic rhythmic frequency bands
        for i in range(self.num_bars):
            freq = (i + 1) * 0.7
            harmonic1 = math.sin(self.phase * freq + i * 0.4)
            harmonic2 = math.cos(self.phase * 0.8 + i * 0.9)
            noise = random.uniform(-0.15, 0.15)
            
            # Bass emphasis on lower bands (0..5), treble flutter on upper bands (12..18)
            curve = 1.0 - (i / self.num_bars) * 0.35
            val = (abs(harmonic1 * 0.6 + harmonic2 * 0.4) + noise) * curve * vol_factor
            val = max(0.05, min(1.0, val))

            # Smooth bar motion
            if val > self.bars[i]:
                self.bars[i] = val
            else:
                self.bars[i] = self.bars[i] * self.decay + val * (1.0 - self.decay)

            # Peak dots physics
            if self.bars[i] >= self.peaks[i]:
                self.peaks[i] = self.bars[i]
                self.peak_speeds[i] = 0.005
            else:
                self.peaks[i] -= self.peak_speeds[i]
                self.peak_speeds[i] += self.gravity

            self.peaks[i] = max(0.0, min(1.0, self.peaks[i]))

        return self.bars, self.peaks

    def get_oscilloscope_wave(self, is_playing, num_points=70, volume=80):
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

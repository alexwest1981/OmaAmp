import math
import numpy as np
import scipy.signal as signal

BAND_FREQUENCIES = [60, 170, 310, 600, 1000, 3000, 6000, 12000, 14000, 16000]

class DspEqualizer:
    def __init__(self, sample_rate=44100):
        self.sample_rate = sample_rate
        self.enabled = True
        self.preamp_gain = 1.0
        self.bands = [0.0] * len(BAND_FREQUENCIES)
        self.sos_matrix = None
        self.zi = None
        self.recalculate_filters()

    def set_sample_rate(self, sr):
        if sr != self.sample_rate and sr > 0:
            self.sample_rate = sr
            self.recalculate_filters()

    def set_params(self, bands, preamp, enabled=True):
        self.enabled = enabled
        self.bands = list(bands)
        # Preamp slider: -10 to +10 mapped to -12dB to +12dB
        preamp_db = (preamp / 10.0) * 12.0
        self.preamp_gain = 10.0 ** (preamp_db / 20.0)
        self.recalculate_filters()

    def recalculate_filters(self):
        sos_list = []
        fs = self.sample_rate

        for f0, gain_slider in zip(BAND_FREQUENCIES, self.bands):
            # Slider -10 to +10 mapped to -14dB to +14dB for noticeable audible impact
            gain_db = (gain_slider / 10.0) * 14.0
            
            # Avoid Nyquist violation
            if f0 >= fs / 2.0:
                f0 = (fs / 2.0) - 100.0

            if abs(gain_db) < 0.1:
                # Passthrough filter
                sos_list.append([1.0, 0.0, 0.0, 1.0, 0.0, 0.0])
            else:
                # RBJ Peaking EQ Biquad Filter Formula
                A = 10.0 ** (gain_db / 40.0)
                w0 = 2.0 * math.pi * f0 / fs
                q = 1.414  # ~1 octave bandwidth
                alpha = math.sin(w0) / (2.0 * q)
                cos_w0 = math.cos(w0)

                b0 = 1.0 + alpha * A
                b1 = -2.0 * cos_w0
                b2 = 1.0 - alpha * A
                a0 = 1.0 + alpha / A
                a1 = -2.0 * cos_w0
                a2 = 1.0 - alpha / A

                sos_list.append([b0 / a0, b1 / a0, b2 / a0, 1.0, a1 / a0, a2 / a0])

        self.sos_matrix = np.array(sos_list, dtype=np.float64)
        # 10 filters, 2 channels, 2 states
        if self.zi is None or self.zi.shape[0] != len(sos_list):
            self.zi = np.zeros((len(sos_list), 2, 2), dtype=np.float64)

    def process(self, audio_chunk):
        """
        Processes an (N, 2) float32 stereo audio chunk through the 10-band EQ.
        """
        if not self.enabled:
            return audio_chunk

        # Apply Preamp
        out = audio_chunk * self.preamp_gain

        # Apply 10-Band Biquad Cascade
        if self.sos_matrix is not None:
            out, self.zi = signal.sosfilt(self.sos_matrix, out, axis=0, zi=self.zi)

        # Soft-knee analog limiter to avoid harsh digital clipping when boosted
        peak = np.max(np.abs(out))
        if peak > 0.98:
            out = np.tanh(out * 0.95)

        return out.astype(np.float32)

"""Prov för strömmens samplingsfrekvens.

Bakgrund: den utgående strömmen var låst till 44,1 kHz medan lokala spår behåller
filens egen takt (soundfile ger WAV:ens 48 kHz, miniaudio ger MP3:ans 44,1 kHz).
Ett 48 kHz-spår spelades därför 9 % långsammare och lägre — samma musik lät olika
beroende på vilken takt filen råkade ha, utan att något sade ifrån.

    QT_QPA_PLATFORM=offscreen python3 -m unittest tests.test_stream_rate -v
"""

import os
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication  # noqa: E402

from core import audio_engine as ae  # noqa: E402
from core.audio_engine import AudioEngine  # noqa: E402

APP = QApplication.instance() or QApplication([])


class _FalskStrom:
    def start(self):
        pass

    def stop(self):
        pass

    def close(self):
        pass


class StreamRateTest(unittest.TestCase):
    def setUp(self):
        self.engine = AudioEngine()
        self.oppnade = []
        self.riktig = ae.sd.OutputStream
        ae.sd.OutputStream = lambda **kw: (self.oppnade.append(kw), _FalskStrom())[1]
        self.addCleanup(lambda: setattr(ae.sd, "OutputStream", self.riktig))

    def test_48k_spar_oppnar_48k_strom(self):
        self.engine.is_live_stream = False
        self.engine.sample_rate = 48000
        self.engine._start_stream()
        self.assertEqual(self.oppnade[-1]["samplerate"], 48000)

    def test_441k_spar_oppnar_44100_strom(self):
        self.engine.is_live_stream = False
        self.engine.sample_rate = 44100
        self.engine._start_stream()
        self.assertEqual(self.oppnade[-1]["samplerate"], 44100)

    def test_live_strom_ar_alltid_44100(self):
        # sample_rate kan vara kvarglömd från ett 48 kHz-spår — live ska ändå gå i 44100
        self.engine.sample_rate = 48000
        self.engine.is_live_stream = True
        self.engine._start_stream()
        self.assertEqual(self.oppnade[-1]["samplerate"], 44100)


if __name__ == "__main__":
    unittest.main()

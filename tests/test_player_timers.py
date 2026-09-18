"""Prov för renderingslooparna: de ska bara gå när de syns och spelar.

Bakgrund: visualiseringen och den skinnade spelaren tickade 50 gånger i
sekunden dygnet runt — även med fönstret dolt och musiken stoppad — och
LCD-vinylen 25 gånger i sekunden i paus. Provet mäter att looparna står still
när det inte finns något att rita.

    QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -v
"""

import os
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication  # noqa: E402

from core.audio_engine import AudioEngine  # noqa: E402
from core.config import ConfigManager  # noqa: E402
from core.theme_manager import ThemeManager  # noqa: E402
from ui.lcd_display import LcdDisplay, MarqueeDisplay  # noqa: E402
from ui.main_window import MainWindow  # noqa: E402
from ui.skinned_player import SkinnedPlayerWidget  # noqa: E402

APP = QApplication.instance() or QApplication([])


class TimerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.theme_mgr = ThemeManager()
        cls.config_mgr = ConfigManager()

    def setUp(self):
        self.engine = AudioEngine()

    def drive(self, playing):
        """Samma väg som speltiden tar: flaggan sätts och signalen går ut."""
        self.engine.is_playing = playing
        self.engine.playback_state_changed.emit(playing)
        APP.processEvents()

    def test_visualizer_loop_only_runs_while_playing_and_visible(self):
        win = MainWindow(self.engine, self.theme_mgr, self.config_mgr)
        win.show()
        APP.processEvents()
        vis = win.vis

        self.assertFalse(vis.timer.isActive(), "stoppad ska stå still")

        self.drive(True)
        self.assertTrue(vis.timer.isActive(), "spelande och synlig ska ticka")

        self.drive(False)
        self.assertFalse(vis.timer.isActive(), "paus ska stanna loopen")

        self.drive(True)
        vis.hide()
        APP.processEvents()
        self.assertFalse(vis.timer.isActive(), "dold ska stanna loopen")
        win.close()

    def test_lcd_vinyl_and_marquee_follow_playback_and_visibility(self):
        lcd = LcdDisplay(self.theme_mgr)
        lcd.show()
        APP.processEvents()
        self.assertFalse(lcd.anim_timer.isActive(), "ingen skiva i paus")

        lcd.set_playing(True)
        APP.processEvents()
        self.assertTrue(lcd.anim_timer.isActive(), "vinylen snurrar medan den spelas")

        lcd.hide()
        APP.processEvents()
        self.assertFalse(lcd.anim_timer.isActive(), "dold skiva ska stå still")

        marquee = MarqueeDisplay(self.theme_mgr)
        marquee.show()
        APP.processEvents()
        self.assertTrue(marquee.scroll_timer.isActive(), "texten rullar när den syns")
        marquee.hide()
        APP.processEvents()
        self.assertFalse(marquee.scroll_timer.isActive(), "dold text ska stå still")

    def test_skinned_player_loops_follow_playback_and_visibility(self):
        player = SkinnedPlayerWidget(self.engine, self.theme_mgr)
        player.show()
        APP.processEvents()
        self.assertFalse(player.timer.isActive(), "stoppad ska stå still")
        self.assertTrue(player.scroll_timer.isActive(), "synlig marquee ska rulla")

        self.drive(True)
        self.assertTrue(player.timer.isActive(), "spelande och synlig ska ticka")

        player.hide()
        APP.processEvents()
        self.assertFalse(player.timer.isActive(), "dold ska stanna 50 FPS-loopen")
        self.assertFalse(player.scroll_timer.isActive(), "dold ska stanna marquee")


if __name__ == "__main__":
    unittest.main(verbosity=2)

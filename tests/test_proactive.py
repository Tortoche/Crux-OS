import time
import unittest
from core.proactive.daemon import ProactiveDaemon

class TestProactiveDaemon(unittest.TestCase):
    def setUp(self):
        self.events = []
        self.daemon = ProactiveDaemon(
            check_interval=0.1,
            cooldown_seconds=1.0,
            on_event_callback=lambda title, msg: self.events.append((title, msg))
        )

    def tearDown(self):
        if self.daemon.is_running():
            self.daemon.stop()

    def test_idle_time_and_fullscreen_detection(self):
        idle = self.daemon.get_idle_time_seconds()
        self.assertIsInstance(idle, float)
        self.assertGreaterEqual(idle, 0.0)

        is_game = self.daemon.is_fullscreen_game_active()
        self.assertIsInstance(is_game, bool)

    def test_daemon_lifecycle(self):
        self.assertFalse(self.daemon.is_running())
        self.daemon.start()
        self.assertTrue(self.daemon.is_running())
        self.daemon.stop()
        self.assertFalse(self.daemon.is_running())

    def test_audio_active_suppression(self):
        class MockTTS:
            is_speaking = True

        daemon_with_audio = ProactiveDaemon(
            tts=MockTTS(),
            on_event_callback=lambda title, msg: self.events.append((title, msg))
        )
        self.assertTrue(daemon_with_audio.is_audio_active())
        self.assertFalse(daemon_with_audio.can_notify())

        # Déclenchement bloqué si audio actif
        daemon_with_audio.trigger_proactive_event("Alerte Audio", "Message non envoyé.")
        self.assertEqual(len(self.events), 0)

if __name__ == "__main__":
    unittest.main()

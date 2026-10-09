import unittest
from unittest.mock import MagicMock
from core.handoff.manager import HandoffManager
from core.agent import CruxAgent

class TestHandoffManager(unittest.TestCase):
    def setUp(self):
        self.handoff = HandoffManager()
        self.mock_agent = MagicMock()
        self.mock_agent.tts = MagicMock()
        self.mock_agent.sys = MagicMock()
        self.mock_agent.memory = MagicMock()
        self.mock_agent.computer_use = MagicMock()
        self.handoff.agent = self.mock_agent

    def test_initial_state(self):
        self.assertEqual(self.handoff.active_node, "pc")
        status = self.handoff.get_status()
        self.assertEqual(status["active_node"], "pc")

    def test_transfer_to_mobile(self):
        reply, is_exit = self.handoff.transfer_to_mobile(self.mock_agent)
        self.assertEqual(self.handoff.active_node, "mobile")
        self.assertTrue(is_exit)
        self.assertIn("téléphone", reply.lower())
        self.assertIn("veille", reply.lower())

    def test_resume_on_pc(self):
        self.handoff.active_node = "mobile"
        reply, is_exit = self.handoff.resume_on_pc(self.mock_agent)
        self.assertEqual(self.handoff.active_node, "pc")
        self.assertFalse(is_exit)
        self.assertIn("pc", reply.lower())
        self.assertIn("pl2766h", reply.lower())
        self.mock_agent.tts.set_target_device.assert_called_with("screen")

    def test_execute_remote_commands(self):
        # Multimédia Play/Pause
        res_play = self.handoff.execute_remote_command("media_play_pause", agent=self.mock_agent)
        self.assertTrue(res_play["success"])
        self.mock_agent.sys.media_play_pause.assert_called_once()

        # Volume Up
        res_vol = self.handoff.execute_remote_command("volume_up", {"steps": 4}, agent=self.mock_agent)
        self.assertTrue(res_vol["success"])
        self.mock_agent.sys.volume_up.assert_called_with(steps=4)

        # Show desktop
        res_desk = self.handoff.execute_remote_command("show_desktop", agent=self.mock_agent)
        self.assertTrue(res_desk["success"])
        self.mock_agent.sys.minimize_all_windows.assert_called_once()

        # Switch audio to screen PL2766H
        res_audio = self.handoff.execute_remote_command("switch_audio_screen", agent=self.mock_agent)
        self.assertTrue(res_audio["success"])
        self.mock_agent.tts.set_target_device.assert_called_with("screen")

        # Unknown command
        res_unknown = self.handoff.execute_remote_command("unknown_xyz")
        self.assertFalse(res_unknown["success"])

    def test_agent_handoff_voice_triggers(self):
        agent = CruxAgent()
        
        # Test trigger transfert vers mobile
        rep_mob, exit_mob = agent.process_command("Crux passe sur mon téléphone")
        self.assertTrue(exit_mob)
        self.assertIn("téléphone", rep_mob.lower())
        self.assertEqual(agent.handoff.active_node, "mobile")

        # Test trigger reprise sur PC
        rep_pc, exit_pc = agent.process_command("Crux reprends sur le PC")
        self.assertFalse(exit_pc)
        self.assertIn("pc", rep_pc.lower())
        self.assertEqual(agent.handoff.active_node, "pc")

if __name__ == "__main__":
    unittest.main()

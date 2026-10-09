import unittest
from core.agent_tools.computer_use import ComputerUseController

class TestComputerUse(unittest.TestCase):
    def setUp(self):
        self.controller = ComputerUseController()

    def test_mouse_position(self):
        pos = self.controller.get_mouse_position()
        self.assertIsInstance(pos, tuple)
        self.assertEqual(len(pos), 2)
        self.assertIsInstance(pos[0], int)
        self.assertIsInstance(pos[1], int)

    def test_window_listing_and_title(self):
        title = self.controller.get_active_window_title()
        self.assertIsInstance(title, str)
        windows = self.controller.list_visible_windows()
        self.assertIsInstance(windows, list)

    def test_critical_action_guardrails(self):
        # Action critique : fermeture de fenêtre
        is_crit, msg = self.controller.is_critical_action("close_window", {"title_pattern": "notepad"})
        self.assertTrue(is_crit)
        self.assertIn("notepad", msg)

        # Action non-critique : clic souris ou déplacement
        is_crit_mouse, _ = self.controller.is_critical_action("mouse_click", {})
        self.assertFalse(is_crit_mouse)

        # Action critique : Alt+F4
        is_crit_hotkey, _ = self.controller.is_critical_action("keyboard_hotkey", {"keys": ["alt", "f4"]})
        self.assertTrue(is_crit_hotkey)

    def test_confirmation_workflow(self):
        self.assertFalse(self.controller.has_pending_confirmation())
        self.controller.request_confirmation("close_window", {"title_pattern": "test_win"}, "Confirmer fermeture ?")
        self.assertTrue(self.controller.has_pending_confirmation())

        # Annulation
        msg_cancel = self.controller.cancel_pending_action()
        self.assertIn("annulée", msg_cancel)
        self.assertFalse(self.controller.has_pending_confirmation())

    def test_run_script_guardrail_and_execution(self):
        # Vérification action critique run_script
        is_crit, msg = self.controller.is_critical_action("run_script", {"script": "build.py"})
        self.assertTrue(is_crit)
        self.assertIn("build.py", msg)

        # Validation de touches valides
        self.assertTrue(self.controller.is_valid_key("ctrl"))
        self.assertTrue(self.controller.is_valid_key("alt"))
        self.assertTrue(self.controller.is_valid_key("a"))
        self.assertFalse(self.controller.is_valid_key("invalid_key_xyz"))

        # Confirmation workflow run_script
        self.controller.request_confirmation("run_script", {"script": "non_existent.py"}, "Confirmer ?")
        self.assertTrue(self.controller.has_pending_confirmation())
        ok, res_msg = self.controller.execute_confirmed_action()
        self.assertFalse(ok)
        self.assertIn("introuvable", res_msg)
        self.assertFalse(self.controller.has_pending_confirmation())

if __name__ == "__main__":
    unittest.main()

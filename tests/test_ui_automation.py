import unittest
from unittest.mock import MagicMock, patch
from core.agent_tools.ui_automation import UIAutomationEngine

class TestUIAutomationEngine(unittest.TestCase):
    def test_availability(self):
        self.assertTrue(UIAutomationEngine.is_available())

    def test_dump_window_summary_string_result(self):
        summary = UIAutomationEngine.dump_window_summary()
        self.assertIsInstance(summary, str)
        self.assertTrue(len(summary) > 0)

    def test_inspect_active_window_list_result(self):
        elems = UIAutomationEngine.inspect_active_window()
        self.assertIsInstance(elems, list)

    def test_click_control_not_found(self):
        ok, msg = UIAutomationEngine.click_control(name="NonExistentControlXYZ_123")
        self.assertFalse(ok)
        self.assertIn("introuvable", msg)

    def test_set_control_value_not_found(self):
        ok, msg = UIAutomationEngine.set_control_value("text", name="NonExistentControlXYZ_123")
        self.assertFalse(ok)
        self.assertIn("introuvable", msg)

    def test_mock_control_invoke(self):
        mock_ctrl = MagicMock()
        mock_ctrl.Name = "Bouton Valider"
        mock_invoke = MagicMock()
        mock_ctrl.GetInvokePattern.return_value = mock_invoke

        with patch.object(UIAutomationEngine, 'find_control', return_value=mock_ctrl):
            ok, msg = UIAutomationEngine.click_control(name="Valider")
            self.assertTrue(ok)
            mock_invoke.Invoke.assert_called_once()
            self.assertIn("Invoke", msg)

    def test_mock_control_set_value(self):
        mock_ctrl = MagicMock()
        mock_ctrl.Name = "Champ Recherche"
        mock_val_pattern = MagicMock()
        mock_ctrl.GetValuePattern.return_value = mock_val_pattern

        with patch.object(UIAutomationEngine, 'find_control', return_value=mock_ctrl):
            ok, msg = UIAutomationEngine.set_control_value("Jarvis", name="Recherche")
            self.assertTrue(ok)
            mock_val_pattern.SetValue.assert_called_once_with("Jarvis")
            self.assertIn("injectée", msg)

    def test_find_window_and_window_title_targeting(self):
        mock_win = MagicMock()
        mock_win.Name = "Bloc-notes"
        mock_btn = MagicMock()
        mock_btn.Name = "Fermer"
        mock_invoke = MagicMock()
        mock_btn.GetInvokePattern.return_value = mock_invoke

        with patch.object(UIAutomationEngine, 'find_window', return_value=mock_win), \
             patch.object(UIAutomationEngine, 'find_control', return_value=mock_btn) as mock_fc:
            ok, msg = UIAutomationEngine.click_control(name="Fermer", window_title="Bloc-notes")
            self.assertTrue(ok)
            mock_fc.assert_called_once_with(
                name="Fermer",
                control_type=None,
                automation_id=None,
                parent=None,
                window_title="Bloc-notes"
            )

    def test_dump_window_summary_with_window_title(self):
        with patch.object(UIAutomationEngine, 'inspect_active_window', return_value=[{"name": "OK", "type": "Button", "automation_id": "1"}]) as mock_insp:
            summary = UIAutomationEngine.dump_window_summary(window_title="Calculatrice")
            self.assertIn("[Button] OK", summary)
            mock_insp.assert_called_once_with(max_depth=2, window_title="Calculatrice")

if __name__ == "__main__":
    unittest.main()

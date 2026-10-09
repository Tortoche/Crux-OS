import unittest
from unittest.mock import MagicMock, patch
from core.ui_generator.generator import DynamicUIDesigner
from core.ui_generator.runtime import DynamicUIRuntime

class TestDynamicUI(unittest.TestCase):
    def setUp(self):
        self.designer = DynamicUIDesigner()
        self.mock_hud = MagicMock()
        self.runtime = DynamicUIRuntime(designer=self.designer, hud=self.mock_hud)

    def test_designer_generates_activities_ui(self):
        view = self.designer.generate_html_from_prompt("affiche mes activités à faire")
        self.assertIn("Activités & Tâches", view["title"])
        self.assertIn("crux-ui-wrapper", view["html"])
        self.assertIn("crux-task-item", view["html"])
        self.assertEqual(view["type"], "activities")

    def test_designer_generates_crypto_ui(self):
        view = self.designer.generate_html_from_prompt("affiche le cours du bitcoin et de la crypto")
        self.assertIn("Marchés & Crypto", view["title"])
        self.assertIn("Bitcoin", view["html"])
        self.assertEqual(view["type"], "crypto")

    def test_designer_generates_monitor_ui(self):
        view = self.designer.generate_html_from_prompt("monitoring système et performance du processeur")
        self.assertIn("Télémétrie Système", view["title"])
        self.assertIn("Processeur (CPU)", view["html"])
        self.assertEqual(view["type"], "monitor")

    def test_runtime_render_sends_coucou_event(self):
        view = self.runtime.render_from_prompt("affiche mes activités")
        self.mock_hud.send_event.assert_called_once()
        args = self.mock_hud.send_event.call_args[0]
        self.assertEqual(args[0], "dynamic_ui")
        self.assertEqual(args[1]["action"], "show")
        self.assertIn("crux-ui-wrapper", args[1]["html"])

    def test_runtime_append_task_live(self):
        initial_count = len(self.runtime.tasks_store)
        new_task = self.runtime.append_task("Nouvelle tâche de test", tag="Test")
        self.assertEqual(len(self.runtime.tasks_store), initial_count + 1)
        self.assertEqual(new_task["text"], "Nouvelle tâche de test")
        self.assertFalse(new_task["done"])

    def test_runtime_toggle_and_delete_task(self):
        new_task = self.runtime.append_task("Tâche à basculer")
        task_id = new_task["id"]
        
        # Toggle done
        is_done = self.runtime.toggle_task(task_id)
        self.assertTrue(is_done)

        # Toggle back
        is_done = self.runtime.toggle_task(task_id)
        self.assertFalse(is_done)

        # Delete
        deleted = self.runtime.delete_task(task_id)
        self.assertTrue(deleted)
        self.assertNotIn(task_id, [t["id"] for t in self.runtime.tasks_store])

    def test_runtime_close(self):
        self.runtime.close()
        self.mock_hud.send_event.assert_called_with("dynamic_ui", {"action": "hide"})

    @patch('core.agent.genai.Client')
    def test_crux_agent_dynamic_ui_command(self, mock_genai):
        from core.agent import CruxAgent
        agent = CruxAgent()
        agent.hud = MagicMock()
        agent.ui_runtime.hud = agent.hud

        reply, is_exit = agent.process_command("Crux affiche mes activités à faire")
        self.assertFalse(is_exit)
        self.assertIn("générée et affichée dans la bulle", reply)
        agent.hud.send_event.assert_called()
        self.assertEqual(agent.hud.send_event.call_args[0][0], "dynamic_ui")

if __name__ == "__main__":
    unittest.main()

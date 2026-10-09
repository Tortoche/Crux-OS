import unittest
from core.plugins.base import BasePlugin
from core.plugins.iot_lighting import IoTLightingPlugin
from core.plugins.manager import PluginManager

class DummyTestPlugin(BasePlugin):
    name = "dummy_plugin"
    version = "1.0.0"

    def get_tools(self):
        return [{"name": "dummy_action", "description": "dummy test"}]

    def execute_action(self, action_name, params):
        return {"success": True, "action": action_name, "params": params}

    def can_handle_command(self, user_text):
        return "dummy test command" in user_text.lower()

    def handle_voice_command(self, user_text):
        return "Ordre dummy exécuté.", False

class TestPlugins(unittest.TestCase):
    def setUp(self):
        self.pm = PluginManager()

    def test_iot_lighting_plugin_actions(self):
        plugin = IoTLightingPlugin({"endpoint_url": "mock://localhost"})
        # 1. Turn on
        res_on = plugin.execute_action("turn_on", {"brightness": 80, "color": "bleu"})
        self.assertTrue(res_on["success"])
        self.assertEqual(plugin.state["power"], "on")
        self.assertEqual(plugin.state["brightness"], 80)
        self.assertEqual(plugin.state["color"], "bleu")

        # 2. Turn off
        res_off = plugin.execute_action("turn_off", {})
        self.assertTrue(res_off["success"])
        self.assertEqual(plugin.state["power"], "off")

        # 3. Toggle
        res_toggle = plugin.execute_action("toggle", {})
        self.assertTrue(res_toggle["success"])
        self.assertEqual(plugin.state["power"], "on")

    def test_iot_lighting_voice_commands(self):
        plugin = IoTLightingPlugin()
        self.assertTrue(plugin.can_handle_command("Crux allume la lumière du bureau"))
        self.assertTrue(plugin.can_handle_command("Éteins les lumières"))

        resp, is_exit = plugin.handle_voice_command("Allume la lumière")
        self.assertFalse(is_exit)
        self.assertIn("allumée", resp)

        resp_off, _ = plugin.handle_voice_command("Éteins la lumière")
        self.assertIn("éteinte", resp_off)

        resp_col, _ = plugin.handle_voice_command("Mets la lumière en rouge")
        self.assertIn("rouge", resp_col)

    def test_plugin_manager_lifecycle_and_routing(self):
        dummy = DummyTestPlugin()
        self.pm.register_plugin(dummy)
        self.assertIsNotNone(self.pm.get_plugin("dummy_plugin"))

        # Vérification des tools combinés
        tools = self.pm.get_all_tools()
        self.assertTrue(any(t["name"] == "dummy_action" for t in tools))
        self.assertTrue(any(t["name"] == "lighting_control" for t in tools))

        # Routage direct vers dummy
        routed = self.pm.route_voice_command("Execute dummy test command")
        self.assertIsNotNone(routed)
        self.assertEqual(routed[0], "Ordre dummy exécuté.")

        # Routage vers lumière
        routed_light = self.pm.route_voice_command("Tamise la lumière")
        self.assertIsNotNone(routed_light)
        self.assertIn("tamisée", routed_light[0])

        self.pm.unregister_plugin("dummy_plugin")
        self.assertIsNone(self.pm.get_plugin("dummy_plugin"))

if __name__ == "__main__":
    unittest.main()

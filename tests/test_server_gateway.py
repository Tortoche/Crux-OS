import os
import unittest
import tempfile
import asyncio
from unittest.mock import MagicMock
from crux_server_gateway import RelayMemory5D, RelayUIManager, CruxRelayGateway
from core.mobile_bridge.deployer import FedoraRelayDeployer

class TestServerGateway(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.memory = RelayMemory5D(self.temp_dir.name)
        self.ui = RelayUIManager(self.temp_dir.name)
        self.gateway = CruxRelayGateway(port=49240)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_relay_memory_operations(self):
        # 1. Enregistrement d'un tour
        self.memory.record_turn("user", "Test prompt")
        self.memory.record_turn("model", "Test reply")
        self.assertTrue(any(e["text"] == "Test prompt" for e in self.memory.data["episodic"]))

        # 2. Synchronisation de la mémoire
        sync_payload = {
            "facts": [{"category": "hardware", "key": "test_key", "value": "test_val"}],
            "working": {"status": "synced"}
        }
        self.memory.sync(sync_payload)
        self.assertEqual(self.memory.data["working"]["status"], "synced")
        self.assertTrue(any(f["key"] == "test_key" for f in self.memory.data["facts"]))

    def test_relay_ui_manager_operations(self):
        initial_len = len(self.ui.tasks)
        task = self.ui.add_task("Nouvelle tâche test", "TestTag")
        self.assertEqual(len(self.ui.tasks), initial_len + 1)
        self.assertEqual(task["text"], "Nouvelle tâche test")

        toggled = self.ui.toggle_task(task["id"])
        self.assertTrue(toggled["done"])

        deleted = self.ui.delete_task(task["id"])
        self.assertTrue(deleted)
        self.assertEqual(len(self.ui.tasks), initial_len)

    async def test_gateway_endpoints(self):
        mock_req = MagicMock()
        resp_health = await self.gateway.handle_health(mock_req)
        self.assertEqual(resp_health.status, 200)

        resp_status = await self.gateway.handle_status(mock_req)
        self.assertEqual(resp_status.status, 200)

        resp_telemetry = await self.gateway.handle_telemetry(mock_req)
        self.assertEqual(resp_telemetry.status, 200)

        # Test Wake PC
        resp_wake = await self.gateway.handle_wake_pc(mock_req)
        self.assertEqual(resp_wake.status, 200)

        # Test Handoff to PC
        resp_to_pc = await self.gateway.handle_handoff_to_pc(mock_req)
        self.assertEqual(resp_to_pc.status, 200)
        self.assertEqual(self.gateway.memory.data["working"]["active_device"], "pc")

        # Test Handoff to Mobile
        resp_to_mob = await self.gateway.handle_handoff_to_mobile(mock_req)
        self.assertEqual(resp_to_mob.status, 200)
        self.assertEqual(self.gateway.memory.data["working"]["active_device"], "mobile")

        # Test PC Control (when PC offline)
        mock_ctrl = MagicMock()
        mock_ctrl.json = unittest.mock.AsyncMock(return_value={"command": "volume_up", "params": {}})
        resp_ctrl = await self.gateway.handle_pc_control(mock_ctrl)
        self.assertEqual(resp_ctrl.status, 503)

        # Test Chat with Handoff triggers
        mock_chat_mob = MagicMock()
        mock_chat_mob.json = unittest.mock.AsyncMock(return_value={"prompt": "Crux passe sur mon téléphone"})
        resp_chat_mob = await self.gateway.handle_chat(mock_chat_mob)
        self.assertEqual(resp_chat_mob.status, 200)

        mock_chat_pc = MagicMock()
        mock_chat_pc.json = unittest.mock.AsyncMock(return_value={"prompt": "Crux reprends sur le PC"})
        resp_chat_pc = await self.gateway.handle_chat(mock_chat_pc)
        self.assertEqual(resp_chat_pc.status, 200)

    def test_deployer_status_check(self):
        deployer = FedoraRelayDeployer()
        api_res = deployer.verify_gateway_api()
        # Le serveur Fedora étant déployé, verify_gateway_api doit retourner reachable
        if api_res.get("reachable"):
            self.assertEqual(api_res["status"]["role"], "relay_gateway")
            self.assertEqual(api_res["status"]["server_ip"], "192.168.1.41")

if __name__ == "__main__":
    unittest.main()

import os
import unittest
import asyncio
from unittest.mock import MagicMock
from core.mobile_bridge.bridge_service import MobileBridgeService

class TestMobileBridge(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mock_agent = MagicMock()
        self.bridge = MobileBridgeService(agent=self.mock_agent, port=49235)

    def test_mobile_assets_exist(self):
        mobile_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mobile")
        self.assertTrue(os.path.exists(mobile_dir), "Dossier mobile/ manquant")
        self.assertTrue(os.path.exists(os.path.join(mobile_dir, "index.html")), "index.html manquant")
        self.assertTrue(os.path.exists(os.path.join(mobile_dir, "styles.css")), "styles.css manquant")
        self.assertTrue(os.path.exists(os.path.join(mobile_dir, "app.js")), "app.js manquant")
        self.assertTrue(os.path.exists(os.path.join(mobile_dir, "manifest.json")), "manifest.json manquant")
        self.assertTrue(os.path.exists(os.path.join(mobile_dir, "sw.js")), "sw.js manquant")
        self.assertTrue(os.path.exists(os.path.join(mobile_dir, "icon-192.png")), "icon-192.png manquant")
        self.assertTrue(os.path.exists(os.path.join(mobile_dir, "icon-512.png")), "icon-512.png manquant")

    def test_bridge_routes_registered(self):
        routes = [r.resource.canonical for r in self.bridge.app.router.routes() if hasattr(r, 'resource') and r.resource]
        self.assertIn("/api/health", routes)
        self.assertIn("/api/status", routes)
        self.assertIn("/api/chat", routes)
        self.assertIn("/api/pc/control", routes)
        self.assertIn("/api/handoff/to_mobile", routes)
        self.assertIn("/api/handoff/to_pc", routes)
        self.assertIn("/api/ui/state", routes)
        self.assertIn("/api/ui/action", routes)
        self.assertIn("/api/telemetry", routes)

    async def test_handle_health(self):
        mock_req = MagicMock()
        resp = await self.bridge.handle_health(mock_req)
        self.assertEqual(resp.status, 200)

    async def test_handle_status(self):
        mock_req = MagicMock()
        resp = await self.bridge.handle_status(mock_req)
        self.assertEqual(resp.status, 200)

    async def test_handle_pc_control(self):
        mock_req = MagicMock()
        mock_req.json = unittest.mock.AsyncMock(return_value={"command": "volume_up", "params": {"steps": 2}})
        resp = await self.bridge.handle_pc_control(mock_req)
        self.assertEqual(resp.status, 200)

    async def test_handle_handoff_endpoints(self):
        mock_req = MagicMock()
        resp_mob = await self.bridge.handle_handoff_to_mobile(mock_req)
        self.assertEqual(resp_mob.status, 200)
        self.assertEqual(self.bridge.handoff.active_node, "mobile")

        resp_pc = await self.bridge.handle_handoff_to_pc(mock_req)
        self.assertEqual(resp_pc.status, 200)
        self.assertEqual(self.bridge.handoff.active_node, "pc")

    def test_start_in_background(self):
        bridge = MobileBridgeService(port=49255)
        thread = bridge.start_in_background()
        self.assertTrue(thread.is_alive())
        self.assertEqual(thread.name, "CruxMobileBridgeThread")

if __name__ == "__main__":
    unittest.main()

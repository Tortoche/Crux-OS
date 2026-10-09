import unittest
from core.agent_tools.system_telemetry import SystemTelemetryEngine

class TestSystemTelemetryEngine(unittest.TestCase):
    def test_get_telemetry_structure(self):
        telem = SystemTelemetryEngine.get_system_telemetry()
        self.assertIn("cpu", telem)
        self.assertIn("memory", telem)
        self.assertIn("disks", telem)
        self.assertIn("network", telem)
        self.assertIn("uptime_formatted", telem)
        self.assertIsInstance(telem["cpu"]["percent"], (int, float))
        self.assertIsInstance(telem["memory"]["percent"], (int, float))

    def test_format_telemetry_summary(self):
        summary = SystemTelemetryEngine.format_telemetry_summary()
        self.assertIsInstance(summary, str)
        self.assertIn("Processeur", summary)
        self.assertIn("RAM", summary)

    def test_list_processes(self):
        procs_cpu = SystemTelemetryEngine.list_processes(sort_by="cpu", limit=5)
        self.assertIsInstance(procs_cpu, list)
        self.assertLessEqual(len(procs_cpu), 5)
        if procs_cpu:
            self.assertIn("pid", procs_cpu[0])
            self.assertIn("name", procs_cpu[0])

        procs_ram = SystemTelemetryEngine.list_processes(sort_by="ram", limit=5)
        self.assertIsInstance(procs_ram, list)
        self.assertLessEqual(len(procs_ram), 5)

    def test_format_top_processes_summary(self):
        summary = SystemTelemetryEngine.format_top_processes_summary(sort_by="cpu", limit=3)
        self.assertIsInstance(summary, str)
        self.assertTrue(len(summary) > 0)

    def test_get_process_info_for_current_process(self):
        import os
        current_pid = os.getpid()
        info = SystemTelemetryEngine.get_process_info(current_pid)
        self.assertIsNotNone(info)
        self.assertEqual(info["pid"], current_pid)
        self.assertIn("python", info["name"].lower())

    def test_get_process_info_non_existent(self):
        info = SystemTelemetryEngine.get_process_info(99999999)
        self.assertIsNone(info)

if __name__ == "__main__":
    unittest.main()

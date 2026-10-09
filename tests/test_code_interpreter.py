import unittest
from core.agent_tools.code_interpreter import CodeInterpreterEngine

class TestCodeInterpreterEngine(unittest.TestCase):
    def test_run_command_echo(self):
        res = CodeInterpreterEngine.run_command("Write-Output 'Hello Jarvis'", shell="powershell")
        self.assertTrue(res["success"])
        self.assertIn("Hello Jarvis", res["stdout"])
        self.assertEqual(res["returncode"], 0)

    def test_run_python(self):
        code = "print(10 * 10)"
        res = CodeInterpreterEngine.run_python(code)
        self.assertTrue(res["success"])
        self.assertEqual(res["stdout"], "100")

    def test_is_dangerous_detection(self):
        is_d, msg = CodeInterpreterEngine.is_dangerous("Format C:")
        self.assertTrue(is_d)
        self.assertIn("sensible", msg)

        is_d2, msg2 = CodeInterpreterEngine.is_dangerous("Remove-Item -Recurse C:\\Windows")
        self.assertTrue(is_d2)

        is_safe, _ = CodeInterpreterEngine.is_dangerous("Get-Process")
        self.assertFalse(is_safe)

    def test_empty_command(self):
        res = CodeInterpreterEngine.run_command("")
        self.assertFalse(res["success"])

    def test_dangerous_python_and_cmd_patterns(self):
        self.assertTrue(CodeInterpreterEngine.is_dangerous("shutil.rmtree('/tmp')")[0])
        self.assertTrue(CodeInterpreterEngine.is_dangerous("os.remove('sys.dll')")[0])
        self.assertTrue(CodeInterpreterEngine.is_dangerous("rd /s /q testdir")[0])

    def test_unicode_command_output(self):
        res = CodeInterpreterEngine.run_command("Write-Output 'Écran ViewSonic & PL2766H'", shell="powershell")
        self.assertTrue(res["success"])
        self.assertIn("Écran ViewSonic", res["stdout"])

if __name__ == "__main__":
    unittest.main()

import unittest
from core.agent_tools.clipboard_manager import ClipboardManager

class TestClipboardManager(unittest.TestCase):
    def test_set_and_get_text(self):
        test_str = "Crux AI Test Clipboard Content 12345"
        ok = ClipboardManager.set_text(test_str)
        if ok:
            read_back = ClipboardManager.get_text()
            self.assertEqual(read_back, test_str)

    def test_clear_clipboard(self):
        ClipboardManager.set_text("temporary")
        ok = ClipboardManager.clear()
        if ok:
            read_back = ClipboardManager.get_text()
            self.assertEqual(read_back, "")

    def test_set_empty_text(self):
        ok = ClipboardManager.set_text("")
        self.assertTrue(ok)
        self.assertEqual(ClipboardManager.get_text(), "")

    def test_set_unicode_text(self):
        test_unicode = "Crux AI Jarvis — Écran PL2766H & Luminosité 100% 🚀"
        ok = ClipboardManager.set_text(test_unicode)
        self.assertTrue(ok)
        read_back = ClipboardManager.get_text()
        self.assertEqual(read_back, test_unicode)

if __name__ == "__main__":
    unittest.main()

import unittest
from PIL import Image
from core.vision.screen_capture import ScreenCapture

class TestScreenCapture(unittest.TestCase):
    def setUp(self):
        self.sc = ScreenCapture()

    def test_capture_image(self):
        img = self.sc.capture_image()
        self.assertIsInstance(img, Image.Image)
        self.assertGreater(img.width, 0)
        self.assertGreater(img.height, 0)

    def test_capture_jpeg_bytes(self):
        jpeg_bytes = self.sc.capture_jpeg_bytes(quality=75, max_dimension=1024)
        self.assertIsInstance(jpeg_bytes, bytes)
        self.assertGreater(len(jpeg_bytes), 100)
        # Vérification du header JPEG (0xFF, 0xD8)
        self.assertEqual(jpeg_bytes[:2], b'\xff\xd8')

    def test_capture_base64(self):
        b64_str = self.sc.capture_base64(quality=60, max_dimension=800)
        self.assertIsInstance(b64_str, str)
        self.assertGreater(len(b64_str), 100)

    def test_screen_changed_delta(self):
        # Premier appel initialise la miniature de référence
        changed1 = self.sc.has_screen_changed(threshold=0.05)
        self.assertTrue(changed1)

        # Deuxième appel immédiat sans mouvement significatif doit renvoyer False (ou True si animation)
        changed2 = self.sc.has_screen_changed(threshold=0.80)
        self.assertFalse(changed2)

    def test_capture_gemini_part(self):
        part = self.sc.capture_gemini_part()
        self.assertIsNotNone(part)

if __name__ == "__main__":
    unittest.main()

import io
import time
import base64
from typing import Optional, Tuple, Dict, Any
from PIL import Image

try:
    import mss
    HAS_MSS = True
except ImportError:
    HAS_MSS = False

try:
    from PIL import ImageGrab
    HAS_IMAGEGRAB = True
except ImportError:
    HAS_IMAGEGRAB = False

try:
    from google.genai import types
    HAS_GENAI_TYPES = True
except ImportError:
    HAS_GENAI_TYPES = False


class ScreenCapture:
    """
    Module de capture d'écran multimodal ultra-rapide (<30ms).
    STRICTEMENT activé à la demande vocale (0 capture en tâche de fond en veille).
    Fournit l'encodage optimisé JPEG et l'empaquetage pour Gemini 3.8 Flash Vision.
    """
    def __init__(self):
        self._sct = None
        self._last_thumbnail: Optional[Image.Image] = None

    def _get_mss(self):
        if self._sct is None and HAS_MSS:
            cls = getattr(mss, "MSS", getattr(mss, "mss", None))
            self._sct = cls() if cls else None
        return self._sct

    def capture_image(self, monitor_index: int = 1) -> Image.Image:
        """Capture l'écran et retourne une instance PIL Image."""
        t0 = time.perf_counter()
        img = None

        if HAS_MSS:
            try:
                sct = self._get_mss()
                monitors = sct.monitors
                target_mon = None
                if monitor_index == 1:
                    # Priorité à l'écran principal (is_primary ou origine à 0, 0)
                    for m in monitors[1:]:
                        if m.get("is_primary", False) or (m.get("left") == 0 and m.get("top") == 0):
                            target_mon = m
                            break
                if not target_mon:
                    target_mon = monitors[monitor_index] if monitor_index < len(monitors) else monitors[1]
                sct_img = sct.grab(target_mon)
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            except Exception:
                img = None

        if img is None and HAS_IMAGEGRAB:
            try:
                img = ImageGrab.grab()
                if img.mode != "RGB":
                    img = img.convert("RGB")
            except Exception:
                img = None

        if img is None:
            # Fallback image vide en cas d'impossibilité système
            img = Image.new("RGB", (800, 600), color=(30, 30, 30))

        return img

    def capture_jpeg_bytes(self, quality: int = 80, max_dimension: int = 1600) -> bytes:
        """
        Capture et compresse l'écran en JPEG sous forme de bytes.
        Redimensionne proportionnellement si la résolution dépasse max_dimension
        pour une latence réseau minimale (< 200ms vers Gemini Vision).
        """
        img = self.capture_image()

        # Redimensionnement optimisé si nécessaire
        width, height = img.size
        if max(width, height) > max_dimension:
            scale = max_dimension / max(width, height)
            new_w = int(width * scale)
            new_h = int(height * scale)
            img = img.resize((new_w, new_h), Image.Resampling.BILINEAR)

        # Sauvegarde en mémoire JPEG
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        return buf.getvalue()

    def capture_base64(self, quality: int = 80, max_dimension: int = 1600) -> str:
        """Retourne la capture sous forme de chaîne Base64."""
        data = self.capture_jpeg_bytes(quality=quality, max_dimension=max_dimension)
        return base64.b64encode(data).decode("utf-8")

    def capture_gemini_part(self, quality: int = 80, max_dimension: int = 1600) -> Any:
        """
        Empaquette la capture pour les SDKs Gemini Google GenAI.
        Retourne types.Part.from_bytes si disponible, sinon un dictionnaire compatible.
        """
        jpeg_bytes = self.capture_jpeg_bytes(quality=quality, max_dimension=max_dimension)
        if HAS_GENAI_TYPES:
            try:
                return types.Part.from_bytes(data=jpeg_bytes, mime_type="image/jpeg")
            except Exception:
                pass
        return {
            "inline_data": {
                "mime_type": "image/jpeg",
                "data": base64.b64encode(jpeg_bytes).decode("utf-8")
            }
        }

    def compute_thumbnail(self, img: Optional[Image.Image] = None) -> Image.Image:
        """Génère une miniature en niveaux de gris 64x64 pour comparaison rapide de deltas."""
        if img is None:
            img = self.capture_image()
        return img.convert("L").resize((64, 64), Image.Resampling.NEAREST)

    def has_screen_changed(self, threshold: float = 0.05) -> bool:
        """
        Compare la capture actuelle avec la précédente miniature enregistrée.
        Retourne True si plus de threshold% de l'image a changé.
        """
        curr = self.compute_thumbnail()
        if self._last_thumbnail is None:
            self._last_thumbnail = curr
            return True

        # Comparaison rapide pixel par pixel
        curr_bytes = curr.tobytes()
        last_bytes = self._last_thumbnail.tobytes()
        diff_count = sum(1 for a, b in zip(curr_bytes, last_bytes) if abs(a - b) > 15)
        total = len(curr_bytes)
        ratio = diff_count / total

        self._last_thumbnail = curr
        return ratio >= threshold

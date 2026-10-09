import time
import re
import unicodedata
import numpy as np
import sounddevice as sd
from typing import Callable, Optional, Tuple

class WakeWordDetector:
    """
    Détecteur de mot-clé multi-déclencheurs ('Crux', 'Salut Crux', 'Bonjour Crux', 'Hey Crux', etc.).
    Supporte de multiples formules d'activation naturelles et gère les phonétiques.
    """
    CRUX_PATTERN = re.compile(
        r'\b(?:hey|eh|he|salut|bonjour|coucou|yo|dis|dix|10|dick|ok|allo|bonsoir)?\s*(crux|krux|kruchs|kruch|crue|kroox|croox|cruk|cruks|krups|krup|crups|trucks|truck|trux|russe)\b',
        re.IGNORECASE
    )

    def __init__(
        self,
        sample_rate: int = 16000,
        chunk_size: int = 1024,
        energy_threshold: float = 0.0025
    ):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.energy_threshold = energy_threshold

    def calibrate_noise_floor(self, device: Optional[int] = None, duration: float = 0.4):
        """Mesure le bruit ambiant réel pour ajuster automatiquement le seuil pour écoute lointaine."""
        try:
            samples = int(self.sample_rate * duration)
            rec = sd.rec(samples, samplerate=self.sample_rate, channels=1, dtype='float32', device=device)
            sd.wait()
            ambient = float(np.sqrt(np.mean(rec**2)))
            self.energy_threshold = max(0.0020, ambient * 1.35)
            print(f"[Crux Micro] Bruit ambiant : {ambient:.5f} | Seuil de détection : {self.energy_threshold:.5f} (Capteur lointain actif)")
        except Exception:
            self.energy_threshold = 0.0025

    @staticmethod
    def normalize_text(text: str) -> str:
        """Supprime les accents et la ponctuation pour une comparaison phonétique robuste."""
        text = unicodedata.normalize('NFD', text.lower())
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
        text = re.sub(r'[^a-z0-9\s]', ' ', text)
        return ' '.join(text.split())

    def check_wake_word(self, raw_text: str) -> Tuple[bool, str]:
        """
        Vérifie si une formule de réveil est présente et extrait la commande immédiate éventuelle.
        Ex: 'salut crux tu peux ouvrir discord' -> (True, 'tu peux ouvrir discord')
        Ex: 'crux' -> (True, '')
        Ex: 'bonjour crux' -> (True, '')
        """
        normalized = self.normalize_text(raw_text)
        match = self.CRUX_PATTERN.search(normalized)
        if match:
            end_pos = match.end()
            trailing = normalized[end_pos:].strip()
            return True, trailing
        return False, ""

    def wait_for_wake_word(self, stt_transcribe_func: Callable[[np.ndarray, int], str], device: Optional[int] = None) -> str:
        """
        Écoute passivement le micro avec seuil haute sensibilité.
        Affiche le niveau en direct pour confirmer la captation.
        """
        print("[Crux WakeWord] En veille... Dites 'Crux', 'Salut Crux', 'Bonjour Crux' ou 'Hey Crux'.")

        buffer = []
        pre_buffer = []
        silence_count = 0
        recording = False

        def audio_callback(indata, frames, time_info, status):
            nonlocal silence_count, recording, buffer, pre_buffer
            chunk = indata[:, 0]
            rms = np.sqrt(np.mean(chunk**2))

            if rms > self.energy_threshold:
                if not recording:
                    recording = True
                    buffer.extend(pre_buffer)
                silence_count = 0
                buffer.append(chunk.copy())
            elif recording:
                buffer.append(chunk.copy())
                silence_count += 1
                if silence_count > int(self.sample_rate / self.chunk_size * 0.75):
                    recording = False
            else:
                pre_buffer.append(chunk.copy())
                if len(pre_buffer) > 8:
                    pre_buffer.pop(0)

        stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            blocksize=self.chunk_size,
            dtype="float32",
            device=device,
            callback=audio_callback
        )

        with stream:
            while True:
                sd.sleep(40)
                if not recording and len(buffer) > 0:
                    recorded_audio = np.concatenate(buffer)
                    buffer = []

                    if len(recorded_audio) > self.sample_rate * 0.25:
                        raw_text = stt_transcribe_func(recorded_audio, self.sample_rate)
                        if raw_text.strip():
                            print(f"[Veille] Entendu : '{raw_text}'")
                            is_wake, trailing_command = self.check_wake_word(raw_text)
                            if is_wake:
                                print("\n[Crux WakeWord] ACTIVATION VALIDÉE !")
                                return trailing_command

import os
import io
import re
import warnings
import tempfile
import numpy as np
import soundfile as sf
from typing import Optional
import speech_recognition as sr
from faster_whisper import WhisperModel

warnings.filterwarnings("ignore")
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

class SpeechToText:
    """
    Système de transcription vocal haute fidélité pour Crux AI.
    1. Moteur Principal : Google Speech Engine avec correction contextuelle stricte.
    2. Post-processing : Remplace automatiquement les erreurs phonétiques (Krups, Russe) par 'Crux'.
    3. Secours Local : Faster-Whisper avec guidage 'Crux'.
    """
    def __init__(self, primary_engine: str = "google", whisper_model_size: str = "base", cpu_threads: int = 4):
        self.primary_engine = primary_engine
        self.whisper_model_size = whisper_model_size
        self.cpu_threads = cpu_threads
        self.recognizer = sr.Recognizer()
        self._whisper_model: Optional[WhisperModel] = None

    @property
    def whisper_model(self) -> WhisperModel:
        if self._whisper_model is None:
            print(f"[STT] Chargement du moteur local de secours ({self.whisper_model_size})...")
            self._whisper_model = WhisperModel(
                self.whisper_model_size,
                device="cpu",
                compute_type="int8",
                cpu_threads=self.cpu_threads
            )
        return self._whisper_model

    def normalize_audio(self, audio: np.ndarray) -> np.ndarray:
        """Normalise et amplifie l'audio pour une captation claire."""
        if len(audio) == 0:
            return audio
        peak = np.max(np.abs(audio))
        if peak > 0.001:
            return (audio / peak) * 0.95
        return audio

    @staticmethod
    def correct_crux_vocabulary(text: str) -> str:
        """
        Corrige les confusions phonétiques françaises de 'Crux' (ex: Krups, Dick russe, etc.).
        Garantit que Crux apparaît toujours correctement orthographié.
        """
        if not text:
            return ""

        # Remplacement des composés ("10 krups", "dick russe")
        text = re.sub(r'\b(?:10|dix|dick)\s+(?:krups|crups|krux|russe)\b', 'dis Crux', text, flags=re.IGNORECASE)
        # Remplacement direct des homophones de Crux
        text = re.sub(r'\b(?:krups|crups|kruchs|krux|crue|croox|cruks|trucks|truck|trux)\b', 'Crux', text, flags=re.IGNORECASE)
        # Remplacement de 'russe' isolé après salutation
        text = re.sub(r'\b(salut|bonjour|coucou|yo|ok|hey|dis)\s+russe\b', r'\1 Crux', text, flags=re.IGNORECASE)

        return text.strip()

    def transcribe_with_google(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        """Transcrit avec le moteur Google Speech."""
        int16_audio = (np.clip(audio_data, -1.0, 1.0) * 32767).astype(np.int16)
        
        bio = io.BytesIO()
        sf.write(bio, int16_audio, sample_rate, format='WAV', subtype='PCM_16')
        bio.seek(0)

        with sr.AudioFile(bio) as source:
            sr_audio = self.recognizer.record(source)

        text = self.recognizer.recognize_google(sr_audio, language="fr-FR")
        return self.correct_crux_vocabulary(text)

    def transcribe_with_whisper(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        """Fallback local rapide avec Faster-Whisper."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
            sf.write(tf.name, audio_data, sample_rate)
            wav_path = tf.name

        try:
            segments, _ = self.whisper_model.transcribe(
                wav_path,
                language="fr",
                beam_size=1,
                temperature=0.0,
                vad_filter=True,
                initial_prompt="Bonjour Crux, je suis Corentin. Conversation avec l'assistant Crux."
            )
            raw = " ".join(seg.text for seg in segments).strip()
            return self.correct_crux_vocabulary(raw)
        finally:
            try:
                os.remove(wav_path)
            except Exception:
                pass

    def transcribe_audio_data(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        """Transcrit et retourne le texte corrigé et propre."""
        if len(audio_data) == 0:
            return ""

        audio_data = self.normalize_audio(audio_data)

        # 1. Google Speech
        try:
            text = self.transcribe_with_google(audio_data, sample_rate)
            if text:
                return text
        except sr.UnknownValueError:
            return ""
        except Exception:
            pass

        # 2. Secours Whisper local
        try:
            return self.transcribe_with_whisper(audio_data, sample_rate)
        except Exception as e:
            print(f"[STT Error] Échec de la transcription : {e}")
            return ""

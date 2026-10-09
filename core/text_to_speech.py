import os
import io
import asyncio
import tempfile
import winsound
import numpy as np
import soundfile as sf
import sounddevice as sd
import scipy.signal
import edge_tts
from typing import Optional, Tuple

class TextToSpeech:
    """
    Système de synthèse vocale Jarvis pour Crux AI.
    Intègre un préambule d'éveil Bluetooth (anti-coupure du DAC pour enceinte JBL).
    """
    def __init__(
        self,
        engine: str = "edge",
        voice: str = "fr-FR-HenriNeural"
    ):
        self.engine = engine
        self.voice = voice
        self.force_device: Optional[str] = None
        self.is_speaking = False

    def set_target_device(self, target: str):
        """Définit manuellement la cible audio ('jbl', 'screen', 'auto')."""
        target_lower = target.lower().strip()
        if "jbl" in target_lower or "enceinte" in target_lower:
            self.force_device = "jbl"
        elif "ecran" in target_lower or "moniteur" in target_lower or "screen" in target_lower:
            self.force_device = "screen"
        else:
            self.force_device = None

    def find_target_audio_device(self) -> Tuple[Optional[int], str, int]:
        """
        Retourne le périphérique audio cible.
        Par défaut : utilise la piste audio de base (périphérique par défaut Windows).
        Si explicitement demandé par Corentin : bascule sur JBL ou Écran.
        """
        devices = sd.query_devices()

        def get_best_match(keywords):
            candidates = []
            for i, d in enumerate(devices):
                if d['max_output_channels'] > 0 and any(k in d['name'].lower() for k in keywords):
                    try:
                        sr = int(d.get('default_samplerate', 44100))
                        sd.check_output_settings(device=i, samplerate=sr)
                        api_prio = 0 if d['hostapi'] == 2 else (1 if d['hostapi'] == 1 else 2)
                        candidates.append((api_prio, i, d['name'], sr))
                    except Exception:
                        pass
            if candidates:
                candidates.sort(key=lambda x: x[0])
                best = candidates[0]
                return best[1], best[2], best[3]
            return None, None, None

        # 1. Si Corentin a explicitement demandé l'enceinte JBL
        if self.force_device == "jbl":
            idx, name, sr = get_best_match(['jbl'])
            if idx is not None:
                return idx, f"Enceinte JBL ({name})", sr

        # 2. Si Corentin a explicitement demandé le casque
        if self.force_device in ["headset", "casque", "g435"]:
            idx, name, sr = get_best_match(['g435', 'casque'])
            if idx is not None:
                return idx, f"Casque ({name})", sr

        # 3. PRIORITÉ ABSOLUE PAR DÉFAUT : Haut-parleurs de l'écran (PL2766H)
        idx, name, sr = get_best_match(['pl2766h', 'va2405', 'amd'])
        if idx is not None:
            return idx, f"Haut-parleurs Écran ({name})", sr

        # 4. REPLI : Piste audio de base (Windows par défaut)
        try:
            default_out_idx = sd.default.device[1]
            if default_out_idx is not None and default_out_idx >= 0:
                dev_info = sd.query_devices(default_out_idx)
                dev_name = dev_info.get('name', 'Périphérique standard')
                sr = int(dev_info.get('default_samplerate', 48000))
                return None, f"Piste de base ({dev_name})", sr
        except Exception:
            pass

        return None, "Piste audio de base (Windows par défaut)", 48000

    def _ensure_voicemeeter_healthy(self):
        """Vérifie que Voicemeeter ne bloque pas la sortie audio sur un périphérique éteint."""
        try:
            vm_path = r"C:\Program Files (x86)\VB\Voicemeeter\VoicemeeterRemote64.dll"
            if not os.path.exists(vm_path):
                return
            import ctypes
            vm = ctypes.windll.LoadLibrary(vm_path)
            if vm.VBVMR_Login() == 0:
                # Vérifie que Bus[0] est bien assigné
                buff = ctypes.create_string_buffer(256)
                vm.VBVMR_GetParameterStringA(b"Bus[0].device.name", buff)
                if not buff.value or b"JBL" in buff.value:
                    # Si A1 est vide ou pointait sur une JBL éteinte, basculer sur les haut-parleurs/écrans actifs
                    vm.VBVMR_SetParameterStringA(b"Bus[0].device.wdm", b"4 - PL2766H (AMD High Definition Audio Device)")
                # Assure que Strip 3 (Voicemeeter VAIO / Input) renvoie bien sur A1 et A2 et n'est pas mute
                vm.VBVMR_SetParameterFloat(b"Strip[3].A1", ctypes.c_float(1.0))
                vm.VBVMR_SetParameterFloat(b"Strip[3].A2", ctypes.c_float(1.0))
                vm.VBVMR_SetParameterFloat(b"Strip[3].Mute", ctypes.c_float(0.0))
                vm.VBVMR_Logout()
        except Exception:
            pass

    async def _generate_edge_audio(self, text: str) -> bytes:
        communicate = edge_tts.Communicate(text, self.voice)
        audio_stream = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_stream.write(chunk["data"])
        return audio_stream.getvalue()

    def find_hardware_monitor_device(self) -> Tuple[Optional[int], Optional[str], int]:
        """Détecte l'écran physique pour sortie miroir de secours."""
        for i, d in enumerate(sd.query_devices()):
            if d['max_output_channels'] > 0 and any(k in d['name'].lower() for k in ['pl2766h', 'va2405', 'amd']):
                try:
                    sr = int(d.get('default_samplerate', 48000))
                    sd.check_output_settings(device=i, samplerate=sr)
                    return i, d['name'], sr
                except Exception:
                    pass
        return None, None, 48000

    def speak(self, text: str):
        """Diffuse la voix de Crux avec préambule d'éveil Bluetooth."""
        if not text or not text.strip():
            return

        text = text.strip()
        print(f"\n[Crux Vocal] > {text}")

        target_dev, dev_name, target_sr = self.find_target_audio_device()
        print(f"[Crux Audio] Sortie active : {dev_name}")

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                audio_data = asyncio.run_coroutine_threadsafe(
                    self._generate_edge_audio(text), loop
                ).result()
            else:
                audio_data = loop.run_until_complete(self._generate_edge_audio(text))
        except RuntimeError:
            audio_data = asyncio.run(self._generate_edge_audio(text))

        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tf:
                tf.write(audio_data)
                mp3_path = tf.name

            data, orig_fs = sf.read(mp3_path)

            if orig_fs != target_sr:
                num_samples = int(len(data) * target_sr / orig_fs)
                data = scipy.signal.resample(data, num_samples)

            # Préambule d'éveil Bluetooth actif (150ms de signal sub-audible 25Hz à -45dB)
            # Force la puce Bluetooth (JBL / DAC) à déverrouiller l'amplificateur avant la première syllabe
            wake_samples = int(target_sr * 0.15)
            t_wake = np.linspace(0, 0.15, wake_samples)
            wake_ramp = (np.sin(2 * np.pi * 25 * t_wake) * 0.005 * np.linspace(0.1, 1.0, wake_samples)).astype(np.float32)
            data = np.concatenate([wake_ramp, data])

            if data.ndim == 1:
                stereo_data = np.column_stack([data, data]).astype(np.float32)
            else:
                stereo_data = data.astype(np.float32)

            self.is_speaking = True

            try:
                sd.play(stereo_data, samplerate=target_sr, device=target_dev)
                sd.wait()
            except Exception:
                wav_path = mp3_path.replace(".mp3", ".wav")
                sf.write(wav_path, stereo_data, target_sr, subtype="PCM_16")
                winsound.PlaySound(wav_path, winsound.SND_FILENAME)
                try:
                    os.remove(wav_path)
                except Exception:
                    pass

            self.is_speaking = False

            try:
                os.remove(mp3_path)
            except Exception:
                pass

        except Exception as e:
            print(f"[TTS Error] {e}")
            self.is_speaking = False

    def stop(self):
        sd.stop()
        self.is_speaking = False

import os
import winsound
import threading
import time
import numpy as np
import soundfile as sf
import sounddevice as sd
import scipy.signal
from pathlib import Path
from typing import Optional

class SoundEffects:
    """
    Générateur et lecteur d'effets sonores futuristes style Jarvis (Iron Man / Marvel).
    Intègre une protection thread-safe (Lock) pour éviter les collisions matérielles PortAudio.
    """
    def __init__(self, sounds_dir: str = "sounds"):
        self.sounds_dir = Path(__file__).parent.parent / sounds_dir
        self.sounds_dir.mkdir(parents=True, exist_ok=True)
        self.fs = 44100
        self._lock = threading.Lock()
        self._thinking_active = False
        self._ensure_all_sfx_exist()

    def _save_wav(self, filename: str, audio: np.ndarray):
        path = self.sounds_dir / filename
        peak = np.max(np.abs(audio))
        if peak > 0.001:
            audio = (audio / peak) * 0.98
        sf.write(str(path), audio, self.fs, subtype="PCM_16")
        sf.write(str(path), audio, self.fs, subtype="PCM_16")

    def _ensure_all_sfx_exist(self):
        """Génère tous les bruitages futuristes haute fidélité au format WAV."""
        fs = self.fs

        # 1. WAKE : Réveil Jarvis (Double pulsation montante haute fidélité style Iron Man)
        t1 = np.linspace(0, 0.18, int(fs * 0.18))
        tone1 = (np.sin(2 * np.pi * 659 * t1) + 0.3 * np.sin(2 * np.pi * 1318 * t1)) * np.exp(-t1 * 12)
        t2 = np.linspace(0, 0.22, int(fs * 0.22))
        tone2 = (np.sin(2 * np.pi * 987 * t2) + 0.4 * np.sin(2 * np.pi * 1974 * t2) + 0.15 * np.sin(2 * np.pi * 2960 * t2)) * np.exp(-t2 * 6)
        sil = np.zeros(int(fs * 0.02))
        wake = np.concatenate([tone1, sil, tone2])
        wake = wake * np.minimum(np.linspace(0, 1, len(wake)) / 0.03, 1.0)
        self._save_wav("wake.wav", np.column_stack([wake, wake]).astype(np.float32))

        # 2. LISTEN : Prise d'écoute (Blip cristallin net & affirmatif)
        t_l = np.linspace(0, 0.25, int(fs * 0.25))
        listen = (np.sin(2 * np.pi * 1175 * t_l) + 0.35 * np.sin(2 * np.pi * 2350 * t_l)) * np.exp(-t_l * 14)
        listen = listen * np.minimum(t_l / 0.02, 1.0)
        self._save_wav("listen.wav", np.column_stack([listen, listen]).astype(np.float32))

        # 3. PROCESS : Scan & Réflexion IA (Chirp cybernétique de calcul)
        t_p = np.linspace(0, 0.32, int(fs * 0.32))
        freq = 600 + 1200 * (t_p / 0.32)**1.2
        proc = (np.sin(2 * np.pi * freq * t_p) + 0.25 * np.sin(4 * np.pi * freq * t_p)) * np.exp(-t_p * 6)
        proc = proc * np.minimum(t_p / 0.03, 1.0)
        self._save_wav("process.wav", np.column_stack([proc, proc]).astype(np.float32))

        # 4. SUCCESS : Accord triomphant Jarvis (Validation d'ordre)
        t_a = np.linspace(0, 0.12, int(fs * 0.12))
        t_b = np.linspace(0, 0.12, int(fs * 0.12))
        t_c = np.linspace(0, 0.28, int(fs * 0.28))
        c1 = (np.sin(2 * np.pi * 587 * t_a) + 0.2 * np.sin(2 * np.pi * 1174 * t_a)) * np.exp(-t_a * 10)
        c2 = (np.sin(2 * np.pi * 740 * t_b) + 0.2 * np.sin(2 * np.pi * 1480 * t_b)) * np.exp(-t_b * 10)
        c3 = (np.sin(2 * np.pi * 880 * t_c) + 0.35 * np.sin(2 * np.pi * 1760 * t_c) + 0.15 * np.sin(2 * np.pi * 2640 * t_c)) * np.exp(-t_c * 6)
        succ = np.concatenate([c1, np.zeros(int(fs * 0.01)), c2, np.zeros(int(fs * 0.01)), c3])
        succ = succ * np.minimum(np.linspace(0, 1, len(succ)) / 0.02, 1.0)
        self._save_wav("success.wav", np.column_stack([succ, succ]).astype(np.float32))

        # 5. SLEEP : Mise en veille (Descente harmonique douce)
        t_sl = np.linspace(0, 0.40, int(fs * 0.40))
        freq_down = 900 - 600 * (t_sl / 0.40)
        sl = (np.sin(2 * np.pi * freq_down * t_sl) + 0.3 * np.sin(2 * np.pi * (freq_down * 0.5) * t_sl)) * np.exp(-t_sl * 5.5)
        sl = sl * np.minimum(t_sl / 0.03, 1.0)
        self._save_wav("sleep.wav", np.column_stack([sl, sl]).astype(np.float32))

        # 6. THINKING : Pulsation cybernétique continue Jarvis (Réflexion complexe)
        t_th = np.linspace(0, 0.85, int(fs * 0.85))
        f_mod = 520 + 90 * np.sin(2 * np.pi * 4.0 * t_th)
        c_th = np.sin(2 * np.pi * f_mod * t_th) * 0.35
        t_ticks = np.sin(2 * np.pi * 2200 * t_th) * (np.sin(2 * np.pi * 16 * t_th) > 0.82) * 0.15
        thinking = (c_th + t_ticks) * (0.8 + 0.2 * np.sin(2 * np.pi * 3 * t_th))
        env_th = np.ones_like(thinking)
        fl = int(fs * 0.04)
        env_th[:fl] = np.linspace(0, 1, fl)
        env_th[-fl:] = np.linspace(1, 0, fl)
        thinking = (thinking * env_th).astype(np.float32)
        self._save_wav("thinking.wav", np.column_stack([thinking, thinking]).astype(np.float32))

        # 7. SNAP : Clic mécanique de réorganisation holographique des fenêtres
        t_sn = np.linspace(0, 0.16, int(fs * 0.16))
        f_sn = 280 + 1400 * np.exp(-t_sn * 28)
        sn = np.sin(2 * np.pi * f_sn * t_sn) * np.exp(-t_sn * 22)
        click_sn = (np.random.rand(len(t_sn)) * 2 - 1) * np.exp(-t_sn * 70) * 0.25
        snap_audio = ((sn + click_sn) * 0.95).astype(np.float32)
        self._save_wav("snap.wav", np.column_stack([snap_audio, snap_audio]).astype(np.float32))

        # 8. PRESET : Accord double de déploiement d'espace de travail
        t_pr = np.linspace(0, 0.35, int(fs * 0.35))
        cp1 = np.sin(2 * np.pi * 523 * t_pr) * np.exp(-t_pr * 8)
        cp2 = np.sin(2 * np.pi * 659 * t_pr) * np.exp(-t_pr * 7)
        cp3 = np.sin(2 * np.pi * 1046 * t_pr) * np.exp(-t_pr * 6)
        preset_audio = ((cp1 * 0.35 + cp2 * 0.35 + cp3 * 0.45) * 0.95).astype(np.float32)
        self._save_wav("preset.wav", np.column_stack([preset_audio, preset_audio]).astype(np.float32))

        # 9. NOTIFY : Chime cristalline de notification
        t_no = np.linspace(0, 0.26, int(fs * 0.26))
        no1 = np.sin(2 * np.pi * 880 * t_no) * np.exp(-t_no * 11)
        no2 = np.sin(2 * np.pi * 1760 * t_no) * np.exp(-t_no * 13) * 0.4
        notify_audio = ((no1 + no2) * 0.95).astype(np.float32)
        self._save_wav("notify.wav", np.column_stack([notify_audio, notify_audio]).astype(np.float32))

    def _get_fallback_device(self) -> Optional[int]:
        """Retourne l'écran physique actif (PL2766H) en priorité, ou None si non trouvé."""
        return self._find_screen_device()

    def _find_screen_device(self) -> Optional[int]:
        for i, d in enumerate(sd.query_devices()):
            if d['max_output_channels'] > 0 and any(k in d['name'].lower() for k in ['pl2766h', 'va2405', 'amd']):
                try:
                    sr = int(d.get('default_samplerate', 48000))
                    sd.check_output_settings(device=i, samplerate=sr)
                    return i
                except Exception:
                    pass
        return None

    def play(self, sfx_name: str, device: Optional[int] = None, wait: bool = True):
        """Joue un bruitage futuriste directement sur le matériel cible de manière thread-safe."""
        filename = f"{sfx_name}.wav" if not sfx_name.endswith(".wav") else sfx_name
        path = self.sounds_dir / filename

        if not path.exists():
            return

        target_dev = device
        if target_dev is None:
            target_dev = self._get_fallback_device()

        with self._lock:
            try:
                data, orig_fs = sf.read(str(path))
                target_sr = orig_fs

                if target_dev is not None:
                    try:
                        d_info = sd.query_devices(target_dev)
                        target_sr = int(d_info.get("default_samplerate", orig_fs))
                    except Exception:
                        pass

                if target_sr != orig_fs:
                    num_samples = int(len(data) * target_sr / orig_fs)
                    data = scipy.signal.resample(data, num_samples)

                # Pré-éveil DAC Bluetooth (60ms)
                ramp_samples = int(target_sr * 0.06)
                t_r = np.linspace(0, 0.06, ramp_samples)
                wake_signal = (np.sin(2 * np.pi * 30 * t_r) * 0.003 * np.linspace(0.1, 1.0, ramp_samples)).astype(np.float32)
                if data.ndim == 1:
                    data = np.concatenate([wake_signal, data])
                    data = np.column_stack([data, data]).astype(np.float32)
                else:
                    wake_2d = np.column_stack([wake_signal, wake_signal])
                    data = np.concatenate([wake_2d, data]).astype(np.float32)

                sd.play(data, samplerate=target_sr, device=target_dev)
                if wait:
                    sd.wait()
            except Exception:
                try:
                    flag = winsound.SND_FILENAME if wait else (winsound.SND_FILENAME | winsound.SND_ASYNC)
                    winsound.PlaySound(str(path), flag)
                except Exception:
                    pass

    def start_thinking(self):
        """Joue une impulsion sonore de calcul sans saturer le sous-système audio."""
        self._thinking_active = True
        def loop():
            # Une impulsion au démarrage puis répétition douce toutes les 1.8s
            while getattr(self, '_thinking_active', False):
                self.play("thinking", wait=True)
                for _ in range(18):
                    if not getattr(self, '_thinking_active', False):
                        break
                    time.sleep(0.1)
        t = threading.Thread(target=loop, daemon=True)
        t.start()

    def stop_thinking(self):
        """Arrête immédiatement le SFX de réflexion."""
        self._thinking_active = False

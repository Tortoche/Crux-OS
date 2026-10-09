import time
import ctypes
import threading
from typing import Optional, Dict, Any, Callable
from ctypes import wintypes
import psutil

from core.coucou_client import CoucouClient

user32 = ctypes.windll.user32

class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("dwTime", wintypes.DWORD)
    ]

# Liste de jeux connus pour ne pas déranger en plein écran
KNOWN_GAME_PROCESSES = {
    "cs2.exe", "valorant.exe", "league of legends.exe", "r5apex.exe",
    "fortniteclient-win64-shipping.exe", "overwatch.exe", "gta5.exe",
    "cyberpunk2077.exe", "minecraft.exe", "javaw.exe", "cod.exe",
    "eldenring.exe", "helldivers2.exe", "starfield.exe"
}

class GUID(ctypes.Structure):
    _fields_ = [
        ('Data1', wintypes.DWORD),
        ('Data2', wintypes.WORD),
        ('Data3', wintypes.WORD),
        ('Data4', wintypes.BYTE * 8)
    ]
    def __init__(self, l, w1, w2, b1, b2, b3, b4, b5, b6, b7, b8):
        super().__init__(l, w1, w2, (wintypes.BYTE*8)(b1, b2, b3, b4, b5, b6, b7, b8))

CLSID_MMDeviceEnumerator = GUID(0xBCDE0395, 0xE52F, 0x467C, 0x8E, 0x3D, 0xC4, 0x57, 0x92, 0x91, 0x69, 0x2E)
IID_IMMDeviceEnumerator = GUID(0xA95664D2, 0x9614, 0x4F35, 0xA7, 0x46, 0xDE, 0x8D, 0xB6, 0x36, 0x17, 0xE6)
IID_IAudioSessionManager2 = GUID(0x77AA99A0, 0x1BD6, 0x484F, 0x8B, 0xC7, 0x2C, 0x65, 0x4C, 0x9A, 0x9B, 0x6F)

class ProactiveDaemon:
    """
    Daemon d'arrière-plan 100% local surveillant l'état de la machine SANS consommer de tokens LLM.
    Détecte les opportunités pertinentes (inactivité, saturation CPU, fin de tâche/erreur, pause).
    Déclenche une pulsation visuelle discrète sur la Notch Coucou puis une phrase courte,
    avec interdiction stricte d'interrompre si un jeu plein écran est actif.
    """
    def __init__(
        self,
        tts: Optional[Any] = None,
        hud: Optional[CoucouClient] = None,
        check_interval: float = 5.0,
        cooldown_seconds: float = 300.0,
        on_event_callback: Optional[Callable[[str, str], None]] = None
    ):
        self.tts = tts
        self.hud = hud or CoucouClient.get_instance()
        self.check_interval = check_interval
        self.cooldown_seconds = cooldown_seconds
        self.on_event_callback = on_event_callback

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._last_notification_time = 0.0
        self._work_start_time = time.time()
        self._last_active_window = ""
        self._last_cpu_high_time = 0.0

    def start(self):
        """Démarre la surveillance d'arrière-plan."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._work_start_time = time.time()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Arrête le daemon."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # ==========================================
    # MESURES SYSTÈME LOCALES SANS LLM
    # ==========================================
    def get_idle_time_seconds(self) -> float:
        """Retourne le temps écoulé depuis la dernière saisie clavier/souris de l'utilisateur."""
        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if user32.GetLastInputInfo(ctypes.byref(lii)):
            millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
            return max(0.0, millis / 1000.0)
        return 0.0

    def is_fullscreen_game_active(self) -> bool:
        """Détecte si un jeu vidéo en plein écran est actuellement actif."""
        try:
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return False

            # Vérifier le nom du process
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value:
                try:
                    proc = psutil.Process(pid.value)
                    if proc.name().lower() in KNOWN_GAME_PROCESSES:
                        return True
                except Exception:
                    pass

            # Vérifier si la fenêtre couvre l'intégralité de l'écran principal
            rect = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            screen_w = user32.GetSystemMetrics(0)
            screen_h = user32.GetSystemMetrics(1)
            is_fullscreen = (
                rect.left <= 0 and rect.top <= 0 and
                rect.right >= screen_w and rect.bottom >= screen_h
            )

            # Vérifier si le titre évoque un jeu
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value.lower()
                if is_fullscreen and any(g in title for g in ["game", "play", "directx", "unreal", "unity"]):
                    return True

        except Exception:
            pass
        return False

    def is_audio_active(self) -> bool:
        """Détecte si un flux audio ou vocal est actuellement actif sur le système (WASAPI / TTS)."""
        if self.tts and getattr(self.tts, "is_speaking", False):
            return True

        try:
            ole32 = ctypes.oledll.ole32
            ole32.CoInitialize(None)
            enumerator = ctypes.c_void_p()
            hr = ole32.CoCreateInstance(
                ctypes.byref(CLSID_MMDeviceEnumerator), None, 1,
                ctypes.byref(IID_IMMDeviceEnumerator), ctypes.byref(enumerator)
            )
            if hr == 0 and enumerator:
                vtable_enum = ctypes.cast(enumerator, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
                GetDefaultAudioEndpoint = ctypes.WINFUNCTYPE(
                    ctypes.HRESULT, ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p)
                )(vtable_enum[4])
                device = ctypes.c_void_p()
                if GetDefaultAudioEndpoint(enumerator, 0, 1, ctypes.byref(device)) == 0 and device:
                    vtable_dev = ctypes.cast(device, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
                    Activate = ctypes.WINFUNCTYPE(
                        ctypes.HRESULT, ctypes.c_void_p, ctypes.POINTER(GUID), wintypes.DWORD, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)
                    )(vtable_dev[3])
                    mgr = ctypes.c_void_p()
                    if Activate(device, ctypes.byref(IID_IAudioSessionManager2), 1, None, ctypes.byref(mgr)) == 0 and mgr:
                        vtable_mgr = ctypes.cast(mgr, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
                        GetSessionEnumerator = ctypes.WINFUNCTYPE(
                            ctypes.HRESULT, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)
                        )(vtable_mgr[5])
                        session_enum = ctypes.c_void_p()
                        if GetSessionEnumerator(mgr, ctypes.byref(session_enum)) == 0 and session_enum:
                            vtable_sess = ctypes.cast(session_enum, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
                            GetCount = ctypes.WINFUNCTYPE(ctypes.HRESULT, ctypes.c_void_p, ctypes.POINTER(ctypes.c_int))(vtable_sess[3])
                            GetSession = ctypes.WINFUNCTYPE(ctypes.HRESULT, ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p))(vtable_sess[4])
                            count = ctypes.c_int()
                            if GetCount(session_enum, ctypes.byref(count)) == 0:
                                for idx in range(count.value):
                                    ctrl = ctypes.c_void_p()
                                    if GetSession(session_enum, idx, ctypes.byref(ctrl)) == 0 and ctrl:
                                        vtable_ctrl = ctypes.cast(ctrl, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
                                        GetState = ctypes.WINFUNCTYPE(ctypes.HRESULT, ctypes.c_void_p, ctypes.POINTER(ctypes.c_int))(vtable_ctrl[3])
                                        state = ctypes.c_int()
                                        if GetState(ctrl, ctypes.byref(state)) == 0:
                                            if state.value == 1:  # AudioSessionStateActive
                                                return True
        except Exception:
            pass

        return False

    def can_notify(self) -> bool:
        """Vérifie le respect du cooldown et des règles de non-dérangement (plein écran ou audio actif)."""
        now = time.time()
        if (now - self._last_notification_time) < self.cooldown_seconds:
            return False
        if self.is_fullscreen_game_active():
            return False
        if self.is_audio_active():
            return False
        return True

    def trigger_proactive_event(self, title: str, voice_message: str):
        """
        Déclenche la séquence validée :
        1. Pulsation visuelle discrète sur la Notch Coucou
        2. Appel vocal ultra court (1 phrase max)
        """
        if not self.can_notify():
            return

        self._last_notification_time = time.time()

        # 1. Pulsation Notch Coucou
        if self.hud:
            self.hud.notify(title, voice_message, 4.0)

        # 2. Phrase vocale très courte
        if self.tts:
            try:
                self.tts.speak(voice_message)
            except Exception:
                pass

        if self.on_event_callback:
            self.on_event_callback(title, voice_message)

    def _check_conditions(self):
        """Évalue les déclencheurs proactifs locaux."""
        now = time.time()
        idle_sec = self.get_idle_time_seconds()

        # Règle 1 : Pause ergonomique après 60 minutes de travail continu sans inactivité (> 2 min)
        continuous_work = now - self._work_start_time
        if continuous_work > 3600 and idle_sec < 120:
            self.trigger_proactive_event(
                "Pause Suggérée",
                "Corentin, tu travailles depuis plus d'une heure sans interruption, pense à faire une courte pause."
            )
            self._work_start_time = now
            return

        # Règle 2 : Réinitialisation du temps de travail si inactivité prolongée (> 15 minutes)
        if idle_sec > 900:
            self._work_start_time = now

        # Règle 3 : Alerte saturation CPU (> 90% pendant plus de 15s)
        cpu_usage = psutil.cpu_percent(interval=None)
        if cpu_usage > 90.0:
            if self._last_cpu_high_time == 0.0:
                self._last_cpu_high_time = now
            elif (now - self._last_cpu_high_time) > 15.0:
                self.trigger_proactive_event(
                    "Charge CPU Élevée",
                    "Le processeur est fortement sollicité, veux-tu que j'identifie le processus ?"
                )
                self._last_cpu_high_time = 0.0
                return
        else:
            self._last_cpu_high_time = 0.0

        # Règle 4 : Détection de fin de tâche dans le titre de la console active
        try:
            hwnd = user32.GetForegroundWindow()
            if hwnd:
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buf, length + 1)
                    curr_title = buf.value.lower()
                    if ("error" in curr_title or "failed" in curr_title) and curr_title != self._last_active_window:
                        self._last_active_window = curr_title
                        self.trigger_proactive_event(
                            "Erreur Détectée",
                            "J'ai repéré un échec dans ta console, dis-moi si tu veux que j'analyse l'erreur."
                        )
                        return
                    self._last_active_window = curr_title
        except Exception:
            pass

    def _run_loop(self):
        """Boucle de surveillance locale."""
        while not self._stop_event.is_set():
            try:
                self._check_conditions()
            except Exception:
                pass
            self._stop_event.wait(self.check_interval)

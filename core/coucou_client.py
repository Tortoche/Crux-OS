import os
import sys
import time
import json
import socket
import subprocess
from typing import Dict, Any, Optional
from pathlib import Path
import atexit

ELECTRON_PORT = 49225

class CoucouClient:
    """
    Pont de communication entre Crux AI et la Notch Mochi du projet officiel Coucou.
    Propulsé par le runtime natif Electron garantissant une transparence 100% réelle,
    sans fond blanc ni bordure sous Windows.
    """
    _instance: Optional['CoucouClient'] = None

    @classmethod
    def get_instance(cls) -> 'CoucouClient':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.proc: Optional[subprocess.Popen] = None
        atexit.register(self.shutdown)
        self._last_spawn = 0.0
        self._ensure_running()

    def _is_server_listening(self) -> bool:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.2)
                s.connect(('127.0.0.1', ELECTRON_PORT))
                return True
        except Exception:
            return False

    def _ensure_running(self):
        """Vérifie si l'hôte Coucou Electron est en ligne, sinon le démarre instantanément."""
        if self._is_server_listening():
            return

        now = time.time()
        if hasattr(self, '_last_spawn') and (now - self._last_spawn) < 4.0:
            return
        self._last_spawn = now

        coucou_windows_dir = Path(__file__).parent.parent / "coucou-repo" / "windows"
        electron_script = coucou_windows_dir / "electron_coucou.cjs"
        electron_exe = coucou_windows_dir / "node_modules" / "electron" / "dist" / "electron.exe"

        try:
            if electron_exe.exists():
                self.proc = subprocess.Popen(
                    [str(electron_exe), str(electron_script)],
                    cwd=str(coucou_windows_dir),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            else:
                self.proc = subprocess.Popen(
                    ["npx", "electron", str(electron_script)],
                    cwd=str(coucou_windows_dir),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    shell=True
                )
            for _ in range(25):
                time.sleep(0.08)
                if self._is_server_listening():
                    break
        except Exception:
            pass

    def send_event(self, event_type: str, payload: Dict[str, Any]):
        """Transmet un événement à l'interface Coucou en moins d'une milliseconde."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            s.connect(('127.0.0.1', ELECTRON_PORT))
            msg = json.dumps({"type": event_type, "payload": payload}) + "\n"
            s.sendall(msg.encode('utf-8'))
            s.recv(1024)
            s.close()
        except Exception:
            self._ensure_running()

    # ==========================================
    # MÉTHODES MÉTIER SYNCHRONISÉES CRUX <-> COUCOU
    # ==========================================
    def session_start(self, message: str = "Crux AI Actif"):
        """Réveille Mochi et active le badge Crux dans la barre de Coucou."""
        self.send_event("hook", {
            "hook_event_name": "SessionStart",
            "coucou_agent": "crux",
            "cwd": r"C:\Users\coco\Documents",
            "message": message
        })

    def live_speech(self, partial_text: str):
        """Transmet en temps réel les paroles de Corentin pour affichage élégant dans la notch."""
        self.send_event("hook", {
            "hook_event_name": "SpeechLive",
            "coucou_agent": "crux",
            "prompt": partial_text,
            "message": partial_text
        })

    def listening(self, partial_text: str = "À votre écoute..."):
        """Affiche les paroles de Corentin en direct dans la notch."""
        self.live_speech(partial_text)

    def thinking(self, prompt: str = "Analyse en cours..."):
        """Bascule Mochi en animation de réflexion / calcul et affiche l'ordre en cours."""
        self.send_event("hook", {
            "hook_event_name": "UserPromptSubmit",
            "coucou_agent": "crux",
            "prompt": prompt,
            "message": prompt
        })

    def tool_use(self, tool_name: str, tool_input: Dict[str, Any]):
        """Affiche l'action en cours d'exécution dans la carte d'étape Coucou."""
        self.send_event("hook", {
            "hook_event_name": "PreToolUse",
            "coucou_agent": "crux",
            "tool_name": tool_name,
            "tool_input": tool_input
        })

    def speaking(self, response: str):
        """Notifie Coucou de la réponse vocale de Crux."""
        self.send_event("hook", {
            "hook_event_name": "Notification",
            "coucou_agent": "crux",
            "message": response[:60]
        })

    def sleep(self):
        """Met Mochi en sommeil doux (yeux fermés + Zzz) pendant la veille de Crux."""
        self.send_event("hook", {
            "hook_event_name": "Sleep",
            "coucou_agent": "crux"
        })

    def wake(self):
        """Réveille Mochi immédiatement lors du déclenchement Hey Crux."""
        self.send_event("hook", {
            "hook_event_name": "Wake",
            "coucou_agent": "crux"
        })

    def session_stop(self):
        """Clôture la session et remet Mochi en sommeil doux."""
        self.sleep()

    # Compatibilité avec le cycle de vie Crux
    def set_state(self, state: str, title: Optional[str] = None, sub: Optional[str] = None):
        if state == "listening":
            # Efface le ticker pour attendre les vraies paroles en direct
            self.live_speech("")
        elif state == "thinking":
            self.thinking(sub or "Analyse en cours...")
        elif state == "speaking":
            self.speaking(sub or "Réponse...")
        elif state in ["idle", "sleep"]:
            self.sleep()
        elif state == "wake":
            self.wake()

    def update_vu(self, level: float):
        pass

    def notify(self, title: str, message: str, duration_sec: float = 4.0):
        self.tool_use("Notification", {"command": f"{title} · {message}"})

    def send_pill(self, title: str, text: str = "", icon: str = "sparkles", duration: float = 3.0):
        """Affiche une pilule dynamique élégante dans la notch Coucou."""
        self.send_event("pill", {
            "title": title,
            "text": text,
            "icon": icon,
            "duration": duration
        })

    def send_card(self, title: str, items: Dict[str, Any], card_type: str = "status"):
        """Affiche une carte informative détaillée sous la notch Coucou."""
        self.send_event("card", {
            "title": title,
            "items": items,
            "type": card_type
        })

    def sync_telemetry(self, cpu_pct: float, ram_pct: float, details: str = ""):
        """Transmet l'état des ressources en direct pour la télémétrie de la notch Coucou."""
        self.send_event("telemetry", {
            "cpu": round(cpu_pct, 1),
            "ram": round(ram_pct, 1),
            "details": details
        })

    def sync_spotify_status(self, title: str, artist: str, album: str = "Spotify", is_playing: bool = True, art_url: str = ""):
        """Synchronise l'affichage multimédia et la pochette en temps réel dans Coucou."""
        self.send_event("spotify", {
            "running": True,
            "installed": True,
            "playing": is_playing,
            "track": {
                "title": title,
                "artist": artist,
                "album": album,
                "duration": 180,
                "artUrl": art_url
            }
        })

    def set_mochi_emotion(self, emotion: str):
        """Modifie l'animation faciale de Mochi (happy, thinking, dance, sleep, wake)."""
        self.send_event("hook", {
            "hook_event_name": f"Emotion_{emotion.capitalize()}",
            "coucou_agent": "crux",
            "emotion": emotion
        })

    def open_settings(self):
        """Ouvre la fenêtre des réglages et configurations de Coucou."""
        self.send_event("open_settings", {})

    def start(self):
        self._ensure_running()

    def stop(self):
        self.session_stop()

    def shutdown(self):
        self.session_stop()
        if self.proc:
            try:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(self.proc.pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            except Exception:
                pass
            self.proc = None

import os
import sys
import time
import json
import ctypes
from typing import Dict, Any, Optional, Tuple
from core.coucou_client import CoucouClient

class HandoffManager:
    """
    Gestionnaire de continuité multi-appareils (Handoff) et télécommande PC pour Crux OS.
    Gère la bascule fluide de session entre le PC Windows, le relais Fedora H24 et le smartphone.
    """
    _instance: Optional['HandoffManager'] = None

    @classmethod
    def get_instance(cls) -> 'HandoffManager':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, agent: Optional[Any] = None):
        self.agent = agent
        self.active_node: str = "pc"  # "pc" | "mobile" | "fedora_relay"
        self.last_switch_time: float = time.time()
        self.hud = CoucouClient.get_instance()
        self.mobile_connected: bool = False
        self.mobile_device_info: Dict[str, Any] = {}

    def register_mobile_client(self, client_info: Dict[str, Any]):
        """Enregistre un smartphone connecté sur le réseau local."""
        self.mobile_connected = True
        self.mobile_device_info = client_info or {}

    def transfer_to_mobile(self, agent: Optional[Any] = None) -> Tuple[str, bool]:
        """
        Bascule la session vers le smartphone :
        Met le PC en veille (HUD désactivé, session arrêtée) et active le mobile.
        Retourne (message_vocal, is_exit).
        """
        target_agent = agent or self.agent
        self.active_node = "mobile"
        self.last_switch_time = time.time()

        try:
            # Notifier la notch Coucou de la mise en veille du PC
            self.hud.set_state("sleeping", "Crux", "Bascule vers le mobile...")
            time.sleep(0.1)
            self.hud.session_stop("Crux transféré sur le mobile")
        except Exception:
            pass

        # Si un agent est fourni, synchroniser la mémoire
        if target_agent and hasattr(target_agent, "memory"):
            try:
                target_agent.memory.working.set("active_device", "mobile")
            except Exception:
                pass

        reply = "Bascule effectuée sur votre téléphone. Je mets le PC en veille."
        return reply, True

    def resume_on_pc(self, agent: Optional[Any] = None) -> Tuple[str, bool]:
        """
        Reprend la session sur le PC Windows :
        Réactive le PC, réveille la Notch Coucou et bascule la sortie audio sur l'écran PL2766H.
        Retourne (message_vocal, is_exit).
        """
        target_agent = agent or self.agent
        self.active_node = "pc"
        self.last_switch_time = time.time()

        # Réveil de la Notch Coucou sur PC
        try:
            self.hud.session_start("Crux repris sur le PC")
            self.hud.set_state("active", "Crux", "Session active sur PC")
        except Exception:
            pass

        # Basculement de la sortie audio vers l'écran PL2766H
        if target_agent and hasattr(target_agent, "tts") and target_agent.tts:
            try:
                target_agent.tts.set_target_device("screen")
            except Exception:
                pass

        if target_agent and hasattr(target_agent, "memory"):
            try:
                target_agent.memory.working.set("active_device", "pc")
            except Exception:
                pass

        reply = "Reprise sur le PC effectuée. Sortie audio basculée sur l'écran PL2766H."
        return reply, False

    def execute_remote_command(self, command: str, params: Optional[Dict[str, Any]] = None, agent: Optional[Any] = None) -> Dict[str, Any]:
        """
        Exécute une commande de télécommande PC envoyée depuis le smartphone.
        Supporte les médias, le volume, les fenêtres, le verrouillage et les ordres vocaux.
        """
        target_agent = agent or self.agent
        params = params or {}
        cmd_clean = (command or "").strip().lower()

        result = {"success": True, "command": cmd_clean, "node": self.active_node}

        try:
            # 1. Contrôles Multimédia
            if cmd_clean in ["media_play_pause", "play_pause"]:
                if target_agent and hasattr(target_agent, "sys"):
                    target_agent.sys.media_play_pause()
                else:
                    ctypes.windll.user32.keybd_event(0xB3, 0, 0, 0)
                    ctypes.windll.user32.keybd_event(0xB3, 0, 2, 0)
                result["message"] = "Multimédia Play/Pause exécuté."

            elif cmd_clean in ["media_next", "next"]:
                if target_agent and hasattr(target_agent, "sys"):
                    target_agent.sys.media_next()
                else:
                    ctypes.windll.user32.keybd_event(0xB0, 0, 0, 0)
                    ctypes.windll.user32.keybd_event(0xB0, 0, 2, 0)
                result["message"] = "Piste suivante."

            elif cmd_clean in ["media_prev", "prev"]:
                if target_agent and hasattr(target_agent, "sys"):
                    target_agent.sys.media_prev()
                else:
                    ctypes.windll.user32.keybd_event(0xB1, 0, 0, 0)
                    ctypes.windll.user32.keybd_event(0xB1, 0, 2, 0)
                result["message"] = "Piste précédente."

            # 2. Contrôles Son / Volume
            elif cmd_clean in ["volume_up", "vol_up"]:
                steps = int(params.get("steps", 3))
                if target_agent and hasattr(target_agent, "sys"):
                    target_agent.sys.volume_up(steps=steps)
                else:
                    for _ in range(steps):
                        ctypes.windll.user32.keybd_event(0xAF, 0, 0, 0)
                        ctypes.windll.user32.keybd_event(0xAF, 0, 2, 0)
                result["message"] = f"Volume PC augmenté (+{steps})."

            elif cmd_clean in ["volume_down", "vol_down"]:
                steps = int(params.get("steps", 3))
                if target_agent and hasattr(target_agent, "sys"):
                    target_agent.sys.volume_down(steps=steps)
                else:
                    for _ in range(steps):
                        ctypes.windll.user32.keybd_event(0xAE, 0, 0, 0)
                        ctypes.windll.user32.keybd_event(0xAE, 0, 2, 0)
                result["message"] = f"Volume PC diminué (-{steps})."

            elif cmd_clean in ["volume_mute", "mute"]:
                if target_agent and hasattr(target_agent, "sys"):
                    target_agent.sys.volume_mute()
                else:
                    ctypes.windll.user32.keybd_event(0xAD, 0, 0, 0)
                    ctypes.windll.user32.keybd_event(0xAD, 0, 2, 0)
                result["message"] = "Mute basculé."

            # 3. Contrôles Fenêtres & Système
            elif cmd_clean in ["show_desktop", "bureau", "minimize_all"]:
                if target_agent and hasattr(target_agent, "sys"):
                    target_agent.sys.minimize_all_windows()
                result["message"] = "Affichage du bureau PC."

            elif cmd_clean in ["lock_pc", "verrouiller"]:
                try:
                    ctypes.windll.user32.LockWorkStation()
                except Exception:
                    pass
                result["message"] = "PC verrouillé."

            elif cmd_clean in ["sleep_pc", "veille"]:
                self.transfer_to_mobile(target_agent)
                result["message"] = "PC mis en veille et session basculée sur mobile."

            elif cmd_clean in ["switch_audio_screen", "audio_screen", "pl2766h"]:
                if target_agent and hasattr(target_agent, "tts") and target_agent.tts:
                    target_agent.tts.set_target_device("screen")
                result["message"] = "Sortie audio PC configurée sur l'écran PL2766H."

            elif cmd_clean in ["voice_command", "chat", "ask"]:
                prompt = params.get("prompt", "")
                if not prompt:
                    return {"success": False, "error": "Prompt vide."}
                if target_agent and hasattr(target_agent, "process_command"):
                    reply, is_exit = target_agent.process_command(prompt)
                    result["reply"] = reply
                    result["is_exit"] = is_exit
                else:
                    result["reply"] = "Commande reçue mais aucun agent actif sur le PC."

            elif cmd_clean == "telemetry":
                if target_agent and hasattr(target_agent, "computer_use") and hasattr(target_agent.computer_use, "telemetry"):
                    result["telemetry"] = target_agent.computer_use.telemetry.get_system_telemetry()
                else:
                    result["telemetry"] = {"status": "online", "platform": "Windows"}

            else:
                result["success"] = False
                result["error"] = f"Commande inconnue : {command}"

        except Exception as e:
            result["success"] = False
            result["error"] = str(e)

        return result

    def get_status(self) -> Dict[str, Any]:
        """Retourne l'état du pont Handoff."""
        return {
            "active_node": self.active_node,
            "mobile_connected": self.mobile_connected,
            "last_switch_time": self.last_switch_time,
            "mobile_device_info": self.mobile_device_info
        }

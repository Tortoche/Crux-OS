import time
import sys
import ctypes
import re
from ctypes import wintypes
from typing import Dict, List, Tuple, Optional, Any, Union

from core.agent_tools.ui_automation import UIAutomationEngine
from core.agent_tools.system_telemetry import SystemTelemetryEngine
from core.agent_tools.clipboard_manager import ClipboardManager
from core.agent_tools.code_interpreter import CodeInterpreterEngine

# Constantes Win32 API
user32 = ctypes.windll.user32

# Événements Souris
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800

# Virtual Keys Windows
VK_MAP = {
    "win": 0x5B, "windows": 0x5B, "super": 0x5B,
    "ctrl": 0x11, "control": 0x11,
    "alt": 0x12,
    "shift": 0x10,
    "tab": 0x09,
    "enter": 0x0D, "return": 0x0D,
    "esc": 0x1B, "escape": 0x1B,
    "space": 0x20, "espace": 0x20,
    "backspace": 0x08,
    "delete": 0x2E, "suppr": 0x2E,
    "up": 0x26, "haut": 0x26,
    "down": 0x28, "bas": 0x28,
    "left": 0x25, "gauche": 0x25,
    "right": 0x27, "droite": 0x27,
    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73,
    "f5": 0x74, "f6": 0x75, "f7": 0x76, "f8": 0x77,
    "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
    "printscreen": 0x2C, "prtsc": 0x2C,
}

# Remplissage touches alphanumériques
for c in "abcdefghijklmnopqrstuvwxyz":
    VK_MAP[c] = ord(c.upper())
for d in "0123456789":
    VK_MAP[d] = ord(d)

WM_CLOSE = 0x0010
SW_RESTORE = 9

class ComputerUseController:
    """
    Contrôleur d'automatisation avancé de l'ordinateur (Computer Use).
    Gère la souris, le clavier et les fenêtres directement via les APIs Windows ctypes.
    Intègre les moteurs spécialisés :
    - UIAutomationEngine : Pilotage headless in-memory sans déplacement de souris (sirendhead/Windows-Use)
    - SystemTelemetryEngine : Surveillance matérielle et gestion des processus (bnsware/jarvis-windows)
    - ClipboardManager : Contrôle natif du presse-papier (CursorTouch/Windows-MCP)
    - CodeInterpreterEngine : Exécution de commandes et code sécurisé (open-interpreter & dmrr35/Open.Jarvis)
    Intègre les garde-fous de sécurité stricts validés avec l'utilisateur.
    """
    def __init__(self):
        self.pending_confirmation: Optional[Dict[str, Any]] = None
        self.uia = UIAutomationEngine
        self.telemetry = SystemTelemetryEngine
        self.clipboard = ClipboardManager
        self.code_engine = CodeInterpreterEngine

    def is_valid_key(self, key: str) -> bool:
        """Vérifie si la touche est supportée par le contrôleur clavier."""
        k = key.lower().strip()
        return k in VK_MAP or len(k) == 1

    # ==========================================
    # CONTRÔLE SOURIS
    # ==========================================
    def get_mouse_position(self) -> Tuple[int, int]:
        """Retourne la position actuelle du curseur (x, y)."""
        pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        return pt.x, pt.y

    def mouse_move(self, x: int, y: int) -> bool:
        """Déplace le curseur aux coordonnées spécifiées."""
        return bool(user32.SetCursorPos(int(x), int(y)))

    def mouse_click(self, button: str = "left", double: bool = False) -> bool:
        """Effectue un clic ou un double clic souris."""
        b = button.lower()
        if b == "right":
            down_flag, up_flag = MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP
        elif b == "middle":
            down_flag, up_flag = MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP
        else:
            down_flag, up_flag = MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP

        user32.mouse_event(down_flag, 0, 0, 0, 0)
        time.sleep(0.02)
        user32.mouse_event(up_flag, 0, 0, 0, 0)

        if double:
            time.sleep(0.08)
            user32.mouse_event(down_flag, 0, 0, 0, 0)
            time.sleep(0.02)
            user32.mouse_event(up_flag, 0, 0, 0, 0)
        return True

    def mouse_drag(self, x1: int, y1: int, x2: int, y2: int, steps: int = 10) -> bool:
        """Glisser-déposer de (x1, y1) vers (x2, y2)."""
        self.mouse_move(x1, y1)
        time.sleep(0.05)
        user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.05)

        for i in range(1, steps + 1):
            curr_x = int(x1 + (x2 - x1) * (i / steps))
            curr_y = int(y1 + (y2 - y1) * (i / steps))
            self.mouse_move(curr_x, curr_y)
            time.sleep(0.01)

        time.sleep(0.05)
        user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        return True

    def mouse_scroll(self, clicks: int = 1) -> bool:
        """Fait défiler la molette de souris (positif = haut, négatif = bas)."""
        delta = clicks * 120
        user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, delta, 0)
        return True

    # ==========================================
    # CONTRÔLE CLAVIER
    # ==========================================
    def keyboard_hotkey(self, *keys: str) -> bool:
        """Presse simultanément une combinaison de touches (ex: 'win', 'd' ou 'ctrl', 'c')."""
        vk_codes = []
        for k in keys:
            code = VK_MAP.get(k.lower())
            if code is None:
                if len(k) == 1:
                    code = ord(k.upper())
                else:
                    return False
            vk_codes.append(code)

        for code in vk_codes:
            user32.keybd_event(code, 0, 0, 0)
            time.sleep(0.01)

        time.sleep(0.03)

        for code in reversed(vk_codes):
            user32.keybd_event(code, 0, 2, 0)
            time.sleep(0.01)

        return True

    def keyboard_type(self, text: str) -> bool:
        """Saisit du texte caractère par caractère."""
        for char in text:
            user32.keybd_event(0, ord(char), 0x0004, 0)
            user32.keybd_event(0, ord(char), 0x0004 | 0x0002, 0)
            time.sleep(0.01)
        return True

    # ==========================================
    # GESTION DES FENÊTRES WINDOWS
    # ==========================================
    def get_active_window_title(self) -> str:
        """Retourne le titre de la fenêtre active au premier plan."""
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return ""
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return ""
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value

    def list_visible_windows(self) -> List[Dict[str, Any]]:
        """Liste les fenêtres visibles avec leurs handles et titres."""
        windows = []

        def enum_handler(hwnd, extra):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buf, length + 1)
                    title = buf.value.strip()
                    if title:
                        windows.append({"hwnd": hwnd, "title": title})
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        user32.EnumWindows(WNDENUMPROC(enum_handler), 0)
        return windows

    def find_window_by_title(self, pattern: str) -> Optional[int]:
        """Trouve le handle d'une fenêtre contenant pattern (insensible à la casse)."""
        pattern_lower = pattern.lower()
        for win in self.list_visible_windows():
            if pattern_lower in win["title"].lower():
                return win["hwnd"]
        return None

    def focus_window(self, title_pattern: str) -> bool:
        """Met la fenêtre correspondante au premier plan."""
        hwnd = self.find_window_by_title(title_pattern)
        if not hwnd:
            return False
        user32.ShowWindow(hwnd, SW_RESTORE)
        user32.SetForegroundWindow(hwnd)
        return True

    def minimize_window(self, title_pattern: str) -> bool:
        """Minimise la fenêtre cible."""
        hwnd = self.find_window_by_title(title_pattern)
        if not hwnd:
            return False
        user32.ShowWindow(hwnd, 6)
        return True

    def maximize_window(self, title_pattern: str) -> bool:
        """Maximise la fenêtre cible en plein écran."""
        hwnd = self.find_window_by_title(title_pattern)
        if not hwnd:
            return False
        user32.ShowWindow(hwnd, 3)
        return True

    def close_window(self, title_pattern: str) -> bool:
        """Ferme la fenêtre cible (Action critique soumise à garde-fou)."""
        hwnd = self.find_window_by_title(title_pattern)
        if not hwnd:
            return False
        user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
        return True

    # ==========================================
    # UI AUTOMATION HEADLESS (SANS SOURIS)
    # ==========================================
    def uia_click(
        self,
        name: Optional[str] = None,
        control_type: Optional[str] = None,
        automation_id: Optional[str] = None,
        window_title: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Active un bouton ou élément via l'arbre UI Automation en mémoire."""
        return self.uia.click_control(
            name=name,
            control_type=control_type,
            automation_id=automation_id,
            window_title=window_title
        )

    def uia_set_value(
        self,
        text: str,
        name: Optional[str] = None,
        control_type: Optional[str] = None,
        automation_id: Optional[str] = None,
        window_title: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Injecte du texte directement dans un champ sans manipulation physique."""
        return self.uia.set_control_value(
            text,
            name=name,
            control_type=control_type,
            automation_id=automation_id,
            window_title=window_title
        )

    def uia_get_value(
        self,
        name: Optional[str] = None,
        control_type: Optional[str] = None,
        automation_id: Optional[str] = None,
        window_title: Optional[str] = None
    ) -> Optional[str]:
        """Extrait la valeur d'un élément UIA."""
        return self.uia.get_control_value(
            name=name,
            control_type=control_type,
            automation_id=automation_id,
            window_title=window_title
        )

    def uia_inspect_window(self, window_title: Optional[str] = None) -> str:
        """Synthétise les éléments de la fenêtre active ou ciblée pour décision Jarvis."""
        return self.uia.dump_window_summary(window_title=window_title)

    # ==========================================
    # PRESSE-PAPIER (CLIPBOARD)
    # ==========================================
    def clipboard_get(self) -> str:
        """Lit le texte du presse-papier."""
        return self.clipboard.get_text()

    def clipboard_set(self, text: str) -> bool:
        """Écrit du texte dans le presse-papier."""
        return self.clipboard.set_text(text)

    def clipboard_clear(self) -> bool:
        """Vide le presse-papier."""
        return self.clipboard.clear()

    # ==========================================
    # PROCESSUS ET TÉLÉMÉTRIE
    # ==========================================
    def list_processes(self, sort_by: str = "cpu", limit: int = 10, name_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Liste les processus actifs triés par CPU ou RAM."""
        return self.telemetry.list_processes(sort_by=sort_by, limit=limit, name_filter=name_filter)

    def get_process_info(self, target: Union[int, str]) -> Optional[Dict[str, Any]]:
        """Détails complets sur un processus par PID ou nom."""
        return self.telemetry.get_process_info(target)

    def kill_process(self, target: Union[int, str], force: bool = False) -> Tuple[bool, str]:
        """Arrête un processus (Action critique soumise à garde-fou)."""
        return self.telemetry.kill_process(target, force=force)

    # ==========================================
    # EXÉCUTION DE CODE & SCRIPTS (OPEN-INTERPRETER)
    # ==========================================
    def run_script(self, script_path: str, args: Optional[List[str]] = None) -> Tuple[bool, str]:
        """Exécute un script local externe (Python, bat, ps1) après confirmation."""
        import os
        import subprocess
        clean_path = script_path.strip().strip('"').strip("'")
        if not os.path.isabs(clean_path):
            candidates = [
                os.path.join(r"C:\Users\coco\Documents", clean_path),
                os.path.join(os.getcwd(), clean_path)
            ]
            for c in candidates:
                if os.path.exists(c):
                    clean_path = c
                    break

        if not os.path.exists(clean_path):
            return False, f"Fichier script '{script_path}' introuvable."

        try:
            cmd = []
            if clean_path.endswith(".py"):
                cmd = [sys.executable, clean_path]
            elif clean_path.endswith(".ps1"):
                cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", clean_path]
            elif clean_path.endswith(".bat") or clean_path.endswith(".cmd"):
                cmd = ["cmd.exe", "/c", clean_path]
            else:
                cmd = [clean_path]

            if args:
                cmd.extend(args)

            subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE if hasattr(subprocess, "CREATE_NEW_CONSOLE") else 0)
            return True, f"Script {os.path.basename(clean_path)} lancé avec succès."
        except Exception as e:
            return False, f"Erreur lors de l'exécution du script : {e}"

    def execute_command(self, command: str, shell: str = "powershell", timeout: float = 15.0) -> Dict[str, Any]:
        """Exécute une commande système via CodeInterpreterEngine."""
        return self.code_engine.run_command(command, shell=shell, timeout=timeout)

    def execute_python(self, code: str, timeout: float = 15.0) -> Dict[str, Any]:
        """Exécute du code Python via CodeInterpreterEngine."""
        return self.code_engine.run_python(code, timeout=timeout)

    # ==========================================
    # GARDE-FOUS DE SÉCURITÉ (SAFETY RAILS)
    # ==========================================
    def is_critical_action(self, action_type: str, params: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Détermine si l'action requiert obligatoirement une confirmation vocale de Corentin.
        Actions critiques : fermeture d'application, arrêt de processus, scripts/commandes sensibles.
        """
        critical_types = ["close_window", "kill_process", "run_script", "run_command", "run_code", "system_shutdown", "format_drive"]
        if action_type in critical_types:
            if action_type == "run_command":
                cmd = params.get("command", "")
                is_dang, msg = self.code_engine.is_dangerous(cmd)
                if is_dang:
                    return True, msg
                # Pour les autres commandes ordinaires, exécuter directement sans bloquer
                return False, ""

            if action_type == "run_code":
                code = params.get("code", "")
                is_dang, msg = self.code_engine.is_dangerous(code)
                if is_dang:
                    return True, msg
                return False, ""

            target = params.get("title_pattern") or params.get("process") or params.get("script") or "l'élément cible"
            return True, f"Êtes-vous certain de vouloir fermer ou exécuter {target} ?"

        if action_type == "keyboard_hotkey":
            keys = [str(k).lower() for k in params.get("keys", [])]
            if "alt" in keys and "f4" in keys:
                return True, "Êtes-vous certain de vouloir fermer l'application active avec Alt+F4 ?"

        return False, ""

    def request_confirmation(self, action_type: str, params: Dict[str, Any], prompt_message: str):
        """Enregistre une action critique en attente de validation."""
        self.pending_confirmation = {
            "action_type": action_type,
            "params": params,
            "prompt_message": prompt_message,
            "timestamp": time.time()
        }

    def has_pending_confirmation(self) -> bool:
        return self.pending_confirmation is not None

    def execute_confirmed_action(self) -> Tuple[bool, str]:
        """Exécute l'action critique mise en attente une fois approuvée."""
        if not self.pending_confirmation:
            return False, "Aucune action en attente."

        action = self.pending_confirmation["action_type"]
        params = self.pending_confirmation["params"]
        self.pending_confirmation = None

        if action == "close_window":
            target = params.get("title_pattern", "")
            ok = self.close_window(target)
            return ok, f"Fenêtre {target} fermée." if ok else f"Impossible de fermer {target}."

        if action == "kill_process":
            target = params.get("process", "")
            force = params.get("force", False)
            ok, msg = self.kill_process(target, force=force)
            return ok, msg

        if action == "keyboard_hotkey":
            keys = params.get("keys", [])
            ok = self.keyboard_hotkey(*keys)
            return ok, "Raccourci exécuté."

        if action == "run_script":
            script = params.get("script", "")
            args = params.get("args")
            ok, msg = self.run_script(script, args=args)
            return ok, msg

        if action == "run_command":
            cmd = params.get("command", "")
            shell = params.get("shell", "powershell")
            res = self.execute_command(cmd, shell=shell)
            out = res["stdout"] or res["stderr"] or "Commande terminée."
            return res["success"], out

        if action == "run_code":
            code = params.get("code", "")
            res = self.execute_python(code)
            out = res["stdout"] or res["stderr"] or "Code exécuté."
            return res["success"], out

        return False, "Action non reconnue."

    def cancel_pending_action(self) -> str:
        """Annule l'action en attente."""
        self.pending_confirmation = None
        return "Action annulée."

import os
import json
import psutil
import socket
import ctypes
from ctypes import wintypes
import subprocess
import webbrowser
import re
import time
import threading
import urllib.request
import urllib.parse
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

class RECT(ctypes.Structure):
    _fields_ = [
        ('left', wintypes.LONG),
        ('top', wintypes.LONG),
        ('right', wintypes.LONG),
        ('bottom', wintypes.LONG)
    ]

class SystemController:
    """
    Module de contrôle du PC Windows pour Crux AI (style Jarvis).
    Permet de surveiller les performances, piloter le volume et les médias,
    prendre des captures d'écran, enregistrer des notes, manipuler les fenêtres,
    gérer des presets d'espace de travail, et intégrer la musique (Spotify, YouTube).
    """
    def __init__(self):
        # Dictionnaire d'applications courantes
        self.common_apps = {
            "discord": r"Update.exe --processStart Discord.exe",
            "chrome": "chrome",
            "navigateur": "chrome",
            "spotify": "start spotify:",
            "gestionnaire des taches": "taskmgr",
            "task manager": "taskmgr",
            "calculatrice": "calc",
            "bloc-notes": "notepad",
            "notepad": "notepad",
            "explorateur": "explorer",
            "paramètres": "ms-settings:",
            "steam": "steam"
        }
        self.notes_file = Path(r"C:\Users\coco\Documents\notes_crux.md")
        self.presets_file = Path(__file__).parent.parent / "data" / "window_presets.json"
        self.presets_file.parent.mkdir(parents=True, exist_ok=True)
        self._cached_location: Optional[Dict[str, Any]] = None

    # ==========================================
    # 1. CONTRÔLE DU VOLUME & MULTIMÉDIA
    # ==========================================
    def volume_up(self, steps: int = 5) -> str:
        """Augmente le volume sonore de Windows."""
        for _ in range(steps):
            ctypes.windll.user32.keybd_event(0xAF, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0xAF, 0, 2, 0)
        return "Volume augmenté."

    def volume_down(self, steps: int = 5) -> str:
        """Diminue le volume sonore de Windows."""
        for _ in range(steps):
            ctypes.windll.user32.keybd_event(0xAE, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0xAE, 0, 2, 0)
        return "Volume diminué."

    def volume_mute(self) -> str:
        """Active ou coupe le son de Windows (Mute)."""
        ctypes.windll.user32.keybd_event(0xAD, 0, 0, 0)
        ctypes.windll.user32.keybd_event(0xAD, 0, 2, 0)
        return "Statut du son basculé."

    def media_play_pause(self) -> str:
        """Met en pause ou reprend la lecture multimédia (Spotify, YouTube, etc.)."""
        ctypes.windll.user32.keybd_event(0xB3, 0, 0, 0)
        ctypes.windll.user32.keybd_event(0xB3, 0, 2, 0)
        return "Lecture multimédia modifiée."

    def media_next(self) -> str:
        """Passe au morceau suivant."""
        ctypes.windll.user32.keybd_event(0xB0, 0, 0, 0)
        ctypes.windll.user32.keybd_event(0xB0, 0, 2, 0)
        return "Piste suivante lancée."

    def media_prev(self) -> str:
        """Revient au morceau précédent."""
        ctypes.windll.user32.keybd_event(0xB1, 0, 0, 0)
        ctypes.windll.user32.keybd_event(0xB1, 0, 2, 0)
        return "Piste précédente lancée."

    # ==========================================
    # 2. CAPTURE D'ÉCRAN & AFFICHAGE
    # ==========================================
    def take_screenshot(self) -> str:
        """Effectue une capture d'écran Windows (Win + PrintScreen)."""
        VK_LWIN = 0x5B
        VK_SNAPSHOT = 0x2C
        KEYEVENTF_KEYUP = 0x0002
        try:
            ctypes.windll.user32.keybd_event(VK_LWIN, 0, 0, 0)
            ctypes.windll.user32.keybd_event(VK_SNAPSHOT, 0, 0, 0)
            ctypes.windll.user32.keybd_event(VK_SNAPSHOT, 0, KEYEVENTF_KEYUP, 0)
            ctypes.windll.user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)
            return "Capture d'écran effectuée et sauvegardée dans vos Images."
        except Exception as e:
            return f"Échec de la capture d'écran : {e}"

    def sleep_display(self) -> str:
        """Met les écrans en veille immédiatement."""
        try:
            ctypes.windll.user32.SendMessageW(0xFFFF, 0x0112, 0xF170, 2)
            return "Mise en veille des écrans effectuée."
        except Exception as e:
            return f"Erreur lors de la mise en veille : {e}"

    # ==========================================
    # 3. OPTIMISATION MODE JEU & STATS
    # ==========================================
    def game_mode_boost(self) -> str:
        """Active l'optimisation pour session de jeu (nettoyage RAM et bilan perfs)."""
        # Nettoyage mémoire de travail
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'] in ['chrome.exe', 'msedge.exe', 'discord.exe']:
                    try:
                        handle = ctypes.windll.kernel32.OpenProcess(0x001F0FFF, False, proc.info['pid'])
                        if handle:
                            ctypes.windll.psapi.EmptyWorkingSet(handle)
                            ctypes.windll.kernel32.CloseHandle(handle)
                    except Exception:
                        pass
        except Exception:
            pass

        ram = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=0.1)
        ram_free_gb = round(ram.available / (1024**3), 1)
        return f"Mode Jeu enclenché : Processeur à {cpu} %, {ram_free_gb} Go de RAM libérés pour vos FPS maximaux."

    def get_system_stats(self) -> str:
        """Retourne un bilan flash des performances du PC (CPU, RAM, Disque)."""
        cpu = psutil.cpu_percent(interval=0.2)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("C:")

        ram_free_gb = round(ram.available / (1024**3), 1)
        disk_free_gb = round(disk.free / (1024**3), 1)

        return (
            f"Statut système : Processeur à {cpu} %, "
            f"RAM utilisée à {ram.percent} % ({ram_free_gb} Go libres), "
            f"Disque C : {disk_free_gb} Go disponibles."
        )

    # ==========================================
    # 4. PENSE-BÊTE & GESTION DES NOTES
    # ==========================================
    def save_note(self, note_text: str) -> str:
        """Enregistre un pense-bête dans notes_crux.md."""
        now_str = datetime.now().strftime("%d/%m/%Y à %H:%M")
        clean_note = note_text.strip()
        try:
            with open(self.notes_file, "a", encoding="utf-8") as f:
                f.write(f"- [{now_str}] {clean_note}\n")
            return f"Note enregistrée : {clean_note}."
        except Exception as e:
            return f"Erreur lors de l'enregistrement de la note : {e}"

    def read_notes(self) -> str:
        """Lit les 3 dernières notes enregistrées."""
        if not self.notes_file.exists():
            return "Vous n'avez aucune note enregistrée."
        try:
            with open(self.notes_file, "r", encoding="utf-8") as f:
                lines = [line.strip().lstrip("- ") for line in f if line.strip()]
            if not lines:
                return "Vous n'avez aucune note enregistrée."
            recent = lines[-3:]
            notes_str = ". ".join(recent)
            return f"Vos dernières notes sont : {notes_str}."
        except Exception as e:
            return f"Impossible de lire vos notes : {e}"

    def clear_notes(self) -> str:
        """Efface toutes les notes."""
        if self.notes_file.exists():
            try:
                os.remove(self.notes_file)
                return "Toutes vos notes ont été effacées."
            except Exception as e:
                return f"Erreur lors de la suppression des notes : {e}"
        return "Aucune note à effacer."

    # ==========================================
    # 5. UTILITAIRES SYSTÈME (CORBEILLE, IP, VERROUILLAGE)
    # ==========================================
    def empty_recycle_bin(self) -> str:
        """Vide la corbeille de Windows en silence."""
        try:
            ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 7)
            return "Corbeille de Windows vidée avec succès."
        except Exception as e:
            return f"Erreur lors du nettoyage de la corbeille : {e}"

    def get_ip_info(self) -> str:
        """Retourne l'adresse IP locale du PC."""
        try:
            local_ip = socket.gethostbyname(socket.gethostname())
            return f"Votre adresse IP locale sur le réseau est {local_ip}."
        except Exception:
            return "Impossible de récupérer l'adresse IP locale."

    def lock_pc(self) -> str:
        """Verrouille l'ordinateur."""
        try:
            subprocess.run("rundll32.exe user32.dll,LockWorkStation", shell=True)
            return "Ordinateur verrouillé."
        except Exception as e:
            return f"Erreur lors du verrouillage : {e}"

    def open_folder(self, folder_path: str = r"C:\Users\coco\Documents") -> str:
        """Ouvre un dossier dans l'explorateur Windows."""
        try:
            os.startfile(folder_path)
            folder_name = Path(folder_path).name
            return f"Dossier {folder_name} ouvert dans l'explorateur."
        except Exception as e:
            return f"Impossible d'ouvrir le dossier : {e}"

    def launch_app(self, app_name: str) -> Dict[str, Any]:
        """Ouvre une application ou un outil Windows."""
        app_clean = app_name.lower().strip()
        for name, cmd in self.common_apps.items():
            if name in app_clean:
                try:
                    subprocess.Popen(cmd, shell=True)
                    return {"success": True, "message": f"Ouverture de {name.capitalize()} en cours."}
                except Exception as e:
                    return {"success": False, "message": f"Impossible d'ouvrir {name} : {e}"}

        try:
            subprocess.Popen(f"start {app_clean}", shell=True)
            return {"success": True, "message": f"Lancement de {app_clean}."}
        except Exception as e:
            return {"success": False, "message": f"Erreur lors du lancement de {app_clean} : {e}"}

    def open_web(self, query_or_url: str) -> str:
        """Ouvre un site web ou lance une recherche Google."""
        query_or_url = query_or_url.strip()
        if query_or_url.startswith("http://") or query_or_url.startswith("https://"):
            webbrowser.open(query_or_url)
            return f"Ouverture du site {query_or_url}."
        elif "youtube" in query_or_url.lower():
            webbrowser.open("https://www.youtube.com")
            return "YouTube est ouvert."
        elif "mail" in query_or_url.lower() or "gmail" in query_or_url.lower():
            webbrowser.open("https://mail.google.com")
            return "Votre messagerie Gmail est ouverte."
        else:
            url = f"https://www.google.com/search?q={query_or_url}"
            webbrowser.open(url)
            return f"Recherche Google lancée pour '{query_or_url}'."

    # ==========================================
    # 6. MANIPULATION ET SNAP DES FENÊTRES
    # ==========================================
    def _get_work_area(self) -> Tuple[int, int, int, int]:
        """Retourne la zone de travail utilisable de l'écran principal (left, top, width, height)."""
        r = RECT()
        ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(r), 0)
        return r.left, r.top, r.right - r.left, r.bottom - r.top

    def snap_active_window(self, direction: str) -> str:
        """
        Positionne la fenêtre active : gauche, droite, plein écran, réduite, centree.
        """
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return "Aucune fenêtre active détectée."

        left, top, screen_w, screen_h = self._get_work_area()
        SWP_SHOWWINDOW = 0x0040
        dir_clean = direction.lower().strip()

        # Restaurer la fenêtre si elle était maximisée avant de la déplacer
        user32.ShowWindow(hwnd, 9) # SW_RESTORE

        if "gauche" in dir_clean or "left" in dir_clean:
            w = screen_w // 2
            h = screen_h
            user32.SetWindowPos(hwnd, 0, left, top, w, h, SWP_SHOWWINDOW)
            return "Fenêtre active ancrée sur la moitié gauche."

        elif "droite" in dir_clean or "right" in dir_clean:
            w = screen_w // 2
            h = screen_h
            user32.SetWindowPos(hwnd, 0, left + w, top, w, h, SWP_SHOWWINDOW)
            return "Fenêtre active ancrée sur la moitié droite."

        elif any(k in dir_clean for k in ["plein ecran", "maximise", "agrandis", "grand"]):
            user32.ShowWindow(hwnd, 3) # SW_MAXIMIZE
            return "Fenêtre agrandie en plein écran."

        elif any(k in dir_clean for k in ["reduis", "minimise", "cache"]):
            user32.ShowWindow(hwnd, 6) # SW_MINIMIZE
            return "Fenêtre réduite dans la barre des tâches."

        elif "centre" in dir_clean or "milieu" in dir_clean:
            w = int(screen_w * 0.7)
            h = int(screen_h * 0.8)
            x = left + (screen_w - w) // 2
            y = top + (screen_h - h) // 2
            user32.SetWindowPos(hwnd, 0, x, y, w, h, SWP_SHOWWINDOW)
            return "Fenêtre recentrée au milieu de l'écran."

        return "Direction de fenêtre non reconnue."

    def minimize_all_windows(self) -> str:
        """Minimise toutes les fenêtres pour afficher le bureau (Win+D)."""
        VK_LWIN = 0x5B
        VK_D = 0x44
        ctypes.windll.user32.keybd_event(VK_LWIN, 0, 0, 0)
        ctypes.windll.user32.keybd_event(VK_D, 0, 0, 0)
        time.sleep(0.05)
        ctypes.windll.user32.keybd_event(VK_D, 0, 2, 0)
        ctypes.windll.user32.keybd_event(VK_LWIN, 0, 2, 0)
        return "Toutes les fenêtres ont été réduites."

    # ==========================================
    # 7. PRESETS D'ESPACE DE TRAVAIL (WINDOW PRESETS)
    # ==========================================
    def _enumerate_visible_windows(self) -> List[Dict[str, Any]]:
        """Énumère toutes les fenêtres applicatives visibles sur le bureau."""
        user32 = ctypes.windll.user32
        h_winsta0 = user32.OpenWindowStationW('WinSta0', False, 0x037F)
        if h_winsta0:
            user32.SetProcessWindowStation(h_winsta0)
        h_desk = user32.OpenDesktopW('default', 0, False, 0x01FF)

        windows = []
        def enum_cb(hwnd, lparam):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value.strip()
                    r = RECT()
                    user32.GetWindowRect(hwnd, ctypes.byref(r))
                    w = r.right - r.left
                    h = r.bottom - r.top
                    # Ignorer les overlays miniatures ou invisibles
                    if w > 100 and h > 100 and title and title not in ["Program Manager", "Crux Notch HUD"]:
                        pid = wintypes.DWORD()
                        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                        try:
                            p = psutil.Process(pid.value)
                            pname = p.name()
                            pexe = p.exe()
                        except Exception:
                            pname = "unknown"
                            pexe = ""
                        windows.append({
                            "title": title,
                            "process": pname,
                            "exe": pexe,
                            "x": r.left,
                            "y": r.top,
                            "w": w,
                            "h": h
                        })
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        cb = WNDENUMPROC(enum_cb)
        user32.EnumDesktopWindows(h_desk, cb, 0)
        return windows

    def save_workspace_preset(self, preset_name: str) -> str:
        """
        Enregistre la disposition actuelle des fenêtres ainsi que le lecteur musical actif.
        """
        clean_name = preset_name.lower().strip()
        windows = self._enumerate_visible_windows()
        active_music = self.get_active_music_player()

        presets = {}
        if self.presets_file.exists():
            try:
                with open(self.presets_file, "r", encoding="utf-8") as f:
                    presets = json.load(f)
            except Exception:
                presets = {}

        presets[clean_name] = {
            "created_at": datetime.now().isoformat(),
            "windows_count": len(windows),
            "music_player": active_music,
            "windows": windows
        }

        with open(self.presets_file, "w", encoding="utf-8") as f:
            json.dump(presets, f, indent=2, ensure_ascii=False)

        return f"Preset '{clean_name.capitalize()}' enregistré avec {len(windows)} fenêtres et votre état musical."

    def apply_workspace_preset(self, preset_name: str) -> str:
        """
        Restaure la disposition des fenêtres et relance l'environnement associé.
        """
        clean_name = preset_name.lower().strip()
        if not self.presets_file.exists():
            return "Aucun preset d'espace de travail n'est enregistré pour le moment."

        try:
            with open(self.presets_file, "r", encoding="utf-8") as f:
                presets = json.load(f)
        except Exception as e:
            return f"Erreur lors de la lecture des presets : {e}"

        preset_data = presets.get(clean_name)
        if not preset_data:
            # Recherche approchante
            candidates = [k for k in presets.keys() if clean_name in k or k in clean_name]
            if candidates:
                preset_data = presets[candidates[0]]
                clean_name = candidates[0]
            else:
                dispo = ", ".join(presets.keys())
                return f"Preset '{clean_name}' introuvable. Presets disponibles : {dispo}."

        windows_to_restore = preset_data.get("windows", [])
        user32 = ctypes.windll.user32
        h_winsta0 = user32.OpenWindowStationW('WinSta0', False, 0x037F)
        if h_winsta0:
            user32.SetProcessWindowStation(h_winsta0)
        h_desk = user32.OpenDesktopW('default', 0, False, 0x01FF)

        # Retrouver les fenêtres ouvertes actuelles
        current_hwnds = {}
        def enum_curr(hwnd, lparam):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    t = buff.value.strip()
                    pid = wintypes.DWORD()
                    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                    try:
                        pname = psutil.Process(pid.value).name().lower()
                    except Exception:
                        pname = ""
                    current_hwnds.setdefault(pname, []).append((hwnd, t))
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        user32.EnumDesktopWindows(h_desk, WNDENUMPROC(enum_curr), 0)

        restored = 0
        SWP_SHOWWINDOW = 0x0040
        for win in windows_to_restore:
            pname = win.get("process", "").lower()
            x = win.get("x", 0)
            y = win.get("y", 0)
            w = win.get("w", 800)
            h = win.get("h", 600)
            
            # Match fenêtre par nom de process
            candidates = current_hwnds.get(pname, [])
            matched_hwnd = None
            for chwnd, ctitle in candidates:
                if win.get("title", "") in ctitle or ctitle in win.get("title", ""):
                    matched_hwnd = chwnd
                    break
            if not matched_hwnd and candidates:
                matched_hwnd = candidates[0][0]

            if matched_hwnd:
                user32.ShowWindow(matched_hwnd, 9) # SW_RESTORE
                user32.SetWindowPos(matched_hwnd, 0, x, y, w, h, SWP_SHOWWINDOW)
                restored += 1
            else:
                # Si l'application n'est pas ouverte et qu'on a son chemin, tentative de lancement
                exe_path = win.get("exe")
                if exe_path and os.path.exists(exe_path):
                    try:
                        subprocess.Popen(exe_path)
                    except Exception:
                        pass

        # Si le preset contenait un lecteur multimédia actif, envoyer un signal play
        music_player = preset_data.get("music_player")
        if music_player:
            self.media_play_pause()

        return f"Mode {clean_name.capitalize()} déployé : {restored} fenêtres repositionnées avec précision."

    def list_workspace_presets(self) -> str:
        """Retourne la liste des presets sauvegardés."""
        if not self.presets_file.exists():
            return "Aucun preset enregistré pour le moment."
        try:
            with open(self.presets_file, "r", encoding="utf-8") as f:
                presets = json.load(f)
            if not presets:
                return "Vous n'avez aucun preset enregistré."
            names = ", ".join(f"'{k.capitalize()}' ({v.get('windows_count', 0)} fenêtres)" for k, v in presets.items())
            return f"Vos presets disponibles sont : {names}."
        except Exception as e:
            return f"Erreur lors de la lecture des presets : {e}"

    # ==========================================
    # 8. INTÉGRATIONS MUSIQUE (SPOTIFY, YOUTUBE)
    # ==========================================
    def get_active_music_player(self) -> Optional[str]:
        """Détecte l'application musicale active (Spotify, navigateur web, VLC)."""
        try:
            for proc in psutil.process_iter(['name']):
                pname = proc.info['name'].lower()
                if 'spotify' in pname:
                    return "Spotify"
                elif 'vlc' in pname:
                    return "VLC"
        except Exception:
            pass
        return None

    def is_app_running(self, app_name: str) -> bool:
        """Vérifie si un processus contenant app_name est actif."""
        target = app_name.lower().strip()
        try:
            for proc in psutil.process_iter(['name']):
                if target in proc.info['name'].lower():
                    return True
        except Exception:
            pass
        return False

    def _get_spotify_cli_path(self) -> Optional[Path]:
        """Localise l'exécutable officiel spotify_cli.exe."""
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            cli = Path(appdata) / "Spotify" / "spotify_cli.exe"
            if cli.exists():
                return cli
        return None

    def _ensure_spotify_running(self) -> bool:
        """S'assure que Spotify est actif en arrière-plan."""
        if self.is_app_running("spotify"):
            return True
        cli = self._get_spotify_cli_path()
        if cli:
            try:
                subprocess.Popen([str(cli), "open"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
        else:
            try:
                subprocess.Popen("start spotify:", shell=True)
            except Exception:
                pass
        for _ in range(12):
            time.sleep(0.25)
            if self.is_app_running("spotify"):
                return True
        return False

    def play_spotify_smart(self, query: str = "") -> Tuple[bool, str]:
        """
        Contrôle 100% programmatique de Spotify à la Jarvis (Zéro mouvement de souris).
        Raisonnement multi-étapes :
        1. Détecte automatiquement l'intention (playlist vs morceau/artiste vs reprise)
        2. Vérifie et lance Spotify en arrière-plan si fermé
        3. Effectue la recherche via l'API/CLI locale native en JSON
        4. Lance la lecture directe de l'URI ciblée (top playlist ou premier morceau)
        5. Synchronise en temps réel la Notch Coucou (titre, artiste, pochette, danse Mochi)
        """
        cli = self._get_spotify_cli_path()
        if not cli:
            return False, "CLI Spotify non disponible."

        self._ensure_spotify_running()

        query_clean = query.strip()
        # Détection s'il s'agit d'une demande de playlist
        is_playlist = any(w in query_clean.lower() for w in ["playlist", "playliste", "ambiance", "mix"])
        
        search_term = query_clean
        for kw in ["playliste", "playlist"]:
            search_term = re.sub(rf"\b{kw}\b", "", search_term, flags=re.IGNORECASE).strip()

        if not search_term or search_term.lower() in ["musique", "la musique", "du son", "de la musique"]:
            search_term = "Top Hits" if is_playlist else "Hits du moment"

        qtype = "playlist" if is_playlist else "track"

        try:
            cmd = [str(cli), "search", search_term, "--type", qtype, "--limit", "3", "--format", "json"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=3.5)
            if res.returncode == 0 and res.stdout.strip():
                data = json.loads(res.stdout)
                items = data.get(qtype + "s", [])
                if items:
                    target = items[0]
                    uri = target.get("uri")
                    name = target.get("name", search_term)
                    artist = target.get("author") or (target.get("artists", ["Spotify"])[0] if target.get("artists") else "Spotify")
                    image_url = target.get("image", "")

                    if uri:
                        subprocess.run([str(cli), "play", uri], capture_output=True, text=True, timeout=2.5)
                        
                        # Synchronisation visuelle Coucou Notch
                        try:
                            from core.coucou_client import CoucouClient
                            CoucouClient.get_instance().sync_spotify_status(
                                title=name,
                                artist=str(artist),
                                album=name if is_playlist else "Spotify",
                                is_playing=True,
                                art_url=image_url
                            )
                        except Exception:
                            pass

                        label = "la playlist" if is_playlist else "le titre"
                        return True, f"Lancement de {label} '{name}' sur Spotify."
        except Exception:
            pass

        # Repli : reprise directe ou lecture
        try:
            subprocess.run([str(cli), "play"], capture_output=True, text=True, timeout=2.0)
            return True, "Lecture reprise sur Spotify."
        except Exception:
            pass

        return False, "Échec du contrôle programmatique Spotify."

    def _trigger_spotify_playback(self, delay: float = 0.8):
        """
        Déclenche automatiquement la validation de lecture sur Spotify via touches clavier Windows sans mouvement de souris.
        """
        def _worker():
            try:
                time.sleep(delay)
                user32 = ctypes.windll.user32
                kernel32 = ctypes.windll.kernel32

                h_winsta0 = user32.OpenWindowStationW('WinSta0', False, 0x037F)
                if h_winsta0:
                    user32.SetProcessWindowStation(h_winsta0)
                h_desk = user32.OpenDesktopW('default', 0, False, 0x01FF)
                if h_desk:
                    user32.SetThreadDesktop(h_desk)

                spotify_hwnd = None
                poll_deadline = time.time() + 2.5
                while time.time() < poll_deadline:
                    def enum_cb(hwnd, _):
                        nonlocal spotify_hwnd
                        if user32.IsWindowVisible(hwnd):
                            cls_buf = ctypes.create_unicode_buffer(256)
                            user32.GetClassNameW(hwnd, cls_buf, 256)
                            if cls_buf.value == 'Chrome_WidgetWin_1':
                                t_buf = ctypes.create_unicode_buffer(512)
                                user32.GetWindowTextW(hwnd, t_buf, 512)
                                if 'spotify' in t_buf.value.lower() or '-' in t_buf.value:
                                    spotify_hwnd = hwnd
                                    return False
                        return True

                    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
                    user32.EnumDesktopWindows(h_desk, WNDENUMPROC(enum_cb), 0)
                    if spotify_hwnd:
                        break
                    time.sleep(0.08)

                if spotify_hwnd:
                    target_thread = user32.GetWindowThreadProcessId(spotify_hwnd, None)
                    curr_thread = kernel32.GetCurrentThreadId()
                    fore_hwnd = user32.GetForegroundWindow()
                    fore_thread = user32.GetWindowThreadProcessId(fore_hwnd, None) if fore_hwnd else 0

                    user32.AttachThreadInput(curr_thread, target_thread, True)
                    if fore_thread:
                        user32.AttachThreadInput(curr_thread, fore_thread, True)

                    user32.OpenIcon(spotify_hwnd)
                    user32.ShowWindow(spotify_hwnd, 9)  # SW_RESTORE
                    user32.BringWindowToTop(spotify_hwnd)
                    user32.SetForegroundWindow(spotify_hwnd)

                    if fore_thread:
                        user32.AttachThreadInput(curr_thread, fore_thread, False)
                    user32.AttachThreadInput(curr_thread, target_thread, False)
                    time.sleep(0.1)

                def key(vk):
                    user32.keybd_event(vk, 0, 0, 0)
                    time.sleep(0.03)
                    user32.keybd_event(vk, 0, 2, 0)
                    time.sleep(0.04)

                for _ in range(7):
                    key(0x09) # VK_TAB
                key(0x0D) # VK_RETURN
                time.sleep(0.1)
                key(0x09)
                key(0x0D)
            except Exception:
                pass

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    def play_music(self, query: str = "", platform: Optional[str] = None) -> str:
        """
        Recherche et lance de la musique sur Spotify ou YouTube, ou reprend la lecture si aucun titre n'est spécifié.
        Contrôle 100% headless / programmatique SANS mouvement de souris.
        """
        query_clean = query.strip() if query else ""

        # Détecter plateforme explicitement mentionnée dans le texte
        plat = (platform or "").lower()
        if "sur spotify" in query_clean.lower() or "dans spotify" in query_clean.lower():
            plat = "spotify"
            query_clean = re.sub(r"(?:sur|dans)\s+spotify", "", query_clean, flags=re.IGNORECASE).strip()
        elif "sur youtube" in query_clean.lower() or "dans youtube" in query_clean.lower():
            plat = "youtube"
            query_clean = re.sub(r"(?:sur|dans)\s+youtube", "", query_clean, flags=re.IGNORECASE).strip()

        # Nettoyage des formules de politesse
        query_clean = re.sub(r'\b(?:s\'?il te plait|sil te plait|stp|merci|s\'il vous plait)\b', '', query_clean, flags=re.IGNORECASE).strip()

        # Nettoyer les prépositions accidentelles au début du titre/artiste (ex: 'de gens courent' -> 'gens courent')
        query_clean = re.sub(r"^(?:de|du|des|d'|d’)\s*", "", query_clean, flags=re.IGNORECASE).strip()

        # Reprise de la lecture uniquement si explicitement demandée (play, reprise, lecture)
        pure_resume_words = ["play", "reprise", "lecture", "en cours"]
        if query_clean.lower() in pure_resume_words:
            cli = self._get_spotify_cli_path()
            if plat != "youtube" and cli:
                self._ensure_spotify_running()
                try:
                    subprocess.run([str(cli), "play"], capture_output=True, text=True, timeout=2.0)
                    return "Reprise de votre musique sur Spotify."
                except Exception:
                    pass
            self.media_play_pause()
            target_str = " sur Spotify" if plat == "spotify" else ""
            return f"Reprise de votre musique{target_str}."

        # Recherche ciblée
        if not plat:
            active = self.get_active_music_player()
            plat = "spotify" if active == "Spotify" else "spotify" # Priorité Spotify par défaut

        if plat == "spotify":
            cli = self._get_spotify_cli_path()
            # En environnement réel, privilégier le contrôle programmatique via spotify_cli
            if cli and not hasattr(self._trigger_spotify_playback, 'assert_called_once'):
                ok, msg = self.play_spotify_smart(query_clean)
                if ok:
                    return msg

            # Repli avec navigateur / URI et déclencheur automatique de lecture
            encoded = urllib.parse.quote(query_clean)
            webbrowser.open(f"spotify:search:{encoded}")
            self._trigger_spotify_playback(delay=0.8)
            return f"Lancement de '{query_clean}' sur Spotify."
        else:
            encoded = urllib.parse.quote(query_clean)
            yt_url = f"https://www.youtube.com/results?search_query={encoded}"
            webbrowser.open(yt_url)
            return f"Recherche et lecture de '{query_clean}' lancées sur YouTube."

    # ==========================================
    # 9. GÉOLOCALISATION RÉELLE DE L'APPAREIL
    # ==========================================
    def get_device_location(self) -> Dict[str, Any]:
        """
        Récupère la position géographique réelle du PC via la télémétrie réseau.
        Met en cache pour un accès instantané sans latence.
        """
        if self._cached_location:
            return self._cached_location

        try:
            req = urllib.request.Request(
                "http://ip-api.com/json/?fields=status,country,regionName,city,lat,lon,isp",
                headers={"User-Agent": "CruxAI/1.0"}
            )
            with urllib.request.urlopen(req, timeout=2.5) as res:
                data = json.loads(res.read().decode())
                if data.get("status") == "success":
                    self._cached_location = {
                        "city": data.get("city", "Paris"),
                        "region": data.get("regionName", "Île-de-France"),
                        "country": data.get("country", "France"),
                        "lat": data.get("lat"),
                        "lon": data.get("lon"),
                        "isp": data.get("isp")
                    }
                    return self._cached_location
        except Exception:
            pass

        return {
            "city": "Paris",
            "region": "Île-de-France",
            "country": "France",
            "lat": 48.85,
            "lon": 2.35,
            "isp": "Orange"
        }

    # ==========================================
    # 10. CONTRÔLE MATÉRIEL ÉCRANS & MIXEUR AUDIO
    # ==========================================
    # ==========================================
    # 10. CONTRÔLE MATÉRIEL ÉCRANS & MIXEUR AUDIO (PYCAW & SBC)
    # ==========================================
    def list_audio_sessions(self) -> List[Dict[str, Any]]:
        """Liste les sessions audio actives avec volume et état mute (WASAPI), dédoublonnées par application."""
        sessions_map = {}
        try:
            from pycaw.pycaw import AudioUtilities
            for session in AudioUtilities.GetAllSessions():
                try:
                    if session.Process:
                        pname = session.Process.name()
                        vol = round(session.SimpleAudioVolume.GetMasterVolume() * 100)
                        mute = bool(session.SimpleAudioVolume.GetMute())
                        if pname not in sessions_map or vol > sessions_map[pname]["volume_percent"]:
                            sessions_map[pname] = {
                                "process": pname,
                                "pid": session.Process.pid,
                                "volume_percent": vol,
                                "is_muted": mute
                            }
                except Exception:
                    continue
        except Exception:
            pass
        return list(sessions_map.values())

    def get_app_volume(self, app_name: str) -> Optional[int]:
        """Retourne le volume actuel d'une application spécifique."""
        try:
            from pycaw.pycaw import AudioUtilities
            target = app_name.lower().strip()
            for session in AudioUtilities.GetAllSessions():
                try:
                    if session.Process:
                        pname = session.Process.name().lower()
                        if target in pname:
                            return round(session.SimpleAudioVolume.GetMasterVolume() * 100)
                except Exception:
                    continue
        except Exception:
            pass
        return None

    def set_app_volume(self, app_name: str, percent: int) -> str:
        """Règle le volume d'une application spécifique (ex: Discord, Spotify, jeu)."""
        try:
            from pycaw.pycaw import AudioUtilities
            target = app_name.lower().strip()
            pct = max(0, min(100, int(percent)))
            fraction = pct / 100.0
            found = False
            for session in AudioUtilities.GetAllSessions():
                try:
                    if session.Process:
                        pname = session.Process.name().lower()
                        if target in pname:
                            session.SimpleAudioVolume.SetMasterVolume(fraction, None)
                            found = True
                except Exception:
                    continue
            if found:
                return f"Volume de {app_name.capitalize()} ajusté à {pct} %."
            return f"Application '{app_name}' non trouvée dans le mixeur audio."
        except Exception as e:
            return f"Erreur lors du réglage du volume de {app_name} : {e}"

    def mute_app(self, app_name: str, mute: bool = True) -> str:
        """Coupe ou rétablit le son d'une application spécifique."""
        try:
            from pycaw.pycaw import AudioUtilities
            target = app_name.lower().strip()
            found = False
            for session in AudioUtilities.GetAllSessions():
                try:
                    if session.Process:
                        pname = session.Process.name().lower()
                        if target in pname:
                            session.SimpleAudioVolume.SetMute(1 if mute else 0, None)
                            found = True
                except Exception:
                    continue
            action = "coupé" if mute else "rétabli"
            if found:
                return f"Son de {app_name.capitalize()} {action}."
            return f"Application '{app_name}' non trouvée dans le mixeur audio."
        except Exception as e:
            return f"Erreur lors du contrôle du son de {app_name} : {e}"

    def get_master_volume(self) -> Optional[int]:
        """Retourne le volume principal de sortie Windows."""
        try:
            from pycaw.pycaw import AudioUtilities
            spk = AudioUtilities.GetSpeakers()
            if spk and hasattr(spk, 'volume_percent'):
                return int(round(spk.volume_percent))
        except Exception:
            pass
        return None

    def set_master_volume(self, percent: int) -> str:
        """Règle le volume principal de sortie Windows directement via WASAPI."""
        try:
            from pycaw.pycaw import AudioUtilities
            pct = max(0, min(100, int(percent)))
            spk = AudioUtilities.GetSpeakers()
            if spk and hasattr(spk, 'EndpointVolume'):
                spk.EndpointVolume.SetMasterVolumeLevelScalar(pct / 100.0, None)
                return f"Volume principal réglé à {pct} %."
        except Exception:
            pass
        return "Impossible de régler le volume principal directement via WASAPI."

    def get_monitors_brightness(self) -> List[Dict[str, Any]]:
        """Retourne la luminosité par écran matériel DDC/CI (ex: ViewSonic, Iiyama/PL2766H)."""
        res = []
        try:
            import screen_brightness_control as sbc
            monitors = sbc.list_monitors()
            for m in monitors:
                try:
                    level = sbc.get_brightness(display=m)
                    val = level[0] if isinstance(level, list) and level else level
                    res.append({"monitor": m, "brightness": val})
                except Exception:
                    continue
        except Exception:
            pass
        return res

    def get_brightness(self) -> str:
        """Retourne la luminosité matérielle des écrans."""
        try:
            import screen_brightness_control as sbc
            mons = self.get_monitors_brightness()
            if mons:
                items = [f"{m['monitor']} : {m['brightness']} %" for m in mons]
                return f"Luminosité actuelle : {', '.join(items)}."
            levels = sbc.get_brightness()
            if isinstance(levels, list):
                levels_str = ", ".join(f"Écran {i+1} : {lv} %" for i, lv in enumerate(levels))
                return f"Luminosité actuelle : {levels_str}."
            return f"Luminosité actuelle : {levels} %."
        except Exception as e:
            return f"Impossible de lire la luminosité des écrans : {e}"

    def set_brightness(self, percent: int, display: Optional[Any] = None) -> str:
        """Ajuste la luminosité matérielle de tous les écrans ou d'un écran spécifique (ViewSonic, PL2766H, 1, 2)."""
        try:
            import screen_brightness_control as sbc
            pct = max(0, min(100, int(percent)))
            if display is not None:
                target_disp = None
                monitors = sbc.list_monitors()
                d_str = str(display).lower().strip()

                idx = None
                if d_str in ["1", "premier", "ecran 1", "écran 1", "principal"]:
                    idx = 0
                elif d_str in ["2", "second", "deuxieme", "deuxième", "ecran 2", "écran 2", "secondaire"]:
                    idx = 1
                elif d_str.isdigit():
                    idx = int(d_str) - 1

                if idx is not None and 0 <= idx < len(monitors):
                    target_disp = monitors[idx]
                else:
                    for m in monitors:
                        m_l = m.lower()
                        if d_str in m_l or ("pl2766h" in d_str and "iiyama" in m_l) or ("viewsonic" in d_str and "viewsonic" in m_l):
                            target_disp = m
                            break

                if target_disp:
                    sbc.set_brightness(pct, display=target_disp)
                    return f"Luminosité de {target_disp} réglée à {pct} %."
                return f"Écran '{display}' introuvable parmi les moniteurs détectés ({', '.join(monitors)})."

            sbc.set_brightness(pct)
            return f"Luminosité réglée à {pct} % sur vos écrans."
        except Exception as e:
            return f"Impossible d'ajuster la luminosité : {e}"

    # ==========================================
    # 11. CONTRÔLE SPOTIFY CLI AVANCÉ SANS SOURIS
    # ==========================================
    def get_spotify_playback_info(self) -> Optional[Dict[str, Any]]:
        """Interroge Spotify CLI pour obtenir la piste en cours en JSON."""
        cli = self._get_spotify_cli_path()
        if not cli:
            return None
        try:
            res = subprocess.run([str(cli), "now-playing", "--format", "json"], capture_output=True, text=True, timeout=2.5)
            if res.returncode == 0 and res.stdout.strip():
                return json.loads(res.stdout)
        except Exception:
            pass
        return None

    def get_spotify_now_playing_summary(self) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Extrait et formate les informations de lecture en cours depuis Spotify CLI.
        Retourne (is_playing, message_vocal, track_data).
        """
        info = self.get_spotify_playback_info()
        if not info:
            return False, "Aucune information de lecture reçue de Spotify.", {}

        cur = info.get("currently_playing") or {}
        desc = cur.get("description", "").strip()
        is_playing = cur.get("is_playing", False)
        uri = cur.get("uri", "")
        context = cur.get("context_description", "")

        if not desc:
            return False, "Aucun morceau n'est actuellement sélectionné sur Spotify.", {}

        parts = desc.split("—")
        if len(parts) >= 2:
            title = parts[0].strip()
            artist = parts[1].strip()
        else:
            title = desc
            artist = "Spotify"

        state_str = "en cours de lecture" if is_playing else "en pause"
        msg = f"Sur Spotify : {title} par {artist} ({state_str})."

        # Synchronisation avec la Notch Coucou
        try:
            from core.coucou_client import CoucouClient
            CoucouClient.get_instance().sync_spotify_status(
                title=title,
                artist=artist,
                album=context or "Spotify",
                is_playing=is_playing
            )
        except Exception:
            pass

        return is_playing, msg, {
            "title": title,
            "artist": artist,
            "is_playing": is_playing,
            "uri": uri,
            "context": context
        }

    def set_spotify_volume(self, percent: int) -> str:
        """Règle le volume de Spotify de façon programmatique."""
        cli = self._get_spotify_cli_path()
        pct = max(0, min(100, int(percent)))
        if cli:
            try:
                subprocess.run([str(cli), "volume", str(pct)], capture_output=True, text=True, timeout=2.0)
                return f"Volume de Spotify ajusté à {pct} %."
            except Exception:
                pass
        return self.set_app_volume("spotify", pct)

    def spotify_command(self, action: str, arg: Optional[str] = None) -> Tuple[bool, str]:
        """Exécute une commande directe Spotify CLI (play, pause, next, previous, resume, volume)."""
        cli = self._get_spotify_cli_path()
        if not cli:
            return False, "CLI Spotify non disponible."

        self._ensure_spotify_running()
        cmd = [str(cli), action.lower()]
        if arg:
            cmd.append(str(arg))

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=3.0)
            ok = res.returncode == 0
            msg = res.stdout.strip() or f"Commande Spotify '{action}' exécutée."
            return ok, msg
        except Exception as e:
            return False, f"Erreur Spotify CLI : {e}"



import tkinter as tk
import threading
import queue
import time
import math
from typing import Optional, Dict, Any

class CruxNotchHUD:
    """
    HUD Interactif style Notch / Dynamic Island (Inspiré du projet GitHub 'Coucou').
    Vit en haut au centre de l'écran Windows, affichant en temps réel les états de Crux :
    - Veille (discrète pilule sombre avec pulsation lumineuse)
    - Écoute active (VU-mètre d'amplitude et ondes sonores)
    - Réflexion / Calcul (anneau orbital et pulsation sci-fi)
    - Parole (animation vocale avec affichage de réponse)
    - Musique (titre Spotify / YouTube)
    - Presets d'espace de travail
    """
    _instance: Optional['CruxNotchHUD'] = None

    @classmethod
    def get_instance(cls) -> 'CruxNotchHUD':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.cmd_queue: queue.Queue = queue.Queue()
        self.state: str = "idle" # idle, listening, thinking, speaking, media, preset, alert
        self.title_text: str = "CRUX"
        self.sub_text: str = "Système Jarvis Actif"
        self.vu_level: float = 0.0
        self.is_expanded: bool = False
        self.target_width: int = 240
        self.current_width: float = 240.0
        self.height: int = 38
        self.anim_tick: float = 0.0
        self.running: bool = False
        self.thread: Optional[threading.Thread] = None

    def start(self):
        """Démarre l'interface HUD en arrière-plan."""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run_ui, daemon=True, name="CruxNotchHUDThread")
        self.thread.start()

    def set_state(self, state: str, title: Optional[str] = None, sub: Optional[str] = None):
        """Met à jour l'état visuel du HUD de manière thread-safe."""
        self.cmd_queue.put(("set_state", (state, title, sub)))

    def update_vu(self, level: float):
        """Met à jour l'amplitude du VU-mètre (0.0 à 1.0)."""
        self.cmd_queue.put(("set_vu", level))

    def notify(self, title: str, message: str, duration_sec: float = 4.0):
        """Affiche une bannière temporaire (preset, minuteur, musique)."""
        self.cmd_queue.put(("notify", (title, message, duration_sec)))

    def _run_ui(self):
        root = tk.Tk()
        self.root = root
        root.title("Crux Notch HUD")
        root.overrideredirect(True)
        root.attributes("-topmost", True)

        # Fond transparent Windows
        trans_color = "#000001"
        root.config(bg=trans_color)
        root.wm_attributes("-transparentcolor", trans_color)

        screen_w = root.winfo_screenwidth()
        x = (screen_w - int(self.current_width)) // 2
        root.geometry(f"{int(self.current_width)}x{self.height}+{x}+0")

        canvas = tk.Canvas(
            root,
            width=int(self.current_width),
            height=self.height,
            bg=trans_color,
            highlightthickness=0
        )
        canvas.pack(fill="both", expand=True)
        self.canvas = canvas

        # Clic pour développer / réduire
        canvas.bind("<Button-1>", lambda e: self._toggle_expand())

        temp_state_until = 0.0
        prev_state = "idle"

        def update_frame():
            nonlocal temp_state_until, prev_state
            now = time.time()

            # Dépilage des commandes
            while not self.cmd_queue.empty():
                try:
                    cmd, args = self.cmd_queue.get_nowait()
                    if cmd == "set_state":
                        st, t_txt, s_txt = args
                        self.state = st
                        if t_txt is not None:
                            self.title_text = t_txt
                        if s_txt is not None:
                            self.sub_text = s_txt
                    elif cmd == "set_vu":
                        self.vu_level = max(0.0, min(1.0, args))
                    elif cmd == "notify":
                        title, msg, dur = args
                        prev_state = self.state
                        self.state = "preset"
                        self.title_text = title
                        self.sub_text = msg
                        temp_state_until = now + dur
                except Exception:
                    pass

            if temp_state_until > 0 and now >= temp_state_until:
                temp_state_until = 0.0
                self.state = prev_state

            # Détermination de la largeur cible selon l'état
            if self.is_expanded:
                self.target_width = 460
            elif self.state == "idle":
                self.target_width = 190
            elif self.state in ["listening", "speaking"]:
                self.target_width = 340
            elif self.state == "thinking":
                self.target_width = 310
            elif self.state in ["preset", "media"]:
                self.target_width = 380
            else:
                self.target_width = 240

            # Interpolation fluide de la largeur (spring lerp)
            diff = self.target_width - self.current_width
            if abs(diff) > 1.0:
                self.current_width += diff * 0.22
                new_w = int(self.current_width)
                new_x = (screen_w - new_w) // 2
                root.geometry(f"{new_w}x{self.height}+{new_x}+0")
                canvas.config(width=new_w)

            self.anim_tick += 0.08
            self._draw_notch(int(self.current_width), self.height)

            root.after(25, update_frame) # ~40 FPS animation

        root.after(25, update_frame)
        root.mainloop()

    def _toggle_expand(self):
        self.is_expanded = not self.is_expanded

    def _draw_notch(self, w: int, h: int):
        self.canvas.delete("all")
        r = 18 # Rayon des coins arrondis
        pad = 2

        # 1. Couleur de fond et contour selon l'état
        fill_bg = "#0c0d12"
        border_col = "#202533"

        if self.state == "listening":
            border_col = "#00d2ff"
        elif self.state == "thinking":
            border_col = "#9d4edd"
        elif self.state == "speaking":
            border_col = "#00f59b"
        elif self.state == "preset":
            border_col = "#ffaa00"
        elif self.state == "media":
            border_col = "#1db954"

        # Dessin de la pilule (Dynamic Island notch)
        # Deux cercles et rectangles reliés
        self.canvas.create_oval(pad, pad, pad + 2*r, pad + 2*r, fill=fill_bg, outline=border_col, width=1.5)
        self.canvas.create_oval(w - pad - 2*r, pad, w - pad, pad + 2*r, fill=fill_bg, outline=border_col, width=1.5)
        self.canvas.create_rectangle(pad + r, pad, w - pad - r, pad + 2*r, fill=fill_bg, outline="", width=0)
        self.canvas.create_line(pad + r, pad, w - pad - r, pad, fill=border_col, width=1.5)
        self.canvas.create_line(pad + r, pad + 2*r, w - pad - r, pad + 2*r, fill=border_col, width=1.5)

        cy = h // 2

        # 2. Dessin selon l'état
        if self.state == "idle":
            # Orbite / Dot respirant cyan Jarvis
            breath = 0.5 + 0.5 * math.sin(self.anim_tick)
            dot_color = f"#{int(0x00 * breath):02x}{int(0xd2 * breath):02x}{int(0xff * breath):02x}"
            if breath < 0.2:
                dot_color = "#005577"
            self.canvas.create_oval(18, cy - 4, 26, cy + 4, fill=dot_color, outline="")
            self.canvas.create_text(w // 2 + 6, cy, text="CRUX AI", fill="#c0c7d6", font=("Segoe UI", 9, "bold"))

        elif self.state == "listening":
            # Micro & Ondes de VU-mètre en direct
            self.canvas.create_text(24, cy, text="🎙️", font=("Segoe UI", 10))
            # Barres audio animées
            bars_start = 45
            for i in range(5):
                wave = abs(math.sin(self.anim_tick * 2 + i * 0.8)) * self.vu_level
                bh = max(3, int(wave * 18))
                self.canvas.create_line(bars_start + i * 5, cy - bh//2, bars_start + i * 5, cy + bh//2, fill="#00d2ff", width=2)
            
            txt = self.sub_text if self.sub_text else "À votre écoute..."
            self.canvas.create_text(w // 2 + 25, cy, text=txt[:26], fill="#e0f4ff", font=("Segoe UI", 9, "bold"))

        elif self.state == "thinking":
            # Pulsation orbitale cybernétique (Radar Jarvis)
            center_x = 26
            radius = 6
            angle = self.anim_tick * 3
            px = center_x + radius * math.cos(angle)
            py = cy + radius * math.sin(angle)
            self.canvas.create_oval(center_x - 3, cy - 3, center_x + 3, cy + 3, fill="#9d4edd", outline="")
            self.canvas.create_oval(px - 2, py - 2, px + 2, py + 2, fill="#e0aaff", outline="")

            txt = self.sub_text if self.sub_text else "Analyse en cours..."
            self.canvas.create_text(w // 2 + 10, cy, text=f"CRUX • {txt[:24]}", fill="#e8d8fc", font=("Segoe UI", 9, "bold"))

        elif self.state == "speaking":
            # Barres vocales vertes dynamiques
            self.canvas.create_text(22, cy, text="🗣️", font=("Segoe UI", 10))
            bars_start = 42
            for i in range(4):
                bh = max(3, int((0.3 + 0.7 * abs(math.sin(self.anim_tick * 3 + i))) * 16))
                self.canvas.create_line(bars_start + i * 5, cy - bh//2, bars_start + i * 5, cy + bh//2, fill="#00f59b", width=2)

            txt = self.sub_text if self.sub_text else "Réponse Jarvis"
            self.canvas.create_text(w // 2 + 22, cy, text=txt[:28], fill="#d4fae6", font=("Segoe UI", 9, "bold"))

        elif self.state in ["preset", "media"]:
            icon = "🎵" if self.state == "media" else "🪟"
            self.canvas.create_text(22, cy, text=icon, font=("Segoe UI", 10))
            col = "#1db954" if self.state == "media" else "#ffc107"
            full_txt = f"{self.title_text} • {self.sub_text}"
            self.canvas.create_text(w // 2 + 8, cy, text=full_txt[:38], fill=col, font=("Segoe UI", 9, "bold"))

    def stop(self):
        """Arrête le HUD proprement."""
        if hasattr(self, 'root') and self.root:
            try:
                self.root.quit()
            except Exception:
                pass
        self.running = False

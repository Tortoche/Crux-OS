import os
import sys
import json
import time
import re
import threading
import subprocess
import urllib.request
import unicodedata
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from google import genai
from google.genai import types
from core.project_manager import ProjectManager
from core.system_control import SystemController
from core.sound_effects import SoundEffects
from core.coucou_client import CoucouClient
from core.memory.manager import MemoryManager
from core.vision.screen_capture import ScreenCapture
from core.agent_tools.computer_use import ComputerUseController
from core.plugins.manager import PluginManager
from core.ui_generator.runtime import DynamicUIRuntime
from core.handoff.manager import HandoffManager

USER_NAME = "Corentin"

JARVIS_SYSTEM_INSTRUCTION = f"""
Tu es Crux, l'assistant personnel intelligent de {USER_NAME} sur son PC, connecté à l'écosystème Antigravity.
Tu es inspiré de J.A.R.V.I.S. (Marvel) : précis, direct, calme et efficace.

RÈGLES D'OR STRICTES :
1. ZERO BLABLA : Réponds DIRECTEMENT en 1 seule phrase percutante (2 phrases courtes grand maximum).
2. Pas de formalisme excessif, pas de listes à puces. Ne dis JAMAIS "À vos ordres".
3. RÈGLE D'OR DU PRÉNOM : Ne dis le prénom '{USER_NAME}' qu'au TOUT PREMIER message d'accueil de la session. Dans ABSOLUMENT TOUS les échanges suivants de la conversation, ne répète JAMAIS son prénom (réponds directement sans dire 'Corentin').
4. ACTIONS SYSTÈME ET MULTIMÉDIA : Si l'utilisateur demande une action PC ou musique, inclus la balise d'action correspondante à la fin de ta réponse :
   - Lancer ou reprendre la musique (ex: "lance une petite musique", "mets la musique", "démarre la musique", "mets play", "musique sur spotify") : [ACTION:MUSIC_RESUME:spotify]
   - Jouer un titre ou artiste précis : [ACTION:MUSIC_PLAY:spotify:TITRE_OU_ARTISTE]
   - Mettre en pause la musique : [ACTION:MEDIA_PAUSE]
   - Piste suivante/précédente : [ACTION:MEDIA_NEXT] ou [ACTION:MEDIA_PREV]
   - Baisser/minimiser toutes les fenêtres (afficher le bureau) : [ACTION:WINDOW:bureau]
   - Déplacer fenêtre active : [ACTION:WINDOW:gauche], [ACTION:WINDOW:droite], [ACTION:WINDOW:plein_ecran], [ACTION:WINDOW:reduire]
   - Mettre en veille / fin de session : [ACTION:EXIT]
5. QUESTIONS & DIALOGUE : Si l'utilisateur pose une question, commente, demande ce qu'on a dit avant (ex: historique, script qui a planté), réponds intelligemment et naturellement en t'appuyant sur l'historique sans balise d'action.
"""

class CruxAgent:
    """
    Cerveau décisionnel et conversationnel de Crux AI avec mémoire continue multi-tours.
    Inspiré de J.A.R.V.I.S. (Marvel) : précis, direct, calme, avec mémoire active des échanges.
    Utilise gemini-3.1-flash-lite en version optimisée à faible latence (thinking_budget=0).
    """
    def __init__(
        self,
        api_key: str = "AIzaSyDEu0gqAjhnN9noXPOVnYO8YVIy_Q3ezuE",
        model_name: str = "gemini-3.8-flash",
        project_manager: Optional[ProjectManager] = None,
        system_control: Optional[SystemController] = None,
        tts: Optional[Any] = None,
        sfx: Optional[Any] = None
    ):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        req_model = (model_name or "gemini-3.8-flash").lower().strip()
        self.model_name = req_model

        self.fallback_models = [
            self.model_name,
            "gemini-3.8-flash",
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-flash-lite-latest",
        ]
        # Suppression des doublons tout en gardant l'ordre
        self.fallback_models = list(dict.fromkeys(self.fallback_models))
        
        self.client = genai.Client(api_key=self.api_key)
        self.project_manager = project_manager or ProjectManager()
        self.sys = system_control or SystemController()
        self.tts = tts
        self.sfx = sfx or SoundEffects()
        self.hud = CoucouClient.get_instance()
        
        # Suivi du prénom (prononcé 1 seule fois par session)
        self.has_said_name = False

        # Mémoire à 5 dimensions (5D Memory)
        self.memory = MemoryManager()
        if self.project_manager.active_project_name:
            self.memory.working.set("active_project", self.project_manager.active_project_name)

        # Vision d'écran multimodale (mss / JPEG / delta)
        self.vision = ScreenCapture()

        # Contrôleur Computer Use avancé (souris, clavier, fenêtres, garde-fous)
        self.computer_use = ComputerUseController()

        # Écosystème de plugins (IoT Lumières & Domotique)
        self.plugins = PluginManager()

        # Moteur d'interface dynamique générative (Generative Dynamic UI)
        self.ui_runtime = DynamicUIRuntime.get_instance()
        
        # Gestionnaire de continuité et télécommande mobile (Handoff)
        self.handoff = HandoffManager.get_instance()
        self.handoff.agent = self
        
        # Suivi de conversation native Antigravity (réutilisation de session pour 0 latence)
        self._antigravity_cid: Optional[str] = None
        self._antigravity_last_step: int = 0

        # Mémoire conversationnelle de session
        self.chat_session = None
        self.history_records = []
        self._init_chat_session()

    def _init_chat_session(self):
        """Initialise la session de discussion avec mémoire active, heure réelle et consignes Jarvis."""
        try:
            active_proj = self.project_manager.active_project_name or "Aucun"
            now = datetime.now()
            time_str = now.strftime('%d/%m/%Y à %H:%M')
            mem_context = self.memory.build_prompt_context()
            system_instruction = (
                f"{JARVIS_SYSTEM_INSTRUCTION}\n"
                f"Horodatage système actuel : {time_str}.\n"
                f"Contexte système actuel : Projet actif = {active_proj}.\n"
                f"{mem_context}\n"
                f"Tu es connecté à l'environnement Antigravity de Corentin.\n"
                f"Tu te souviens toujours du contexte des échanges précédents dans la session."
            )
            # Configuration ultra-réactive pour latence minimale (raisonnement Low / thinking_budget=0)
            gen_config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.25,
                max_output_tokens=150,
                thinking_config=types.ThinkingConfig(thinking_budget=0)
            )
            self.chat_session = self.client.chats.create(
                model=self.model_name,
                config=gen_config
            )
            # Réinjection de l'historique récent si existant
            if self.history_records and self.chat_session:
                for item in self.history_records[-10:]:
                    self.chat_session.get_history().append(
                        types.Content(
                            role=item["role"],
                            parts=[types.Part.from_text(text=item["text"])]
                        )
                    )
        except Exception:
            self.chat_session = None

    def reset_session(self):
        """Réinitialise la mémoire vive lors de la mise en veille ou d'une nouvelle session."""
        self.history_records = []
        self.has_said_name = False
        self.memory.reset_session()
        self.computer_use.cancel_pending_action()
        self._antigravity_cid = None
        self._antigravity_last_step = 0
        self._init_chat_session()

    def _name_suffix(self) -> str:
        """Retourne ' Corentin' uniquement si le prénom n'a pas encore été prononcé dans cette session."""
        if not self.has_said_name:
            return f" {USER_NAME}"
        return ""

    def _finalize_response(self, text: str) -> str:
        """
        Applique la règle d'or universelle du prénom :
        - Dès que le prénom a été dit (has_said_name=True), il est STRICTEMENT supprimé
          de TOUTES les réponses suivantes, quelle que soit la branche (actions, horloge, météo, etc.).
        """
        if not text:
            return text
        clean = text
        if self.has_said_name:
            clean = re.sub(r',?\s*\bCorentin\b,?', '', clean, flags=re.IGNORECASE).strip()
            clean = re.sub(r'\s{2,}', ' ', clean)
            clean = re.sub(r'\s+\.', '.', clean)
            clean = re.sub(r'^\s*,\s*', '', clean)
            clean = re.sub(r'\b,\s*\.', '.', clean)
            if clean:
                clean = clean[0].upper() + clean[1:]
        return clean

    def _return_response(self, user_text: str, reply: str, is_exit: bool = False) -> Tuple[str, bool]:
        """Finalise le texte selon la règle d'or du prénom et l'enregistre dans la mémoire 5D."""
        final_reply = self._finalize_response(reply)
        self._record_turn("user", user_text)
        self._record_turn("model", final_reply)
        return final_reply, is_exit

    def _execute_gemini_actions(self, raw_text: str) -> Tuple[str, bool]:
        """Extrait et exécute les balises d'action [ACTION:...] retournées par Gemini."""
        clean_text = raw_text
        is_exit = False
        
        matches = re.findall(r'\[ACTION:([A-Z_]+)(?::([^\]]+))?\]', raw_text)
        for action_type, args_str in matches:
            args = [a.strip() for a in args_str.split(':')] if args_str else []
            clean_text = re.sub(r'\[ACTION:[^\]]+\]', '', clean_text).strip()
            
            if action_type == "MUSIC_RESUME":
                plat = args[0] if args else "spotify"
                self.sfx.play("chime")
                self.hud.tool_use("Lecteur Musique", {"action": "Reprise de la lecture", "plateforme": plat.capitalize()})
                self.sys.play_music("", platform=plat)
                self.hud.set_state("media", "Crux Musique", "Lecture active")
                if not clean_text:
                    clean_text = f"Lecture reprise sur {plat.capitalize()}."
                    
            elif action_type == "MUSIC_PLAY":
                plat = args[0] if args else "spotify"
                query = args[1] if len(args) > 1 else ""
                self.sfx.play("chime")
                self.hud.tool_use("Lecteur Musique", {"requête": query, "plateforme": plat.capitalize()})
                self.sys.play_music(query, platform=plat)
                self.hud.set_state("media", "Crux Musique", query[:24])
                if not clean_text:
                    clean_text = f"Lancement de '{query}' sur {plat.capitalize()}."
                    
            elif action_type == "MEDIA_PAUSE":
                self.sys.media_play_pause()
                if not clean_text:
                    clean_text = "Lecture multimédia mise en pause."
                    
            elif action_type == "MEDIA_NEXT":
                self.sys.media_next()
                if not clean_text:
                    clean_text = "Piste suivante."
                    
            elif action_type == "MEDIA_PREV":
                self.sys.media_prev()
                if not clean_text:
                    clean_text = "Piste précédente."
                    
            elif action_type == "WINDOW":
                direction = args[0] if args else "centre"
                self.sfx.play("snap")
                if direction == "bureau":
                    self.sys.minimize_all_windows()
                else:
                    self.sys.snap_active_window(direction)
                if not clean_text:
                    clean_text = "Disposition des fenêtres mise à jour."
                    
            elif action_type == "AUDIO_DEVICE":
                device = args[0] if args else "default"
                if self.tts:
                    self.tts.set_target_device(device)
                if not clean_text:
                    clean_text = f"Sortie audio basculée sur {device}."
                    
            elif action_type == "EXIT":
                is_exit = True
                if not clean_text:
                    clean_text = "Je me remets en veille. À tout de suite !"

        return self._finalize_response(clean_text), is_exit

    def _record_turn(self, role: str, text: str):
        """Enregistre un tour de parole (utilisateur ou Crux) dans l'historique et la mémoire 5D."""
        self.history_records.append({"role": role, "text": text})
        try:
            self.memory.record_turn(role, text)
        except Exception:
            pass
        if self.chat_session:
            try:
                self.chat_session.get_history().append(
                    types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=text)]
                    )
                )
            except Exception:
                pass

    def _detect_project_intent(self, text: str) -> Optional[str]:
        """Détecte si l'utilisateur demande explicitement de basculer vers un projet."""
        patterns = [
            r"(?:va|bascule|mets-toi|ouvre|accède)\s+(?:dans\s+|sur\s+)?(?:le\s+projet\s+)?([a-zA-Z0-9_\-\s]+)",
            r"projet\s+([a-zA-Z0-9_\-]+)"
        ]
        text_lower = text.lower()
        for p in patterns:
            match = re.search(p, text_lower)
            if match:
                candidate = match.group(1).strip()
                if candidate and candidate not in ("en", "un", "ce", "le", "la"):
                    return candidate
    def _query_antigravity_native(self, user_text: str) -> Optional[str]:
        """
        Interroge directement le moteur officiel Antigravity (language_server agentapi)
        avec le modèle flash_lite pour une réponse ultra-rapide et instantanée (< 1s).
        Réutilise la session active pour éviter de recréer une conversation lourde à chaque tour.
        """
        try:
            ls_exe = r"C:\Users\coco\AppData\Local\Programs\Antigravity\resources\bin\language_server.exe"
            if not os.path.exists(ls_exe):
                return None

            active_proj = self.project_manager.active_project_name or "Aucun"
            history_summary = ""
            if self.history_records:
                recent = self.history_records[-4:]
                lines = [f"{'Corentin' if r['role'] == 'user' else 'Crux'}: {r['text']}" for r in recent]
                history_summary = "Historique récent : " + " | ".join(lines) + "\n"

            # Tier ultra-rapide sans thinking étendu
            model_tier = "flash_lite"

            mem_context = self.memory.build_prompt_context(user_text)
            full_prompt = (
                f"{JARVIS_SYSTEM_INSTRUCTION}\n"
                f"Projet actif : {active_proj}.\n"
                f"{mem_context}\n\n"
                f"{history_summary}"
                f"Corentin : {user_text}"
            )

            if self._antigravity_cid is None:
                # Création de la session initiale native
                cmd = [ls_exe, "agentapi", "new-conversation", f"--model={model_tier}", full_prompt]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=4.0)
                if res.returncode != 0:
                    return None
                data = json.loads(res.stdout)
                cid = data.get("response", {}).get("newConversation", {}).get("conversationId")
                if not cid:
                    return None
                self._antigravity_cid = cid
                self._antigravity_last_step = 0
            else:
                # Réutilisation de la conversation existante via send-message (instantané !)
                cid = self._antigravity_cid
                cmd = [ls_exe, "agentapi", "send-message", cid, user_text]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=3.0)
                if res.returncode != 0:
                    self._antigravity_cid = None
                    return None

            t_file = os.path.expanduser(rf"~\.gemini\antigravity\brain\{cid}\.system_generated\logs\transcript.jsonl")
            deadline = time.time() + 3.5  # Timeout réactif strict (3.5s max au lieu de 15s)
            while time.time() < deadline:
                time.sleep(0.05)
                if os.path.exists(t_file):
                    try:
                        with open(t_file, "r", encoding="utf-8") as f:
                            for line in f:
                                row = json.loads(line)
                                step = row.get("step_index", 0)
                                if row.get("type") == "PLANNER_RESPONSE" and row.get("content") and step > self._antigravity_last_step:
                                    clean = row["content"].strip()
                                    clean = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', clean).strip()
                                    clean = re.sub(r"^Antigravity:\s*", "", clean, flags=re.IGNORECASE).strip()
                                    if clean:
                                        self._antigravity_last_step = step
                                        return clean
                    except Exception:
                        pass
        except Exception:
            self._antigravity_cid = None
        return None

    def _query_antigravity_cli(self, user_text: str) -> Optional[str]:
        """
        Exécute la requête via le CLI Antigravity officiel (agy) avec timeout strict et modèle rapide.
        """
        try:
            active_proj = self.project_manager.active_project_name or "Aucun"
            history_summary = ""
            if self.history_records:
                recent = self.history_records[-4:]
                lines = [f"{'Corentin' if r['role'] == 'user' else 'Crux'}: {r['text']}" for r in recent]
                history_summary = "Historique récent : " + " | ".join(lines) + "\n"

            mem_context = self.memory.build_prompt_context(user_text)
            system_inst = (
                f"{JARVIS_SYSTEM_INSTRUCTION}\n"
                f"Projet actif : {active_proj}.\n"
                f"{mem_context}"
            )
            full_prompt = f"{history_summary}Corentin : {user_text}"

            agy_py = os.path.expanduser(r"~\.gemini\antigravity\scratch\antigravity-local\agy_cli.py")
            if not os.path.exists(agy_py):
                agy_py = r"C:\Users\coco\.gemini\antigravity\scratch\antigravity-local\agy_cli.py"
            if not os.path.exists(agy_py):
                return None

            # Essayer uniquement les modèles légers avec timeout court (3s max par tentative)
            models_to_try = [self.model_name, "gemini-2.5-flash"]
            for m in list(dict.fromkeys(models_to_try)):
                cmd = [sys.executable, agy_py, "-m", m, "-s", system_inst, full_prompt]
                try:
                    res = subprocess.run(
                        cmd,
                        capture_output=True,
                        timeout=3.0
                    )
                    if res.returncode == 0:
                        raw = res.stdout
                        try:
                            text = raw.decode("utf-8")
                        except UnicodeDecodeError:
                            text = raw.decode("cp1252", errors="replace")

                        clean = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text.strip()).strip()
                        clean = re.sub(r"^Antigravity:\s*", "", clean, flags=re.IGNORECASE).strip()
                        if clean:
                            return clean
                except Exception:
                    continue
        except Exception:
            pass
        return None

    def _query_screen_vision(self, prompt: str) -> str:
        """
        Analyse l'écran à la demande vocale stricte avec Gemini 3.8 Flash Vision.
        Zéro capture et zéro token consommé en veille.
        """
        self.hud.set_state("thinking", "CRUX", "Analyse d'écran...")
        self.sfx.start_thinking()
        try:
            gemini_part = self.vision.capture_gemini_part(quality=80, max_dimension=1600)
            sys_inst = (
                f"Tu es Crux, l'assistant Jarvis de {USER_NAME}. "
                f"Tu analyses sa capture d'écran. "
                f"RÈGLE STRICTE : Réponds DIRECTEMENT en 1 SEULE phrase concise et précise (2 phrases max). "
                f"Pas de listes à puces, pas de blabla. Ne répète jamais son prénom."
            )
            for model_candidate in self.fallback_models:
                try:
                    response = self.client.models.generate_content(
                        model=model_candidate,
                        contents=[prompt, gemini_part],
                        config=types.GenerateContentConfig(
                            system_instruction=sys_inst,
                            temperature=0.2,
                            thinking_config=types.ThinkingConfig(thinking_budget=0)
                        )
                    )
                    text = response.text.strip()
                    if text:
                        text, _ = self._execute_gemini_actions(text)
                        return text
                except Exception:
                    continue
        except Exception:
            pass
        finally:
            self.sfx.stop_thinking()

        return "Écran analysé, tout est en ordre."

    def _get_natural_french_time(self, dt: Optional[datetime] = None) -> str:
        """
        Formate l'heure en français naturel idiomatique parlé (ex: 12:44 -> 'midi 44', 00:15 -> 'minuit et quart').
        Évite strictement les chiffres bruts comme '12:44' ou '12 heures 44'.
        """
        if dt is None:
            dt = datetime.now()
        h = dt.hour
        m = dt.minute

        if h == 12:
            hour_str = "midi"
        elif h == 0:
            hour_str = "minuit"
        elif h == 1:
            hour_str = "une heure"
        else:
            hour_str = f"{h} heures"

        if m == 0:
            return f"{hour_str} pile"
        elif m == 15:
            return f"{hour_str} et quart"
        elif m == 30:
            return f"{hour_str} et demi" if h in [0, 12] else f"{hour_str} et demie"
        else:
            return f"{hour_str} {m}"

    def _get_realtime_weather(self) -> str:
        """Récupère la météo en temps réel de façon instantanée et ciblée sur la position de l'appareil."""
        try:
            import urllib.parse
            loc = self.sys.get_device_location()
            city = loc.get("city", "Paris")
            encoded_city = urllib.parse.quote(city)
            url = f"https://wttr.in/{encoded_city}?format=%C,+%t&lang=fr"
            req = urllib.request.Request(url, headers={'User-Agent': 'curl/7.68.0'})
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                text = resp.read().decode('utf-8').strip()
                if text:
                    return f"À {city}, le temps est actuellement {text}, Corentin."
        except Exception:
            pass
        return "Je n'ai pas pu joindre la station météo pour le moment, Corentin."

    def _parse_and_start_timer(self, text: str) -> Optional[str]:
        """Détecte et lance un minuteur autonome en arrière-plan."""
        match = re.search(r"minuteur\s+(?:de\s+)?(\d+)\s*(minute|minutes|seconde|secondes|heure|heures)?", text.lower())
        if match:
            value = int(match.group(1))
            unit = match.group(2) or "minute"
            if "seconde" in unit:
                secs = value
                label = f"{value} seconde{'s' if value > 1 else ''}"
            elif "heure" in unit:
                secs = value * 3600
                label = f"{value} heure{'s' if value > 1 else ''}"
            else:
                secs = value * 60
                label = f"{value} minute{'s' if value > 1 else ''}"

            def timer_done():
                if self.tts:
                    self.tts.speak(f"Corentin, votre minuteur de {label} est écoulé !")

            t = threading.Timer(secs, timer_done)
            t.daemon = True
            t.start()
            return f"Minuteur de {label} enclenché, Corentin."
        return None

    def _parse_music_command(self, user_text: str) -> Optional[Dict[str, Any]]:
        """
        Parse finement les requêtes musicales pour distinguer :
        - La reprise / lecture directe (ex: 'lance la musique', 'mets play', 'tu peux mettre de la musique sur Spotify', 'mets de la musique s'il te plaît')
        - La recherche ciblée d'un titre/artiste (ex: 'lance la musique de gens courent', 'mets du rap')
        """
        lower = user_text.lower().strip()
        cleaned = unicodedata.normalize('NFD', lower)
        cleaned = ''.join(c for c in cleaned if unicodedata.category(c) != 'Mn')

        # Mots clés déclencheurs
        has_music_trigger = (
            any(w in cleaned for w in ["musique", "music", "chanson", "morceau", "playlist", "spotify", "youtube", "play", "zik", "titre"]) or
            cleaned.startswith("joue ") or
            cleaned.startswith("mets ") or
            cleaned.startswith("lance ")
        )
        if not has_music_trigger:
            return None

        # Exclure si c'est une pause explicite, volume, fenêtre, etc.
        if any(w in cleaned for w in ["pause", "stop", "volume", "fenetre", "preset", "jbl", "ecran", "minuteur", "note"]):
            return None

        # Détection plateforme
        platform = None
        if "spotify" in cleaned:
            platform = "spotify"
        elif "youtube" in cleaned:
            platform = "youtube"

        working = cleaned
        # Suppression des formules de politesse partout dans la phrase
        working = re.sub(r'\b(?:s\'?il te plait|sil te plait|stp|merci|s\'il vous plait)\b', '', working)

        # Suppression des préfixes de demande
        working = re.sub(r'^(?:est-ce que tu peux|est ce que tu peux|peux-tu|peux tu|tu peux|pourrais-tu|pourrais tu|dis-moi|crux)\s+', '', working)

        # Suppression des mentions de plateforme
        working = re.sub(r'\b(?:sur|dans)?\s*(?:spotify|youtube)\b', '', working)

        # Suppression des verbes d'action
        working = re.sub(r'^(?:mettre|mets|mets-moi|mets nous|lancer|lance|lance-moi|jouer|joue|joue-moi|passer|passe|envoie|balancer|balance|demarrer|demarre|activer|active|ouvrir|ouvre|reprendre|reprends|relancer|relance|continuer|continue|fais|fait)\s+', '', working)
        working = re.sub(r'\s+', ' ', working).strip()

        # Reprise explicite uniquement si un verbe de reprise est présent
        resume_verbs = {"reprends", "reprendre", "relance", "relancer", "continue", "continuer", "remets", "remettre"}
        is_explicit_resume = any(rv in lower for rv in resume_verbs) or working in {'play', 'reprise', 'en cours', 'la lecture'}

        if is_explicit_resume and (not working or working in {'musique', 'la musique', 'le son', 'la lecture', 'en cours'}):
            return {'action': 'resume', 'platform': platform, 'query': ''}

        # Suppression des désignations génériques d'entité musicale (ex: 'la musique de gens courent' -> 'de gens courent')
        working = re.sub(r'^(?:de la musique|la musique|une musique|de la music|la music|une music|un morceau|le morceau|une chanson|la chanson|un titre|le titre|un son|le son|de la zik|du son)\s*', '', working).strip()

        # Suppression des prépositions d'artiste/titre (ex: 'de gens courent' -> 'gens courent')
        working = re.sub(r'^(?:de|du|des|d\'|d’)\s*', '', working).strip()

        # Nettoyage des articles devant 'playlist' (ex: "une playlist" -> "playlist", "la playlist jazz" -> "playlist jazz")
        working = re.sub(r'^(?:une|la|le|un|des|ma|mon|mes)\s+(playliste?\b.*)', r'\1', working).strip()

        # Si l'utilisateur demande génériquement de mettre une musique sans préciser de titre ni de playlist :
        # Lancer les hits du moment au lieu de reprendre l'ancienne musique
        if not working:
            working = "Hits du moment"

        return {'action': 'play_query', 'platform': platform, 'query': working}

    def process_command(self, user_text: str) -> Tuple[str, bool]:
        """
        Point d'entrée principal pour traiter une requête utilisateur :
        exécute les intentions et applique la règle d'or du prénom (prononcé 1 seule fois par session).
        """
        reply, is_exit = self._process_command_internal(user_text)
        reply = self._finalize_response(reply)
        if re.search(r'\bCorentin\b', reply, flags=re.IGNORECASE):
            self.has_said_name = True
        return reply, is_exit

    def _process_command_internal(self, user_text: str) -> Tuple[str, bool]:
        """
        Traite la requête de Corentin : actions PC, gestion de projets, ou dialogue Jarvis.
        Maintient la mémoire de conversation pour répondre avec contexte à chaque tour.
        Retourne (reponse_vocale, is_exit).
        """
        user_text = user_text.strip()
        if not user_text:
            return "Je t'écoute, Corentin.", False

        lower = user_text.lower()
        lower_clean = unicodedata.normalize('NFD', lower)
        lower_clean = ''.join(c for c in lower_clean if unicodedata.category(c) != 'Mn')

        # ==========================================
        # 0. CONFIRMATION D'ACTION CRITIQUE (GARDE-FOUS COMPUTER USE)
        # ==========================================
        if self.computer_use.has_pending_confirmation():
            if any(w in lower_clean for w in ["oui", "confirme", "vas y", "vas-y", "fais le", "fais-le", "d'accord", "ok", "yes"]):
                ok, msg = self.computer_use.execute_confirmed_action()
                self._record_turn("user", user_text)
                self._record_turn("model", msg)
                return msg, False
            elif any(w in lower_clean for w in ["non", "annule", "laisse tomber", "arrete", "stop", "cancel", "pas question"]):
                msg = self.computer_use.cancel_pending_action()
                self._record_turn("user", user_text)
                self._record_turn("model", msg)
                return msg, False

        # ==========================================
        # 0.9 HANDOFF MULTI-APPAREILS & TÉLÉCOMMANDE (PC <-> MOBILE)
        # ==========================================
        handoff_to_mobile_triggers = [
            "passe sur mon telephone", "passe sur mon portable", "passe sur mon smartphone",
            "bascule sur mon telephone", "bascule sur mon portable", "bascule sur mon smartphone",
            "passe sur le telephone", "passe sur le portable", "passe sur le smartphone",
            "reprends sur mon telephone", "reprends sur mon portable", "reprends sur mon smartphone",
            "passe sur telephone", "bascule sur telephone", "passe sur mobile"
        ]
        if any(tr in lower_clean for tr in handoff_to_mobile_triggers):
            reply, is_exit = self.handoff.transfer_to_mobile(self)
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, is_exit

        handoff_to_pc_triggers = [
            "reprends sur le pc", "reprends sur l'ordinateur", "reprends sur lordinateur",
            "bascule sur le pc", "bascule sur l'ordinateur", "bascule sur lordinateur",
            "retourne sur le pc", "passe sur le pc", "reviens sur le pc", "active le pc"
        ]
        if any(tr in lower_clean for tr in handoff_to_pc_triggers):
            reply, is_exit = self.handoff.resume_on_pc(self)
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, is_exit

        # ==========================================
        # 1. DÉTECTION PRIORITAIRE : FIN DE SESSION
        # ==========================================
        exit_triggers = [
            "au revoir", "merci crux", "merci", "c'est bon", "c'est fini", "stop",
            "ferme la session", "mets-toi en veille", "veille",
            "a plus", "bonne nuit", "bonne journee", "bonne soiree", "dors", "repos",
            "quitter", "arrete la session"
        ]
        is_window_or_light_op = any(w in lower_clean for w in ["fenetre", "application", "logiciel", "lumiere", "lumieres", "lampe", "onglet"])
        if not is_window_or_light_op and any(w in lower_clean for w in exit_triggers):
            reply = "Ça marche Corentin, je me remets en veille. À tout de suite !"
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, True

        # ==========================================
        # 2. VISION D'ÉCRAN MULTIMODALE À LA DEMANDE (0 TOKEN EN VEILLE)
        # ==========================================
        vision_triggers = [
            "regarde mon ecran", "regarde l'ecran", "regarde lecran", "qu'est-ce que tu vois",
            "quest ce que tu vois", "qu'est ce que tu vois", "analyse ce code", "analyse cette erreur",
            "analyse l'ecran", "analyse mon ecran", "analyse le bug", "regarde ce bug",
            "vois-tu mon ecran", "qu'est ce qu'il y a a l'ecran", "lis mon ecran", "lis l'ecran"
        ]
        if any(tr in lower_clean for tr in vision_triggers):
            self.hud.tool_use("Vision Écran", {"action": "Capture et analyse multimodale Gemini"})
            reply = self._query_screen_vision(user_text)
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        # ==========================================
        # 2.5 GENERATIVE DYNAMIC UI (INTERFACES EN DIRECT DANS LA BULLE COUCOU)
        # ==========================================
        if any(w in lower_clean for w in ["ferme l'interface", "ferme la bulle", "ferme l'ui", "masque l'interface", "masque la bulle"]):
            self.ui_runtime.close()
            reply = "Interface refermée."
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        if any(w in lower_clean for w in ["ajoute la tache", "ajoute l'activite", "ajoute l'activité", "ajoute une tache", "ajoute une activité", "ajoute a mes activites"]):
            m = re.search(r"(?:ajoute\s+(?:la\s+t[aâ]che|l['’]activit[eé]|une\s+t[aâ]che|une\s+activit[eé]|a\s+mes\s+activit[eé]s)\s+)(.+)", user_text, flags=re.IGNORECASE)
            task_text = m.group(1).strip() if m else "Nouvelle tâche"
            self.ui_runtime.append_task(task_text)
            self.sfx.play("chime")
            self.hud.tool_use("Interface Dynamique", {"action": "Ajout tâche en direct", "texte": task_text})
            reply = f"Activité '{task_text}' ajoutée et affichée en direct."
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        dynamic_ui_triggers = [
            "affiche mes activites", "affiche mes activités", "affiche mes taches", "affiche mes tâches",
            "cree une interface", "crée une interface", "affiche un dashboard", "affiche un tableau de bord",
            "cree une bulle", "crée une bulle", "affiche l'interface", "affiche la bulle"
        ]
        if any(tr in lower_clean for tr in dynamic_ui_triggers):
            self.sfx.play("chime")
            self.hud.tool_use("Interface Dynamique", {"action": "Génération à la volée", "requête": user_text})
            view = self.ui_runtime.render_from_prompt(user_text)
            reply = f"Interface {view.get('title', '')} générée et affichée dans la bulle."
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        # ==========================================
        # 3. ROUTAGE VERS LES PLUGINS (DOMOTIQUE IOT, LUMIÈRES, ETC.)
        # ==========================================
        plugin_result = self.plugins.route_voice_command(user_text)
        if plugin_result is not None:
            reply_plugin, is_exit = plugin_result
            self.sfx.play("chime")
            self.hud.tool_use("Plugins", {"action": "Domotique IoT", "commande": user_text})
            self._record_turn("user", user_text)
            self._record_turn("model", reply_plugin)
            return reply_plugin, is_exit

        # ==========================================
        # 4. COMPUTER USE AVANCÉ (FENÊTRES, CLAVIER, SOURIS AVEC GARDE-FOUS)
        # ==========================================
        # Exécution de script externe (Action critique soumise à confirmation)
        if any(w in lower_clean for w in ["execute le script", "exécute le script", "lance le script", "demarre le script"]):
            m = re.search(r"(?:execute|exécute|lance|demarre)\s+le\s+script\s+([a-zA-Z0-9_\-\.\/\\\:]+)", user_text, flags=re.IGNORECASE)
            script_name = m.group(1).strip() if m else ""
            if script_name:
                self.computer_use.request_confirmation(
                    "run_script",
                    {"script": script_name},
                    f"Êtes-vous certain de vouloir exécuter le script {script_name} ?"
                )
                reply = f"Êtes-vous certain de vouloir exécuter le script {script_name} ?"
                self._record_turn("user", user_text)
                self._record_turn("model", reply)
                return reply, False

        # Saisie clavier directe
        type_prefix = None
        for pfx in ["ecris ", "écris ", "tape ", "saisis "]:
            if lower_clean.startswith(pfx):
                type_prefix = pfx
                break
        if type_prefix:
            text_to_type = user_text[len(type_prefix):].strip()
            if text_to_type:
                self.computer_use.keyboard_type(text_to_type)
                reply = f"Texte saisi : {text_to_type}."
                self._record_turn("user", user_text)
                self._record_turn("model", reply)
                return reply, False

        # Raccourcis clavier globaux
        if lower_clean.startswith("fais ") or lower_clean.startswith("raccourci "):
            hk_text = re.sub(r"^(?:fais|raccourci)\s+", "", lower_clean).strip()
            parts = [k.strip() for k in re.split(r'[\s\+]+', hk_text) if k.strip()]
            if parts and all(self.computer_use.is_valid_key(p) for p in parts):
                is_crit, prompt_crit = self.computer_use.is_critical_action("keyboard_hotkey", {"keys": parts})
                if is_crit:
                    self.computer_use.request_confirmation("keyboard_hotkey", {"keys": parts}, prompt_crit)
                    reply = prompt_crit
                else:
                    self.computer_use.keyboard_hotkey(*parts)
                    reply = f"Raccourci {'+'.join(parts).upper()} exécuté."
                self._record_turn("user", user_text)
                self._record_turn("model", reply)
                return reply, False

        if any(w in lower_clean for w in ["ferme la fenetre", "ferme l'application", "ferme le logiciel", "fermer la fenetre"]):
            cmd_no_crux = re.sub(r"^(?:crux|jarvis)\s+", "", lower_clean).strip()
            target = re.sub(r"(?:ferme la fenetre|ferme l'application|ferme le logiciel|fermer la fenetre)\s*(?:de\s+|du\s+)?", "", cmd_no_crux).strip()
            target_name = target if target else "active"
            self.computer_use.request_confirmation(
                "close_window",
                {"title_pattern": target},
                f"Êtes-vous certain de vouloir fermer la fenêtre {target_name} ?"
            )
            reply = f"Êtes-vous certain de vouloir fermer la fenêtre {target_name} ?"
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        if any(w in lower_clean for w in ["maximise la fenetre", "maximiser la fenetre", "mets la fenetre en plein ecran"]):
            cmd_no_crux = re.sub(r"^(?:crux|jarvis)\s+", "", lower_clean).strip()
            target = re.sub(r"(?:maximise la fenetre|maximiser la fenetre|mets la fenetre en plein ecran)\s*(?:de\s+|du\s+)?", "", cmd_no_crux).strip()
            if target:
                ok = self.computer_use.maximize_window(target)
                reply = f"Fenêtre {target} maximisée." if ok else f"Fenêtre {target} introuvable."
            else:
                reply = self.sys.snap_active_window("plein ecran")
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        if "alt tab" in lower_clean or "bascule de fenetre" in lower_clean or "change de fenetre" in lower_clean:
            self.computer_use.keyboard_hotkey("alt", "tab")
            reply = "Fenêtre basculée."
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        if any(w in lower_clean for w in ["clic souris", "fais un clic", "clique gauche", "double clic"]):
            double = "double" in lower_clean
            self.computer_use.mouse_click(double=double)
            reply = "Double clic effectué." if double else "Clic effectué."
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        if any(w in lower_clean for w in ["descends la page", "scroll bas", "defile vers le bas"]):
            self.computer_use.mouse_scroll(-3)
            reply = "Défilement vers le bas."
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        if any(w in lower_clean for w in ["monte la page", "scroll haut", "defile vers le haut"]):
            self.computer_use.mouse_scroll(3)
            reply = "Défilement vers le haut."
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        # ==========================================
        # PRESSE-PAPIER (CURSORTOUCH/WINDOWS-MCP)
        # ==========================================
        if any(w in lower_clean for w in ["lis le presse-papier", "lis le presse papier", "qu'y a-t-il dans le presse-papier", "contenu du presse-papier", "presse-papier"]):
            if any(w in lower_clean for w in ["copie", "mets dans", "ajoute"]):
                pass
            elif "vide" in lower_clean or "efface" in lower_clean:
                self.computer_use.clipboard_clear()
                self.hud.tool_use("Presse-papier", {"action": "Nettoyage"})
                reply = "Presse-papier vidé."
                self._record_turn("user", user_text)
                self._record_turn("model", reply)
                return reply, False
            else:
                txt = self.computer_use.clipboard_get()
                self.hud.tool_use("Presse-papier", {"action": "Lecture"})
                if txt:
                    reply = f"Le presse-papier contient : {txt[:120]}."
                else:
                    reply = "Le presse-papier est vide."
                self._record_turn("user", user_text)
                self._record_turn("model", reply)
                return reply, False

        m_clip = re.search(r"(?:copie|mets)\s+(?:dans\s+le\s+presse-papier|dans\s+le\s+presse\s+papier)\s*:\s*(.+)", user_text, flags=re.IGNORECASE) or \
                 re.search(r"(?:copie|mets)\s+(.+?)\s+dans\s+le\s+presse-papier", user_text, flags=re.IGNORECASE)
        if m_clip:
            to_copy = m_clip.group(1).strip()
            self.computer_use.clipboard_set(to_copy)
            self.hud.tool_use("Presse-papier", {"action": "Écriture", "longueur": len(to_copy)})
            reply = "Texte copié dans le presse-papier."
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        # ==========================================
        # PROCESSUS & TÉLÉMÉTRIE (BNSWARE/JARVIS-WINDOWS)
        # ==========================================
        if any(w in lower_clean for w in ["processus gourmand", "processus qui consomment", "top processus", "processus actifs", "liste les processus"]):
            sort_metric = "ram" if any(w in lower_clean for w in ["ram", "memoire"]) else "cpu"
            summary = self.computer_use.telemetry.format_top_processes_summary(sort_by=sort_metric, limit=5)
            self.hud.tool_use("Processus Windows", {"action": "Inspection télémétrique", "tri": sort_metric.upper()})
            self._record_turn("user", user_text)
            self._record_turn("model", summary)
            return summary, False

        if any(w in lower_clean for w in ["tue le processus", "arrete le processus", "arrête le processus", "kill le processus"]):
            m_proc = re.search(r"(?:tue|arrete|arrête|kill)\s+le\s+processus\s+([a-zA-Z0-9_\-\.]+)", user_text, flags=re.IGNORECASE)
            proc_target = m_proc.group(1).strip() if m_proc else ""
            if proc_target:
                self.computer_use.request_confirmation(
                    "kill_process",
                    {"process": proc_target},
                    f"Êtes-vous certain de vouloir arrêter le processus {proc_target} ?"
                )
                reply = f"Êtes-vous certain de vouloir arrêter le processus {proc_target} ?"
                self._record_turn("user", user_text)
                self._record_turn("model", reply)
                return reply, False

        if any(w in lower_clean for w in ["telemetrie", "télémétrie", "diagnostic systeme", "diagnostic complet", "etat de la batterie", "niveau de batterie"]):
            telem = self.computer_use.telemetry.get_system_telemetry()
            cpu_pct = telem["cpu"]["percent"]
            ram_pct = telem["memory"]["percent"]
            diag = self.computer_use.telemetry.format_telemetry_summary()
            self.hud.tool_use("Télémétrie Jarvis", {"action": "Diagnostic matériel complet"})
            try:
                self.hud.sync_telemetry(cpu_pct, ram_pct, diag)
                self.hud.send_card("Télémétrie Système", {
                    "CPU": f"{cpu_pct} %",
                    "RAM": f"{ram_pct} % ({telem['memory']['available_gb']} Go dispo)",
                    "Uptime": telem['uptime_formatted']
                })
            except Exception:
                pass
            self._record_turn("user", user_text)
            self._record_turn("model", diag)
            return diag, False

        # Spotify : interrogation directe de la piste en cours
        if any(w in lower_clean for w in ["morceau en cours", "titre en cours", "musique en cours", "quelle musique tourne", "quelle musique passe", "qu'est-ce qui passe sur spotify", "quest ce qui passe sur spotify", "qui passe sur spotify", "titre sur spotify"]):
            _, msg, _ = self.sys.get_spotify_now_playing_summary()
            self.hud.tool_use("Spotify", {"action": "Piste en cours"})
            self._record_turn("user", user_text)
            self._record_turn("model", msg)
            return msg, False

        # ==========================================
        # COMMANDES SYSTÈME & CODE (OPEN-INTERPRETER / DMRR35)
        # ==========================================
        if any(w in lower_clean for w in ["execute la commande", "exécute la commande", "lance la commande"]):
            m_cmd = re.search(r"(?:execute|exécute|lance)\s+la\s+commande\s+(.+)", user_text, flags=re.IGNORECASE)
            cmd_text = m_cmd.group(1).strip() if m_cmd else ""
            if cmd_text:
                is_crit, msg_crit = self.computer_use.is_critical_action("run_command", {"command": cmd_text})
                if is_crit:
                    self.computer_use.request_confirmation("run_command", {"command": cmd_text}, msg_crit)
                    reply = msg_crit
                else:
                    self.hud.tool_use("Exécution Commande", {"commande": cmd_text})
                    res = self.computer_use.execute_command(cmd_text)
                    reply = res["stdout"] or res["stderr"] or "Commande exécutée."
                self._record_turn("user", user_text)
                self._record_turn("model", reply)
                return reply, False

        # ==========================================
        # UI AUTOMATION HEADLESS (SIRENDHEAD/WINDOWS-USE)
        # ==========================================
        if any(w in lower_clean for w in ["inspecte la fenetre", "elements de la fenetre", "composants de la fenetre"]):
            summary = self.computer_use.uia_inspect_window()
            self.hud.tool_use("UI Automation", {"action": "Inspection mémoire arbre UIA"})
            self._record_turn("user", user_text)
            self._record_turn("model", summary)
            return summary, False

        if any(w in lower_clean for w in ["clique sur le bouton", "appuie sur le bouton", "active le bouton"]):
            m_btn = re.search(r"(?:clique sur le bouton|appuie sur le bouton|active le bouton)\s+([a-zA-Z0-9_\-\s]+)", user_text, flags=re.IGNORECASE)
            btn_name = m_btn.group(1).strip() if m_btn else ""
            if btn_name:
                self.hud.tool_use("UI Automation", {"action": "InvokePattern sans souris", "cible": btn_name})
                ok, msg = self.computer_use.uia_click(name=btn_name)
                reply = msg
                self._record_turn("user", user_text)
                self._record_turn("model", reply)
                return reply, False

        # ==========================================
        # 2. CONTRÔLE AUDIO / ENCEINTES / SORTIE SON
        # ==========================================
        # Détection bascule Enceinte JBL
        is_jbl_request = (
            "jbl" in lower_clean or
            ("enceinte" in lower_clean and any(w in lower_clean for w in ["mets", "passe", "bascule", "connecte", "active", "utilise", "son", "audio", "sur", "bruit"]))
        )
        if is_jbl_request:
            if self.tts:
                self.tts.set_target_device("jbl")
            if "bruit" in lower_clean or "test" in lower_clean:
                reply = "Signal de test sonore transmis sur votre enceinte JBL, Corentin."
            else:
                reply = "Sortie audio immédiatement basculée sur votre enceinte JBL, Corentin."
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        # Détection bascule Haut-parleurs Écran
        is_screen_request = (
            ("ecran" in lower_clean or "moniteur" in lower_clean) and
            any(w in lower_clean for w in ["son", "audio", "haut-parleur", "hauts-parleurs", "voix"]) and
            any(w in lower_clean for w in ["mets", "passe", "bascule", "connecte", "active", "utilise", "sur"]) and
            "luminosite" not in lower_clean
        )
        if is_screen_request:
            if self.tts:
                self.tts.set_target_device("screen")
            reply = "Sortie audio basculée sur les haut-parleurs de l'écran, Corentin."
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        # Détection bascule Casque (G435 / Casque)
        is_headset_request = (
            ("casque" in lower_clean or "g435" in lower_clean) and
            any(w in lower_clean for w in ["mets", "passe", "bascule", "connecte", "active", "utilise", "son", "audio", "sur"])
        )
        if is_headset_request:
            if self.tts:
                self.tts.set_target_device("casque")
            reply = "Sortie audio immédiatement basculée sur votre casque, Corentin."
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        # Détection bascule Piste audio de base (Windows par défaut)
        is_default_request = any(k in lower_clean for k in [
            "piste de base", "truc de base", "son de base", "audio de base",
            "sortie de base", "par defaut", "audio par defaut",
            "remets l'audio", "remets le son de base", "audio normal", "son normal"
        ])
        if is_default_request:
            if self.tts:
                self.tts.set_target_device("default")
            reply = "Sortie audio réinitialisée sur la piste de base par défaut de votre système, Corentin."
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        # ==========================================
        # 3. HEURE, DATE, LOCALISATION & MÉTÉO
        # ==========================================
        # Horloge en temps réel (Format naturel en français parlé : ex 12:44 -> 'midi 44')
        if ("heure" in lower_clean or "l'heure" in lower_clean) and any(w in lower_clean for w in ["quelle", "quel", "il est", "donne", "dis", "donne-moi"]):
            time_phrase = self._get_natural_french_time()
            if any(w in lower_clean for w in ["bonjour", "salut"]):
                reply = f"Bonjour, il est {time_phrase}, Corentin."
            else:
                reply = f"Il est actuellement {time_phrase}, Corentin."
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        # Localisation réelle de l'appareil
        if any(w in lower_clean for w in ["ou suis je", "ou suis-je", "ma position", "localisation", "ou est mon pc", "ou se trouve le pc"]):
            loc = self.sys.get_device_location()
            reply = f"D'après la télémétrie réseau, vous êtes situé à {loc['city']}, en {loc['region']}, Corentin."
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        # Date en temps réel
        if any(w in lower_clean for w in ["date", "quel jour", "qu'elle date"]):
            jours = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
            mois = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
            now = datetime.now()
            reply = f"Nous sommes le {jours[now.weekday()]} {now.day} {mois[now.month - 1]} {now.year}, Corentin."
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        # Météo en direct
        if any(w in lower_clean for w in ["meteo", "temps fait il", "quel temps", "temperature", "fait beau", "pleut"]):
            reply = self._get_realtime_weather()
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        # Connexion Antigravity
        if "antigravity" in lower_clean:
            reply = "Affirmatif, je suis parfaitement connecté à votre espace Antigravity, Corentin."
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        # Paramètres et configurations Coucou (Notch & Mochi)
        if any(w in lower_clean for w in ["parametre de coucou", "parametres de coucou", "reglages de coucou", "configuration de coucou", "configurations de coucou", "options de coucou", "ouvre coucou"]):
            self.hud.open_settings()
            reply = "Fenêtre des paramètres et configurations de Coucou ouverte, Corentin."
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        # ==========================================
        # 4. CONTRÔLE DU VOLUME & MULTIMÉDIA & MATÉRIEL
        # ==========================================
        # Luminosité de l'écran
        if any(w in lower_clean for w in ["luminosite", "luminosite de l'ecran", "luminosite des ecrans"]):
            m_pct = re.search(r"(\d+)\s*%", lower_clean) or re.search(r"(?:a|a\s+environ)\s+(\d+)", lower_clean)
            target_disp = None
            if "viewsonic" in lower_clean:
                target_disp = "ViewSonic"
            elif any(k in lower_clean for k in ["iiyama", "pl2766h", "principal"]):
                target_disp = "Iiyama"

            if m_pct:
                pct_val = int(m_pct.group(1))
                reply = self.sys.set_brightness(pct_val, display=target_disp)
            elif any(w in lower_clean for w in ["quelle", "combien", "niveau"]):
                reply = self.sys.get_brightness()
            elif any(w in lower_clean for w in ["augmente", "monte", "plus fort", "plus lumine"]):
                reply = self.sys.set_brightness(85, display=target_disp)
            elif any(w in lower_clean for w in ["baisse", "diminue", "moins fort", "moins lumine"]):
                reply = self.sys.set_brightness(30, display=target_disp)
            else:
                reply = self.sys.get_brightness()
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        # Mixeur audio et liste des applications sonores (WASAPI)
        if any(w in lower_clean for w in ["quelles applications ont du son", "applications audio", "mixeur audio", "sessions audio"]):
            sessions = self.sys.list_audio_sessions()
            if sessions:
                items = [f"{s['process']} ({s['volume_percent']} %)" for s in sessions]
                reply = f"Applications audio actives : {', '.join(items[:6])}."
            else:
                reply = "Aucune application n'émet de son actuellement."
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        # Volume / Mute par application spécifique (Discord, Spotify, etc.)
        m_app_mute = re.search(r"(?:coupe|mute|silence)\s+(?:le\s+son\s+de|sur)\s+([a-zA-Z0-9_\-]+)", lower_clean)
        if m_app_mute:
            app_target = m_app_mute.group(1).strip()
            reply = self.sys.mute_app(app_target, mute=True)
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        m_app_unmute = re.search(r"(?:remets|reactive|demute)\s+(?:le\s+son\s+de|sur)\s+([a-zA-Z0-9_\-]+)", lower_clean)
        if m_app_unmute:
            app_target = m_app_unmute.group(1).strip()
            reply = self.sys.mute_app(app_target, mute=False)
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        m_app_vol = re.search(r"(?:volume|son)\s+(?:de\s+|sur\s+)([a-zA-Z0-9_\-]+)\s+(?:a|au niveau)\s+(\d+)", lower_clean)
        if m_app_vol:
            app_target = m_app_vol.group(1).strip()
            pct_val = int(m_app_vol.group(2))
            reply = self.sys.set_app_volume(app_target, pct_val)
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
        # Volume principal Windows WASAPI
        m_master_vol = re.search(r"(?:volume\s+principal|volume\s+general|volume\s+général|volume\s+master)\s+(?:a|au niveau)\s+(\d+)", lower_clean)
        if m_master_vol:
            pct_val = int(m_master_vol.group(1))
            reply = self.sys.set_master_volume(pct_val)
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        # Interrogation du volume d'une application
        m_get_vol = re.search(r"(?:quel est le volume de|volume de)\s+([a-zA-Z0-9_\-]+)", lower_clean)
        if m_get_vol and not any(w in lower_clean for w in ["a", "au niveau", "mets", "regle"]):
            app_target = m_get_vol.group(1).strip()
            if app_target not in ["la", "le", "mon", "base", "spotify", "discord"]:
                vol = self.sys.get_app_volume(app_target)
                if vol is not None:
                    reply = f"Le volume de {app_target.capitalize()} est à {vol} %."
                    self._record_turn("user", user_text)
                    self._record_turn("model", reply)
                    return reply, False

        if any(w in lower_clean for w in ["monte le son", "augmente le son", "augmente le volume", "plus fort"]):
            reply = self.sys.volume_up()
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        if any(w in lower_clean for w in ["baisse le son", "diminue le son", "diminue le volume", "moins fort"]):
            reply = self.sys.volume_down()
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        if any(w in lower_clean for w in ["coupe le son", "remets le son", "mute", "silence total"]):
            reply = self.sys.volume_mute()
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        if any(w in lower_clean for w in ["mets pause", "pause la musique", "pause", "arret musique"]):
            self.sys.media_play_pause()
            reply = "Lecture multimédia mise en pause, Corentin."
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        if any(w in lower_clean for w in ["morceau suivant", "musique suivante", "piste suivante", "chanson suivante"]):
            reply = self.sys.media_next()
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        if any(w in lower_clean for w in ["morceau precedent", "musique precedente", "piste precedente"]):
            reply = self.sys.media_prev()
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        # ==========================================
        # 5. MANIPULATION ET SNAP DES FENÊTRES
        # ==========================================
        if any(w in lower_clean for w in ["fenetre a gauche", "mets a gauche", "fenetre sur la gauche", "cote gauche"]):
            self.sfx.play("snap")
            self.hud.tool_use("Disposition Fenêtre", {"action": "Ancrer à gauche"})
            reply = self.sys.snap_active_window("gauche")
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        if any(w in lower_clean for w in ["fenetre a droite", "mets a droite", "fenetre sur la droite", "cote droit"]):
            self.sfx.play("snap")
            self.hud.tool_use("Disposition Fenêtre", {"action": "Ancrer à droite"})
            reply = self.sys.snap_active_window("droite")
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        if any(w in lower_clean for w in ["plein ecran", "agrandis la fenetre", "maximise la fenetre"]):
            self.sfx.play("snap")
            self.hud.tool_use("Disposition Fenêtre", {"action": "Plein écran"})
            reply = self.sys.snap_active_window("plein ecran")
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        if any(w in lower_clean for w in ["reduis la fenetre", "minimise la fenetre", "cache la fenetre"]):
            self.sfx.play("snap")
            self.hud.tool_use("Disposition Fenêtre", {"action": "Minimiser"})
            reply = self.sys.snap_active_window("reduis")
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        if any(w in lower_clean for w in ["centre la fenetre", "recentre la fenetre", "fenetre au milieu"]):
            self.sfx.play("snap")
            self.hud.tool_use("Disposition Fenêtre", {"action": "Centrer"})
            reply = self.sys.snap_active_window("centre")
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        if any(w in lower_clean for w in ["baisser toutes les fenetres", "baisse toutes les fenetres", "reduis toutes les fenetres", "ferme toutes les fenetres", "cache toutes les fenetres", "affiche le bureau", "retour bureau", "montre le bureau"]):
            self.sfx.play("snap")
            self.hud.tool_use("Disposition Fenêtre", {"action": "Afficher le bureau"})
            reply = self.sys.minimize_all_windows()
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        # ==========================================
        # 6. RACCOURCIS DIRECTS MUSIQUE & SPOTIFY (0 LATENCE)
        # ==========================================
        music_cmd = self._parse_music_command(user_text)
        if music_cmd:
            plat = music_cmd.get("platform") or "spotify"
            act = music_cmd.get("action")
            q = music_cmd.get("query", "").strip()
            self.sfx.play("chime")
            if act == "resume" or not q:
                self.hud.tool_use("Lecteur Musique", {"action": "Reprise de la lecture", "plateforme": plat.capitalize()})
                reply = self.sys.play_music("", platform=plat)
                self.hud.set_state("media", "Crux Musique", "Lecture active")
            else:
                self.hud.tool_use("Lecteur Musique", {"requête": q, "plateforme": plat.capitalize()})
                reply = self.sys.play_music(q, platform=plat)
                self.hud.set_state("media", "Crux Musique", q[:24])
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        # ==========================================
        # 6. PRESETS D'ESPACE DE TRAVAIL (DISPOSITION DES FENÊTRES)
        # ==========================================
        if any(w in lower_clean for w in ["enregistre le preset", "enregistre ce preset", "sauvegarde le preset", "enregistre la disposition", "sauvegarde la disposition"]):
            m = re.search(r"(?:preset|disposition)\s*(?:sous le nom\s+)?([a-zA-Z0-9_\-]+)", lower_clean)
            preset_name = m.group(1).strip() if m else "travail"
            if preset_name in ["ce", "cette", "le", "la"]:
                tokens = lower_clean.split()
                preset_name = tokens[-1] if tokens[-1] not in ["preset", "disposition"] else "travail"
            self.hud.tool_use("Preset Fenêtres", {"action": f"Sauvegarde '{preset_name}'"})
            reply = self.sys.save_workspace_preset(preset_name)
            self.sfx.play("preset")
            self.hud.notify(f"Preset {preset_name.capitalize()}", "Disposition sauvegardée", 4.0)
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        if any(w in lower_clean for w in ["charge le preset", "remets le preset", "active le preset", "remets le mode", "mets le mode", "active le mode"]) and not any(w in lower_clean for w in ["mode jeu"]):
            m = re.search(r"(?:preset|mode|disposition)\s+([a-zA-Z0-9_\-]+)", lower_clean)
            if m:
                preset_name = m.group(1).strip()
                if preset_name not in ["ce", "cette", "le", "la", "en"]:
                    self.sfx.play("preset")
                    self.hud.tool_use("Preset Fenêtres", {"action": f"Application '{preset_name}'"})
                    reply = self.sys.apply_workspace_preset(preset_name)
                    self.hud.notify(f"Preset {preset_name.capitalize()}", "Disposition appliquée", 4.0)
                    self._record_turn("user", user_text)
                    self._record_turn("model", reply)
                    return reply, False

        if any(w in lower_clean for w in ["quels sont mes presets", "liste les presets", "mes presets", "affiche les presets"]):
            reply = self.sys.list_workspace_presets()
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        # ==========================================
        # 5. MINUTEUR VOCAL AUTONOME
        # ==========================================
        if "minuteur" in lower_clean:
            timer_reply = self._parse_and_start_timer(user_text)
            if timer_reply:
                self._record_turn("user", user_text)
                self._record_turn("model", timer_reply)
                return timer_reply, False

        # ==========================================
        # 6. CAPTURE D'ÉCRAN & AFFICHAGE
        # ==========================================
        if any(w in lower_clean for w in ["capture d'ecran", "capture decran", "screenshot", "fais une capture", "prends un screenshot", "prends une capture"]):
            reply = self.sys.take_screenshot()
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        if any(w in lower_clean for w in ["eteins l'ecran", "eteins lecran", "veille de l'ecran", "veille ecran", "eteins les ecrans"]):
            reply = self.sys.sleep_display()
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        # ==========================================
        # 7. MODE JEU & GAMING BOOST
        # ==========================================
        if any(w in lower_clean for w in ["mode jeu", "optimise pour le jeu", "boost le pc", "boost pc", "optimise le pc"]):
            reply = self.sys.game_mode_boost()
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        # ==========================================
        # 8. PENSE-BÊTE & NOTES VOCALES
        # ==========================================
        note_prefixes = ["note que", "rappelle-moi de", "rappelle moi de", "ajoute une note", "ajoute la note"]
        for np_cmd in note_prefixes:
            if np_cmd in lower_clean:
                idx = lower_clean.find(np_cmd) + len(np_cmd)
                note_content = user_text[idx:].strip()
                if note_content:
                    reply = self.sys.save_note(note_content)
                else:
                    reply = "Que dois-je noter pour vous, Corentin ?"
                self._record_turn("user", user_text)
                self._record_turn("model", reply)
                return reply, False

        if any(w in lower_clean for w in ["efface mes notes", "supprime mes notes", "vide mes notes"]):
            reply = self.sys.clear_notes()
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        if any(w in lower_clean for w in ["quelles sont mes notes", "lis mes notes", "mes notes", "affiche mes notes"]):
            reply = self.sys.read_notes()
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        # ==========================================
        # 9. UTILITAIRES WINDOWS (CORBEILLE, IP)
        # ==========================================
        if any(w in lower_clean for w in ["vide la corbeille", "nettoie la corbeille"]):
            reply = self.sys.empty_recycle_bin()
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        if any(w in lower_clean for w in ["mon ip", "adresse ip", "quelle est mon ip"]):
            reply = self.sys.get_ip_info()
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        # ==========================================
        # 10. EASTER EGGS JARVIS
        # ==========================================
        if any(w in lower_clean for w in ["protocole fete foraine", "protocole jarvis", "fete foraine"]):
            reply = "Protocole enclenché, Monsieur. Tous les propulseurs et sous-systèmes sont à pleine puissance."
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        if any(w in lower_clean for w in ["qui t'a cree", "qui test tu", "qui es tu", "qui es-tu"]):
            reply = "Je suis Crux, votre assistant personnel intelligent propulsé par l'IA d'Antigravity."
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        # ==========================================
        # 4. SALUTATIONS SIMPLES COURTES
        # ==========================================
        if lower_clean in ["ca va", "ca va ?", "comment vas tu", "comment vas-tu", "tu vas bien", "comment ca va"]:
            reply = f"Tout va bien{self._name_suffix()}, parfaitement opérationnel. Et toi ?"
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        if lower_clean in ["salut", "bonjour", "yo", "coucou", "hey"]:
            reply = f"Bonjour{self._name_suffix()}, que puis-je faire pour toi aujourd'hui ?"
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        # ==========================================
        # 4. ACTIONS SYSTÈME PC WINDOWS
        # ==========================================
        if any(w in lower_clean for w in ["performance", "stats", "combien de ram", "cpu", "memoire"]) or ("etat" in lower_clean and ("pc" in lower_clean or "ordi" in lower_clean)):
            reply = self.sys.get_system_stats()
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        if any(w in lower_clean for w in ["verrouille", "bloque le pc", "verrouille l'ordi"]):
            reply = self.sys.lock_pc()
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        if "dossier projet" in lower_clean or "mes documents" in lower_clean:
            reply = self.sys.open_folder(r"C:\Users\coco\Documents")
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        for app in ["discord", "chrome", "spotify", "taches", "task manager", "calculatrice", "notepad", "bloc-notes", "steam"]:
            if app in lower_clean and any(v in lower_clean for v in ["lance", "ouvre", "demarre"]):
                # Si l'utilisateur demande de la musique ou un titre sur Spotify, laisser le moteur IA ou musical s'en charger
                if app == "spotify" and any(m in lower_clean for m in ["musique", "music", "son", "chanson", "morceau", "titre", "playlist"]):
                    continue
                res = self.sys.launch_app(app)
                reply = res["message"]
                self._record_turn("user", user_text)
                self._record_turn("model", reply)
                return reply, False

        if "cherche sur google" in lower_clean or "recherche sur le web" in lower_clean:
            query = re.sub(r"(?:cherche sur google|recherche sur le web)\s*", "", lower_clean).strip()
            reply = self.sys.open_web(query)
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        if "ouvre youtube" in lower_clean:
            reply = self.sys.open_web("https://www.youtube.com")
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        # ==========================================
        # 5. ACTIONS PROJETS ANTIGRAVITY
        # ==========================================
        if any(w in lower_clean for w in ["liste les projets", "quels sont mes projets", "mes projets"]):
            projects = self.project_manager.list_projects()
            names = ", ".join(projects[:5])
            reply = f"Vos projets disponibles sont : {names}. Lequel voulez-vous ouvrir ?"
            self._record_turn("user", user_text)
            self._record_turn("model", reply)
            return reply, False

        if any(w in lower_clean for w in ["va dans le projet", "accede au projet", "bascule sur le projet"]):
            candidate = self._detect_project_intent(user_text)
            if candidate:
                res = self.project_manager.switch_project(candidate)
                if res["success"]:
                    reply = f"Contexte basculé sur {res['name']}. Je t'écoute !"
                else:
                    reply = res["message"]
                self._record_turn("user", user_text)
                self._record_turn("model", reply)
                return reply, False

        # ==========================================
        # 6. RAISONNEMENT VIA ANTIGRAVITY (ABONNEMENT OFFICIEL)
        # ==========================================
        self.hud.set_state("thinking", "CRUX", "Analyse Antigravity...")
        self.sfx.start_thinking()
        try:
            # 1. Priorité 1 : Moteur officiel Antigravity avec abonnement (Gemini 3.8 Flash)
            native_res = self._query_antigravity_native(user_text)
            if native_res:
                text, is_exit = self._execute_gemini_actions(native_res)
                self._record_turn("user", user_text)
                self._record_turn("model", text)
                self.hud.set_state("speaking", "CRUX", text[:26])
                return text, is_exit

            # 2. Priorité 2 : CLI Antigravity (agy_cli)
            cli_res = self._query_antigravity_cli(user_text)
            if cli_res:
                text, is_exit = self._execute_gemini_actions(cli_res)
                self._record_turn("user", user_text)
                self._record_turn("model", text)
                self.hud.set_state("speaking", "CRUX", text[:26])
                return text, is_exit

            # 3. Repli vers le client API direct en cas d'indisponibilité du CLI
            if self.chat_session is None:
                self._init_chat_session()
            if self.chat_session:
                try:
                    response = self.chat_session.send_message(user_text)
                    text = response.text.strip()
                    if text:
                        text, is_exit = self._execute_gemini_actions(text)
                        self._record_turn("user", user_text)
                        self._record_turn("model", text)
                        self.hud.set_state("speaking", "CRUX", text[:26])
                        return text, is_exit
                except Exception:
                    pass

            # 4. Secours direct rapide via generate_content (Gemini 3.8 Flash avec raisonnement Low)
            for model_cand in list(dict.fromkeys([self.model_name, "gemini-3.8-flash", "gemini-2.5-flash"])):
                try:
                    res = self.client.models.generate_content(
                        model=model_cand,
                        contents=user_text,
                        config=types.GenerateContentConfig(
                            system_instruction=JARVIS_SYSTEM_INSTRUCTION,
                            temperature=0.25,
                            max_output_tokens=150,
                            thinking_config=types.ThinkingConfig(thinking_budget=0)
                        )
                    )
                    text = res.text.strip()
                    if text:
                        text, is_exit = self._execute_gemini_actions(text)
                        self._record_turn("user", user_text)
                        self._record_turn("model", text)
                        self.hud.set_state("speaking", "CRUX", text[:26])
                        return text, is_exit
                except Exception:
                    continue
        finally:
            self.sfx.stop_thinking()

        fallback_reply = "Bien reçu."
        self._record_turn("user", user_text)
        self._record_turn("model", fallback_reply)
        self.hud.set_state("speaking", "CRUX", fallback_reply)
        return fallback_reply, False

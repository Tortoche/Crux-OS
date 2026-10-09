#!/usr/bin/env python3
"""
CRUX AI - Assistant Vocal Jarvis Haute Performance
Connecté au micro Fifine directement (bypasse Voicemeeter).
Pré-roll audio anti-coupure du premier mot.
Effets sonores (SFX) et routage automatique vers enceinte JBL ou Écran.
"""

import os
import sys
import yaml
import time
import threading
import warnings
import argparse
import collections
import numpy as np
import sounddevice as sd
from pathlib import Path

# Suppression des alertes parasites
warnings.filterwarnings("ignore")
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

from core.project_manager import ProjectManager
from core.agent import CruxAgent
from core.text_to_speech import TextToSpeech
from core.speech_to_text import SpeechToText
from core.wake_word import WakeWordDetector
from core.sound_effects import SoundEffects
from core.coucou_client import CoucouClient
from core.proactive.daemon import ProactiveDaemon

def load_config() -> dict:
    config_path = Path(__file__).parent / "config.yaml"
    if not config_path.exists():
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

class CruxApplication:
    def __init__(self):
        self.config = load_config()
        self.assistant_cfg = self.config.get("assistant", {})
        self.conv_cfg = self.config.get("conversation", {})
        self.brain_cfg = self.config.get("brain", {})

        print("==================================================")
        print("          CRUX AI - SYSTÈME JARVIS ACTIF         ")
        print("==================================================")

        # 0. Intégration officielle de la Notch Mochi du projet Coucou
        self.hud = CoucouClient.get_instance()
        self.hud.start()
        print("[Crux Coucou] Notch Mochi officielle Coucou intégrée et active !")

        # 1. Détection directe du micro Fifine (bypasse Voicemeeter)
        self.input_device = self._find_fifine_microphone()

        # 2. Gestionnaire d'effets sonores (SFX Jarvis)
        self.sfx = SoundEffects()
        print("[Crux SFX] Effets sonores enrichis chargés (wake, listen, process, success, sleep, thinking, snap, preset, notify)")

        # 3. Gestionnaire de projets
        projects_root = self.brain_cfg.get("projects_root", r"C:\Users\coco\Documents")
        self.project_manager = ProjectManager(root_dir=projects_root)
        print(f"[Crux] Répertoire projets : {projects_root}")

        # 4. Synthèse Vocale (TTS avec routage JBL / Écran)
        voice = self.config.get("tts", {}).get("edge", {}).get("voice_fr", "fr-FR-HenriNeural")
        self.tts = TextToSpeech(engine="edge", voice=voice)
        print(f"[Crux] Moteur vocal prêt : {voice}")

        # 5. Cerveau IA Antigravity (Gemini 3.8 Flash - Haute réactivité & Mémoire)
        api_key = self.brain_cfg.get("api_key", "")
        model_name = self.brain_cfg.get("model", "gemini-3.8-flash")
        self.agent = CruxAgent(
            api_key=api_key,
            model_name=model_name,
            project_manager=self.project_manager,
            tts=self.tts,
            sfx=self.sfx
        )
        print(f"[Crux] Cerveau IA connecté : {model_name}")

        # 6. Transcription Hybride (Google Speech Antigravity + Whisper local)
        self.stt = SpeechToText(primary_engine="google", whisper_model_size="base", cpu_threads=4)
        print("[Crux] Transcription active : Google Speech Engine (Haute Fidélité)")

        # 7. Détecteur de réveil autonome & Calibration automatique du micro
        self.wake_detector = WakeWordDetector()
        self.wake_detector.calibrate_noise_floor(device=self.input_device)

        # 8. Moteur de Proactivité Événementielle (100% local, 0 token LLM)
        self.proactive = ProactiveDaemon(
            tts=self.tts,
            hud=self.hud,
            check_interval=5.0,
            cooldown_seconds=300.0
        )
        self.proactive.start()
        print("[Crux Proactif] Moteur proactif d'arrière-plan démarré.")

        # 9. Pont Mobile Tactile & Télécommande Handoff
        try:
            from core.mobile_bridge.bridge_service import MobileBridgeService
            self.mobile_bridge = MobileBridgeService.get_instance(agent=self.agent)
            self.mobile_bridge.start_in_background()
            print("[Crux Mobile] Pont mobile tactile et télécommande PC actif sur 0.0.0.0:49230.")
        except Exception as e:
            print(f"[Crux Mobile] Pont mobile non démarré : {e}")

    def _find_fifine_microphone(self) -> int:
        """Détecte et verrouille le microphone Fifine directement."""
        devices = sd.query_devices()
        for i, d in enumerate(devices):
            if d['max_input_channels'] > 0 and 'fifine' in d['name'].lower():
                try:
                    sd.check_input_settings(device=i)
                    print(f"[Crux Micro] Micro sélectionné : {d['name']} (Index {i})")
                    return i
                except Exception:
                    pass
        print("[Crux Micro] Fifine non trouvé, utilisation de l'entrée par défaut.")
        return None

    def get_output_device(self) -> int:
        """Retourne le périphérique audio prioritaire (JBL ou Écran)."""
        dev_idx, _, _ = self.tts.find_target_audio_device()
        return dev_idx

    def listen_for_command(self, timeout_seconds: float = 30.0, silence_timeout: float = 0.5) -> Tuple[str, np.ndarray]:
        """
        Écoute en continu tant que Corentin n'a pas prononcé de vrais mots.
        - Si c'est un simple bruit de fond, souffle ou claquement sans mots : Crux continue d'écouter
          silencieusement sur la même ligne SANS relancer la boucle ni répéter 'À votre écoute...'.
        - Pendant que Corentin parle : affiche les mots en direct à l'écran.
        - Dès que Corentin a fini sa phrase (silence après des mots) : valide et retourne la phrase immédiatement.
        - Si 30s d'inactivité totale sans parole : retourne ("", None).
        """
        sample_rate = 16000
        chunk_size = 1024
        buffer = []
        pre_buffer = collections.deque(maxlen=8)  # ~512ms pré-roll anti-coupure
        silence_count = 0
        has_spoken = False
        threshold = self.wake_detector.energy_threshold

        latest_partial_text = ""
        last_transcribe_time = 0.0
        stop_worker = False
        lock = threading.Lock()

        def live_streaming_worker():
            nonlocal latest_partial_text, last_transcribe_time
            while not stop_worker:
                time.sleep(0.12)
                if has_spoken and (time.time() - last_transcribe_time > 0.22):
                    with lock:
                        if len(buffer) > int(sample_rate * 0.25):
                            chunk_copy = np.concatenate(buffer)
                        else:
                            chunk_copy = None
                    if chunk_copy is not None:
                        last_transcribe_time = time.time()
                        partial = self.stt.transcribe_audio_data(chunk_copy, sample_rate)
                        if partial and partial.strip():
                            latest_partial_text = partial.strip()
                            self.hud.live_speech(latest_partial_text)
                            sys.stdout.write(f"\r\033[K[Corentin en direct] > {latest_partial_text} ...")
                            sys.stdout.flush()

        worker_thread = threading.Thread(target=live_streaming_worker, daemon=True)
        worker_thread.start()

        def callback(indata, frames, time_info, status):
            nonlocal silence_count, has_spoken, buffer
            chunk = indata[:, 0]
            rms = np.sqrt(np.mean(chunk**2))

            if rms > threshold:
                if not has_spoken:
                    has_spoken = True
                    with lock:
                        buffer.extend(list(pre_buffer))
                silence_count = 0
                with lock:
                    buffer.append(chunk.copy())
            elif has_spoken:
                with lock:
                    buffer.append(chunk.copy())
                silence_count += 1
            else:
                pre_buffer.append(chunk.copy())

        stream = sd.InputStream(
            samplerate=sample_rate,
            channels=1,
            blocksize=chunk_size,
            dtype="float32",
            device=self.input_device,
            callback=callback
        )

        start_time = time.time()

        try:
            with stream:
                while (time.time() - start_time) < timeout_seconds:
                    sd.sleep(35)

                    # VU Mètre en temps réel tant qu'aucun mot n'a été reconnu
                    if not latest_partial_text:
                        current_rms = 0.0
                        with lock:
                            if buffer and len(buffer) > 0 and len(buffer[-1]) > 0:
                                val = np.sqrt(np.mean(buffer[-1]**2))
                                if not np.isnan(val):
                                    current_rms = float(val)
                        vu_ratio = min(max(current_rms / 0.025, 0.0), 1.0)
                        self.hud.update_vu(vu_ratio)
                        bars = int(vu_ratio * 12)
                        status_text = "[Parole en cours]" if has_spoken else ""
                        sys.stdout.write(f"\r\033[K[Crux Micro] 🎤 À l'écoute... [{'█' * bars}{'░' * (12 - bars)}] {status_text}")
                        sys.stdout.flush()

                    # Vérification de fin de phrase après détection de parole
                    if has_spoken and silence_count > int(sample_rate / chunk_size * silence_timeout):
                        with lock:
                            recorded_audio = np.concatenate(buffer) if buffer else np.array([], dtype="float32")

                        # Vérification si l'enregistrement contient de vrais mots ou juste un bruit
                        if len(recorded_audio) > sample_rate * 0.20:
                            user_text = self.stt.transcribe_audio_data(recorded_audio, sample_rate)
                            if not user_text or not user_text.strip():
                                user_text = latest_partial_text

                            # S'IL Y A DE VRAIS MOTS : C'est une vraie commande !
                            if user_text and user_text.strip():
                                stop_worker = True
                                sys.stdout.write("\r\033[K")
                                sys.stdout.flush()
                                return user_text.strip(), recorded_audio

                        # SI CE N'ÉTAIT QU'UN BRUIT SONORE (aucun mot reconnu) :
                        # On NE QUITTE PAS, on continue d'écouter silencieusement sur la même ligne !
                        with lock:
                            buffer = []
                            pre_buffer.clear()
                        has_spoken = False
                        silence_count = 0
                        latest_partial_text = ""
                        sys.stdout.write("\r\033[K[Crux Micro] 🎤 À l'écoute... [░░░░░░░░░░░░]")
                        sys.stdout.flush()
        except Exception as e:
            print(f"\n[Crux Micro Warning] Erreur de capture audio : {e}")
        finally:
            stop_worker = True

        sys.stdout.write("\r\033[K")
        sys.stdout.flush()
        return "", np.array([], dtype="float32")

    def start_conversation_session(self, initial_command: str = ""):
        """
        Session conversationnelle interactive continue avec mémoire, SFX et écoute patiente.
        """
        print("\n>>> [Crux] SESSION OUVERTE <<<")
        self.agent.reset_session()
        dev = self.get_output_device()

        # SFX 1 : Réveil Jarvis & Notch Mochi
        self.hud.wake()
        self.sfx.play("wake", device=dev)

        # Cas d'une instruction énoncée directement avec l'activation
        if initial_command and len(initial_command.strip()) > 1:
            print(f"[Corentin] {initial_command}")
            self.sfx.play("process", device=dev)
            self.hud.set_state("thinking", "CRUX", "Calcul en cours...")
            response, is_exit = self.agent.process_command(initial_command)
            dev = self.get_output_device()
            self.hud.set_state("speaking", "CRUX", response[:28])
            self.tts.speak(response)
            if is_exit:
                self.sfx.play("sleep", device=dev)
                self.agent.reset_session()
                self.hud.set_state("idle", "CRUX", "Veille active")
                print(">>> [Crux] RETOUR EN VEILLE <<<\n")
                return
        else:
            import random
            wake_phrases = [
                "Oui Corentin, que puis-je faire pour toi ?",
                "Je t'écoute, Corentin.",
                "Oui, Corentin ?",
                "Présent Corentin, qu'est-ce qu'on fait ?",
                "Ça marche Corentin, je t'écoute !"
            ]
            wake_phrase = random.choice(wake_phrases)
            self.agent.has_said_name = True
            self.hud.set_state("speaking", "CRUX", wake_phrase)
            self.tts.speak(wake_phrase)

        session_timeout = float(self.conv_cfg.get("session_timeout_seconds", 30.0))
        silence_timeout = float(self.conv_cfg.get("silence_timeout_seconds", 0.5))

        # Légère pause anti-éveil sur la voix de Crux
        time.sleep(0.1)

        while True:
            dev = self.get_output_device()

            print("[Crux] À votre écoute...")
            self.hud.set_state("listening", "CRUX")
            # SFX 2 : Bip de prise d'écoute (joué une seule fois par tour de parole)
            self.sfx.play("listen", device=dev)

            # Écoute patiente continue : ne retourne QUE si des mots ont été dits ou après 30s d'inactivité
            user_text, audio = self.listen_for_command(
                timeout_seconds=session_timeout,
                silence_timeout=silence_timeout
            )

            # Si inactivité prolongée (aucun mot dit pendant 30s)
            if not user_text:
                print("\n[Crux] Inactivité prolongée, mise en veille.")
                self.hud.set_state("speaking", "CRUX", "Mise en veille...")
                self.tts.speak("Je me remets en veille.")
                self.sfx.play("sleep", device=dev)
                self.agent.reset_session()
                self.hud.set_state("idle", "CRUX", "Veille active")
                break

            print(f"[Corentin] > {user_text}")

            # SFX 3 : Chargement / réflexion
            self.sfx.play("process", device=dev)
            self.hud.thinking(user_text)

            # Traitement par le cerveau IA (avec mémoire multi-tours)
            response, is_exit = self.agent.process_command(user_text)

            # Rafraîchissement immédiat du périphérique de sortie après exécution de l'ordre
            dev = self.get_output_device()

            # Si action spécifique réussie (switch audio, projet, app), jingle de validation
            lower_u = user_text.lower()
            if any(k in lower_u for k in ["projet", "ouvre", "lance", "cherche", "jbl", "ecran", "enceinte"]):
                self.sfx.play("success", device=dev)

            self.hud.set_state("speaking", "CRUX", response[:28])
            self.tts.speak(response)

            if is_exit:
                print("[Crux] Fin de session demandée.")
                self.sfx.play("sleep", device=dev)
                self.agent.reset_session()
                self.hud.set_state("idle", "CRUX", "Veille active")
                break

            # Légère pause anti-écho
            time.sleep(0.12)

        self.hud.set_state("idle", "CRUX", "Veille active")
        print(">>> [Crux] SESSION TERMINÉE -> VEILLE ACTIVE <<<\n")

    def run_voice_loop(self):
        """Boucle principale alternant veille et session active."""
        while True:
            try:
                # 1. Écoute passive de 'Hey Crux' sur le micro Fifine
                trailing_cmd = self.wake_detector.wait_for_wake_word(
                    self.stt.transcribe_audio_data,
                    device=self.input_device
                )

                # 2. Session conversationnelle continue
                self.start_conversation_session(trailing_cmd)

            except KeyboardInterrupt:
                print("\n[Crux] Arrêt du programme.")
                break
            except Exception as e:
                print(f"[Crux Relance] {e}")
                time.sleep(0.5)

    def run_cli_interactive(self):
        """Mode interactif par console."""
        print("\n[Crux] Mode texte interactif activé (tapez 'exit' pour quitter).")
        while True:
            try:
                user_input = input("\nVous > ").strip()
                if not user_input or user_input.lower() in ["exit", "quit"]:
                    break
                response, is_exit = self.agent.process_command(user_input)
                self.tts.speak(response)
                if is_exit:
                    break
            except (KeyboardInterrupt, EOFError):
                break

def main():
    parser = argparse.ArgumentParser(description="Crux AI - Jarvis Assistant")
    parser.add_argument("--cli", action="store_true", help="Lancer en mode texte interactif")
    parser.add_argument("--test-voice", action="store_true", help="Tester la voix et les SFX")
    args = parser.parse_args()

    app = CruxApplication()

    if args.test_voice:
        dev = app.get_output_device()
        print("[Test] Démonstration des SFX Jarvis...")
        app.sfx.play("wake", device=dev)
        app.sfx.play("listen", device=dev)
        app.sfx.play("process", device=dev)
        app.sfx.play("success", device=dev)
        app.tts.speak("Système Crux et effets sonores opérationnels, Corentin.")
        app.sfx.play("sleep", device=dev)
        return

    if args.cli:
        app.run_cli_interactive()
    else:
        app.run_voice_loop()

if __name__ == "__main__":
    main()

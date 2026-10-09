import unittest
from unittest.mock import MagicMock, patch
from core.agent import CruxAgent

class TestExtendedJarvisFeatures(unittest.TestCase):
    def setUp(self):
        self.agent = CruxAgent(api_key="TEST_MOCK_KEY", model_name="gemini-3.8-flash")
        self.agent.reset_session()

    def test_clipboard_read_and_write_voice_commands(self):
        """Vérifie le pilotage vocal du presse-papier sans manipulation de souris."""
        with patch.object(self.agent.computer_use, 'clipboard_set', return_value=True) as mock_set:
            resp, _ = self.agent.process_command("Crux copie dans le presse-papier : Mon Super Texte")
            self.assertIn("copié", resp.lower())
            mock_set.assert_called_once_with("Mon Super Texte")

        with patch.object(self.agent.computer_use, 'clipboard_get', return_value="Mon Super Texte") as mock_get:
            resp_read, _ = self.agent.process_command("Crux lis le presse-papier")
            self.assertIn("Mon Super Texte", resp_read)
            mock_get.assert_called_once()

    def test_top_processes_telemetry_voice_command(self):
        """Vérifie la synthèse vocale des processus les plus consommateurs."""
        with patch.object(self.agent.computer_use.telemetry, 'format_top_processes_summary', return_value="Discord.exe (1000 Mo), Chrome.exe (500 Mo).") as mock_top:
            resp, _ = self.agent.process_command("Crux quels sont les processus gourmands en mémoire ?")
            self.assertIn("Discord.exe", resp)
            mock_top.assert_called_once_with(sort_by="ram", limit=5)

    def test_kill_process_guardrail_confirmation_flow(self):
        """Vérifie que l'arrêt d'un processus requiert une confirmation de sécurité explicite."""
        # Demande critique
        resp_ask, _ = self.agent.process_command("Crux tue le processus discord.exe")
        self.assertIn("certain de vouloir arrêter", resp_ask)
        self.assertTrue(self.agent.computer_use.has_pending_confirmation())

        # Confirmation acceptée
        with patch.object(self.agent.computer_use, 'kill_process', return_value=(True, "Processus discord.exe arrêté avec succès.")) as mock_kill:
            resp_conf, _ = self.agent.process_command("Oui fais-le confirme")
            self.assertIn("arrêté", resp_conf)
            mock_kill.assert_called_once_with("discord.exe", force=False)
            self.assertFalse(self.agent.computer_use.has_pending_confirmation())

    def test_command_execution_safe_vs_dangerous(self):
        """Vérifie l'exécution directe pour commande sûre et le garde-fou pour commande destructive."""
        # Commande sûre
        with patch.object(self.agent.computer_use, 'execute_command', return_value={"success": True, "stdout": "Test Output", "stderr": ""}):
            resp_safe, _ = self.agent.process_command("Crux exécute la commande Get-Date")
            self.assertIn("Test Output", resp_safe)
            self.assertFalse(self.agent.computer_use.has_pending_confirmation())

        # Commande sensible (Format C:)
        resp_dang, _ = self.agent.process_command("Crux exécute la commande format c:")
        self.assertIn("sensible", resp_dang)
        self.assertTrue(self.agent.computer_use.has_pending_confirmation())

        # Annulation
        resp_cancel, _ = self.agent.process_command("Non annule")
        self.assertIn("annulée", resp_cancel)
        self.assertFalse(self.agent.computer_use.has_pending_confirmation())

    def test_wasapi_audio_sessions_listing(self):
        """Vérifie la détection et la liste des applications émettant du son via WASAPI."""
        fake_sessions = [
            {"process": "Spotify.exe", "volume_percent": 80, "is_muted": False},
            {"process": "Discord.exe", "volume_percent": 100, "is_muted": False}
        ]
        with patch.object(self.agent.sys, 'list_audio_sessions', return_value=fake_sessions):
            resp, _ = self.agent.process_command("Crux quelles applications ont du son ?")
            self.assertIn("Spotify.exe", resp)
            self.assertIn("Discord.exe", resp)

    def test_per_monitor_brightness_command(self):
        """Vérifie le réglage de luminosité ciblé sur un moniteur spécifique (ViewSonic ou PL2766H)."""
        with patch.object(self.agent.sys, 'set_brightness', return_value="Luminosité de ViewSonic réglée à 70 %.") as mock_bright:
            resp, _ = self.agent.process_command("Crux règle la luminosité de l'écran ViewSonic à 70%")
            self.assertIn("ViewSonic", resp)
            mock_bright.assert_called_once_with(70, display="ViewSonic")

    def test_golden_rule_preserved_across_new_commands(self):
        """Vérifie que la règle d'or (Corentin dit 1 seule fois) reste 100% respectée sur les nouvelles fonctionnalités."""
        # Accueil : doit contenir Corentin
        r1, _ = self.agent.process_command("Salut")
        self.assertIn("Corentin", r1)
        self.assertTrue(self.agent.has_said_name)

        # Commande presse-papier suivante : NE DOIT PAS contenir Corentin
        with patch.object(self.agent.computer_use, 'clipboard_get', return_value="abc"):
            r2, _ = self.agent.process_command("Lis le presse-papier")
            self.assertNotIn("Corentin", r2)

        # Commande télémétrie : NE DOIT PAS contenir Corentin
        r3, _ = self.agent.process_command("Télémétrie complète")
        self.assertNotIn("Corentin", r3)

    def test_coucou_client_methods(self):
        """Vérifie que CoucouClient dispose des méthodes d'enrichissement dynamique."""
        hud = self.agent.hud
        self.assertTrue(hasattr(hud, 'send_pill'))
        self.assertTrue(hasattr(hud, 'send_card'))
        self.assertTrue(hasattr(hud, 'sync_telemetry'))
        self.assertTrue(hasattr(hud, 'sync_spotify_status'))
        self.assertTrue(hasattr(hud, 'set_mochi_emotion'))

    def test_spotify_now_playing_voice_command(self):
        """Vérifie l'interrogation vocale de la musique en cours sur Spotify CLI."""
        mock_summary = (True, "Sur Spotify : Bohemian Rhapsody par Queen (en cours de lecture).", {
            "title": "Bohemian Rhapsody", "artist": "Queen", "is_playing": True
        })
        with patch.object(self.agent.sys, 'get_spotify_now_playing_summary', return_value=mock_summary) as mock_np:
            resp, _ = self.agent.process_command("Crux quel est le morceau en cours sur Spotify ?")
            self.assertIn("Bohemian Rhapsody", resp)
            self.assertIn("Queen", resp)
            mock_np.assert_called_once()

    def test_telemetry_coucou_hud_sync(self):
        """Vérifie que la télémétrie vocale synchronise la Notch Coucou avec pills et cartes."""
        fake_telem = {
            "cpu": {"percent": 15.2, "per_core": [15.2], "cores_logical": 8, "cores_physical": 4, "frequency_mhz": 3200},
            "memory": {"total_gb": 32.0, "used_gb": 12.0, "available_gb": 20.0, "percent": 37.5},
            "disks": [{"mountpoint": "C:\\", "free_gb": 250.0, "total_gb": 500.0, "percent": 50.0, "device": "C:", "fstype": "NTFS"}],
            "battery": None,
            "network": {"bytes_sent_mb": 10.0, "bytes_recv_mb": 20.0},
            "uptime_seconds": 3600,
            "uptime_formatted": "1 heure"
        }
        with patch.object(self.agent.computer_use.telemetry, 'get_system_telemetry', return_value=fake_telem), \
             patch.object(self.agent.hud, 'sync_telemetry') as mock_sync, \
             patch.object(self.agent.hud, 'send_card') as mock_card:
            resp, _ = self.agent.process_command("Crux bilan télémétrie complète")
            self.assertIn("Processeur", resp)
            mock_sync.assert_called_once()
            mock_card.assert_called_once()

    def test_master_volume_voice_command(self):
        """Vérifie le réglage du volume principal master via WASAPI."""
        with patch.object(self.agent.sys, 'set_master_volume', return_value="Volume principal réglé à 50 %.") as mock_vol:
            resp, _ = self.agent.process_command("Crux mets le volume principal à 50%")
            self.assertIn("Volume principal", resp)
            mock_vol.assert_called_once_with(50)

    def test_maximize_window_voice_command(self):
        """Vérifie la commande vocale de maximisation de fenêtre."""
        with patch.object(self.agent.computer_use, 'maximize_window', return_value=True) as mock_max:
            resp, _ = self.agent.process_command("Crux maximise la fenêtre de chrome")
            self.assertIn("maximisée", resp)
            mock_max.assert_called_once_with("chrome")

    def test_code_interpreter_dangerous_patterns_expanded(self):
        """Vérifie que les patterns destructeurs (shutil.rmtree, os.remove, rd /s) sont interceptés."""
        engine = self.agent.computer_use.code_engine
        is_dang1, _ = engine.is_dangerous("shutil.rmtree('C:/data')")
        self.assertTrue(is_dang1)
        is_dang2, _ = engine.is_dangerous("rd /s /q C:\\Users")
        self.assertTrue(is_dang2)
        is_dang3, _ = engine.is_dangerous("os.remove('important.dat')")
        self.assertTrue(is_dang3)
        is_safe, _ = engine.is_dangerous("Get-ChildItem")
        self.assertFalse(is_safe)

    def test_set_brightness_index_and_invalid_display(self):
        """Vérifie la sélection de moniteur par index et l'avertissement si inconnu."""
        with patch('screen_brightness_control.list_monitors', return_value=['ViewSonic Generic Monitor', 'Iiyama Generic Monitor']), \
             patch('screen_brightness_control.set_brightness') as mock_sbc:
            # Index 1 (premier écran)
            resp1 = self.agent.sys.set_brightness(80, display="1")
            self.assertIn("ViewSonic", resp1)

            # Écran inconnu
            resp_unk = self.agent.sys.set_brightness(50, display="EcranInconnu")
            self.assertIn("introuvable", resp_unk)

if __name__ == "__main__":
    unittest.main()

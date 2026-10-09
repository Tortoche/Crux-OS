import unittest
from unittest.mock import MagicMock, patch
from core.agent import CruxAgent

class TestCruxAgentIntegration(unittest.TestCase):
    def setUp(self):
        # Initialisation de l'agent sans appels réseau externes
        self.agent = CruxAgent(api_key="TEST_MOCK_KEY", model_name="gemini-3.5-flash-lite")
        self.agent.reset_session()

    def test_golden_rule_name_spoken_once_only(self):
        """
        RÈGLE D'OR STRICTE : Le prénom 'Corentin' ne doit être dit
        QU'AU TOUT PREMIER message d'accueil de la session.
        Dans ABSOLUMENT TOUS les échanges suivants, il ne doit JAMAIS être répété !
        """
        # Tour 1 : Salutation
        resp1, exit1 = self.agent.process_command("Salut")
        self.assertFalse(exit1)
        self.assertIn("Corentin", resp1)
        self.assertTrue(self.agent.has_said_name)

        # Tour 2 : Question suivante (le prénom ne doit PLUS être présent)
        resp2, exit2 = self.agent.process_command("Comment vas-tu ?")
        self.assertFalse(exit2)
        self.assertNotIn("Corentin", resp2)

        # Tour 3 : Autre question
        resp3, exit3 = self.agent.process_command("Quelle heure est-il ?")
        self.assertFalse(exit3)
        self.assertNotIn("Corentin", resp3)

        # Tour 4 : Bascule audio (vérifier que le prénom n'est toujours pas répété)
        resp4, _ = self.agent.process_command("Mets le son sur mon enceinte JBL")
        self.assertNotIn("Corentin", resp4)
        self.assertIn("JBL", resp4)

    def test_audio_device_routing_commands(self):
        """Vérifie le basculement vers JBL, écran PL2766H, casque et piste par défaut."""
        resp_jbl, _ = self.agent.process_command("Mets le son sur mon enceinte JBL")
        self.assertIn("JBL", resp_jbl)

        resp_screen, _ = self.agent.process_command("Bascule l'audio sur l'écran")
        self.assertIn("écran", resp_screen.lower())

        resp_headset, _ = self.agent.process_command("Passe le son sur mon casque")
        self.assertIn("casque", resp_headset.lower())

        resp_def, _ = self.agent.process_command("Remets l'audio de base par défaut")
        self.assertIn("piste de base", resp_def.lower())

    def test_computer_use_script_execution_flow(self):
        """Vérifie le garde-fou pour l'exécution d'un script externe."""
        resp, _ = self.agent.process_command("Crux exécute le script test_deploy.py")
        self.assertIn("certain de vouloir exécuter", resp)
        self.assertTrue(self.agent.computer_use.has_pending_confirmation())

        # Annulation
        resp_c, _ = self.agent.process_command("Non annule")
        self.assertIn("annulée", resp_c)
        self.assertFalse(self.agent.computer_use.has_pending_confirmation())

    def test_computer_use_guardrail_confirmation_flow(self):
        """
        Vérifie le garde-fou : la fermeture d'application requiert
        une confirmation explicite avant d'être exécutée.
        """
        # 1. Ordre de fermeture critique
        resp_ask, _ = self.agent.process_command("Crux ferme la fenêtre de Chrome")
        self.assertIn("certain de vouloir fermer", resp_ask)
        self.assertTrue(self.agent.computer_use.has_pending_confirmation())

        # 2. Confirmation acceptée
        with patch.object(self.agent.computer_use, 'close_window', return_value=True):
            resp_confirmed, _ = self.agent.process_command("Oui vas-y confirme")
            self.assertIn("fermée", resp_confirmed)
            self.assertFalse(self.agent.computer_use.has_pending_confirmation())

        # 3. Test de rejet / annulation
        self.agent.process_command("Ferme l'application Bloc-notes")
        self.assertTrue(self.agent.computer_use.has_pending_confirmation())
        resp_cancel, _ = self.agent.process_command("Non annule")
        self.assertIn("annulée", resp_cancel)
        self.assertFalse(self.agent.computer_use.has_pending_confirmation())

    def test_iot_lighting_plugin_integration(self):
        """Vérifie que les commandes de lumières sont interceptées par le plugin IoT."""
        resp_on, _ = self.agent.process_command("Crux allume la lumière du bureau")
        self.assertIn("allumée", resp_on)

        resp_dim, _ = self.agent.process_command("Tamise la lumière")
        self.assertIn("tamisée", resp_dim)

        resp_off, _ = self.agent.process_command("Éteins la lumière")
        self.assertIn("éteinte", resp_off)

    def test_screen_vision_trigger(self):
        """Vérifie que la vision d'écran est déclenchée STRICTEMENT sur les mots-clés dédiés."""
        with patch.object(self.agent, '_query_screen_vision', return_value="Je vois votre éditeur de code.") as mock_vision:
            resp, is_exit = self.agent.process_command("Crux regarde mon écran et dis-moi ce que tu vois")
            self.assertFalse(is_exit)
            mock_vision.assert_called_once()
            self.assertEqual(resp, "Je vois votre éditeur de code.")

    def test_memory_turn_recording(self):
        """Vérifie que chaque échange est convenablement injecté dans la mémoire 5D."""
        self.agent.process_command("Quel temps fait-il ?")
        recent_turns = self.agent.memory.episodic.get_recent(2)
        self.assertGreaterEqual(len(recent_turns), 1)

    def test_session_exit(self):
        """Vérifie la mise en veille propre sur demande."""
        resp, is_exit = self.agent.process_command("Merci Crux, mets-toi en veille")
        self.assertTrue(is_exit)
        self.assertIn("veille", resp.lower())

    def test_spotify_playlist_instant_playback_trigger(self):
        """Vérifie que la demande de playlist Spotify s'exécute instantanément et déclenche play_music."""
        import time
        with patch.object(self.agent.sys, 'play_music', return_value="Lancement de 'playlist' sur Spotify.") as mock_play:
            t0 = time.time()
            resp, is_exit = self.agent.process_command("Crux lance une playlist sur Spotify")
            elapsed = time.time() - t0
            self.assertFalse(is_exit)
            self.assertIn("Spotify", resp)
            self.assertLess(elapsed, 0.5, "L'interaction doit être quasi-instantanée (< 500ms)")
            mock_play.assert_called_once_with("playlist", platform="spotify")

    def test_spotify_specific_playlist_parsing(self):
        """Vérifie que 'mets la playlist jazz sur spotify' extrait 'playlist jazz'."""
        with patch.object(self.agent.sys, 'play_music', return_value="Lancement de 'playlist jazz' sur Spotify.") as mock_play:
            resp, _ = self.agent.process_command("Crux mets la playlist jazz sur Spotify")
            self.assertIn("Spotify", resp)
            mock_play.assert_called_once_with("playlist jazz", platform="spotify")

    def test_generic_mets_une_musique_searches_hits_instead_of_resume(self):
        """Vérifie que 'mets une musique' lance une recherche de nouveautés et ne relance pas l'ancien morceau."""
        parsed = self.agent._parse_music_command("Crux mets une musique")
        self.assertEqual(parsed['action'], 'play_query')
        self.assertEqual(parsed['query'], 'Hits du moment')

    def test_explicit_reprends_la_musique_triggers_resume(self):
        """Vérifie que 'reprends la musique' déclenche une reprise et non une recherche."""
        parsed = self.agent._parse_music_command("Crux reprends la musique")
        self.assertEqual(parsed['action'], 'resume')

    def test_spotify_system_autoplay_thread_launch(self):
        """Vérifie que SystemController.play_music déclenche l'automatisation de lecture immédiate."""
        with patch.object(self.agent.sys, '_trigger_spotify_playback') as mock_trigger, \
             patch('webbrowser.open') as mock_open:
            res = self.agent.sys.play_music("playlist lofi", platform="spotify")
            self.assertIn("lofi", res)
            mock_open.assert_called_once()
            mock_trigger.assert_called_once()

    def test_native_antigravity_session_reuse(self):
        """Vérifie que le moteur Antigravity natif réutilise le conversationId au lieu de recréer à chaque fois."""
        mock_res_new = MagicMock()
        mock_res_new.returncode = 0
        mock_res_new.stdout = '{"response": {"newConversation": {"conversationId": "cid-12345"}}}'

        mock_res_send = MagicMock()
        mock_res_send.returncode = 0
        mock_res_send.stdout = '{"response": {"sendMessage": {}}}'

        with patch('os.path.exists', return_value=True), \
             patch('subprocess.run', side_effect=[mock_res_new, mock_res_send]) as mock_subproc, \
             patch('time.sleep', return_value=None), \
             patch('builtins.open', unittest.mock.mock_open(read_data='{"step_index": 1, "type": "PLANNER_RESPONSE", "content": "Premier test"}\n{"step_index": 2, "type": "PLANNER_RESPONSE", "content": "Deuxieme test"}\n')):
            # Tour 1 : Doit appeler new-conversation
            r1 = self.agent._query_antigravity_native("Message 1")
            self.assertEqual(r1, "Premier test")
            self.assertEqual(self.agent._antigravity_cid, "cid-12345")
            first_cmd = mock_subproc.call_args_list[0][0][0]
            self.assertIn("new-conversation", first_cmd)
            self.assertIn("--model=flash_lite", first_cmd)

            # Tour 2 : Doit appeler send-message avec le même cid (réutilisation instantanée)
            r2 = self.agent._query_antigravity_native("Message 2")
            self.assertEqual(r2, "Deuxieme test")
            second_cmd = mock_subproc.call_args_list[1][0][0]
            self.assertIn("send-message", second_cmd)
            self.assertIn("cid-12345", second_cmd)

    def test_model_name_mapping_flash_lite(self):
        """Vérifie que Gemini 3.8 Flash est configuré avec succès comme modèle principal."""
        agent38 = CruxAgent(api_key="TEST", model_name="gemini-3.8-flash")
        self.assertEqual(agent38.model_name, "gemini-3.8-flash")
        self.assertIn("gemini-3.8-flash", agent38.fallback_models)

    def test_spotify_system_autoplay_multi_stage_execution(self):
        """Vérifie que l'automatisation Spotify s'exécute avec attachement de session et touches de navigation."""
        import time
        with patch('ctypes.windll.user32') as mock_u32, \
             patch('ctypes.windll.kernel32') as mock_k32:
            mock_u32.OpenWindowStationW.return_value = 1
            mock_u32.OpenDesktopW.return_value = 2
            mock_u32.IsWindowVisible.return_value = True
            mock_u32.GetWindowThreadProcessId.return_value = 100
            mock_k32.GetCurrentThreadId.return_value = 200

            def fake_get_class(hwnd, buf, maxlen):
                buf.value = 'Chrome_WidgetWin_1'
                return len(buf.value)

            def fake_get_title(hwnd, buf, maxlen):
                buf.value = 'Spotify Free'
                return len(buf.value)

            mock_u32.GetClassNameW.side_effect = fake_get_class
            mock_u32.GetWindowTextW.side_effect = fake_get_title

            def fake_enum(h_desk, cb, lparam):
                cb(12345, 0)
                return True

            mock_u32.EnumDesktopWindows.side_effect = fake_enum

            # Lance le worker avec delay nul
            self.agent.sys._trigger_spotify_playback(delay=0.0)
            time.sleep(0.6)

            # Vérifie que les touches de validation ont bien été envoyées
            self.assertTrue(mock_u32.keybd_event.called or mock_u32.SendMessageW.called)

if __name__ == "__main__":
    unittest.main()

import os
import shutil
import tempfile
import unittest
from core.memory.facts_memory import FactsMemory
from core.memory.reflection_memory import ReflectionMemory
from core.memory.manager import (
    WorkingMemory,
    EpisodicMemory,
    ArchivalMemory,
    MemoryManager
)

class Test5DMemory(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_facts.db")
        self.refl_path = os.path.join(self.test_dir, "test_reflections.json")
        self.arch_path = os.path.join(self.test_dir, "test_archive.jsonl")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_facts_memory_crud_and_seed(self):
        facts_mem = FactsMemory(db_path=self.db_path)
        all_facts = facts_mem.get_all_facts()
        self.assertGreaterEqual(len(all_facts), 5)

        # Vérification des faits initiaux
        user_fact = facts_mem.get_fact("user_name")
        self.assertIsNotNone(user_fact)
        self.assertEqual(user_fact["value"], "Corentin")

        # Ajout et mise à jour
        ok = facts_mem.add_fact("preferences", "favorite_editor", "VS Code", confidence=0.95)
        self.assertTrue(ok)
        fact = facts_mem.get_fact("favorite_editor")
        self.assertEqual(fact["value"], "VS Code")

        # Recherche plein texte
        matches = facts_mem.search_facts("editor")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["key"], "favorite_editor")

        # Suppression
        del_ok = facts_mem.delete_fact("favorite_editor")
        self.assertTrue(del_ok)
        self.assertIsNone(facts_mem.get_fact("favorite_editor"))

    def test_reflection_memory(self):
        refl_mem = ReflectionMemory(file_path=self.refl_path)
        item = refl_mem.record_reflection("audio", "L'utilisateur écoute sur l'enceinte JBL.")
        self.assertEqual(item["topic"], "audio")
        self.assertEqual(item["occurrence_count"], 1)

        # Renforcement de l'insight
        updated = refl_mem.record_reflection("audio", "L'utilisateur écoute sur l'enceinte JBL.")
        self.assertEqual(updated["occurrence_count"], 2)

        relevant = refl_mem.get_relevant_reflections("audio", limit=2)
        self.assertTrue(any(r["topic"] == "audio" for r in relevant))

        summary = refl_mem.summarize_reflections()
        self.assertIn("audio", summary)

    def test_working_and_episodic_memory(self):
        wm = WorkingMemory()
        wm.set("active_project", "zenix")
        self.assertEqual(wm.get("active_project"), "zenix")

        wm.set("pending_confirmation", {"action": "delete"})
        self.assertIsNotNone(wm.get("pending_confirmation"))
        wm.clear_confirmation()
        self.assertIsNone(wm.get("pending_confirmation"))

        em = EpisodicMemory(max_turns=3)
        em.add_turn("user", "Hello")
        em.add_turn("model", "Bonjour")
        em.add_turn("user", "Comment vas-tu ?")
        em.add_turn("model", "Bien.")
        # Doit être borné à max_turns
        self.assertEqual(len(em.turns), 3)
        self.assertEqual(em.turns[-1]["text"], "Bien.")

    def test_facts_natural_language_semantic_search(self):
        facts_mem = FactsMemory(db_path=self.db_path)
        # Requête naturelle processeur
        res_cpu = facts_mem.search_facts("Quel est mon processeur ?")
        self.assertGreaterEqual(len(res_cpu), 1)
        self.assertEqual(res_cpu[0]["key"], "cpu")

        # Requête naturelle carte graphique
        res_gpu = facts_mem.search_facts("Quelle est ma carte graphique ?")
        self.assertGreaterEqual(len(res_gpu), 1)
        self.assertEqual(res_gpu[0]["key"], "gpu")

        # Requête naturelle écran
        res_screen = facts_mem.search_facts("Quel est mon écran ?")
        self.assertGreaterEqual(len(res_screen), 1)
        self.assertEqual(res_screen[0]["key"], "screen")

    def test_memory_manager_context_building(self):
        mm = MemoryManager(data_dir=self.test_dir)
        mm.working.set("active_project", "zenix_ai")
        mm.record_turn("user", "Active la musique.")
        mm.record_turn("model", "Musique lancée.")

        ctx = mm.build_prompt_context("musique")
        self.assertIn("zenix_ai", ctx)
        self.assertIn("Historique récent", ctx)

if __name__ == "__main__":
    unittest.main()

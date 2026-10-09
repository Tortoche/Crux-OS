import os
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from core.memory.facts_memory import FactsMemory
from core.memory.reflection_memory import ReflectionMemory

class WorkingMemory:
    """Dimension 1 : Mémoire de travail active (état immédiat, fenêtre, tâche en cours, confirmation en attente)."""
    def __init__(self):
        self.state: Dict[str, Any] = {
            "active_project": None,
            "active_window": "",
            "last_action": None,
            "pending_confirmation": None,
            "system_mode": "normal",
        }

    def set(self, key: str, value: Any):
        self.state[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.state.get(key, default)

    def clear_confirmation(self):
        self.state["pending_confirmation"] = None

class EpisodicMemory:
    """Dimension 2 : Mémoire épisodique (dialogue multi-tours de la session active)."""
    def __init__(self, max_turns: int = 12):
        self.max_turns = max_turns
        self.turns: List[Dict[str, Any]] = []

    def add_turn(self, role: str, text: str):
        self.turns.append({
            "role": role,
            "text": text,
            "timestamp": time.time(),
            "time_str": datetime.now().strftime("%H:%M:%S")
        })
        if len(self.turns) > self.max_turns:
            self.turns = self.turns[-self.max_turns:]

    def get_recent(self, n: int = 6) -> List[Dict[str, Any]]:
        return self.turns[-n:]

    def clear(self):
        self.turns.clear()

class ArchivalMemory:
    """Dimension 5 : Mémoire archivale / long-terme (persistance des échanges et traces de session)."""
    def __init__(self, file_path: Optional[str] = None):
        if file_path is None:
            data_dir = Path(__file__).parent.parent.parent / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            self.file_path = str(data_dir / "archival_history.jsonl")
        else:
            self.file_path = file_path
            Path(self.file_path).parent.mkdir(parents=True, exist_ok=True)

    def archive_entry(self, entry: Dict[str, Any]):
        try:
            with open(self.file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def search_archive(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        if not os.path.exists(self.file_path):
            return []
        matches = []
        q = query.lower()
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    row = json.loads(line)
                    if q in row.get("text", "").lower():
                        matches.append(row)
        except Exception:
            pass
        return matches[-limit:]

class MemoryManager:
    """
    Chef d'orchestre unifié de la Mémoire 5D :
    - D1 : WorkingMemory (contexte immédiat / projet / confirmation)
    - D2 : EpisodicMemory (session active en mémoire vive)
    - D3 : FactsMemory (SQLite data/facts.db - faits immuables)
    - D4 : ReflectionMemory (data/reflections.json - habitudes et apprentissages)
    - D5 : ArchivalMemory (data/archival_history.jsonl - persistance historique)
    """
    def __init__(self, data_dir: Optional[str] = None):
        if data_dir:
            db_path = str(Path(data_dir) / "facts.db")
            refl_path = str(Path(data_dir) / "reflections.json")
            arch_path = str(Path(data_dir) / "archival_history.jsonl")
        else:
            db_path = None
            refl_path = None
            arch_path = None

        self.working = WorkingMemory()
        self.episodic = EpisodicMemory()
        self.facts = FactsMemory(db_path=db_path)
        self.reflection = ReflectionMemory(file_path=refl_path)
        self.archival = ArchivalMemory(file_path=arch_path)

    def record_turn(self, role: str, text: str):
        """Enregistre un tour de parole dans l'épisodique et l'archive."""
        self.episodic.add_turn(role, text)
        self.archival.archive_entry({
            "timestamp": datetime.now().isoformat(),
            "role": role,
            "text": text,
            "project": self.working.get("active_project")
        })

    def reset_session(self):
        """Réinitialise la mémoire vive lors de la mise en veille."""
        self.episodic.clear()
        self.working.clear_confirmation()

    def build_prompt_context(self, user_query: str = "") -> str:
        """
        Construit un bloc de contexte hyper-optimisé (< 200 tokens)
        pour injecter dans Antigravity sans dégrader la latence.
        """
        lines = []

        # 1. Contexte actif
        active_proj = self.working.get("active_project")
        if active_proj:
            lines.append(f"[Projet actif: {active_proj}]")

        # 2. Faits clés pertinents
        if user_query:
            relevant_facts = self.facts.search_facts(user_query)
        else:
            relevant_facts = []

        if not relevant_facts:
            # Faits de base fondamentaux
            f_user = self.facts.get_fact("user_name")
            f_persona = self.facts.get_fact("persona")
            facts_summary = []
            if f_user:
                facts_summary.append(f"Utilisateur: {f_user['value']}")
            if f_persona:
                facts_summary.append(f"Style: {f_persona['value']}")
            if facts_summary:
                lines.append(f"[Profil: {', '.join(facts_summary)}]")
        else:
            facts_txt = "; ".join(f"{f['key']}={f['value']}" for f in relevant_facts[:3])
            lines.append(f"[Faits mémorisés: {facts_txt}]")

        # 3. Réflexions pertinentes
        reflections = self.reflection.get_relevant_reflections(user_query, limit=2)
        if reflections:
            refl_txt = " | ".join(r["insight"] for r in reflections)
            lines.append(f"[Apprentissages: {refl_txt}]")

        # 4. Épisodique récent
        recent_turns = self.episodic.get_recent(n=4)
        if recent_turns:
            dialogue = " | ".join(f"{'Corentin' if t['role'] == 'user' else 'Crux'}: {t['text']}" for t in recent_turns)
            lines.append(f"[Historique récent: {dialogue}]")

        return "\n".join(lines)

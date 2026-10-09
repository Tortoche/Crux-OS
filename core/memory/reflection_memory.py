import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

class ReflectionMemory:
    """
    Strate 4 (Réflexion & Apprentissages récurrents) de la mémoire 5D.
    Synthétise les apprentissages comportementaux, feedbacks et préférences émergentes.
    """
    def __init__(self, file_path: Optional[str] = None):
        if file_path is None:
            data_dir = Path(__file__).parent.parent.parent / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            self.file_path = str(data_dir / "reflections.json")
        else:
            self.file_path = file_path
            Path(self.file_path).parent.mkdir(parents=True, exist_ok=True)

        self._reflections: List[Dict[str, Any]] = []
        self._load()

    def _load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self._reflections = data
                    else:
                        self._reflections = []
            except Exception:
                self._reflections = []
        else:
            # Réflexions initiales de base
            self._reflections = [
                {
                    "id": "refl_1",
                    "topic": "voice_style",
                    "insight": "Corentin préfère les réponses directes en une seule phrase sans fioritures ni salutations superflues.",
                    "confidence": 1.0,
                    "occurrence_count": 1,
                    "last_observed": datetime.now().isoformat()
                },
                {
                    "id": "refl_2",
                    "topic": "audio_setup",
                    "insight": "Privilégier le son sur l'enceinte JBL quand elle est allumée, sinon écran PL2766H.",
                    "confidence": 1.0,
                    "occurrence_count": 1,
                    "last_observed": datetime.now().isoformat()
                }
            ]
            self._save()

    def _save(self):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self._reflections, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def record_reflection(self, topic: str, insight: str, confidence: float = 0.9) -> Dict[str, Any]:
        """Enregistre un nouvel enseignement ou incrémente un enseignement existant."""
        now = datetime.now().isoformat()
        topic_lower = topic.lower().strip()

        # Chercher si un insight similaire existe déjà pour le même topic
        for item in self._reflections:
            if item.get("topic", "").lower() == topic_lower:
                # Mise à jour
                item["insight"] = insight
                item["occurrence_count"] = item.get("occurrence_count", 1) + 1
                item["confidence"] = min(1.0, max(item.get("confidence", 0.8), confidence))
                item["last_observed"] = now
                self._save()
                return item

        # Nouvel item
        new_item = {
            "id": f"refl_{len(self._reflections) + 1}_{int(datetime.now().timestamp())}",
            "topic": topic,
            "insight": insight,
            "confidence": confidence,
            "occurrence_count": 1,
            "last_observed": now
        }
        self._reflections.append(new_item)
        self._save()
        return new_item

    def get_all_reflections(self) -> List[Dict[str, Any]]:
        return list(self._reflections)

    def get_relevant_reflections(self, query: Optional[str] = None, limit: int = 4) -> List[Dict[str, Any]]:
        """Retourne les réflexions les plus pertinentes pour un mot-clé ou en général."""
        if not query:
            # Tri par occurrences puis récence
            sorted_items = sorted(
                self._reflections,
                key=lambda x: (x.get("occurrence_count", 1), x.get("last_observed", "")),
                reverse=True
            )
            return sorted_items[:limit]

        query_lower = query.lower()
        scored = []
        for item in self._reflections:
            score = 0
            if item.get("topic", "").lower() in query_lower or query_lower in item.get("topic", "").lower():
                score += 3
            if any(word in item.get("insight", "").lower() for word in query_lower.split() if len(word) > 3):
                score += 1
            if score > 0:
                scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:limit]]

    def summarize_reflections(self) -> str:
        """Synthèse concise formatée pour injection dans le prompt."""
        if not self._reflections:
            return ""
        items = self.get_relevant_reflections(limit=3)
        return " | ".join(f"{it['topic']}: {it['insight']}" for it in items)

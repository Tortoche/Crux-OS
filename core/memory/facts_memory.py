import os
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

DEFAULT_FACTS = [
    {"category": "user", "key": "user_name", "value": "Corentin", "confidence": 1.0},
    {"category": "user", "key": "language", "value": "Français", "confidence": 1.0},
    {"category": "hardware", "key": "cpu", "value": "AMD Ryzen 7 7800X3D (8 cœurs, 16 threads)", "confidence": 1.0},
    {"category": "hardware", "key": "gpu", "value": "AMD Radeon RX 7800 XT (16 Go GDDR6)", "confidence": 1.0},
    {"category": "hardware", "key": "ram", "value": "32 Go DDR5", "confidence": 1.0},
    {"category": "hardware", "key": "screen", "value": "Iiyama G-Master PL2766H", "confidence": 1.0},
    {"category": "hardware", "key": "mic", "value": "Fifine USB Microphone", "confidence": 1.0},
    {"category": "audio", "key": "preferred_speakers", "value": "Enceinte JBL Bluetooth et Haut-parleurs Écran PL2766H", "confidence": 1.0},
    {"category": "style", "key": "persona", "value": "J.A.R.V.I.S. (précis, calme, direct, 1 phrase concise max)", "confidence": 1.0},
    {"category": "environment", "key": "projects_root", "value": r"C:\Users\coco\Documents", "confidence": 1.0},
    {"category": "ai", "key": "platform", "value": "Antigravity Google DeepMind (Gemini 3.8 Flash)", "confidence": 1.0},
]

class FactsMemory:
    """
    Strate 3 (Sémantique / Faits) de la mémoire 5D.
    Base de données SQLite locale stockant les connaissances immuables et préférences de Corentin.
    """
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            data_dir = Path(__file__).parent.parent.parent / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = str(data_dir / "facts.db")
        else:
            self.db_path = db_path
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT NOT NULL,
                    confidence REAL DEFAULT 1.0,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.commit()

            cursor.execute("SELECT COUNT(*) FROM facts")
            count = cursor.fetchone()[0]
            if count == 0:
                self._seed_default_facts(conn)
        finally:
            conn.close()

    def _seed_default_facts(self, conn: sqlite3.Connection):
        now = datetime.now().isoformat()
        cursor = conn.cursor()
        for fact in DEFAULT_FACTS:
            cursor.execute("""
                INSERT OR IGNORE INTO facts (category, key, value, confidence, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (fact["category"], fact["key"], fact["value"], fact["confidence"], now))
        conn.commit()

    def add_fact(self, category: str, key: str, value: str, confidence: float = 1.0) -> bool:
        """Ajoute ou met à jour un fait dans la mémoire immuable."""
        now = datetime.now().isoformat()
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO facts (category, key, value, confidence, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    category = excluded.category,
                    value = excluded.value,
                    confidence = excluded.confidence,
                    updated_at = excluded.updated_at
            """, (category, key, value, confidence, now))
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()

    def get_fact(self, key: str) -> Optional[Dict[str, Any]]:
        """Récupère un fait par sa clé."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT category, key, value, confidence, updated_at FROM facts WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        finally:
            conn.close()

    def get_facts_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Retourne tous les faits d'une catégorie."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT category, key, value, confidence, updated_at FROM facts WHERE category = ?", (category,))
            return [dict(r) for r in cursor.fetchall()]
        finally:
            conn.close()

    def get_all_facts(self) -> List[Dict[str, Any]]:
        """Retourne l'intégralité des faits enregistrés."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT category, key, value, confidence, updated_at FROM facts ORDER BY category, key")
            return [dict(r) for r in cursor.fetchall()]
        finally:
            conn.close()

    def search_facts(self, query: str) -> List[Dict[str, Any]]:
        """Recherche sémantique et par mots-clés/alias dans les faits."""
        if not query or not query.strip():
            return []

        import unicodedata
        import re

        def normalize(t: str) -> str:
            cleaned = unicodedata.normalize('NFD', t.lower())
            return ''.join(c for c in cleaned if unicodedata.category(c) != 'Mn')

        q_clean = normalize(query.strip())

        # Dictionnaire d'alias pour mapper les questions naturelles vers les clés de facts
        alias_map = {
            "processeur": "cpu",
            "proc": "cpu",
            "ryzen": "cpu",
            "carte graphique": "gpu",
            "graphique": "gpu",
            "carte video": "gpu",
            "radeon": "gpu",
            "ram": "ram",
            "memoire": "ram",
            "ecran": "screen",
            "moniteur": "screen",
            "iiyama": "screen",
            "micro": "mic",
            "microphone": "mic",
            "fifine": "mic",
            "enceinte": "preferred_speakers",
            "haut-parleur": "preferred_speakers",
            "jbl": "preferred_speakers",
            "audio": "preferred_speakers",
            "nom": "user_name",
            "prenom": "user_name",
            "utilisateur": "user_name",
            "langue": "language",
            "projet": "projects_root",
            "projets": "projects_root",
            "ia": "platform",
            "antigravity": "platform",
            "gemini": "platform",
            "style": "persona",
            "jarvis": "persona",
        }

        target_keys = set()
        for alias, fact_key in alias_map.items():
            if alias in q_clean:
                target_keys.add(fact_key)

        # Mots signifiants
        stop_words = {"quel", "quelle", "quels", "quelles", "est", "mon", "ma", "mes", "ton", "ta", "tes", "le", "la", "les", "un", "une", "des", "du", "de", "ce", "cette", "quoi", "combien", "qui", "pour", "dans", "sur", "ai-je", "ai"}
        tokens = [w for w in re.findall(r'[a-zA-Z0-9_\-]+', q_clean) if len(w) > 1 and w not in stop_words]

        all_facts = self.get_all_facts()
        scored_facts = []

        for f in all_facts:
            score = 0
            f_key = normalize(f["key"])
            f_val = normalize(f["value"])
            f_cat = normalize(f["category"])

            # 1. Alias direct
            if f["key"] in target_keys:
                score += 10

            # 2. Correspondance brute
            if q_clean in f_key or q_clean in f_val:
                score += 8

            # 3. Correspondance par token
            for t in tokens:
                if t in f_key:
                    score += 5
                elif t in f_val:
                    score += 3
                elif t in f_cat:
                    score += 2

            if score > 0:
                scored_facts.append((score, f))

        scored_facts.sort(key=lambda x: x[0], reverse=True)
        return [f for _, f in scored_facts]

    def delete_fact(self, key: str) -> bool:
        """Supprime un fait par sa clé."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM facts WHERE key = ?", (key,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

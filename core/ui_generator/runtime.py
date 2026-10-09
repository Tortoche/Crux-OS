"""
Crux OS - Dynamic UI Runtime Orchestrator
Gère le cycle de vie, la mise à jour incrémentale en direct et la communication
bidirectionnelle entre Crux Agent et l'hôte Electron de la notch Coucou.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, Callable, List
from core.coucou_client import CoucouClient
from core.ui_generator.generator import DynamicUIDesigner

logger = logging.getLogger("CruxDynamicUI")

class DynamicUIRuntime:
    """
    Chef d'orchestre de l'interface dynamique générative de Crux.
    Permet à Crux :
    1. D'afficher instantanément une interface sur-mesure dans la bulle Coucou
    2. De modifier des valeurs en temps réel sans rechargement
    3. D'ajouter ou supprimer des éléments à chaud
    4. De réagir aux actions de l'utilisateur (clics, checkboxes, formulaires)
    """

    _instance: Optional['DynamicUIRuntime'] = None

    @classmethod
    def get_instance(cls) -> 'DynamicUIRuntime':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, designer: Optional[DynamicUIDesigner] = None, hud: Optional[CoucouClient] = None):
        self.designer = designer or DynamicUIDesigner()
        self.hud = hud or CoucouClient.get_instance()
        self.active_view: Optional[Dict[str, Any]] = None
        self.action_handlers: Dict[str, Callable[[Any], None]] = {}
        self.tasks_store: List[Dict[str, Any]] = [
            {"id": "t1", "text": "Pousser le code Crux OS sur GitHub TortocheTV", "done": True, "tag": "Git"},
            {"id": "t2", "text": "Valider la suite de tests automatisés (76 tests)", "done": True, "tag": "Tests"},
            {"id": "t3", "text": "Tester le moteur d'interface dynamique à la volée", "done": False, "tag": "Coucou"},
            {"id": "t4", "text": "Vérifier le contrôle vocal et audio sur PL2766H", "done": False, "tag": "Audio"},
        ]

    def render_from_prompt(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Génère et affiche immédiatement l'interface demandée par l'utilisateur."""
        ctx = context or {}
        if "tasks" not in ctx:
            ctx["tasks"] = self.tasks_store

        view_data = self.designer.generate_html_from_prompt(prompt, ctx)
        self.active_view = view_data

        # Envoi de l'événement à la notch Coucou
        self.hud.send_event("dynamic_ui", {
            "action": "show",
            "id": view_data["id"],
            "title": view_data["title"],
            "html": view_data["html"],
            "width": view_data.get("width", 640),
            "height": view_data.get("height", 380),
            "type": view_data.get("type", "custom")
        })
        return view_data

    def update_content(self, html: str, target_selector: Optional[str] = None):
        """Met à jour une portion ou l'intégralité de l'interface active."""
        if not self.active_view:
            return
        self.hud.send_event("dynamic_ui", {
            "action": "update",
            "id": self.active_view.get("id"),
            "html": html,
            "target": target_selector
        })

    def append_task(self, text: str, tag: str = "Tâche") -> Dict[str, Any]:
        """Ajoute une activité en direct à la vue des tâches."""
        import uuid
        task_id = f"t_{uuid.uuid4().hex[:4]}"
        new_task = {"id": task_id, "text": text, "done": False, "tag": tag}
        self.tasks_store.append(new_task)

        # Si l'interface des tâches est ouverte, on la met à jour immédiatement
        if self.active_view and self.active_view.get("type") == "activities":
            self.render_from_prompt("affiche mes activités")
        return new_task

    def toggle_task(self, task_id: str) -> bool:
        """Inverse l'état d'une tâche."""
        for t in self.tasks_store:
            if t["id"] == task_id:
                t["done"] = not t.get("done", False)
                return t["done"]
        return False

    def delete_task(self, task_id: str) -> bool:
        """Supprime une tâche de la liste."""
        initial_len = len(self.tasks_store)
        self.tasks_store = [t for t in self.tasks_store if t["id"] != task_id]
        return len(self.tasks_store) < initial_len

    def close(self):
        """Ferme la bulle d'interface dynamique."""
        self.active_view = None
        self.hud.send_event("dynamic_ui", {
            "action": "hide"
        })

    def register_action_handler(self, action_name: str, handler: Callable[[Any], None]):
        """Enregistre une fonction de rappel déclenchée par un clic utilisateur."""
        self.action_handlers[action_name] = handler

    def handle_user_event(self, action: str, data: Any = None):
        """Reçoit une interaction envoyée depuis la bulle Coucou."""
        if action in self.action_handlers:
            self.action_handlers[action](data)
        elif action == "CLOSE":
            self.close()

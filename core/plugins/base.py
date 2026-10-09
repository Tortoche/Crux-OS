from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any

class BasePlugin(ABC):
    """
    SDK de base pour tous les plugins et extensions Crux AI.
    Définit le cycle de vie, les outils exposés aux agents, et le routage d'actions.
    """
    name: str = "base_plugin"
    version: str = "1.0.0"
    description: str = "Plugin de base"
    enabled: bool = True

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.is_initialized = False

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """Initialise les ressources du plugin (connexions, clés API, endpoints)."""
        if config:
            self.config.update(config)
        self.is_initialized = True
        return True

    def shutdown(self) -> bool:
        """Libère les ressources lors de la fermeture de Crux."""
        self.is_initialized = False
        return True

    @abstractmethod
    def get_tools(self) -> List[Dict[str, Any]]:
        """Retourne la liste des définitions d'outils exposés au LLM."""
        return []

    @abstractmethod
    def execute_action(self, action_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Exécute une action demandée par le cerveau de Crux."""
        return {"success": False, "message": f"Action '{action_name}' non implémentée"}

    def can_handle_command(self, user_text: str) -> bool:
        """Vérifie si le plugin peut traiter directement une intention vocale."""
        return False

    def handle_voice_command(self, user_text: str) -> Optional[Tuple[str, bool]]:
        """Traite directement une commande vocale et retourne (reponse, is_exit)."""
        return None

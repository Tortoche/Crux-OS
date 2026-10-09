from typing import Dict, List, Optional, Tuple, Any

from core.plugins.base import BasePlugin
from core.plugins.iot_lighting import IoTLightingPlugin

class PluginManager:
    """
    Gestionnaire centralisé de plugins pour Crux AI.
    Découvre, charge et route les actions et commandes vocales vers les plugins adéquats.
    """
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._plugins: Dict[str, BasePlugin] = {}
        self._init_default_plugins()

    def _init_default_plugins(self):
        # Enregistrement des plugins natifs
        iot_cfg = self.config.get("iot_lighting", {})
        lighting_plugin = IoTLightingPlugin(config=iot_cfg)
        self.register_plugin(lighting_plugin)

    def register_plugin(self, plugin: BasePlugin) -> bool:
        """Enregistre et initialise un plugin."""
        try:
            plugin.initialize()
            self._plugins[plugin.name] = plugin
            return True
        except Exception:
            return False

    def unregister_plugin(self, plugin_name: str) -> bool:
        if plugin_name in self._plugins:
            self._plugins[plugin_name].shutdown()
            del self._plugins[plugin_name]
            return True
        return False

    def get_plugin(self, plugin_name: str) -> Optional[BasePlugin]:
        return self._plugins.get(plugin_name)

    def get_all_plugins(self) -> List[BasePlugin]:
        return list(self._plugins.values())

    def get_all_tools(self) -> List[Dict[str, Any]]:
        """Collecte toutes les définitions d'outils exposées par les plugins actifs."""
        tools = []
        for p in self._plugins.values():
            if p.enabled:
                tools.extend(p.get_tools())
        return tools

    def route_voice_command(self, user_text: str) -> Optional[Tuple[str, bool]]:
        """
        Tente d'acheminer une commande vocale directement vers un plugin capable de la traiter.
        Retourne (reponse_vocale, is_exit) ou None.
        """
        for plugin in self._plugins.values():
            if plugin.enabled and plugin.can_handle_command(user_text):
                res = plugin.handle_voice_command(user_text)
                if res is not None:
                    return res
        return None

    def execute_tool_action(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Exécute une action par nom d'outil."""
        for plugin in self._plugins.values():
            if not plugin.enabled:
                continue
            for tool in plugin.get_tools():
                if tool.get("name") == tool_name:
                    action = params.get("action", tool_name)
                    return plugin.execute_action(action, params)
        return {"success": False, "message": f"Outil '{tool_name}' non trouvé."}

    def shutdown_all(self):
        for p in self._plugins.values():
            try:
                p.shutdown()
            except Exception:
                pass

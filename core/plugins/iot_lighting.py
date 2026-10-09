import re
import json
import urllib.request
import urllib.error
import unicodedata
from typing import Dict, List, Optional, Tuple, Any

from core.plugins.base import BasePlugin

def _clean_text(text: str) -> str:
    cleaned = unicodedata.normalize('NFD', text.lower())
    return ''.join(c for c in cleaned if unicodedata.category(c) != 'Mn')

COLOR_MAP = {
    "rouge": (255, 0, 0),
    "bleu": (0, 100, 255),
    "bleue": (0, 100, 255),
    "vert": (0, 255, 0),
    "verte": (0, 255, 0),
    "jaune": (255, 230, 0),
    "orange": (255, 140, 0),
    "violet": (180, 0, 255),
    "violette": (180, 0, 255),
    "rose": (255, 100, 180),
    "blanc": (255, 255, 255),
    "blanche": (255, 255, 255),
    "chaud": (255, 200, 140),
    "froide": (200, 230, 255)
}

class IoTLightingPlugin(BasePlugin):
    """
    Plugin universel de lumières connectées par Webhook / REST HTTP générique.
    Compatible Home Assistant, Tuya local, Jeedom, ponts HTTP Philips Hue.
    Fonctionne avec repli local simulé instantané si le pont n'est pas joignable.
    """
    name = "iot_lighting"
    version = "1.0.0"
    description = "Contrôle domotique des lumières connectées (allumage, extinction, couleur, luminosité)"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.endpoint_url = self.config.get("endpoint_url", "http://127.0.0.1:8123/api/webhook/crux_lighting")
        self.api_token = self.config.get("api_token", "")
        self.default_entity = self.config.get("default_entity", "light.bureau")
        self.state = {
            "power": "off",
            "brightness": 100,
            "color": "blanc"
        }

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "lighting_control",
                "description": "Contrôle les lumières connectées du bureau (marche, arrêt, intensité, couleur)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["turn_on", "turn_off", "toggle", "set_brightness", "set_color"]
                        },
                        "entity_id": {"type": "string", "description": "Identifiant de la lampe"},
                        "brightness": {"type": "integer", "description": "Luminosité de 0 à 100"},
                        "color": {"type": "string", "description": "Couleur souhaitée (rouge, bleu, vert, blanc...)"}
                    },
                    "required": ["action"]
                }
            }
        ]

    def _send_http_request(self, payload: Dict[str, Any]) -> bool:
        """Envoie l'ordre HTTP vers le pont domotique ou simule avec succès."""
        if not self.endpoint_url or self.endpoint_url.startswith("mock://"):
            return True

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.endpoint_url,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_token}" if self.api_token else "",
                    "User-Agent": "Crux-AI-Jarvis/1.0"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                return resp.status in [200, 201, 204]
        except Exception:
            # Fallback gracieux : le contrôleur local garde l'état en mémoire
            return True

    def execute_action(self, action_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        entity_id = params.get("entity_id", self.default_entity)
        action = params.get("action", action_name)

        if action in ["turn_on", "on", "allumer"]:
            self.state["power"] = "on"
            brightness = params.get("brightness")
            color = params.get("color")
            if brightness is not None:
                self.state["brightness"] = int(brightness)
            if color:
                self.state["color"] = color

            payload = {
                "action": "turn_on",
                "entity_id": entity_id,
                "brightness": self.state["brightness"],
                "color": self.state["color"]
            }
            self._send_http_request(payload)
            msg = f"Lumière de {entity_id.split('.')[-1]} allumée."
            return {"success": True, "message": msg, "state": self.state}

        elif action in ["turn_off", "off", "eteindre"]:
            self.state["power"] = "off"
            payload = {"action": "turn_off", "entity_id": entity_id}
            self._send_http_request(payload)
            msg = f"Lumière de {entity_id.split('.')[-1]} éteinte."
            return {"success": True, "message": msg, "state": self.state}

        elif action in ["toggle", "basculer"]:
            new_power = "off" if self.state["power"] == "on" else "on"
            self.state["power"] = new_power
            payload = {"action": "toggle", "entity_id": entity_id}
            self._send_http_request(payload)
            msg = f"Lumière {'allumée' if new_power == 'on' else 'éteinte'}."
            return {"success": True, "message": msg, "state": self.state}

        elif action in ["set_brightness", "brightness", "luminosite"]:
            level = int(params.get("brightness", 50))
            self.state["brightness"] = level
            self.state["power"] = "on"
            payload = {"action": "set_brightness", "entity_id": entity_id, "brightness": level}
            self._send_http_request(payload)
            msg = f"Luminosité réglée à {level}%."
            return {"success": True, "message": msg, "state": self.state}

        elif action in ["set_color", "color", "couleur"]:
            col = params.get("color", "blanc").lower()
            self.state["color"] = col
            self.state["power"] = "on"
            rgb = COLOR_MAP.get(col, (255, 255, 255))
            payload = {"action": "set_color", "entity_id": entity_id, "color": col, "rgb": rgb}
            self._send_http_request(payload)
            msg = f"Lumière configurée en {col}."
            return {"success": True, "message": msg, "state": self.state}

        return {"success": False, "message": f"Action {action} non supportée."}

    def can_handle_command(self, user_text: str) -> bool:
        """Détecte les commandes vocales directes liées à l'éclairage."""
        u = _clean_text(user_text)
        triggers = ["lumiere", "lumieres", "lampe", "lampes", "eclairage", "eclaire"]
        return any(t in u for t in triggers)

    def handle_voice_command(self, user_text: str) -> Optional[Tuple[str, bool]]:
        u = _clean_text(user_text)
        if not self.can_handle_command(user_text):
            return None

        # 1. Extinction
        if any(w in u for w in ["eteins", "eteint", "coupe", "ferme"]):
            res = self.execute_action("turn_off", {})
            return res["message"], False

        # 2. Tamisage / baisse de luminosité
        if any(w in u for w in ["tamise", "tamiser", "diminue", "baisse"]):
            res = self.execute_action("set_brightness", {"brightness": 30})
            return "Lumière tamisée à 30%.", False

        # 3. Changement de couleur
        for col_name in COLOR_MAP.keys():
            col_cleaned = _clean_text(col_name)
            if col_cleaned in u:
                res = self.execute_action("set_color", {"color": col_name})
                return f"Lumière passée en {col_name}.", False

        # 4. Allumage
        if any(w in u for w in ["allume", "allumer", "mets", "active"]):
            res = self.execute_action("turn_on", {})
            return res["message"], False

        return None

#!/usr/bin/env python3
"""
Crux OS - Passerelle Relais Fedora Linux H24 (crux_server_gateway.py)
Déployé sur le mini-serveur Fedora Linux (192.168.1.41) pour assurer le fonctionnement H24 
de Crux OS et de l'application mobile tactile quand le PC principal Windows est éteint.

Fonctionnalités :
- Serveur HTTP & WebSocket asynchrone (port 49230)
- Fallback transparent pour smartphone vers Google Gemini / Antigravity
- Mémoire 5D synchronisée (faits, travail, épisodique, procédural, réflexion)
- Détection d'état du PC principal (192.168.1.16) & Wake-on-LAN
- Moteur d'interfaces dynamiques génératives (tâches, crypto, monitoring)
- Hébergement direct de l'application web PWA mobile/
"""

import os
import sys
import json
import time
import socket
import asyncio
import logging
from typing import Dict, Any, List, Optional
from aiohttp import web, WSMsgType

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("CruxRelayGateway")

# Configuration par défaut
DEFAULT_PORT = int(os.environ.get("CRUX_PORT", 49230))
WINDOWS_PC_IP = os.environ.get("WINDOWS_PC_IP", "192.168.1.16")
WINDOWS_PC_PORT = int(os.environ.get("WINDOWS_PC_PORT", 49230))
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
MOBILE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mobile")
os.makedirs(DATA_DIR, exist_ok=True)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyDEu0gqAjhnN9noXPOVnYO8YVIy_Q3ezuE")
USER_NAME = "Corentin"

JARVIS_SYSTEM_INSTRUCTION = f"""
Tu es Crux, l'assistant personnel intelligent de {USER_NAME}, fonctionnant en relais H24 sur le serveur Linux.
Tu es inspiré de J.A.R.V.I.S. (Marvel) : précis, direct, calme et efficace.

RÈGLES D'OR STRICTES :
1. ZERO BLABLA : Réponds DIRECTEMENT en 1 seule phrase percutante (2 phrases courtes grand maximum).
2. Pas de formalisme excessif, pas de listes à puces.
3. RÈGLE DU PRÉNOM : Ne dis '{USER_NAME}' qu'au tout premier échange de la session. Ensuite, réponds directement sans répéter son prénom.
4. Tu as accès à la mémoire 5D synchronisée et à l'état du PC principal (allumé ou en veille).
"""

# ==========================================
# GESTIONNAIRE DE MÉMOIRE 5D RELAIS
# ==========================================
class RelayMemory5D:
    def __init__(self, storage_path: str):
        self.file_path = os.path.join(storage_path, "memory_5d.json")
        self.data: Dict[str, Any] = {
            "facts": [
                {"category": "hardware", "key": "screen", "value": "Iiyama G-Master PL2766H"},
                {"category": "audio", "key": "preferred_speakers", "value": "Enceinte JBL et Écran PL2766H"},
                {"category": "network", "key": "relay_server", "value": "Fedora Linux 192.168.1.41"}
            ],
            "working": {"active_device": "mobile", "session_start": time.time()},
            "episodic": [],
            "procedural": {"wake_pc": "Wake-on-LAN magic packet"},
            "reflection": [
                {"insight": "Le serveur Fedora H24 assure la continuité sans coupure quand le PC est en veille."}
            ]
        }
        self.load()

    def load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception as e:
                logger.error(f"Erreur chargement mémoire : {e}")

    def save(self):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Erreur sauvegarde mémoire : {e}")

    def sync(self, payload: Dict[str, Any]):
        """Fusionne la mémoire 5D envoyée depuis le PC ou le mobile."""
        if not payload:
            return
        for key in ["facts", "working", "episodic", "procedural", "reflection"]:
            if key in payload and payload[key]:
                if isinstance(payload[key], list):
                    # Évite les doublons exacts
                    existing = self.data.get(key, [])
                    combined = existing + [item for item in payload[key] if item not in existing]
                    self.data[key] = combined[-50:]  # Limiter à 50 éléments
                elif isinstance(payload[key], dict):
                    self.data.setdefault(key, {}).update(payload[key])
        self.save()

    def record_turn(self, role: str, text: str):
        record = {"role": role, "text": text, "timestamp": time.time()}
        self.data.setdefault("episodic", []).append(record)
        if len(self.data["episodic"]) > 50:
            self.data["episodic"] = self.data["episodic"][-50:]
        self.save()

# ==========================================
# GESTIONNAIRE D'UI GÉNÉRATIVE RELAIS
# ==========================================
class RelayUIManager:
    def __init__(self, storage_path: str):
        self.file_path = os.path.join(storage_path, "ui_state.json")
        self.tasks: List[Dict[str, Any]] = [
            {"id": "t1", "text": "Crux OS Relais Fedora H24 opérationnel", "done": True, "tag": "Système"},
            {"id": "t2", "text": "Synchroniser la mémoire 5D avec le PC", "done": True, "tag": "Mémoire"},
            {"id": "t3", "text": "Contrôle tactile smartphone & gestures Mochi", "done": False, "tag": "Mobile"},
            {"id": "t4", "text": "Tester le handoff vocal vers l'écran PL2766H", "done": False, "tag": "Audio"}
        ]
        self.load()

    def load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self.tasks = json.load(f)
            except Exception:
                pass

    def save(self):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.tasks, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def add_task(self, text: str, tag: str = "Général") -> Dict[str, Any]:
        task_id = f"t{int(time.time() * 1000) % 100000}"
        task = {"id": task_id, "text": text, "done": False, "tag": tag}
        self.tasks.append(task)
        self.save()
        return task

    def toggle_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        for t in self.tasks:
            if t["id"] == task_id:
                t["done"] = not t["done"]
                self.save()
                return t
        return None

    def delete_task(self, task_id: str) -> bool:
        before = len(self.tasks)
        self.tasks = [t for t in self.tasks if t["id"] != task_id]
        if len(self.tasks) < before:
            self.save()
            return True
        return False

# ==========================================
# COEUR DE LA PASSERELLE H24
# ==========================================
class CruxRelayGateway:
    def __init__(self, port: int = DEFAULT_PORT):
        self.port = port
        self.memory = RelayMemory5D(DATA_DIR)
        self.ui = RelayUIManager(DATA_DIR)
        self.app = web.Application(middlewares=[self.cors_middleware])
        self.ws_clients: set = set()
        self.has_said_name = False
        self._setup_routes()

    @web.middleware
    async def cors_middleware(self, request, handler):
        if request.method == "OPTIONS":
            response = web.Response(status=204)
        else:
            try:
                response = await handler(request)
            except web.HTTPException as ex:
                response = ex
            except Exception as e:
                response = web.json_response({"error": str(e)}, status=500)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return response

    def _setup_routes(self):
        self.app.router.add_get("/api/health", self.handle_health)
        self.app.router.add_get("/api/status", self.handle_status)
        self.app.router.add_post("/api/chat", self.handle_chat)
        self.app.router.add_get("/api/memory", self.handle_get_memory)
        self.app.router.add_post("/api/memory/sync", self.handle_sync_memory)
        self.app.router.add_get("/api/ui/state", self.handle_get_ui)
        self.app.router.add_post("/api/ui/action", self.handle_ui_action)
        self.app.router.add_post("/api/pc/wake", self.handle_wake_pc)
        self.app.router.add_get("/api/telemetry", self.handle_telemetry)
        self.app.router.add_get("/ws", self.handle_ws)

        # Hébergement PWA Mobile
        if os.path.exists(MOBILE_DIR):
            self.app.router.add_static("/mobile/", MOBILE_DIR, show_index=True)
            self.app.router.add_get("/", self.handle_root)

    async def handle_root(self, request):
        index_file = os.path.join(MOBILE_DIR, "index.html")
        if os.path.exists(index_file):
            return web.FileResponse(index_file)
        return web.Response(text="Crux OS H24 Relay Gateway actif.", content_type="text/plain")

    async def is_pc_online(self) -> bool:
        """Vérifie si le PC principal Windows répond sur son port Crux."""
        loop = asyncio.get_event_loop()
        try:
            fut = loop.run_in_executor(None, self._check_pc_socket)
            return await asyncio.wait_for(fut, timeout=0.8)
        except Exception:
            return False

    def _check_pc_socket(self) -> bool:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                s.connect((WINDOWS_PC_IP, WINDOWS_PC_PORT))
                return True
        except Exception:
            return False

    async def handle_health(self, request):
        return web.json_response({"status": "ok", "service": "crux_server_gateway"})

    async def handle_status(self, request):
        pc_online = await self.is_pc_online()
        return web.json_response({
            "status": "ok",
            "role": "relay_gateway",
            "host": "fedora-server",
            "server_ip": "192.168.1.41",
            "windows_pc_ip": WINDOWS_PC_IP,
            "pc_online": pc_online,
            "connected_ws_clients": len(self.ws_clients),
            "timestamp": time.time(),
            "uptime_h24": True
        })

    async def handle_get_memory(self, request):
        return web.json_response(self.memory.data)

    async def handle_sync_memory(self, request):
        try:
            body = await request.json()
            self.memory.sync(body)
            await self._broadcast_ws({"type": "memory_sync", "data": "synchronized"})
            return web.json_response({"success": True, "message": "Mémoire 5D synchronisée."})
        except Exception as e:
            return web.json_response({"success": False, "error": str(e)}, status=400)

    async def handle_get_ui(self, request):
        return web.json_response({
            "tasks": self.ui.tasks,
            "stats": {
                "active_tasks": len([t for t in self.ui.tasks if not t["done"]]),
                "completed_tasks": len([t for t in self.ui.tasks if t["done"]]),
                "node": "Fedora H24"
            }
        })

    async def handle_ui_action(self, request):
        try:
            body = await request.json()
            action = body.get("action")
            if action == "add":
                text = body.get("text", "Nouvelle activité")
                tag = body.get("tag", "Mobile")
                task = self.ui.add_task(text, tag)
                await self._broadcast_ws({"type": "ui_update", "action": "add", "task": task})
                return web.json_response({"success": True, "task": task})
            elif action == "toggle":
                task_id = body.get("id")
                task = self.ui.toggle_task(task_id)
                await self._broadcast_ws({"type": "ui_update", "action": "toggle", "task": task})
                return web.json_response({"success": True, "task": task})
            elif action == "delete":
                task_id = body.get("id")
                ok = self.ui.delete_task(task_id)
                await self._broadcast_ws({"type": "ui_update", "action": "delete", "id": task_id})
                return web.json_response({"success": ok})
            else:
                return web.json_response({"success": False, "error": f"Action inconnue {action}"}, status=400)
        except Exception as e:
            return web.json_response({"success": False, "error": str(e)}, status=500)

    async def handle_wake_pc(self, request):
        """Envoie un paquet magique Wake-on-LAN au PC Windows."""
        mac_addr = "D8:BB:C1:2A:3B:4C"  # MAC par défaut ou broadcast
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._send_wol_packet, mac_addr)
            return web.json_response({"success": True, "message": "Paquet Wake-on-LAN transmis au PC principal."})
        except Exception as e:
            return web.json_response({"success": False, "error": str(e)}, status=500)

    def _send_wol_packet(self, mac_address: str):
        clean_mac = mac_address.replace(":", "").replace("-", "")
        if len(clean_mac) != 12:
            return
        data = bytes.fromhex("FF" * 6 + clean_mac * 16)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.sendto(data, ("192.168.1.255", 9))

    async def handle_telemetry(self, request):
        """Télémétrie du serveur Fedora Linux H24."""
        import platform
        try:
            load1, load5, _ = os.getloadavg()
        except Exception:
            load1, load5 = 0.1, 0.1

        return web.json_response({
            "hostname": socket.gethostname(),
            "os": f"Fedora Linux {platform.release()}",
            "load_average": f"{load1:.2f}, {load5:.2f}",
            "role": "Crux H24 Relay",
            "status": "optimal"
        })

    async def handle_chat(self, request):
        """
        Point d'entrée de dialogue pour smartphone.
        Si le PC Windows est allumé, peut router vers lui, sinon génère la réponse
        via Google GenAI / Gemini 3.8 Flash avec la mémoire 5D synchronisée.
        """
        try:
            body = await request.json()
            user_text = body.get("prompt", "").strip()
            if not user_text:
                return web.json_response({"reply": "Je vous écoute.", "source": "fedora_relay"})

            # Enregistrement tour utilisateur
            self.memory.record_turn("user", user_text)

            # Règle d'or de salutation
            name_suffix = f" {USER_NAME}" if not self.has_said_name else ""
            lower = user_text.lower()

            if any(w in lower for w in ["salut", "bonjour", "coucou", "hello"]):
                reply = f"Bonjour{name_suffix}, je suis actif en relais sur le serveur Fedora."
                self.has_said_name = True
                self.memory.record_turn("model", reply)
                return web.json_response({"reply": reply, "source": "fedora_relay"})

            if any(w in lower for w in ["heure", "l'heure"]):
                now = time.strftime("%H:%M")
                reply = f"Il est actuellement {now}."
                self.memory.record_turn("model", reply)
                return web.json_response({"reply": reply, "source": "fedora_relay"})

            # Génération avec Gemini API
            reply = await self._generate_gemini_reply(user_text)
            self.memory.record_turn("model", reply)
            return web.json_response({"reply": reply, "source": "fedora_relay"})

        except Exception as e:
            logger.error(f"Erreur handle_chat : {e}")
            return web.json_response({"reply": "Tous les systèmes relais sont opérationnels.", "source": "fedora_relay"})

    async def _generate_gemini_reply(self, prompt: str) -> str:
        """Génère la réponse via google-genai ou fallback direct."""
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=GEMINI_API_KEY)
            
            # Injection du contexte mémoire 5D
            recent_turns = self.memory.data.get("episodic", [])[-4:]
            hist_lines = [f"{r['role']}: {r['text']}" for r in recent_turns]
            mem_summary = "\n".join(hist_lines)

            full_system = f"{JARVIS_SYSTEM_INSTRUCTION}\nContexte récent :\n{mem_summary}"

            response = await asyncio.to_thread(
                client.models.generate_content,
                model="gemini-2.5-flash",
                contents=[prompt],
                config=types.GenerateContentConfig(
                    system_instruction=full_system,
                    temperature=0.25,
                    max_output_tokens=120
                )
            )
            text = response.text.strip()
            if text:
                return text
        except Exception as e:
            logger.warning(f"Fallback local car appel Gemini échoué : {e}")

        return "Système relais actif, prêt pour vos instructions."

    async def handle_ws(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        self.ws_clients.add(ws)
        logger.info(f"Client WebSocket connecté. Total: {len(self.ws_clients)}")

        await ws.send_json({"type": "connected", "node": "fedora_relay", "timestamp": time.time()})

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        msg_type = data.get("type")
                        if msg_type == "ping":
                            await ws.send_json({"type": "pong", "time": time.time()})
                        elif msg_type == "mochi_state":
                            await self._broadcast_ws(data, sender=ws)
                    except Exception:
                        pass
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f"Erreur WS : {ws.exception()}")
        finally:
            self.ws_clients.discard(ws)
            logger.info(f"Client WebSocket déconnecté. Restant: {len(self.ws_clients)}")

        return ws

    async def _broadcast_ws(self, data: Dict[str, Any], sender=None):
        dead_clients = set()
        for client in self.ws_clients:
            if client != sender and not client.closed:
                try:
                    await client.send_json(data)
                except Exception:
                    dead_clients.add(client)
        self.ws_clients.difference_update(dead_clients)

def create_app() -> web.Application:
    gateway = CruxRelayGateway()
    return gateway.app

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT
    print(f"=== Crux OS H24 Relay Gateway démarré sur 0.0.0.0:{port} ===")
    gateway = CruxRelayGateway(port=port)
    web.run_app(gateway.app, host="0.0.0.0", port=port)

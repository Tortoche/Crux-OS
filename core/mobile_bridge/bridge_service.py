import os
import sys
import json
import time
import socket
import asyncio
import logging
from typing import Dict, Any, List, Optional
from aiohttp import web, WSMsgType

from core.handoff.manager import HandoffManager
from core.ui_generator.runtime import DynamicUIRuntime

logger = logging.getLogger("CruxMobileBridge")

DEFAULT_BRIDGE_PORT = 49230
FEDORA_SERVER_URL = "http://192.168.1.41:49230"
MOBILE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "mobile")

class MobileBridgeService:
    """
    Pont de communication mobile local hébergé sur le PC Windows.
    Permet à l'application smartphone (mobile/) de dialoguer avec le PC en direct à très basse latence,
    d'exécuter la télécommande PC, et de synchroniser la mémoire 5D vers le serveur Fedora H24.
    """
    _instance: Optional['MobileBridgeService'] = None

    @classmethod
    def get_instance(cls, agent=None) -> 'MobileBridgeService':
        if cls._instance is None:
            cls._instance = cls(agent=agent)
        elif agent is not None:
            cls._instance.agent = agent
        return cls._instance

    def __init__(self, agent: Optional[Any] = None, port: int = DEFAULT_BRIDGE_PORT):
        self.agent = agent
        self.port = port
        self.handoff = HandoffManager.get_instance()
        if self.agent:
            self.handoff.agent = self.agent
        self.ui_runtime = DynamicUIRuntime.get_instance()
        self.app = web.Application(middlewares=[self.cors_middleware])
        self.ws_clients: set = set()
        self.runner: Optional[web.AppRunner] = None
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
        self.app.router.add_post("/api/pc/control", self.handle_pc_control)
        self.app.router.add_post("/api/handoff/to_mobile", self.handle_handoff_to_mobile)
        self.app.router.add_post("/api/handoff/to_pc", self.handle_handoff_to_pc)
        self.app.router.add_get("/api/ui/state", self.handle_get_ui)
        self.app.router.add_post("/api/ui/action", self.handle_ui_action)
        self.app.router.add_get("/api/memory/sync", self.handle_get_memory)
        self.app.router.add_post("/api/memory/sync", self.handle_sync_memory)
        self.app.router.add_get("/api/telemetry", self.handle_telemetry)
        self.app.router.add_get("/ws", self.handle_ws)

        # Hébergement direct de l'application mobile PWA
        if os.path.exists(MOBILE_DIR):
            self.app.router.add_static("/mobile/", MOBILE_DIR, show_index=True)
            self.app.router.add_get("/", self.handle_root)

    async def handle_root(self, request):
        index_path = os.path.join(MOBILE_DIR, "index.html")
        if os.path.exists(index_path):
            return web.FileResponse(index_path)
        return web.Response(text="Crux OS Windows Mobile Bridge actif.", content_type="text/plain")

    async def handle_health(self, request):
        return web.json_response({"status": "ok", "service": "crux_mobile_bridge", "node": "pc"})

    async def handle_status(self, request):
        handoff_status = self.handoff.get_status()
        return web.json_response({
            "status": "ok",
            "role": "primary_pc",
            "node": "pc",
            "ip": "192.168.1.16",
            "active_node": handoff_status.get("active_node", "pc"),
            "connected_ws_clients": len(self.ws_clients),
            "timestamp": time.time(),
            "has_agent": self.agent is not None
        })

    async def handle_chat(self, request):
        try:
            body = await request.json()
            prompt = body.get("prompt", "").strip()
            if not prompt:
                return web.json_response({"reply": "Je vous écoute.", "source": "windows_pc"})

            if self.agent and hasattr(self.agent, "process_command"):
                reply, is_exit = self.agent.process_command(prompt)
                # Synchronisation mémoire vers le relais Fedora en tâche de fond
                asyncio.create_task(self.sync_memory_to_fedora())
                return web.json_response({"reply": reply, "source": "windows_pc", "is_exit": is_exit})
            else:
                return web.json_response({"reply": f"Reçu : {prompt} (Agent PC non initialisé)", "source": "windows_pc"})
        except Exception as e:
            return web.json_response({"reply": f"Erreur de traitement : {str(e)}", "source": "windows_pc"}, status=500)

    async def handle_pc_control(self, request):
        try:
            body = await request.json()
            command = body.get("command", "")
            params = body.get("params", {})
            res = self.handoff.execute_remote_command(command, params=params, agent=self.agent)
            return web.json_response(res)
        except Exception as e:
            return web.json_response({"success": False, "error": str(e)}, status=500)

    async def handle_handoff_to_mobile(self, request):
        reply, is_exit = self.handoff.transfer_to_mobile(self.agent)
        # Notifier Fedora
        asyncio.create_task(self.sync_memory_to_fedora())
        return web.json_response({"success": True, "reply": reply, "is_exit": is_exit})

    async def handle_handoff_to_pc(self, request):
        reply, is_exit = self.handoff.resume_on_pc(self.agent)
        return web.json_response({"success": True, "reply": reply, "is_exit": is_exit})

    async def handle_get_ui(self, request):
        tasks = []
        if hasattr(self.ui_runtime, "tasks"):
            tasks = self.ui_runtime.tasks
        return web.json_response({
            "tasks": tasks,
            "stats": {
                "active_tasks": len([t for t in tasks if not t.get("done", False)]),
                "completed_tasks": len([t for t in tasks if t.get("done", False)]),
                "node": "Windows PC"
            }
        })

    async def handle_ui_action(self, request):
        try:
            body = await request.json()
            action = body.get("action")
            if action == "add":
                text = body.get("text", "Nouvelle activité")
                self.ui_runtime.append_task(text)
                await self._broadcast_ws({"type": "ui_update", "action": "add", "text": text})
                return web.json_response({"success": True})
            elif action == "toggle":
                task_id = body.get("id")
                self.ui_runtime.toggle_task(task_id)
                await self._broadcast_ws({"type": "ui_update", "action": "toggle", "id": task_id})
                return web.json_response({"success": True})
            elif action == "delete":
                task_id = body.get("id")
                self.ui_runtime.delete_task(task_id)
                await self._broadcast_ws({"type": "ui_update", "action": "delete", "id": task_id})
                return web.json_response({"success": True})
            return web.json_response({"success": False, "error": "Action inconnue"}, status=400)
        except Exception as e:
            return web.json_response({"success": False, "error": str(e)}, status=500)

    async def handle_get_memory(self, request):
        if self.agent and hasattr(self.agent, "memory"):
            mem_data = {
                "facts": getattr(self.agent.memory.facts, "facts", []),
                "working": getattr(self.agent.memory.working, "state", {}),
                "reflection": getattr(self.agent.memory.reflection, "reflections", [])
            }
            return web.json_response(mem_data)
        return web.json_response({"status": "no_memory"})

    async def handle_sync_memory(self, request):
        try:
            body = await request.json()
            if self.agent and hasattr(self.agent, "memory"):
                if "facts" in body and hasattr(self.agent.memory.facts, "facts"):
                    for f in body["facts"]:
                        if isinstance(f, dict) and "key" in f and "value" in f:
                            self.agent.memory.facts.set(f.get("category", "general"), f["key"], f["value"])
                if "working" in body and hasattr(self.agent.memory.working, "state"):
                    for k, v in body["working"].items():
                        self.agent.memory.working.set(k, v)
            return web.json_response({"success": True, "message": "Mémoire 5D synchronisée sur le PC."})
        except Exception as e:
            return web.json_response({"success": False, "error": str(e)}, status=400)

    async def handle_telemetry(self, request):
        if self.agent and hasattr(self.agent, "computer_use") and hasattr(self.agent.computer_use, "telemetry"):
            return web.json_response(self.agent.computer_use.telemetry.get_system_telemetry())
        return web.json_response({"status": "online", "platform": "Windows 11"})

    async def sync_memory_to_fedora(self):
        """Envoie l'état de la mémoire 5D au serveur relais Fedora."""
        if not self.agent or not hasattr(self.agent, "memory"):
            return
        try:
            import urllib.request
            payload = {
                "facts": getattr(self.agent.memory.facts, "facts", []),
                "working": getattr(self.agent.memory.working, "state", {}),
                "reflection": getattr(self.agent.memory.reflection, "reflections", [])
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{FEDORA_SERVER_URL}/api/memory/sync",
                data=data,
                headers={"Content-Type": "application/json"}
            )
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=1.5))
        except Exception:
            pass

    async def handle_ws(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.ws_clients.add(ws)
        await ws.send_json({"type": "connected", "node": "windows_pc", "timestamp": time.time()})
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        if data.get("type") == "ping":
                            await ws.send_json({"type": "pong", "time": time.time()})
                    except Exception:
                        pass
        finally:
            self.ws_clients.discard(ws)
        return ws

    async def _broadcast_ws(self, data: Dict[str, Any]):
        dead = set()
        for c in self.ws_clients:
            if not c.closed:
                try:
                    await c.send_json(data)
                except Exception:
                    dead.add(c)
        self.ws_clients.difference_update(dead)

    async def start(self):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, "0.0.0.0", self.port)
        await site.start()
        logger.info(f"Serveur Mobile Bridge actif sur 0.0.0.0:{self.port}")

    async def stop(self):
        if self.runner:
            await self.runner.cleanup()
            self.runner = None

    def start_in_background(self):
        """Démarre le serveur aiohttp dans un thread d'arrière-plan."""
        import threading
        def run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop
            loop.run_until_complete(self.start())
            loop.run_forever()

        t = threading.Thread(target=run, daemon=True, name="CruxMobileBridgeThread")
        t.start()
        return t

import os
import time
import platform
import psutil
from datetime import datetime
from typing import Dict, Any, List, Optional, Union, Tuple

class SystemTelemetryEngine:
    """
    Moteur de télémétrie système approfondie et de gestion des processus.
    Inspiré de l'architecture Jarvis de bnsware/jarvis-windows :
    surveillance continue des performances matérielles, CPU, RAM, disques,
    batterie/alimentation, réseaux, et diagnostic des processus en arrière-plan.
    """

    @staticmethod
    def get_system_telemetry() -> Dict[str, Any]:
        """Collecte l'ensemble des métriques système et matérielles du PC."""
        # 1. CPU
        cpu_pct = psutil.cpu_percent(interval=0.1)
        per_cpu = psutil.cpu_percent(interval=None, percpu=True)
        cpu_freq = psutil.cpu_freq()
        cpu_info = {
            "percent": cpu_pct,
            "per_core": per_cpu,
            "cores_logical": psutil.cpu_count(logical=True),
            "cores_physical": psutil.cpu_count(logical=False),
            "frequency_mhz": round(cpu_freq.current, 1) if cpu_freq else None
        }

        # 2. RAM
        ram = psutil.virtual_memory()
        ram_info = {
            "total_gb": round(ram.total / (1024**3), 2),
            "used_gb": round(ram.used / (1024**3), 2),
            "available_gb": round(ram.available / (1024**3), 2),
            "percent": ram.percent
        }

        # 3. Disques
        disks = []
        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
                disks.append({
                    "device": part.device,
                    "mountpoint": part.mountpoint,
                    "fstype": part.fstype,
                    "total_gb": round(usage.total / (1024**3), 1),
                    "free_gb": round(usage.free / (1024**3), 1),
                    "percent": usage.percent
                })
            except Exception:
                continue

        # 4. Batterie / Alimentation
        battery_info = None
        try:
            bat = psutil.sensors_battery()
            if bat:
                battery_info = {
                    "percent": bat.percent,
                    "plugged": bat.power_plugged,
                    "secsleft": bat.secsleft if bat.secsleft != psutil.POWER_TIME_UNLIMITED else None
                }
        except Exception:
            pass

        # 5. Réseau
        net_io = psutil.net_io_counters()
        net_info = {
            "bytes_sent_mb": round(net_io.bytes_sent / (1024**2), 1),
            "bytes_recv_mb": round(net_io.bytes_recv / (1024**2), 1),
        }

        # 6. Uptime
        boot_timestamp = psutil.boot_time()
        uptime_seconds = int(time.time() - boot_timestamp)
        days = uptime_seconds // 86400
        hours = (uptime_seconds % 86400) // 3600
        minutes = (uptime_seconds % 3600) // 60
        uptime_parts = []
        if days > 0:
            uptime_parts.append(f"{days} jour{'s' if days > 1 else ''}")
        if hours > 0:
            uptime_parts.append(f"{hours} heure{'s' if hours > 1 else ''}")
        uptime_parts.append(f"{minutes} minute{'s' if minutes > 1 else ''}")
        uptime_formatted = ", ".join(uptime_parts)

        return {
            "timestamp": datetime.now().isoformat(),
            "cpu": cpu_info,
            "memory": ram_info,
            "disks": disks,
            "battery": battery_info,
            "network": net_info,
            "uptime_seconds": uptime_seconds,
            "uptime_formatted": uptime_formatted,
            "platform": platform.platform()
        }

    @staticmethod
    def format_telemetry_summary() -> str:
        """Formate un résumé concis des métriques système pour réponse vocale Jarvis."""
        telem = SystemTelemetryEngine.get_system_telemetry()
        cpu_pct = telem["cpu"]["percent"]
        ram_pct = telem["memory"]["percent"]
        ram_free = telem["memory"]["available_gb"]
        uptime = telem["uptime_formatted"]

        c_disk = next((d for d in telem["disks"] if "C" in d["mountpoint"].upper()), None)
        disk_str = f", C: {c_disk['free_gb']} Go libres" if c_disk else ""

        bat = telem.get("battery")
        bat_str = ""
        if bat:
            state = "en charge" if bat["plugged"] else "sur batterie"
            bat_str = f", Batterie à {bat['percent']}% ({state})"

        return (
            f"Statut système : Processeur à {cpu_pct} %, RAM à {ram_pct} % ({ram_free} Go disponibles)"
            f"{disk_str}{bat_str}. Système actif depuis {uptime}."
        )

    @staticmethod
    def list_processes(
        sort_by: str = "cpu",
        limit: int = 10,
        name_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Liste et filtre les processus actifs classés par consommation CPU ou mémoire.
        """
        procs = []
        name_f = name_filter.lower().strip() if name_filter else None

        for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'status']):
            try:
                info = p.info
                pname = (info.get('name') or "").strip()
                if not pname or pname.lower() in ["system idle process", "idle"]:
                    continue
                if name_f and name_f not in pname.lower():
                    continue

                mem_bytes = info['memory_info'].rss if info.get('memory_info') else 0
                mem_mb = round(mem_bytes / (1024**2), 1)

                procs.append({
                    "pid": info['pid'],
                    "name": pname,
                    "cpu_percent": round(info.get('cpu_percent') or 0.0, 1),
                    "memory_mb": mem_mb,
                    "status": info.get('status', 'unknown')
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        key_func = (lambda x: x["cpu_percent"]) if sort_by == "cpu" else (lambda x: x["memory_mb"])
        procs.sort(key=key_func, reverse=True)
        return procs[:limit]

    @staticmethod
    def format_top_processes_summary(sort_by: str = "cpu", limit: int = 5) -> str:
        """Formate le top des processus les plus consommateurs pour réponse vocale."""
        procs = SystemTelemetryEngine.list_processes(sort_by=sort_by, limit=limit)
        if not procs:
            return "Aucun processus remarquable détecté."

        if sort_by == "cpu":
            items = [f"{p['name']} ({p['cpu_percent']} % CPU)" for p in procs]
            return f"Processus les plus gourmands en CPU : {', '.join(items)}."
        else:
            items = [f"{p['name']} ({p['memory_mb']} Mo)" for p in procs]
            return f"Processus les plus gourmands en mémoire : {', '.join(items)}."

    @staticmethod
    def get_process_info(target: Union[int, str]) -> Optional[Dict[str, Any]]:
        """Retourne des informations détaillées sur un processus par PID ou nom."""
        try:
            proc = None
            if isinstance(target, int) or (isinstance(target, str) and target.isdigit()):
                proc = psutil.Process(int(target))
            else:
                target_lower = str(target).lower().strip()
                for p in psutil.process_iter(['pid', 'name']):
                    if target_lower in (p.info.get('name') or '').lower():
                        proc = p
                        break

            if not proc:
                return None

            with proc.oneshot():
                return {
                    "pid": proc.pid,
                    "name": proc.name(),
                    "exe": proc.exe() if hasattr(proc, 'exe') else "",
                    "cpu_percent": proc.cpu_percent(interval=0.05),
                    "memory_mb": round(proc.memory_info().rss / (1024**2), 1),
                    "status": proc.status(),
                    "create_time": datetime.fromtimestamp(proc.create_time()).isoformat(),
                    "num_threads": proc.num_threads()
                }
        except Exception:
            return None

    @staticmethod
    def kill_process(target: Union[int, str], force: bool = False) -> Tuple[bool, str]:
        """Arrête un processus par son nom ou son PID."""
        try:
            target_proc = None
            if isinstance(target, int) or (isinstance(target, str) and str(target).isdigit()):
                target_proc = psutil.Process(int(target))
            else:
                target_lower = str(target).lower().strip()
                for p in psutil.process_iter(['pid', 'name']):
                    if target_lower in (p.info.get('name') or '').lower():
                        target_proc = p
                        break

            if not target_proc:
                return False, f"Processus '{target}' introuvable."

            name = target_proc.name()
            pid = target_proc.pid

            if force:
                target_proc.kill()
            else:
                target_proc.terminate()
            target_proc.wait(timeout=2.0)
            return True, f"Processus {name} (PID {pid}) arrêté avec succès."
        except psutil.TimeoutExpired:
            if not force:
                return SystemTelemetryEngine.kill_process(target, force=True)
            return False, f"Délai d'attente dépassé pour arrêter le processus {target}."
        except Exception as e:
            return False, f"Impossible d'arrêter le processus : {e}"

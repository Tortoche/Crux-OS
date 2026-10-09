import os
import sys
import json
import time
import socket
import logging
from typing import Dict, Any, Optional
import paramiko

logger = logging.getLogger("CruxDeployer")

FEDORA_HOST = os.environ.get("FEDORA_HOST", "192.168.1.41")
FEDORA_PORT = int(os.environ.get("FEDORA_PORT", 22))
FEDORA_USER = os.environ.get("FEDORA_USER", "root")
FEDORA_PASSWORD = os.environ.get("FEDORA_PASSWORD", "1234")
REMOTE_DIR = "/root/crux-server"

SYSTEMD_UNIT = """[Unit]
Description=Crux OS H24 Relay Gateway
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/crux-server
ExecStart=/usr/bin/python3 /root/crux-server/crux_server_gateway.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
"""

class FedoraRelayDeployer:
    """
    Outil de déploiement et de gestion à chaud de la passerelle relais H24
    Crux OS sur le mini-serveur Fedora Linux (192.168.1.41).
    """
    def __init__(
        self,
        host: str = FEDORA_HOST,
        port: int = FEDORA_PORT,
        user: str = FEDORA_USER,
        password: str = FEDORA_PASSWORD
    ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.client: Optional[paramiko.SSHClient] = None

    def connect(self) -> paramiko.SSHClient:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=self.host,
            port=self.port,
            username=self.user,
            password=self.password,
            timeout=8.0
        )
        self.client = client
        return client

    def run_command(self, cmd: str) -> Dict[str, Any]:
        if not self.client:
            self.connect()
        stdin, stdout, stderr = self.client.exec_command(cmd)
        exit_code = stdout.channel.recv_exit_status()
        out_str = stdout.read().decode('utf-8', errors='replace').strip()
        err_str = stderr.read().decode('utf-8', errors='replace').strip()
        return {"exit_code": exit_code, "stdout": out_str, "stderr": err_str}

    def deploy(self, local_project_dir: str) -> Dict[str, Any]:
        """
        Déploie crux_server_gateway.py et mobile/ sur le serveur Linux
        et configure le service systemd H24.
        """
        results = {"success": True, "steps": []}
        try:
            self.connect()
            sftp = self.client.open_sftp()

            # 1. Création des répertoires distants
            self.run_command(f"mkdir -p {REMOTE_DIR}/mobile {REMOTE_DIR}/data")
            results["steps"].append("Répertoires distants créés")

            # 2. Upload de crux_server_gateway.py
            gateway_src = os.path.join(local_project_dir, "crux_server_gateway.py")
            if os.path.exists(gateway_src):
                sftp.put(gateway_src, f"{REMOTE_DIR}/crux_server_gateway.py")
                self.run_command(f"chmod +x {REMOTE_DIR}/crux_server_gateway.py")
                results["steps"].append("crux_server_gateway.py transféré")

            # 3. Upload de mobile/ (assets PWA)
            mobile_src = os.path.join(local_project_dir, "mobile")
            if os.path.exists(mobile_src):
                for fname in os.listdir(mobile_src):
                    local_f = os.path.join(mobile_src, fname)
                    if os.path.isfile(local_f):
                        sftp.put(local_f, f"{REMOTE_DIR}/mobile/{fname}")
                results["steps"].append("Assets mobile/ transférés")

            # 4. Configuration systemd
            unit_path = "/etc/systemd/system/crux-server.service"
            with sftp.open(unit_path, "w") as f:
                f.write(SYSTEMD_UNIT)
            results["steps"].append("Fichier service systemd installé")

            # 5. Rechargement et démarrage
            res_reload = self.run_command("systemctl daemon-reload")
            res_enable = self.run_command("systemctl enable crux-server.service")
            res_start = self.run_command("systemctl restart crux-server.service")
            results["steps"].append(f"Service redémarré (exit: {res_start['exit_code']})")

            # 6. Vérification statut du service
            time.sleep(1.0)
            status_res = self.run_command("systemctl is-active crux-server.service")
            is_active = (status_res["stdout"].strip() == "active")
            results["is_active"] = is_active
            results["service_status"] = status_res["stdout"]

            sftp.close()

        except Exception as e:
            results["success"] = False
            results["error"] = str(e)
        finally:
            if self.client:
                self.client.close()
                self.client = None

        return results

    def verify_gateway_api(self, timeout: float = 3.0) -> Dict[str, Any]:
        """Vérifie que l'API HTTP du serveur relais répond sur 192.168.1.41:49230."""
        import urllib.request
        url = f"http://{self.host}:49230/api/status"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'CruxDeployer'})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                return {"reachable": True, "status": data}
        except Exception as e:
            return {"reachable": False, "error": str(e)}

if __name__ == "__main__":
    proj_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    deployer = FedoraRelayDeployer()
    print("Déploiement en cours...")
    res = deployer.deploy(proj_dir)
    print("Résultat déploiement :", res)
    api_res = deployer.verify_gateway_api()
    print("Vérification API :", api_res)

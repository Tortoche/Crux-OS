import os
import sys
import time
import subprocess
import tempfile
import re
from typing import Dict, Any, List, Optional, Tuple

class CodeInterpreterEngine:
    """
    Moteur d'exécution de code et de scripts sécurisé pour Windows.
    Inspiré de l'architecture open-interpreter/open-interpreter et dmrr35/Open.Jarvis :
    permet à Jarvis d'automatiser des tâches système complexes via PowerShell, CMD
    ou Python directement sans manipulation de souris, avec détection proactive des
    commandes destructrices nécessitant confirmation explicite.
    """

    # Motifs de commandes potentiellement destructrices nécessitant confirmation
    DANGEROUS_PATTERNS = [
        r"format\s+[a-z]:",
        r"format-volume",
        r"rmdir\s+/[sq]",
        r"rd\s+/[sq]",
        r"del\s+/[sfq]",
        r"erase\s+/[sfq]",
        r"remove-item\s+.*-recurse",
        r"stop-computer",
        r"restart-computer",
        r"shutdown\s+/[sr]",
        r"bcdedit",
        r"reg\s+delete",
        r"diskpart",
        r"cipher\s+/w",
        r"shutil\.rmtree",
        r"os\.remove",
        r"os\.unlink",
        r"drop\s+database",
        r"drop\s+table"
    ]

    @staticmethod
    def is_dangerous(command_or_code: str) -> Tuple[bool, str]:
        """
        Analyse une commande ou un snippet de code pour détecter s'il présente
        un risque de destruction de données ou d'arrêt du système.
        """
        text = (command_or_code or "").lower()
        for pattern in CodeInterpreterEngine.DANGEROUS_PATTERNS:
            if re.search(pattern, text):
                return True, f"La commande contient une opération sensible ({pattern}) et requiert votre confirmation explicite."
        return False, ""

    @staticmethod
    def run_command(
        command: str,
        shell: str = "powershell",
        timeout: float = 15.0,
        cwd: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Exécute une commande système via PowerShell ou CMD et capture le résultat complet.
        """
        cmd_clean = command.strip()
        if not cmd_clean:
            return {
                "success": False,
                "stdout": "",
                "stderr": "Commande vide.",
                "returncode": -1,
                "duration_sec": 0.0
            }

        shell_type = shell.lower()
        if shell_type == "powershell":
            ps_cmd = f"[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; {cmd_clean}"
            full_cmd = ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd]
        else:
            full_cmd = ["cmd.exe", "/c", cmd_clean]

        def _decode_bytes(data: bytes) -> str:
            if not data:
                return ""
            for enc in ["utf-8", "cp850", "cp1252"]:
                try:
                    return data.decode(enc).strip()
                except UnicodeDecodeError:
                    continue
            return data.decode("utf-8", errors="replace").strip()

        t0 = time.time()
        try:
            res = subprocess.run(
                full_cmd,
                capture_output=True,
                timeout=timeout,
                cwd=cwd or os.getcwd()
            )
            duration = round(time.time() - t0, 3)
            return {
                "success": res.returncode == 0,
                "stdout": _decode_bytes(res.stdout),
                "stderr": _decode_bytes(res.stderr),
                "returncode": res.returncode,
                "duration_sec": duration
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Délai d'exécution dépassé ({timeout}s).",
                "returncode": -1,
                "duration_sec": round(time.time() - t0, 3)
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1,
                "duration_sec": round(time.time() - t0, 3)
            }

    @staticmethod
    def run_python(
        code: str,
        timeout: float = 15.0,
        cwd: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Exécute un bloc de code Python dans un sous-processus isolé et capture les sorties.
        """
        t0 = time.time()
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(code)
            tmp_path = f.name

        def _decode_bytes(data: bytes) -> str:
            if not data:
                return ""
            for enc in ["utf-8", "cp1252", "cp850"]:
                try:
                    return data.decode(enc).strip()
                except UnicodeDecodeError:
                    continue
            return data.decode("utf-8", errors="replace").strip()

        try:
            res = subprocess.run(
                [sys.executable, tmp_path],
                capture_output=True,
                timeout=timeout,
                cwd=cwd or os.getcwd()
            )
            duration = round(time.time() - t0, 3)
            return {
                "success": res.returncode == 0,
                "stdout": _decode_bytes(res.stdout),
                "stderr": _decode_bytes(res.stderr),
                "returncode": res.returncode,
                "duration_sec": duration
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Délai d'exécution Python dépassé ({timeout}s).",
                "returncode": -1,
                "duration_sec": round(time.time() - t0, 3)
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1,
                "duration_sec": round(time.time() - t0, 3)
            }
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass

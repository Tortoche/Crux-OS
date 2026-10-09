import os
import subprocess
from pathlib import Path
from typing import List, Dict, Optional

class ProjectManager:
    """
    Gère la découverte, la navigation et l'exécution de commandes dans les projets Antigravity.
    Garantit une stricte séparation entre la conversation vocale et les fichiers de code.
    """
    def __init__(self, root_dir: str = r"C:\Users\coco\Documents"):
        self.root_dir = Path(root_dir)
        self.active_project_path: Optional[Path] = None
        self.active_project_name: Optional[str] = None

    def list_projects(self) -> List[str]:
        """Liste tous les répertoires de projets valides disponibles."""
        if not self.root_dir.exists():
            return []
        
        projects = []
        for entry in self.root_dir.iterdir():
            if entry.is_dir() and not entry.name.startswith(('.', '$')):
                projects.append(entry.name)
        return sorted(projects)

    def switch_project(self, target_name: str) -> Dict[str, any]:
        """
        Bascule le contexte vers un projet spécifique par nom exact ou approximatif.
        """
        projects = self.list_projects()
        target_lower = target_name.strip().lower()

        # Recherche exacte
        for p in projects:
            if p.lower() == target_lower:
                self.active_project_name = p
                self.active_project_path = self.root_dir / p
                return {
                    "success": True,
                    "name": self.active_project_name,
                    "path": str(self.active_project_path),
                    "message": f"Contexte basculé sur le projet {self.active_project_name}."
                }

        # Recherche partielle
        for p in projects:
            if target_lower in p.lower() or p.lower() in target_lower:
                self.active_project_name = p
                self.active_project_path = self.root_dir / p
                return {
                    "success": True,
                    "name": self.active_project_name,
                    "path": str(self.active_project_path),
                    "message": f"Projet identifié : {self.active_project_name}."
                }

        return {
            "success": False,
            "name": None,
            "path": None,
            "message": f"Projet '{target_name}' introuvable. Projets disponibles : {', '.join(projects[:5])}..."
        }

    def execute_in_project(self, command: str) -> Dict[str, any]:
        """
        Exécute une commande terminal directement dans le répertoire du projet actif.
        """
        cwd = str(self.active_project_path) if self.active_project_path else str(self.root_dir)
        
        try:
            result = subprocess.run(
                command,
                cwd=cwd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=45
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": "Délai d'exécution dépassé (timeout 45s).",
                "returncode": -1
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1
            }

    def get_project_summary(self) -> str:
        """Fournit un résumé rapide de la structure du projet actif."""
        if not self.active_project_path or not self.active_project_path.exists():
            return "Aucun projet actif sélectionné."

        files = []
        try:
            for item in list(self.active_project_path.iterdir())[:15]:
                prefix = "[Dossier]" if item.is_dir() else "[Fichier]"
                files.append(f"{prefix} {item.name}")
        except Exception as e:
            return f"Erreur de lecture du projet: {e}"

        return f"Projet actif: {self.active_project_name}\nChemin: {self.active_project_path}\nContenu:\n" + "\n".join(files)

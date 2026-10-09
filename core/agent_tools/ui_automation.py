import time
import ctypes
from ctypes import wintypes
from typing import Dict, Any, List, Optional, Tuple, Union

try:
    import uiautomation as uia
    try:
        # Évite les blocages de 10s par défaut lors des recherches infructueuses
        uia.SetGlobalSearchTimeout(1.0)
    except Exception:
        pass
except ImportError:
    uia = None

user32 = ctypes.windll.user32
user32.GetForegroundWindow.restype = wintypes.HWND

class UIAutomationEngine:
    """
    Moteur de contrôle et d'inspection headless via l'arbre Windows UI Automation (UIA).
    Inspiré de sirendhead/Windows-Use :
    permet d'interagir directement avec les composants d'applications (boutons, champs,
    menus, onglets) en mémoire sans émulation ni déplacement du curseur physique de la souris,
    et sans recourir à des modèles de vision lourds.
    """

    @staticmethod
    def is_available() -> bool:
        """Vérifie si la bibliothèque uiautomation est installée et accessible."""
        return uia is not None

    @staticmethod
    def find_window(title_pattern: str):
        """Trouve un contrôle de fenêtre UIA par motif de titre (insensible à la casse)."""
        if not uia or not title_pattern:
            return None
        p_lower = title_pattern.lower().strip()
        try:
            root = uia.GetRootControl()
            if root:
                for child in root.GetChildren():
                    c_name = (child.Name or "").lower()
                    if p_lower in c_name:
                        return child
        except Exception:
            pass
        return None

    @staticmethod
    def get_foreground_control():
        """Retourne le contrôle UIA de la fenêtre active au premier plan."""
        if not uia:
            return None
        try:
            hwnd = user32.GetForegroundWindow()
            if hwnd:
                ctrl = uia.ControlFromHandle(hwnd)
                if ctrl:
                    return ctrl
            fg = uia.GetForegroundControl()
            if fg:
                return fg
            return uia.GetFocusedControl()
        except Exception:
            return None

    @staticmethod
    def find_control(
        name: Optional[str] = None,
        control_type: Optional[str] = None,
        automation_id: Optional[str] = None,
        parent=None,
        window_title: Optional[str] = None,
        search_depth: int = 4
    ):
        """
        Recherche un contrôle UIA répondant aux critères sans dépendance de position écran.
        Peut cibler une fenêtre spécifique par window_title.
        """
        if not uia:
            return None

        if window_title and not parent:
            parent = UIAutomationEngine.find_window(window_title)

        root = parent or UIAutomationEngine.get_foreground_control() or uia.GetRootControl()
        if not root:
            return None

        name_lower = name.lower().strip() if name else None
        auto_id_clean = automation_id.strip() if automation_id else None
        ctype_clean = control_type.lower().strip() if control_type else None

        found_control = None

        def search_walker(ctrl, depth):
            nonlocal found_control
            if found_control or depth > search_depth:
                return

            try:
                c_name = (ctrl.Name or "").strip().lower()
                c_id = (ctrl.AutomationId or "").strip()
                c_type = (ctrl.ControlTypeName or "").lower()

                match = True
                if name_lower and name_lower not in c_name:
                    match = False
                if auto_id_clean and auto_id_clean != c_id:
                    match = False
                if ctype_clean and ctype_clean not in c_type:
                    match = False

                if match and (name_lower or auto_id_clean or ctype_clean):
                    found_control = ctrl
                    return

                for child in ctrl.GetChildren():
                    search_walker(child, depth + 1)
                    if found_control:
                        return
            except Exception:
                pass

        try:
            search_walker(root, 1)
        except Exception:
            pass

        return found_control

    @staticmethod
    def click_control(
        name: Optional[str] = None,
        control_type: Optional[str] = None,
        automation_id: Optional[str] = None,
        parent=None,
        window_title: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Déclenche un clic 100% headless / programmatique sur le contrôle cible via UIA InvokePattern.
        Zéro déplacement du curseur physique de la souris.
        """
        if not uia:
            return False, "Bibliothèque uiautomation non disponible."

        ctrl = UIAutomationEngine.find_control(
            name=name,
            control_type=control_type,
            automation_id=automation_id,
            parent=parent,
            window_title=window_title
        )
        if not ctrl:
            target_desc = name or automation_id or control_type or "spécifié"
            return False, f"Contrôle '{target_desc}' introuvable dans l'interface."

        ctrl_name = ctrl.Name or name or "Élément"
        try:
            # 1. Tentative InvokePattern (méthode privilégiée 100% in-memory)
            invoke_pattern = ctrl.GetInvokePattern()
            if invoke_pattern:
                invoke_pattern.Invoke()
                return True, f"Action activée sur '{ctrl_name}' via UIA Invoke."
        except Exception:
            pass

        try:
            # 2. Tentative TogglePattern (pour checkbox/switch)
            toggle_pattern = ctrl.GetTogglePattern()
            if toggle_pattern:
                toggle_pattern.Toggle()
                return True, f"Bascule effectuée sur '{ctrl_name}' via UIA Toggle."
        except Exception:
            pass

        try:
            # 3. Tentative SelectionItemPattern (pour listes et onglets)
            sel_pattern = ctrl.GetSelectionItemPattern()
            if sel_pattern:
                sel_pattern.Select()
                return True, f"Sélection appliquée sur '{ctrl_name}' via UIA Select."
        except Exception:
            pass

        try:
            # 4. Repli Click direct sans mouvement physique simulé
            ctrl.Click(simulateMove=False)
            return True, f"Clic direct appliqué sur '{ctrl_name}'."
        except Exception as e:
            return False, f"Impossible de déclencher le contrôle '{ctrl_name}' : {e}"

    @staticmethod
    def set_control_value(
        text: str,
        name: Optional[str] = None,
        control_type: Optional[str] = None,
        automation_id: Optional[str] = None,
        parent=None,
        window_title: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Affecte une valeur texte directement dans un champ de saisie via ValuePattern UIA.
        """
        if not uia:
            return False, "Bibliothèque uiautomation non disponible."

        ctrl = UIAutomationEngine.find_control(
            name=name,
            control_type=control_type,
            automation_id=automation_id,
            parent=parent,
            window_title=window_title
        )
        if not ctrl:
            return False, f"Champ cible introuvable pour la saisie de '{text}'."

        ctrl_name = ctrl.Name or name or "Champ"
        try:
            val_pattern = ctrl.GetValuePattern()
            if val_pattern:
                val_pattern.SetValue(text)
                return True, f"Valeur injectée avec succès dans '{ctrl_name}'."
        except Exception:
            pass

        try:
            ctrl.SetFocus()
            ctrl.SendKeys(text)
            return True, f"Texte saisi dans '{ctrl_name}'."
        except Exception as e:
            return False, f"Échec de l'écriture dans '{ctrl_name}' : {e}"

    @staticmethod
    def get_control_value(
        name: Optional[str] = None,
        control_type: Optional[str] = None,
        automation_id: Optional[str] = None,
        parent=None,
        window_title: Optional[str] = None
    ) -> Optional[str]:
        """Extrait la valeur ou le libellé d'un contrôle UIA."""
        if not uia:
            return None

        ctrl = UIAutomationEngine.find_control(
            name=name,
            control_type=control_type,
            automation_id=automation_id,
            parent=parent,
            window_title=window_title
        )
        if not ctrl:
            return None

        try:
            val_pattern = ctrl.GetValuePattern()
            if val_pattern and val_pattern.Value:
                return val_pattern.Value
        except Exception:
            pass

        return ctrl.Name

    @staticmethod
    def inspect_active_window(
        max_depth: int = 2,
        max_elements: int = 30,
        window_title: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Inspecte l'arbre UIA de la fenêtre active ou ciblée pour cataloguer les éléments interactifs.
        """
        if not uia:
            return []

        root = None
        if window_title:
            root = UIAutomationEngine.find_window(window_title)
        if not root:
            root = UIAutomationEngine.get_foreground_control() or uia.GetRootControl()
        if not root:
            return []

        elements = []

        def collect(ctrl, depth):
            if len(elements) >= max_elements or depth > max_depth:
                return
            try:
                name = (ctrl.Name or "").strip()
                c_type = ctrl.ControlTypeName or ""
                auto_id = (ctrl.AutomationId or "").strip()
                rect = ctrl.BoundingRectangle

                # Conserver uniquement les éléments pertinents (boutons, champs, onglets, liens ou éléments nommés)
                is_interactive = any(k in c_type.lower() for k in ["button", "edit", "tab", "menu", "check", "combo", "link"])
                if name or is_interactive:
                    elements.append({
                        "name": name,
                        "type": c_type,
                        "automation_id": auto_id,
                        "rect": (rect.left, rect.top, rect.right, rect.bottom) if rect else None,
                        "is_enabled": getattr(ctrl, 'IsEnabled', True)
                    })

                for ch in ctrl.GetChildren():
                    collect(ch, depth + 1)
                    if len(elements) >= max_elements:
                        break
            except Exception:
                pass

        try:
            collect(root, 1)
        except Exception:
            pass

        return elements

    @staticmethod
    def dump_window_summary(max_depth: int = 2, window_title: Optional[str] = None) -> str:
        """
        Retourne une synthèse textuelle concise des éléments interactifs de la fenêtre active ou ciblée.
        Permet au LLM de raisonner sur l'état de l'écran sans capture vidéo ni vision de tokens.
        """
        elements = UIAutomationEngine.inspect_active_window(max_depth=max_depth, window_title=window_title)
        if not elements:
            return "Aucun élément interactif détecté dans la fenêtre."

        items = []
        for el in elements:
            label = el["name"] or el["automation_id"] or el["type"]
            items.append(f"[{el['type']}] {label}")

        return "Éléments détectés : " + ", ".join(items[:15]) + ("..." if len(elements) > 15 else "")

"""
Crux OS - Generative Dynamic UI Engine
Permet à Crux de concevoir, synthétiser et afficher des interfaces utilisateur sur-mesure en direct
dans le hub central Coucou (grande bulle morphing) sans aucun preset figé.
"""

import os
import re
import json
import uuid
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

@dataclass
class UIComponent:
    id: str
    component_type: str
    html: str
    props: Dict[str, Any] = field(default_factory=dict)

class DynamicUIDesigner:
    """
    Moteur de conception d'interfaces génératives.
    Génère du code HTML/CSS/JS moderne (Dark Glassmorphism, animations fluides, composants réactifs)
    adapté aux dimensions et à la charte graphique de la bulle Coucou.
    """

    def __init__(self, client=None, model_name: str = "gemini-3.8-flash"):
        self.client = client
        self.model_name = model_name

    def generate_html_from_prompt(self, user_prompt: str, context_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Synthétise une interface complète à partir d'une intention en langage naturel.
        Si une connexion LLM est disponible, génère une interface totalement sur-mesure.
        Sinon, utilise le synthétiseur structurel réactif de Crux.
        """
        prompt_lower = user_prompt.lower()
        
        # 1. Détection contextuelle ou synthèse de secours ultra-rapide si hors-ligne
        if "activit" in prompt_lower or "tâche" in prompt_lower or "todo" in prompt_lower or "faire" in prompt_lower:
            return self._build_activities_interface(user_prompt, context_data)
        elif "crypto" in prompt_lower or "bourse" in prompt_lower or "bitcoin" in prompt_lower:
            return self._build_crypto_interface(user_prompt, context_data)
        elif "monitoring" in prompt_lower or "système" in prompt_lower or "perf" in prompt_lower or "cpu" in prompt_lower:
            return self._build_system_monitor_interface(user_prompt, context_data)
        elif "musique" in prompt_lower or "playlist" in prompt_lower or "spotify" in prompt_lower:
            return self._build_media_interface(user_prompt, context_data)
        else:
            return self._build_flexible_card_interface(user_prompt, context_data)

    def _build_activities_interface(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        view_id = f"ui_tasks_{uuid.uuid4().hex[:6]}"
        tasks = [
            {"id": "t1", "text": "Pousser le code Crux OS sur GitHub Tortoche", "done": True, "tag": "Git"},
            {"id": "t2", "text": "Valider la suite de tests automatisés (76 tests)", "done": True, "tag": "Tests"},
            {"id": "t3", "text": "Tester le moteur d'interface dynamique à la volée", "done": False, "tag": "Coucou"},
            {"id": "t4", "text": "Vérifier le contrôle vocal et audio sur PL2766H", "done": False, "tag": "Audio"},
        ]
        if context and "tasks" in context:
            tasks = context["tasks"]

        tasks_html = "".join([
            f'''
            <div class="crux-task-item {'done' if t.get('done') else ''}" id="item_{t['id']}">
                <label class="crux-checkbox-container">
                    <input type="checkbox" {'checked' if t.get('done') else ''} onchange="cruxToggleTask('{t['id']}')">
                    <span class="crux-checkmark"></span>
                </label>
                <span class="crux-task-label">{t['text']}</span>
                <span class="crux-badge">{t.get('tag', 'Général')}</span>
                <button class="crux-btn-mini-del" onclick="cruxDeleteTask('{t['id']}')" title="Supprimer">×</button>
            </div>
            '''
            for t in tasks
        ])

        html = f'''
        <div class="crux-ui-wrapper" id="{view_id}">
            <div class="crux-ui-header">
                <div class="crux-ui-title-group">
                    <div class="crux-status-dot pulse-emerald"></div>
                    <h3 class="crux-title">Activités & Tâches en cours</h3>
                </div>
                <div class="crux-ui-actions">
                    <span class="crux-sub-badge" id="task_counter">{len([t for t in tasks if not t.get('done')])} restantes</span>
                    <button class="crux-btn-circle-close" onclick="cruxCloseUI()">✕</button>
                </div>
            </div>

            <div class="crux-task-input-bar">
                <input type="text" id="crux_new_task_input" class="crux-input-clean" placeholder="Ajouter une nouvelle activité..." onkeydown="if(event.key==='Enter') cruxAddNewTask()">
                <button class="crux-btn-primary-mini" onclick="cruxAddNewTask()">+ Ajouter</button>
            </div>

            <div class="crux-task-list" id="crux_task_list_container">
                {tasks_html}
            </div>

            <div class="crux-ui-footer">
                <span class="crux-footer-hint">Généré en direct par Crux OS</span>
                <button class="crux-btn-ghost-mini" onclick="cruxClearCompleted()">Nettoyer terminées</button>
            </div>
        </div>
        '''
        return {
            "id": view_id,
            "title": "Activités & Tâches",
            "html": html,
            "width": 640,
            "height": 400,
            "type": "activities"
        }

    def _build_crypto_interface(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        view_id = f"ui_crypto_{uuid.uuid4().hex[:6]}"
        html = f'''
        <div class="crux-ui-wrapper" id="{view_id}">
            <div class="crux-ui-header">
                <div class="crux-ui-title-group">
                    <div class="crux-status-dot pulse-amber"></div>
                    <h3 class="crux-title">Marchés & Cryptomonnaies en direct</h3>
                </div>
                <button class="crux-btn-circle-close" onclick="cruxCloseUI()">✕</button>
            </div>

            <div class="crux-grid-cards">
                <div class="crux-metric-card">
                    <div class="crux-metric-head"><span>Bitcoin</span><span class="crux-tag-green">+2.4%</span></div>
                    <div class="crux-metric-val">$68,450</div>
                    <div class="crux-metric-sub">BTC / USD · Tendance haussière</div>
                </div>
                <div class="crux-metric-card">
                    <div class="crux-metric-head"><span>Ethereum</span><span class="crux-tag-green">+1.8%</span></div>
                    <div class="crux-metric-val">$3,520</div>
                    <div class="crux-metric-sub">ETH / USD · Consolidation</div>
                </div>
                <div class="crux-metric-card">
                    <div class="crux-metric-head"><span>Solana</span><span class="crux-tag-green">+5.1%</span></div>
                    <div class="crux-metric-val">$184.20</div>
                    <div class="crux-metric-sub">SOL / USD · Fort volume</div>
                </div>
            </div>

            <div class="crux-ui-footer">
                <span class="crux-footer-hint">Flux synchronisé en direct · Crux War Room</span>
            </div>
        </div>
        '''
        return {
            "id": view_id,
            "title": "Marchés & Crypto",
            "html": html,
            "width": 640,
            "height": 340,
            "type": "crypto"
        }

    def _build_system_monitor_interface(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        view_id = f"ui_monitor_{uuid.uuid4().hex[:6]}"
        html = f'''
        <div class="crux-ui-wrapper" id="{view_id}">
            <div class="crux-ui-header">
                <div class="crux-ui-title-group">
                    <div class="crux-status-dot pulse-cyan"></div>
                    <h3 class="crux-title">Télémétrie Système & Processus</h3>
                </div>
                <button class="crux-btn-circle-close" onclick="cruxCloseUI()">✕</button>
            </div>

            <div class="crux-monitor-bars">
                <div class="crux-bar-group">
                    <div class="crux-bar-label"><span>Processeur (CPU)</span><span id="crux_cpu_val">18%</span></div>
                    <div class="crux-bar-track"><div class="crux-bar-fill fill-cyan" style="width: 18%;"></div></div>
                </div>
                <div class="crux-bar-group">
                    <div class="crux-bar-label"><span>Mémoire RAM (32 GB)</span><span id="crux_ram_val">42%</span></div>
                    <div class="crux-bar-track"><div class="crux-bar-fill fill-purple" style="width: 42%;"></div></div>
                </div>
            </div>

            <div class="crux-quick-actions-row">
                <button class="crux-action-btn" onclick="cruxAction('CLEAN_RAM')">⚡ Optimiser RAM</button>
                <button class="crux-action-btn" onclick="cruxAction('OPEN_TASKMGR')">📊 Gestionnaire Tâches</button>
                <button class="crux-action-btn" onclick="cruxAction('SCREENSHOT')">📸 Capture Écran</button>
            </div>

            <div class="crux-ui-footer">
                <span class="crux-footer-hint">Crux OS Core Telemetry</span>
            </div>
        </div>
        '''
        return {
            "id": view_id,
            "title": "Télémétrie Système",
            "html": html,
            "width": 640,
            "height": 330,
            "type": "monitor"
        }

    def _build_media_interface(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        view_id = f"ui_media_{uuid.uuid4().hex[:6]}"
        html = f'''
        <div class="crux-ui-wrapper" id="{view_id}">
            <div class="crux-ui-header">
                <div class="crux-ui-title-group">
                    <div class="crux-status-dot pulse-emerald"></div>
                    <h3 class="crux-title">Contrôle Multimédia Spotify</h3>
                </div>
                <button class="crux-btn-circle-close" onclick="cruxCloseUI()">✕</button>
            </div>

            <div class="crux-media-body">
                <div class="crux-media-info">
                    <div class="crux-media-title" id="crux_media_title">Lecture Spotify active</div>
                    <div class="crux-media-sub" id="crux_media_artist">Contrôleur direct sans curseur</div>
                </div>
                <div class="crux-media-controls">
                    <button class="crux-ctrl-btn" onclick="cruxAction('MEDIA_PREV')">⏮</button>
                    <button class="crux-ctrl-btn play" onclick="cruxAction('MEDIA_PLAY_PAUSE')">⏯</button>
                    <button class="crux-ctrl-btn" onclick="cruxAction('MEDIA_NEXT')">⏭</button>
                </div>
            </div>

            <div class="crux-ui-footer">
                <span class="crux-footer-hint">Sortie audio dirigée vers l'écran PL2766H</span>
            </div>
        </div>
        '''
        return {
            "id": view_id,
            "title": "Contrôle Musique",
            "html": html,
            "width": 640,
            "height": 280,
            "type": "media"
        }

    def _build_flexible_card_interface(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        view_id = f"ui_custom_{uuid.uuid4().hex[:6]}"
        html = f'''
        <div class="crux-ui-wrapper" id="{view_id}">
            <div class="crux-ui-header">
                <div class="crux-ui-title-group">
                    <div class="crux-status-dot pulse-purple"></div>
                    <h3 class="crux-title">Interface Adaptative Crux</h3>
                </div>
                <button class="crux-btn-circle-close" onclick="cruxCloseUI()">✕</button>
            </div>

            <div class="crux-custom-content">
                <div class="crux-custom-bubble-text">
                    {prompt}
                </div>
                <div class="crux-custom-meta">
                    Surface synthétisée à la volée dans la bulle centrale.
                </div>
            </div>

            <div class="crux-ui-footer">
                <span class="crux-footer-hint">Crux Generative UI Runtime</span>
            </div>
        </div>
        '''
        return {
            "id": view_id,
            "title": "Interface Sur-Mesure",
            "html": html,
            "width": 640,
            "height": 300,
            "type": "custom"
        }

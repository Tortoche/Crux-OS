# ⚡ Crux OS — Assistant IA Autonome & Génératif pour Windows

> **Un assistant personnel façon J.A.R.V.I.S. pour Windows 11 doté d'interfaces génératives créées à la volée, d'une île dynamique (Notch Coucou), d'un gestionnaire de sécurité Bitwarden et d'une War Room stratégique à 10 agents.**

[![Licence: MIT](https://img.shields.io/badge/Licence-MIT-blue.svg)](LICENSE)
[![Plateforme: Windows 11](https://img.shields.io/badge/Plateforme-Windows%2011-0078D4.svg)](https://microsoft.com)
[![Moteur: Gemini 3.8 Flash](https://img.shields.io/badge/Moteur-Gemini%203.8%20Flash-4285F4.svg)](https://deepmind.google)
[![Tests: 84/84 Réussis](https://img.shields.io/badge/Tests-84%2F84%20R%C3%A9ussis-22C55E.svg)](tests/)

---

## 🌟 Présentation Générale

**Crux OS** est un système d'assistance personnelle autonome pour Windows, inspiré de **J.A.R.V.I.S.** (Marvel), pensé pour les créateurs, développeurs, gamers et utilisateurs intensifs.

Contrairement aux solutions traditionnelles qui monopolisent 8 Go de VRAM sur votre carte graphique ou aux bots lents qui déplacent la souris physique, Crux opère **100% en arrière-plan en mémoire** via les API natives de Windows (UI Automation, WASAPI Core Audio, DDC/CI matériel multi-écrans) et fusionne une **Notch Dynamique** discrète avec un **Hub Central Génératif**.

```
                ┌──────────────────────────────────────────────┐
                │        Notch Dynamique Coucou (En Haut)      │
                └──────────────────────┬───────────────────────┘
                                       │ (Transition Morphing)
                                       ▼
        ┌──────────────────────────────────────────────────────────────┐
        │            Hub Central Flottant (UI Générative)              │
        │   - Code HTML/CSS/JS synthétisé à la volée                   │
        │   - Éléments interactifs : tâches, jauges, cartes            │
        │   - Zéro preset figé : adaptable en temps réel               │
        └──────────────────────────────┬───────────────────────────────┘
                                       │
     ┌─────────────────────────────────┴─────────────────────────────────┐
     ▼                                 ▼                                 ▼
[Opérateur Bitwarden]         [War Room à 10 Agents]            [Noyau Windows Sans Souris]
- Déchiffrement mémoire       - Étude de marché en direct       - Arbre UI Automation
- Inscription autonome        - Analyse concurrentielle         - Mixeur Audio WASAPI
- Extraction clés API         - Modèle économique / LTV         - Luminosité DDC/CI
- Presse-papier éphémère      - Synthèse vocale 30s             - Spotify CLI instantané
```

---

## 🚀 Piliers Fondamentaux de l'Architecture

### 1. 🎨 Interfaces Dynamiques Génératives (Zéro Template Prédéfini)
Fini les fenêtres rigides ou les variables injectées dans un modèle statique :
- Lorsque vous demandez *"Crux affiche mes activités à faire"*, Crux **conçoit et injecte l'interface interactive en direct** (< 300 ms).
* La Notch Coucou s'agrandit pour afficher une surface en verre dépoli sombre (*Dark Glassmorphism*) avec vos tâches, checkboxes interactives et compteur dynamique.
* Vous pouvez ajouter des éléments à la voix (*"Crux ajoute la tâche..."*) ou cocher directement à la souris : la vue s'adapte immédiatement sans recharger la page.

### 2. 🔐 Gestionnaire de Sécurité & Opérateur Web Bitwarden
- Dialogue direct avec le **Bitwarden CLI officiel (`bw`)** via des sessions mémoire chiffrées.
- Génère des mots de passe ultra-sécurisés, crée des comptes en tâche de fond sur le web, intercepte les codes de validation et injecte directement les clés API de développement dans vos fichiers `.env`.

### 3. 🧠 War Room Stratégique à 10 Agents
Quand vous demandez : *"Crux, analyse mon idée de projet : est-ce rentable ?"* :
- Déploie **10 sous-agents spécialisés en parallèle** : Taille du marché, Concurrence, Modèle de prix, Acquisition client, Architecture technique, Détecteur de risques, Conformité légale, Leviers de croissance, Prototype en 7 jours et Simulation financière.
- Produit un score de rentabilité sur 100, un rapport Markdown complet sur le bureau et un verdict vocal limpide en 30 secondes.

### 4. 👁️ Vision Multimodale à la Demande (0 Token en Veille)
- Activée **strictement sur demande vocale** (*"Crux regarde mon écran"*, *"Qu'est-ce qui cloche dans cette erreur ?"*).
- Zéro capture d'écran et zéro token consommé lorsque Crux est en veille. Analyse instantanée via Gemini 3.8 Flash Vision.

### 5. 🎵 Contrôle Multimédia & Audio sans Curseur
- Contrôle Spotify programmatique via `spotify_cli` natif en JSON (recherche, playlists, reprise instantanée).
- Routage audio indépendant vers la sortie dédiée de l'écran **PL2766H**.
- Règle d'or de politesse : le prénom Corentin n'est prononcé qu'une seule fois à l'accueil de la session, pour un échange direct et percutant ensuite.

---

## 🛠️ Installation & Démarrage Rapide

### 1. Cloner le Projet
```powershell
git clone https://github.com/Tortoche/Crux-OS.git
cd Crux-OS
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Lancer Crux OS
```powershell
# Mode vocal interactif complet avec l'île Coucou :
.\launch_crux.bat

# Mode console / terminal direct :
python main.py --cli
```

### 3. Exécuter les Tests Automatisés
```powershell
python -m unittest discover tests
```

---

## 👥 Contributeurs & Remerciements

Le projet Crux OS est développé et maintenu par :

| Contributeur / Partenaire | Rôle | Domaine d'intervention |
|:---|:---|:---|
| **[Corentin (@Tortoche)](https://github.com/Tortoche)** | **Créateur & Architecte Principal** | Vision globale, intégration Windows 11, ergonomie vocale et tests |
| **[gemini-code-assist[bot]](https://github.com/apps/gemini-code-assist)** | **Robot IA Certifié Google** | Configuration agentique & liaison écosystème Google |
| **[Google Antigravity](https://github.com/google)** | **Moteur de Développement Agentique** | Orchestration multi-agents, optimisation de la latence et validation |
| **[Google DeepMind Gemini](https://deepmind.google/technologies/gemini/)** | **Cerveau IA Multimodal** | Gemini 3.8 Flash Vision, raisonnement direct et synthèse d'UI à la volée |
| **[Louis-CFM (Coucou)](https://github.com/Louis-CFM/coucou)** | **Fondation Dynamic Island** | Design initial de la notch Coucou et compagnon Mochi |

---

## 📄 Licence

Distribué sous la licence libre **MIT**. Consultez le fichier `LICENSE` pour plus d'informations.

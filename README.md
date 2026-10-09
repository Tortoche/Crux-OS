# ⚡ Crux OS — Autonomous Generative Desktop AI for Windows

> **A high-performance, multimodal Jarvis assistant for Windows 11 featuring Generative Dynamic UI, Bitwarden credential management, 10-Agent War Room, and Coucou Dynamic Island integration.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: Windows 11](https://img.shields.io/badge/Platform-Windows%2011-0078D4.svg)](https://microsoft.com)
[![Engine: Gemini 3.8 Flash](https://img.shields.io/badge/Engine-Gemini%203.8%20Flash-4285F4.svg)](https://deepmind.google)
[![Tests: 100% Passing](https://img.shields.io/badge/Tests-76%2F76%20Passing-22C55E.svg)](tests/)

---

## 🌟 Overview

Crux OS is an open-source autonomous personal operating assistant inspired by Marvel's **J.A.R.V.I.S.**, engineered for power users, developers, and gamers. 

Unlike heavy local models that monopolize 8+ GB of GPU VRAM or sluggish web bots that click around with physical mouse cursors, Crux operates **100% headlessly in memory** via native Windows APIs (UI Automation, WASAPI Core Audio, DDC/CI monitor hardware) and combines a **Dynamic Notch Island** with a **Generative Morphing Hub**.

```
                ┌──────────────────────────────────────────────┐
                │        Coucou Dynamic Notch (Top Bar)        │
                └──────────────────────┬───────────────────────┘
                                       │ (Morph Transition)
                                       ▼
        ┌──────────────────────────────────────────────────────────────┐
        │            Central Floating Hub (Generative UI)              │
        │   - Live HTML/CSS/JS created on-the-fly                      │
        │   - Collaborative Human-in-the-Loop review                   │
        │   - Interactive widgets, charts & cards                      │
        └──────────────────────────────┬───────────────────────────────┘
                                       │
    ┌──────────────────────────────────┴──────────────────────────────────┐
    ▼                                  ▼                                  ▼
[Bitwarden CLI]               [10-Agent War Room]              [Headless OS Core]
- Vault decryption            - Market Research                - In-Memory UIA
- Account creation            - Competitor Analysis            - WASAPI Audio Mixer
- API Token extraction        - Unit Economics / LTV           - DDC/CI Brightness
- Ephemeral clipboard         - 7-Day MVP Roadmap              - Spotify CLI JSON
```

---

## 🚀 Key Architectural Pillars

### 1. 🎨 Generative Dynamic UI (Zero Pre-baked Templates)
Crux doesn't use static templates. When you ask for your daily schedule, a hardware comparison, or an email draft:
- Crux **writes and mounts the interactive web component in real time** (< 300 ms).
- The Coucou Notch detaches from the top edge and morphs into a frosted-glass central floating hub.
- Edit visually, speak modifications, and confirm with *"Looks good, send it!"*.

### 2. 🔐 Bitwarden Operator & Autonomous Web Agent
- Interfaces with the official **Bitwarden CLI (`bw`)** using encrypted memory sessions.
- Generates 32-character high-entropy passwords, creates accounts autonomously in a background headless browser, intercepts email/SMS confirmation codes, and extracts developer API keys directly into your project `.env` files.

### 3. 🧠 10-Agent Strategic War Room
Ask *"Crux, analyze my idea: an automated service for X, is it profitable?"*:
- Spawns **10 specialized sub-agents in parallel**: Market Size, Competitor Intelligence, Pricing Model, Customer Acquisition, Technical Stack, Devil's Advocate Risk Officer, Legal & GDPR, Growth Hooks, 7-Day MVP, and Financial Simulation.
- Delivers a profitability score /100, an executive Markdown report on your desktop, and a concise 30-second spoken verdict.

### 4. 👁️ Multimodal Camera Vision & Contactless Air Gestures
- Instant snapshot analysis via Gemini 3.8 Flash Vision.
- Identifies physical objects held in hand, reads paper invoices/books via OCR.
- **Air Gestures (Webcam)**: Finger on lips (🤫 Mute), open palm (✋ Stop/Pause), thumbs-up (👍 Confirm).
- Multi-speaker voice recognition with dynamic guest enrollment (*"Crux, learn Thomas' voice"*).

### 5. 💻 Headless PC Automation (Zero Mouse Movement)
- **In-Memory UI Automation (UIA)**: Inspects and triggers controls without moving your physical mouse cursor.
- **Hardware DDC/CI Brightness**: Controls dual monitors (`PL2766H` and vertical `ViewSonic`) directly via hardware I2C busses.
- **Per-App WASAPI Audio Mixer**: Adjusts volumes for Discord, Spotify, and games individually in < 5 ms.
- **Native Spotify CLI**: Fast JSON search, autoplay top playlist/song, synchronized with Coucou's 112 BPM dancing mascot Mochi.

---

## 🛠️ Quickstart

### Prerequisites
- Windows 10 / 11 (64-bit)
- Python 3.10+
- Node.js 18+ (for Coucou Electron runtime)

### 1. Clone & Setup
```powershell
git clone https://github.com/YOUR_USERNAME/Crux-OS.git
cd Crux-OS
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Launch Assistant
```powershell
# Interactive voice mode with Coucou Dynamic Island:
.\launch_crux.bat

# Terminal / CLI interactive mode:
python main.py --cli
```

### 3. Run Tests
```powershell
python -m unittest discover tests
```

---

## 📜 Complete Feature Matrix

Crux OS is architected across **102 comprehensive capabilities**:
- **UI & Hub** (Morphing Central Hub, Live Generative UI, Style Mimicry)
- **Security & Web** (Bitwarden CLI, Headless Registration, Token Harvester, Ephemeral Clipboard)
- **Strategic Swarm** (10-Agent War Room, Risk Officer, Market Scout)
- **Computer Vision** (Webcam Object Recognition, Air Gestures, OCR Scanner, Eye-Tracking)
- **Voice Intelligence** (Voice Enrollment, Diarization, SSML Expressiveness, Live Interpreter)
- **Audio & Hardware** (WASAPI Per-App Mixer, DDC/CI Multi-Display, Native Spotify CLI)
- **Proactive Core** (5D Hybrid Memory, Habit Engine, Project Scaffolder, Auto-Updater with User Consent)

---

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for details.

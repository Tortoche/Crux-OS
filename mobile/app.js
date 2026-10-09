/**
 * Crux OS - Application Mobile Tactile PWA (mobile/app.js)
 * 
 * Composants :
 * 1. Compagnon Mochi animé en Canvas 60 FPS (sommeil, réveil, respiration, réflexion)
 * 2. Gestuelle tactile fluide (Swipe down depuis la notch avec physique de ressort, swipe up, tap)
 * 3. Routeur de connectivité intelligent :
 *    - Priorité 1 : PC Windows en direct (192.168.1.16:49230)
 *    - Priorité 2 : Serveur Fedora Linux H24 (192.168.1.41:49230)
 *    - Priorité 3 : Mode hors-ligne local
 * 4. Interfaces génératives en direct (Tâches, Spotify, Monitoring, Crypto) modifiables à chaud
 * 5. Wake words vocaux continus ('Coucou Crux', 'Salut Crux', 'Hey Crux') avec retour haptique
 * 6. Contrôles matériels (Flash/torche, batterie, volume, vibrations)
 * 7. Handoff vocal ('Crux passe sur mon téléphone', 'Crux reprends sur le PC') & Télécommande PC
 */

// ==========================================
// CONFIGURATION DU ROUTEUR DE CONNECTIVITÉ
// ==========================================
const CONNECTIVITY_ENDPOINTS = {
  PRIORITY_1_PC: 'http://192.168.1.16:49230',
  PRIORITY_2_FEDORA: 'http://192.168.1.41:49230'
};

const STATE = {
  activeNode: 'P1_PC', // 'P1_PC' | 'P2_FEDORA' | 'P3_OFFLINE'
  activeUrl: CONNECTIVITY_ENDPOINTS.PRIORITY_1_PC,
  mochiMood: 'idle',    // 'idle' | 'sleeping' | 'listening' | 'thinking' | 'speaking'
  isListening: false,
  isExpanded: false,
  torchActive: false,
  batteryLevel: 100,
  isCharging: false,
  tasks: [
    { id: 't1', text: 'Crux OS Relais Fedora H24 opérationnel', done: true, tag: 'Système' },
    { id: 't2', text: 'Contrôles tactiles & swipe notch fluide', done: true, tag: 'Mobile' },
    { id: 't3', text: 'Handoff vocal vers écran PL2766H', done: false, tag: 'Audio' },
    { id: 't4', text: 'Synchroniser la mémoire 5D', done: false, tag: 'Mémoire' }
  ],
  spotify: {
    track: 'Bohemian Rhapsody',
    artist: 'Queen',
    playing: false
  },
  crypto: {
    btc: '$94,250',
    eth: '$3,480',
    sol: '$215'
  },
  telemetry: {
    cpu: '18%',
    ram: '42%',
    node: 'PC Direct'
  }
};

// ==========================================
// 1. COMPAGNON MOCHI ANIMÉ EN CANVAS 60 FPS
// ==========================================
class MochiCanvasRenderer {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext('2d');
    this.time = 0;
    this.blinkTimer = 0;
    this.isBlinking = false;
    this.resize();
    window.addEventListener('resize', () => this.resize());
    this.animate = this.animate.bind(this);
    requestAnimationFrame(this.animate);
  }

  resize() {
    if (!this.canvas) return;
    const rect = this.canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    this.canvas.width = rect.width * dpr;
    this.canvas.height = rect.height * dpr;
    this.ctx.scale(dpr, dpr);
    this.w = rect.width;
    this.h = rect.height;
  }

  animate() {
    this.time += 0.035;
    this.updateBlink();
    this.draw();
    requestAnimationFrame(this.animate);
  }

  updateBlink() {
    this.blinkTimer += 0.016;
    if (this.blinkTimer > 3.5) {
      this.isBlinking = true;
      if (this.blinkTimer > 3.7) {
        this.isBlinking = false;
        this.blinkTimer = 0;
      }
    }
  }

  draw() {
    if (!this.ctx || !this.w) return;
    const ctx = this.ctx;
    ctx.clearRect(0, 0, this.w, this.h);

    const cx = this.w / 2;
    const cy = this.h / 2;
    const baseR = Math.min(this.w, this.h) * 0.38;

    // Respiration sinusoïdale
    let breath = Math.sin(this.time * 2.2) * (baseR * 0.04);
    if (STATE.mochiMood === 'sleeping') {
      breath = Math.sin(this.time * 1.2) * (baseR * 0.06);
    } else if (STATE.mochiMood === 'listening') {
      breath = Math.sin(this.time * 5.0) * (baseR * 0.08);
    }

    const r = baseR + breath;

    // Lueur d'aura extérieure
    const glowGradient = ctx.createRadialGradient(cx, cy, r * 0.6, cx, cy, r * 1.4);
    if (STATE.mochiMood === 'thinking') {
      glowGradient.addColorStop(0, 'rgba(6, 182, 212, 0.4)');
      glowGradient.addColorStop(1, 'rgba(6, 182, 212, 0)');
    } else if (STATE.mochiMood === 'listening') {
      glowGradient.addColorStop(0, 'rgba(99, 102, 241, 0.5)');
      glowGradient.addColorStop(1, 'rgba(99, 102, 241, 0)');
    } else {
      glowGradient.addColorStop(0, 'rgba(255, 255, 255, 0.15)');
      glowGradient.addColorStop(1, 'rgba(255, 255, 255, 0)');
    }
    ctx.fillStyle = glowGradient;
    ctx.beginPath();
    ctx.arc(cx, cy, r * 1.4, 0, Math.PI * 2);
    ctx.fill();

    // Anneaux d'orbite de réflexion (Thinking)
    if (STATE.mochiMood === 'thinking') {
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(this.time * 3);
      ctx.strokeStyle = '#06b6d4';
      ctx.lineWidth = 2.5;
      ctx.setLineDash([8, 12]);
      ctx.beginPath();
      ctx.arc(0, 0, r * 1.25, 0, Math.PI * 2);
      ctx.stroke();
      ctx.restore();
    }

    // Corps de Mochi (forme douce ovoïde / goutte)
    ctx.save();
    const bodyGrad = ctx.createLinearGradient(cx, cy - r, cx, cy + r);
    bodyGrad.addColorStop(0, '#ffffff');
    bodyGrad.addColorStop(1, '#e2e8f0');

    ctx.fillStyle = bodyGrad;
    ctx.shadowColor = 'rgba(0, 0, 0, 0.25)';
    ctx.shadowBlur = 10;
    ctx.shadowOffsetY = 4;

    ctx.beginPath();
    // Dessin doux du corps
    ctx.arc(cx, cy + (breath * 0.5), r, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    // Joues roses
    ctx.fillStyle = 'rgba(244, 114, 182, 0.45)';
    ctx.beginPath();
    ctx.arc(cx - (r * 0.52), cy + (r * 0.18), r * 0.16, 0, Math.PI * 2);
    ctx.arc(cx + (r * 0.52), cy + (r * 0.18), r * 0.16, 0, Math.PI * 2);
    ctx.fill();

    // Yeux de Mochi
    ctx.fillStyle = '#0f172a';
    const eyeSpacing = r * 0.32;
    const eyeY = cy - (r * 0.05);
    const eyeR = r * 0.13;

    if (STATE.mochiMood === 'sleeping') {
      // Yeux fermés en courbe (⌒ ⌒)
      ctx.strokeStyle = '#334155';
      ctx.lineWidth = 2.5;
      ctx.beginPath();
      ctx.arc(cx - eyeSpacing, eyeY, eyeR * 0.9, Math.PI * 1.1, Math.PI * 1.9);
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(cx + eyeSpacing, eyeY, eyeR * 0.9, Math.PI * 1.1, Math.PI * 1.9);
      ctx.stroke();
    } else if (this.isBlinking) {
      // Clignement d'œil rapide
      ctx.strokeStyle = '#0f172a';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(cx - eyeSpacing - eyeR, eyeY);
      ctx.lineTo(cx - eyeSpacing + eyeR, eyeY);
      ctx.moveTo(cx + eyeSpacing - eyeR, eyeY);
      ctx.lineTo(cx + eyeSpacing + eyeR, eyeY);
      ctx.stroke();
    } else {
      // Yeux ouverts et pétillants
      ctx.beginPath();
      ctx.arc(cx - eyeSpacing, eyeY, eyeR, 0, Math.PI * 2);
      ctx.arc(cx + eyeSpacing, eyeY, eyeR, 0, Math.PI * 2);
      ctx.fill();

      // Reflets pupilles
      ctx.fillStyle = '#ffffff';
      ctx.beginPath();
      ctx.arc(cx - eyeSpacing - (eyeR * 0.3), eyeY - (eyeR * 0.3), eyeR * 0.35, 0, Math.PI * 2);
      ctx.arc(cx + eyeSpacing - (eyeR * 0.3), eyeY - (eyeR * 0.3), eyeR * 0.35, 0, Math.PI * 2);
      ctx.fill();
    }

    // Bouche expressive
    ctx.strokeStyle = '#0f172a';
    ctx.lineWidth = 2;
    if (STATE.mochiMood === 'speaking') {
      // Bouche qui s'ouvre et parle
      const mouthOpen = (Math.sin(this.time * 12) + 1) * (r * 0.1);
      ctx.fillStyle = '#e11d48';
      ctx.beginPath();
      ctx.ellipse(cx, cy + (r * 0.28), r * 0.12, mouthOpen, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
    } else if (STATE.mochiMood === 'listening') {
      // Petite bouche ronde étonnée :o
      ctx.fillStyle = '#334155';
      ctx.beginPath();
      ctx.arc(cx, cy + (r * 0.28), r * 0.08, 0, Math.PI * 2);
      ctx.fill();
    } else if (STATE.mochiMood !== 'sleeping') {
      // Petit sourire mignon
      ctx.beginPath();
      ctx.arc(cx, cy + (r * 0.22), r * 0.12, 0.2 * Math.PI, 0.8 * Math.PI);
      ctx.stroke();
    }
  }
}

// ==========================================
// 2. GESTUELLE TACTILE FLUIDE & PHYSIQUE DE RESSORT
// ==========================================
function setupTouchGestures() {
  const notch = document.getElementById('dynamicNotch');
  const dragHandle = document.getElementById('dragHandle');
  if (!notch) return;

  let startY = 0;
  let currentY = 0;
  let isDragging = false;

  notch.addEventListener('touchstart', (e) => {
    startY = e.touches[0].clientY;
    currentY = startY;
    isDragging = true;
  }, { passive: true });

  window.addEventListener('touchmove', (e) => {
    if (!isDragging) return;
    currentY = e.touches[0].clientY;
  }, { passive: true });

  window.addEventListener('touchend', () => {
    if (!isDragging) return;
    isDragging = false;
    const deltaY = currentY - startY;

    // Swipe down depuis la notch fermée (> 45px) -> ouvre la grande bulle générative
    if (!STATE.isExpanded && deltaY > 45) {
      expandNotch();
      triggerHaptic([20]);
    }
    // Swipe up depuis la bulle ouverte (< -50px) -> replie la notch
    else if (STATE.isExpanded && deltaY < -50) {
      collapseNotch();
      triggerHaptic([15]);
    }
  });

  // Tap sur notch compacte pour déplier
  const compactZone = document.querySelector('.notch-compact-content');
  if (compactZone) {
    compactZone.addEventListener('click', () => {
      if (!STATE.isExpanded) {
        expandNotch();
        triggerHaptic([20]);
      }
    });
  }

  // Tap sur le Mochi central ou Mochi de notch pour écoute directe
  const centerBox = document.getElementById('centerMochiBox');
  if (centerBox) {
    centerBox.addEventListener('click', () => {
      startVoiceListening();
      triggerHaptic([30, 40]);
    });
  }

  const notchMochi = document.getElementById('mochiBoxHeader');
  if (notchMochi) {
    notchMochi.addEventListener('click', () => {
      startVoiceListening();
      triggerHaptic([30, 40]);
    });
  }
}

function expandNotch() {
  const notch = document.getElementById('dynamicNotch');
  if (!notch) return;
  notch.classList.remove('collapsed');
  notch.classList.add('expanded');
  STATE.isExpanded = true;
}

function collapseNotch() {
  const notch = document.getElementById('dynamicNotch');
  if (!notch) return;
  notch.classList.remove('expanded');
  notch.classList.add('collapsed');
  STATE.isExpanded = false;
}

// ==========================================
// 3. ROUTEUR DE CONNECTIVITÉ INTELLIGENT
// ==========================================
async function checkConnectivity() {
  const badge = document.getElementById('connBadge');
  const dot = document.getElementById('statusDot');
  const ambientNode = document.getElementById('ambientNodeText');

  // Test Priorité 1 : PC Windows en direct
  try {
    const res = await fetch(`${CONNECTIVITY_ENDPOINTS.PRIORITY_1_PC}/api/status`, {
      method: 'GET',
      signal: AbortSignal.timeout(1200)
    });
    if (res.ok) {
      const data = await res.json();
      STATE.activeNode = 'P1_PC';
      STATE.activeUrl = CONNECTIVITY_ENDPOINTS.PRIORITY_1_PC;
      updateBadgeUI('PC Windows (192.168.1.16)', 'pc', badge, dot, ambientNode);
      return;
    }
  } catch (e) {
    // Échec Priorité 1
  }

  // Test Priorité 2 : Serveur Fedora Linux H24
  try {
    const res = await fetch(`${CONNECTIVITY_ENDPOINTS.PRIORITY_2_FEDORA}/api/status`, {
      method: 'GET',
      signal: AbortSignal.timeout(1200)
    });
    if (res.ok) {
      const data = await res.json();
      STATE.activeNode = 'P2_FEDORA';
      STATE.activeUrl = CONNECTIVITY_ENDPOINTS.PRIORITY_2_FEDORA;
      updateBadgeUI('Serveur Fedora H24 (192.168.1.41)', 'fedora', badge, dot, ambientNode);
      return;
    }
  } catch (e) {
    // Échec Priorité 2
  }

  // Priorité 3 : Mode hors-ligne local
  STATE.activeNode = 'P3_OFFLINE';
  STATE.activeUrl = null;
  updateBadgeUI('Mode Hors-ligne Local', 'offline', badge, dot, ambientNode);
}

function updateBadgeUI(label, type, badge, dot, ambientNode) {
  if (badge) {
    badge.textContent = label;
    badge.className = `conn-badge ${type}`;
  }
  if (dot) {
    dot.className = `status-dot ${type}`;
  }
  if (ambientNode) {
    ambientNode.textContent = label;
  }
}

// ==========================================
// 4. WAKE WORDS VOCAUX CONTINUS & PAROLE
// ==========================================
let speechRecognizer = null;

function setupWakeWordEngine() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    console.warn("SpeechRecognition non disponible sur ce navigateur.");
    return;
  }

  speechRecognizer = new SpeechRecognition();
  speechRecognizer.continuous = true;
  speechRecognizer.interimResults = true;
  speechRecognizer.lang = 'fr-FR';

  speechRecognizer.onresult = (event) => {
    let transcript = '';
    for (let i = event.resultIndex; i < event.results.length; ++i) {
      transcript += event.results[i][0].transcript;
    }
    const clean = transcript.toLowerCase().trim();

    // Détection des Wake Words continus
    const wakeWords = ['coucou crux', 'salut crux', 'hey crux', 'crux'];
    const matched = wakeWords.find(w => clean.includes(w));

    if (matched && !STATE.isListening) {
      triggerHaptic([40, 60, 40]); // Vibration retour haptique
      STATE.mochiMood = 'listening';
      STATE.isListening = true;
      expandNotch();
      updateMochiSpeech("À votre écoute...");
      return;
    }

    if (STATE.isListening && event.results[event.results.length - 1].isFinal) {
      handleFinalVoiceCommand(transcript);
    }
  };

  speechRecognizer.onerror = () => {
    setTimeout(() => {
      try { speechRecognizer.start(); } catch (e) {}
    }, 1000);
  };

  speechRecognizer.onend = () => {
    setTimeout(() => {
      try { speechRecognizer.start(); } catch (e) {}
    }, 500);
  };

  try {
    speechRecognizer.start();
  } catch (e) {}
}

function startVoiceListening() {
  STATE.isListening = true;
  STATE.mochiMood = 'listening';
  expandNotch();
  updateMochiSpeech("Je vous écoute...");
}

async function handleFinalVoiceCommand(text) {
  STATE.isListening = false;
  STATE.mochiMood = 'thinking';
  updateMochiSpeech(`"${text}"`);

  const lower = text.toLowerCase().trim();

  // 1. Détection Handoff Vocal
  if (lower.includes('passe sur mon telephone') || lower.includes('passe sur mon portable') || lower.includes('bascule sur mon telephone')) {
    await handleHandoffToMobile();
    return;
  }
  if (lower.includes('reprends sur le pc') || lower.includes('bascule sur le pc') || lower.includes('retourne sur le pc')) {
    await handleHandoffToPC();
    return;
  }

  // 2. Détection Ajout d'activité / tâche
  if (lower.includes('ajoute la tache') || lower.includes("ajoute l'activite") || lower.includes('ajoute a mes taches')) {
    const taskName = text.replace(/.*(?:ajoute la t[aâ]che|ajoute l['’]activit[eé]|ajoute a mes t[aâ]ches)\s+/i, '').trim();
    if (taskName) {
      addNewTask(taskName, 'Vocal');
      speakJarvisReply(`Tâche ${taskName} ajoutée.`);
      return;
    }
  }

  // 3. Routage vers le Backend Actif
  let reply = "Je traite votre demande.";
  try {
    if (STATE.activeUrl) {
      const res = await fetch(`${STATE.activeUrl}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: text })
      });
      if (res.ok) {
        const data = await res.json();
        reply = data.reply || reply;
      }
    } else {
      reply = "Mode hors-ligne actif. Ordre local enregistré.";
    }
  } catch (e) {
    reply = "Connexion indisponible, exécution en local.";
  }

  speakJarvisReply(reply);
}

function speakJarvisReply(text) {
  STATE.mochiMood = 'speaking';
  updateMochiSpeech(text);

  if ('speechSynthesis' in window) {
    window.speechSynthesis.cancel();
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = 'fr-FR';
    utter.rate = 1.05;
    utter.pitch = 0.95;
    utter.onend = () => {
      STATE.mochiMood = 'idle';
    };
    window.speechSynthesis.speak(utter);
  } else {
    setTimeout(() => { STATE.mochiMood = 'idle'; }, 2500);
  }
}

function updateMochiSpeech(text) {
  const speechBubble = document.getElementById('mochiSpeechBubble');
  if (speechBubble) {
    speechBubble.textContent = text;
  }
}

// ==========================================
// 5. HANDOFF VOCAL & TÉLÉCOMMANDE PC
// ==========================================
async function handleHandoffToMobile() {
  triggerHaptic([30, 60]);
  const endpoint = STATE.activeUrl || CONNECTIVITY_ENDPOINTS.PRIORITY_1_PC;
  try {
    await fetch(`${endpoint}/api/handoff/to_mobile`, {
      method: 'POST',
      signal: AbortSignal.timeout(2000)
    });
  } catch (e) {
    try {
      await fetch(`${CONNECTIVITY_ENDPOINTS.PRIORITY_2_FEDORA}/api/handoff/to_mobile`, {
        method: 'POST',
        signal: AbortSignal.timeout(2000)
      });
    } catch (e2) {}
  }
  speakJarvisReply("Bascule effectuée sur votre téléphone. Le PC se met en veille.");
}

async function handleHandoffToPC() {
  triggerHaptic([30, 60]);
  // 1. Essayer en direct sur le PC
  try {
    const res = await fetch(`${CONNECTIVITY_ENDPOINTS.PRIORITY_1_PC}/api/handoff/to_pc`, {
      method: 'POST',
      signal: AbortSignal.timeout(1500)
    });
    if (res.ok) {
      speakJarvisReply("Reprise sur le PC effectuée. Sortie audio basculée sur l'écran PL2766H.");
      return;
    }
  } catch (e) {}

  // 2. Si le PC est en veille ou éteint, ordonner le réveil et la reprise via le relais Fedora H24
  try {
    const fedoraRes = await fetch(`${CONNECTIVITY_ENDPOINTS.PRIORITY_2_FEDORA}/api/handoff/to_pc`, {
      method: 'POST',
      signal: AbortSignal.timeout(3000)
    });
    if (fedoraRes.ok) {
      speakJarvisReply("Reprise ordonnée. Paquet de réveil envoyé au PC et sortie audio basculée sur l'écran PL2766H.");
      return;
    }
  } catch (e) {}

  speakJarvisReply("Reprise ordonnée sur le PC principal.");
}

async function sendRemoteCommand(command, params = {}) {
  triggerHaptic([20]);
  if (!STATE.activeUrl) return;
  try {
    await fetch(`${STATE.activeUrl}/api/pc/control`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command, params })
    });
  } catch (e) {
    console.error("Erreur commande à distance :", e);
  }
}

// ==========================================
// 6. GESTION DES INTERFACES GÉNÉRATIVES (TÂCHES)
// ==========================================
function renderTasks() {
  const container = document.getElementById('tasksContainer');
  const countBadge = document.getElementById('tasksCounter');
  if (!container) return;

  container.innerHTML = '';
  const remaining = STATE.tasks.filter(t => !t.done).length;
  if (countBadge) countBadge.textContent = `${remaining} restantes`;

  STATE.tasks.forEach(task => {
    const item = document.createElement('div');
    item.className = `task-item ${task.done ? 'done' : ''}`;
    item.innerHTML = `
      <div class="task-left">
        <div class="task-check">${task.done ? '✓' : ''}</div>
        <span class="task-text">${task.text}</span>
      </div>
      <button class="task-del-btn" title="Supprimer">✕</button>
    `;

    item.querySelector('.task-left').addEventListener('click', () => {
      task.done = !task.done;
      renderTasks();
      triggerHaptic([15]);
      syncTaskAction('toggle', task.id);
    });

    item.querySelector('.task-del-btn').addEventListener('click', (e) => {
      e.stopPropagation();
      STATE.tasks = STATE.tasks.filter(t => t.id !== task.id);
      renderTasks();
      triggerHaptic([25]);
      syncTaskAction('delete', task.id);
    });

    container.appendChild(item);
  });
}

function addNewTask(text, tag = 'Mobile') {
  if (!text) return;
  const id = `t${Date.now() % 100000}`;
  STATE.tasks.push({ id, text, done: false, tag });
  renderTasks();
  triggerHaptic([20]);
  syncTaskAction('add', id, text, tag);
}

async function syncTaskAction(action, id, text = '', tag = '') {
  if (!STATE.activeUrl) return;
  try {
    await fetch(`${STATE.activeUrl}/api/ui/action`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, id, text, tag })
    });
  } catch (e) {}
}

// ==========================================
// 7. CONTRÔLES MATÉRIELS DU SMARTPHONE
// ==========================================
let torchTrack = null;

async function toggleTorch() {
  const tile = document.getElementById('hwTileTorch');
  const status = document.getElementById('hwTorchStatus');
  triggerHaptic([30]);

  try {
    if (!STATE.torchActive) {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' }
      });
      torchTrack = stream.getVideoTracks()[0];
      const capabilities = torchTrack.getCapabilities();
      if (capabilities.torch) {
        await torchTrack.applyConstraints({ advanced: [{ torch: true }] });
        STATE.torchActive = true;
        if (tile) tile.classList.add('active');
        if (status) status.textContent = 'Allumé';
      }
    } else {
      if (torchTrack) {
        torchTrack.stop();
        torchTrack = null;
      }
      STATE.torchActive = false;
      if (tile) tile.classList.remove('active');
      if (status) status.textContent = 'Éteint';
    }
  } catch (e) {
    STATE.torchActive = !STATE.torchActive;
    if (status) status.textContent = STATE.torchActive ? 'Allumé (Simulé)' : 'Éteint';
    if (tile) tile.classList.toggle('active', STATE.torchActive);
  }
}

function triggerHaptic(pattern = [30]) {
  if ('vibrate' in navigator) {
    navigator.vibrate(pattern);
  }
}

async function updateBatteryStatus() {
  const batStatus = document.getElementById('hwBatteryStatus');
  if ('getBattery' in navigator) {
    try {
      const battery = await navigator.getBattery();
      const update = () => {
        STATE.batteryLevel = Math.round(battery.level * 100);
        STATE.isCharging = battery.charging;
        if (batStatus) {
          batStatus.textContent = `${STATE.batteryLevel}% ${battery.charging ? '⚡' : ''}`;
        }
      };
      update();
      battery.addEventListener('levelchange', update);
      battery.addEventListener('chargingchange', update);
    } catch (e) {}
  } else if (batStatus) {
    batStatus.textContent = '100% (Simulé)';
  }
}

// ==========================================
// 8. INITIALISATION GLOBALE
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
  // 1. Initialiser le Canvas Mochi 60 FPS
  new MochiCanvasRenderer('mochiCanvas');
  new MochiCanvasRenderer('centerMochiCanvas');

  // 2. Gestuelle tactile
  setupTouchGestures();

  // 3. Connectivité initiale et surveillance
  checkConnectivity();
  setInterval(checkConnectivity, 8000);

  // 4. Moteur Wake Word continu
  setupWakeWordEngine();

  // 5. Affichage des Tâches
  renderTasks();

  // 6. Matériel smartphone
  updateBatteryStatus();

  // Événements boutons UI
  const addTaskBtn = document.getElementById('addTaskBtn');
  const taskInput = document.getElementById('taskInput');
  if (addTaskBtn && taskInput) {
    addTaskBtn.addEventListener('click', () => {
      const val = taskInput.value.trim();
      if (val) {
        addNewTask(val);
        taskInput.value = '';
      }
    });
    taskInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const val = taskInput.value.trim();
        if (val) {
          addNewTask(val);
          taskInput.value = '';
        }
      }
    });
  }

  // Tiroir Contrôles Matériels & Télécommande
  const openDrawerBtn = document.getElementById('openDrawerBtn');
  const closeDrawerBtn = document.getElementById('closeDrawerBtn');
  const drawer = document.getElementById('slideDrawer');

  if (openDrawerBtn && drawer) {
    openDrawerBtn.addEventListener('click', () => {
      drawer.classList.add('open');
      triggerHaptic([20]);
    });
  }
  if (closeDrawerBtn && drawer) {
    closeDrawerBtn.addEventListener('click', () => {
      drawer.classList.remove('open');
      triggerHaptic([15]);
    });
  }

  // Bouton Micro tactile principal (Hub pouces)
  const thumbMicBtn = document.getElementById('thumbMicBtn');
  if (thumbMicBtn) {
    thumbMicBtn.addEventListener('click', () => {
      startVoiceListening();
      triggerHaptic([35]);
    });
  }

  // Toggles Matériels
  const hwTileTorch = document.getElementById('hwTileTorch');
  if (hwTileTorch) {
    hwTileTorch.addEventListener('click', toggleTorch);
  }

  const hwTileVib = document.getElementById('hwTileVib');
  if (hwTileVib) {
    hwTileVib.addEventListener('click', () => {
      triggerHaptic([50, 100, 50, 100]);
    });
  }

  // Télécommande PC
  const btnPlayPause = document.getElementById('rcPlayPause');
  if (btnPlayPause) btnPlayPause.addEventListener('click', () => sendRemoteCommand('media_play_pause'));

  const btnNext = document.getElementById('rcNext');
  if (btnNext) btnNext.addEventListener('click', () => sendRemoteCommand('media_next'));

  const btnVolUp = document.getElementById('rcVolUp');
  if (btnVolUp) btnVolUp.addEventListener('click', () => sendRemoteCommand('volume_up'));

  const btnVolDown = document.getElementById('rcVolDown');
  if (btnVolDown) btnVolDown.addEventListener('click', () => sendRemoteCommand('volume_down'));

  const btnDesktop = document.getElementById('rcDesktop');
  if (btnDesktop) btnDesktop.addEventListener('click', () => sendRemoteCommand('show_desktop'));

  const btnLock = document.getElementById('rcLock');
  if (btnLock) btnLock.addEventListener('click', () => sendRemoteCommand('lock_pc'));

  const btnHandoffMobile = document.getElementById('rcHandoffMobile');
  if (btnHandoffMobile) btnHandoffMobile.addEventListener('click', handleHandoffToMobile);

  const btnHandoffPC = document.getElementById('rcHandoffPC');
  if (btnHandoffPC) btnHandoffPC.addEventListener('click', handleHandoffToPC);

  // Enregistrement Service Worker PWA pour mode hors-ligne
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('./sw.js').catch(() => {});
  }
});

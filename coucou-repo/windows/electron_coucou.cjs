/**
 * Coucou Electron Host
 * Hébergeur natif officiel pour l'interface Coucou (Louis-CFM/coucou)
 * Garantit une transparence 100% sans bordure ni fond blanc sous Windows.
 */

const { app, BrowserWindow, screen, ipcMain } = require('electron');
const path = require('path');
const readline = require('readline');
const net = require('net');

let mainWindow = null;

// Empêche le scintillement blanc au démarrage
app.commandLine.appendSwitch('disable-features', 'ElasticOverscroll');
app.commandLine.appendSwitch('autoplay-policy', 'no-user-gesture-required');

function createWindow() {
  const primaryDisplay = screen.getPrimaryDisplay();
  const screenWidth = primaryDisplay.bounds.width;
  const winW = 700;
  const winH = 360;
  const x = Math.round((screenWidth - winW) / 2);
  const y = 0;

  mainWindow = new BrowserWindow({
    width: winW,
    height: winH,
    x: x,
    y: y,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    hasShadow: false,
    skipTaskbar: true,
    resizable: false,
    focusable: true,
    backgroundColor: '#00000000',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: false,
      webSecurity: false
    }
  });

  const indexPath = path.join(__dirname, 'dist', 'index.html');
  mainWindow.loadFile(indexPath);

  mainWindow.setAlwaysOnTop(true, 'screen-saver');
  mainWindow.showInactive();

  // Par défaut, le clic passe à travers la zone transparente
  mainWindow.setIgnoreMouseEvents(true, { forward: true });

  mainWindow.webContents.on('did-finish-load', () => {
    // Initialise l'état de démarrage de Coucou
    mainWindow.webContents.executeJavaScript(`
      if (window.dispatchCoucouEvent) {
        window.dispatchCoucouEvent('hook', {
          hook_event_name: 'Sleep',
          coucou_agent: 'crux',
          cwd: 'C:\\\\Users\\\\coco\\\\Documents',
          message: 'En veille'
        });
      }

      // Détecte le survol de la notch dynamique pour activer les clics
      document.addEventListener('mousemove', (e) => {
        const island = document.getElementById('island');
        const strip = document.getElementById('wake-strip');
        let onNotch = false;
        if (island) {
          const r = island.getBoundingClientRect();
          if (e.clientX >= r.left && e.clientX <= r.right && e.clientY >= r.top && e.clientY <= r.bottom) {
            onNotch = true;
          }
        }
        if (strip && e.clientY <= 8) {
          const r = strip.getBoundingClientRect();
          if (e.clientX >= r.left && e.clientX <= r.right) {
            onNotch = true;
          }
        }
        const hub = document.getElementById('crux-dynamic-hub');
        if (hub && hub.style.display !== 'none' && hub.style.opacity !== '0') {
          const hr = hub.getBoundingClientRect();
          if (e.clientX >= hr.left && e.clientX <= hr.right && e.clientY >= hr.top && e.clientY <= hr.bottom) {
            onNotch = true;
          }
        }
        if (window.__lastOnNotch !== onNotch) {
          window.__lastOnNotch = onNotch;
          console.log('NOTCH_HOVER:' + onNotch);
        }
      });
    `);
  });

  // Écoute des logs de la page pour activer/désactiver le clic traversant
  mainWindow.webContents.on('did-fail-load', (e, code, desc) => {
    console.error('[Page Load Failed]', code, desc);
  });

  mainWindow.webContents.on('console-message', (event, ...args) => {
    const rawMsg = typeof event === 'object' && event.message !== undefined ? event.message : (args[1] || event);
    const message = String(rawMsg || '');
    if (!message.startsWith('NOTCH_HOVER:')) {
      console.log('[Page Console]', message);
    }
    if (message.startsWith('NOTCH_HOVER:')) {
      const hover = message.split(':')[1] === 'true';
      if (hover) {
        mainWindow.setIgnoreMouseEvents(false);
      } else {
        mainWindow.setIgnoreMouseEvents(true, { forward: true });
      }
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
    app.quit();
  });
}

let settingsWindow = null;
function openSettingsWindow() {
  if (settingsWindow && !settingsWindow.isDestroyed()) {
    settingsWindow.focus();
    return;
  }
  settingsWindow = new BrowserWindow({
    width: 780,
    height: 680,
    title: 'Coucou Settings & Configurations',
    backgroundColor: '#0b0c0e',
    autoHideMenuBar: true,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: false
    }
  });
  const settingsPath = path.join(__dirname, 'dist', 'settings.html');
  settingsWindow.loadFile(settingsPath);
  settingsWindow.on('closed', () => {
    settingsWindow = null;
  });
}

function handleDynamicUI(payload) {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  const action = payload.action || 'show';
  
  if (action === 'hide') {
    mainWindow.webContents.executeJavaScript(`
      const hub = document.getElementById('crux-dynamic-hub');
      if (hub) {
        hub.style.opacity = '0';
        hub.style.transform = 'translate(-50%, -10px) scale(0.98)';
        setTimeout(() => { hub.style.display = 'none'; }, 200);
      }
    `).catch(() => {});
    return;
  }

  const width = payload.width || 640;
  const height = payload.height || 380;
  
  // Ajuste la taille de la fenêtre si nécessaire
  const currentBounds = mainWindow.getBounds();
  const targetH = Math.max(360, height + 80);
  const targetW = Math.max(700, width + 40);
  if (currentBounds.height < targetH || currentBounds.width < targetW) {
    const primaryDisplay = screen.getPrimaryDisplay();
    const newX = Math.round((primaryDisplay.bounds.width - targetW) / 2);
    mainWindow.setBounds({
      x: newX,
      y: 0,
      width: targetW,
      height: targetH
    });
  }

  const jsPayload = JSON.stringify(payload);
  const injectScript = `
    (function() {
      // 1. Injecter les styles génératifs Crux si pas encore présents
      if (!document.getElementById('crux-dynamic-styles')) {
        const style = document.createElement('style');
        style.id = 'crux-dynamic-styles';
        style.textContent = \`
          #crux-dynamic-hub {
            position: fixed;
            top: 48px;
            left: 50%;
            transform: translate(-50%, 0);
            z-index: 99999;
            background: rgba(14, 15, 18, 0.94);
            backdrop-filter: blur(28px) saturate(180%);
            -webkit-backdrop-filter: blur(28px) saturate(180%);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 20px;
            box-shadow: 0 20px 48px rgba(0, 0, 0, 0.65), 0 0 0 1px rgba(255, 255, 255, 0.04);
            color: #f5f6f8;
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            overflow: hidden;
            transition: all 0.28s cubic-bezier(0.16, 1, 0.3, 1);
          }
          .crux-ui-wrapper {
            padding: 18px 22px;
            display: flex;
            flex-direction: column;
            gap: 14px;
            box-sizing: border-box;
          }
          .crux-ui-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding-bottom: 6px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
          }
          .crux-ui-title-group {
            display: flex;
            align-items: center;
            gap: 10px;
          }
          .crux-title {
            font-size: 14.5px;
            font-weight: 600;
            margin: 0;
            color: #f8fafc;
            letter-spacing: -0.2px;
          }
          .crux-status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
          }
          .pulse-emerald { background: #10b981; box-shadow: 0 0 8px #10b981aa; }
          .pulse-amber { background: #f59e0b; box-shadow: 0 0 8px #f59e0baa; }
          .pulse-cyan { background: #06b6d4; box-shadow: 0 0 8px #06b6d4aa; }
          .pulse-purple { background: #8b5cf6; box-shadow: 0 0 8px #8b5cf6aa; }
          .crux-ui-actions {
            display: flex;
            align-items: center;
            gap: 10px;
          }
          .crux-sub-badge {
            font-size: 11px;
            color: #94a3b8;
            background: rgba(255, 255, 255, 0.06);
            padding: 2px 8px;
            border-radius: 12px;
          }
          .crux-btn-circle-close {
            width: 22px;
            height: 22px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.1);
            border: none;
            color: #cbd5e1;
            cursor: pointer;
            display: grid;
            place-items: center;
            font-size: 11px;
            transition: all 0.15s ease;
          }
          .crux-btn-circle-close:hover {
            background: rgba(239, 68, 68, 0.25);
            color: #f87171;
          }
          .crux-task-input-bar {
            display: flex;
            gap: 8px;
          }
          .crux-input-clean {
            flex: 1;
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 8px 12px;
            color: #f8fafc;
            font-size: 12.5px;
            outline: none;
          }
          .crux-input-clean:focus {
            border-color: rgba(56, 189, 248, 0.5);
            background: rgba(255, 255, 255, 0.09);
          }
          .crux-btn-primary-mini {
            background: #f8fafc;
            color: #0b0c0e;
            border: none;
            border-radius: 10px;
            padding: 0 14px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s ease;
          }
          .crux-btn-primary-mini:hover {
            background: #e2e8f0;
            transform: scale(1.02);
          }
          .crux-task-list {
            display: flex;
            flex-direction: column;
            gap: 6px;
            max-height: 220px;
            overflow-y: auto;
            padding-right: 4px;
          }
          .crux-task-list::-webkit-scrollbar { width: 4px; }
          .crux-task-list::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.15); border-radius: 4px; }
          .crux-task-item {
            display: flex;
            align-items: center;
            gap: 10px;
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            padding: 8px 12px;
            transition: all 0.2s ease;
          }
          .crux-task-item:hover {
            background: rgba(255, 255, 255, 0.07);
          }
          .crux-task-item.done {
            opacity: 0.55;
            background: rgba(255, 255, 255, 0.02);
          }
          .crux-task-item.done .crux-task-label {
            text-decoration: line-through;
            color: #64748b;
          }
          .crux-task-label {
            flex: 1;
            font-size: 12.5px;
            color: #e2e8f0;
          }
          .crux-badge {
            font-size: 10px;
            padding: 2px 7px;
            border-radius: 6px;
            background: rgba(56, 189, 248, 0.15);
            color: #38bdf8;
            font-weight: 500;
          }
          .crux-btn-mini-del {
            background: none;
            border: none;
            color: #64748b;
            cursor: pointer;
            font-size: 14px;
            padding: 0 4px;
            opacity: 0;
            transition: opacity 0.15s ease, color 0.15s ease;
          }
          .crux-task-item:hover .crux-btn-mini-del { opacity: 1; }
          .crux-btn-mini-del:hover { color: #f87171; }
          .crux-ui-footer {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding-top: 6px;
            border-top: 1px solid rgba(255, 255, 255, 0.06);
          }
          .crux-footer-hint {
            font-size: 10.5px;
            color: #64748b;
          }
          .crux-btn-ghost-mini {
            background: transparent;
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
            color: #94a3b8;
            font-size: 10.5px;
            padding: 3px 8px;
            cursor: pointer;
          }
          .crux-btn-ghost-mini:hover {
            background: rgba(255, 255, 255, 0.05);
            color: #e2e8f0;
          }
          .crux-grid-cards {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
          }
          .crux-metric-card {
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 12px;
            padding: 12px;
            display: flex;
            flex-direction: column;
            gap: 4px;
          }
          .crux-metric-head {
            display: flex;
            justify-content: space-between;
            font-size: 11px;
            color: #94a3b8;
          }
          .crux-tag-green { color: #34d399; font-weight: 600; }
          .crux-metric-val { font-size: 18px; font-weight: 700; color: #f8fafc; font-family: Cascadia Mono, monospace; }
          .crux-metric-sub { font-size: 10px; color: #64748b; }
          .crux-monitor-bars { display: flex; flex-direction: column; gap: 10px; }
          .crux-bar-group { display: flex; flex-direction: column; gap: 4px; }
          .crux-bar-label { display: flex; justify-content: space-between; font-size: 11.5px; color: #94a3b8; }
          .crux-bar-track { height: 6px; border-radius: 3px; background: rgba(255, 255, 255, 0.08); overflow: hidden; }
          .crux-bar-fill { height: 100%; border-radius: 3px; transition: width 0.3s ease; }
          .fill-cyan { background: #06b6d4; }
          .fill-purple { background: #8b5cf6; }
          .crux-quick-actions-row { display: flex; gap: 8px; margin-top: 6px; }
          .crux-action-btn {
            flex: 1;
            padding: 7px 10px;
            border-radius: 8px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            background: rgba(255, 255, 255, 0.04);
            color: #e2e8f0;
            font-size: 11.5px;
            cursor: pointer;
            transition: all 0.15s ease;
          }
          .crux-action-btn:hover { background: rgba(255, 255, 255, 0.09); border-color: rgba(255, 255, 255, 0.18); }
        \`;
        document.head.appendChild(style);
      }

      // 2. Définir les helpers d'interaction globaux
      window.cruxCloseUI = function() {
        const hub = document.getElementById('crux-dynamic-hub');
        if (hub) {
          hub.style.opacity = '0';
          hub.style.transform = 'translate(-50%, -10px) scale(0.98)';
          setTimeout(() => { hub.style.display = 'none'; }, 200);
        }
      };

      window.cruxToggleTask = function(taskId) {
        const item = document.getElementById('item_' + taskId);
        if (item) {
          item.classList.toggle('done');
          const counter = document.getElementById('task_counter');
          if (counter) {
            const count = document.querySelectorAll('.crux-task-item:not(.done)').length;
            counter.textContent = count + ' restantes';
          }
        }
      };

      window.cruxDeleteTask = function(taskId) {
        const item = document.getElementById('item_' + taskId);
        if (item) {
          item.style.opacity = '0';
          item.style.transform = 'scale(0.9)';
          setTimeout(() => {
            item.remove();
            const counter = document.getElementById('task_counter');
            if (counter) {
              const count = document.querySelectorAll('.crux-task-item:not(.done)').length;
              counter.textContent = count + ' restantes';
            }
          }, 150);
        }
      };

      window.cruxAddNewTask = function() {
        const input = document.getElementById('crux_new_task_input');
        if (!input || !input.value.trim()) return;
        const text = input.value.trim();
        const id = 't_' + Math.random().toString(36).substring(2, 6);
        const container = document.getElementById('crux_task_list_container');
        if (container) {
          const div = document.createElement('div');
          div.className = 'crux-task-item';
          div.id = 'item_' + id;
          div.innerHTML = \`
            <label class="crux-checkbox-container">
              <input type="checkbox" onchange="cruxToggleTask('\${id}')">
              <span class="crux-checkmark"></span>
            </label>
            <span class="crux-task-label">\${text}</span>
            <span class="crux-badge">Crux</span>
            <button class="crux-btn-mini-del" onclick="cruxDeleteTask('\${id}')" title="Supprimer">×</button>
          \`;
          container.prepend(div);
          input.value = '';
          const counter = document.getElementById('task_counter');
          if (counter) {
            const count = document.querySelectorAll('.crux-task-item:not(.done)').length;
            counter.textContent = count + ' restantes';
          }
        }
      };

      window.cruxClearCompleted = function() {
        document.querySelectorAll('.crux-task-item.done').forEach(el => el.remove());
      };

      window.cruxAction = function(name) {
        console.log('[CRUX_ACTION]', name);
      };

      // 3. Injecter ou mettre à jour le conteneur du Hub Dynamique
      let hub = document.getElementById('crux-dynamic-hub');
      if (!hub) {
        hub = document.createElement('div');
        hub.id = 'crux-dynamic-hub';
        document.body.appendChild(hub);
      }

      const p = ${jsPayload};
      hub.style.width = (p.width || 640) + 'px';
      hub.style.height = (p.height || 380) + 'px';
      hub.innerHTML = p.html || '';
      hub.style.display = 'block';
      hub.style.opacity = '1';
      hub.style.transform = 'translate(-50%, 0) scale(1)';
    })();
  `;
  mainWindow.webContents.executeJavaScript(injectScript).catch((e) => {
    console.error('[Dynamic UI Inject Error]', e);
  });
}

function dispatchEvent(type, payload) {
  if (type === 'open_settings' || type === 'settings') {
    openSettingsWindow();
    return;
  }
  if (type === 'dynamic_ui') {
    handleDynamicUI(payload);
    return;
  }
  if (!mainWindow || mainWindow.isDestroyed()) return;
  const script = `
    if (window.dispatchCoucouEvent) {
      window.dispatchCoucouEvent(${JSON.stringify(type)}, ${JSON.stringify(payload)});
    }
  `;
  mainWindow.webContents.executeJavaScript(script).catch(() => {});
}

app.whenReady().then(() => {
  createWindow();

  // 1. Écoute sur stdin pour recevoir les événements Crux via canal direct
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    terminal: false
  });

  rl.on('line', (line) => {
    if (!line || !line.trim()) return;
    try {
      const data = JSON.parse(line.trim());
      dispatchEvent(data.type || 'hook', data.payload || {});
    } catch (e) {}
  });

  // 2. Écoute également sur un serveur TCP localhost:49225 pour IPC rapide
  const server = net.createServer((socket) => {
    let buffer = '';
    socket.on('data', (chunk) => {
      buffer += chunk.toString();
      const lines = buffer.split('\n');
      buffer = lines.pop();
      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const data = JSON.parse(line.trim());
          dispatchEvent(data.type || 'hook', data.payload || {});
          socket.write(JSON.stringify({ status: 'ok' }) + '\n');
        } catch (e) {}
      }
    });
  });

  server.listen(49225, '127.0.0.1', () => {
    console.log('[Coucou Electron] Prêt sur 127.0.0.1:49225');
  });
});

app.on('window-all-closed', () => {
  app.quit();
});

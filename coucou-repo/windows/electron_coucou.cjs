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

function dispatchEvent(type, payload) {
  if (type === 'open_settings' || type === 'settings') {
    openSettingsWindow();
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

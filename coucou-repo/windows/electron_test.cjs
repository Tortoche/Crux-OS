const { app, BrowserWindow, screen } = require('electron');
const path = require('path');

app.whenReady().then(() => {
  const primaryDisplay = screen.getPrimaryDisplay();
  const { width } = primaryDisplay.workAreaSize;
  const winW = 700;
  const winH = 360;

  const win = new BrowserWindow({
    width: winW,
    height: winH,
    x: Math.round((width - winW) / 2),
    y: 0,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    hasShadow: false,
    skipTaskbar: true,
    resizable: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: false
    }
  });

  win.loadFile(path.join(__dirname, 'dist', 'index.html'));

  win.webContents.on('did-finish-load', async () => {
    const info = await win.webContents.executeJavaScript(`
      JSON.stringify({
        title: document.title,
        islandExists: !!document.getElementById('island'),
        canvasExists: !!document.getElementById('bot-canvas'),
        islandBounds: document.getElementById('island') ? document.getElementById('island').getBoundingClientRect() : null,
        bodyBg: getComputedStyle(document.body).backgroundColor
      })
    `);
    console.log('ELECTRON DOM RESULT:', info);
    setTimeout(() => {
      app.quit();
    }, 2000);
  });
});

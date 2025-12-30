const { app, BrowserWindow, ipcMain, globalShortcut, screen } = require('electron');
const path = require('path');
const isDev = require('electron-is-dev');
const { spawn } = require('child_process');

let mainWindow;
let pythonProcess;
let isRecording = false;
let recordingStartTime = Date.now();

// Window dimensions
const WINDOW_SIZES = {
  collapsed: { width: 500, height: 80 },
  expanded: { width: 500, height: 500 }
};

// Create Electron Window - positioned at bottom center
function createWindow() {
  const primaryDisplay = screen.getPrimaryDisplay();
  const { width: screenWidth, height: screenHeight } = primaryDisplay.workAreaSize;

  mainWindow = new BrowserWindow({
    width: WINDOW_SIZES.collapsed.width,
    height: WINDOW_SIZES.collapsed.height,
    x: Math.round((screenWidth - WINDOW_SIZES.collapsed.width) / 2),
    y: screenHeight - WINDOW_SIZES.collapsed.height - 20,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true
    },
    alwaysOnTop: true,
    frame: false,
    transparent: true,
    backgroundColor: '#00000000',
    resizable: false,
    show: false,
    skipTaskbar: false,
    hasShadow: false
  });

  const startUrl = isDev
    ? 'http://localhost:3000'
    : `file://${path.join(__dirname, 'index.html')}`;

  mainWindow.loadURL(startUrl);
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  if (isDev) {
    mainWindow.webContents.openDevTools({ mode: 'detach' });
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// Start Python Backend
function startPythonBackend() {
  const pythonScript = path.join(__dirname, '../backend/electron_bridge.py');
  const projectRoot = path.join(__dirname, '../../');

  console.log('[Python] Starting backend from:', pythonScript);

  try {
    pythonProcess = spawn('python', [pythonScript], {
      cwd: projectRoot,
      stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env }
    });

    pythonProcess.stdout.on('data', (data) => {
      const message = data.toString().trim();
      console.log(`[Python] ${message}`);
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('python-log', message);
      }
    });

    pythonProcess.stderr.on('data', (data) => {
      console.error(`[Python Error] ${data.toString().trim()}`);
    });

    pythonProcess.on('close', (code) => {
      console.log(`[Python] Process exited with code ${code}`);
    });

    pythonProcess.on('error', (err) => {
      console.error('[Python] Failed to start:', err.message);
    });
  } catch (err) {
    console.error('[Python] Error spawning process:', err);
  }
}

// Global Hotkey Setup
function setupGlobalHotkey(hotkey = 'Space') {
  globalShortcut.unregisterAll();

  const registered = globalShortcut.register(hotkey, () => {
    if (!isRecording) {
      isRecording = true;
      recordingStartTime = Date.now();
      console.log('[Hotkey] PTT Start');
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('ptt-start', { timestamp: recordingStartTime });
      }
    }
  });

  if (!registered) {
    console.error(`[Hotkey] Failed to register: ${hotkey}`);
  } else {
    console.log(`[Hotkey] Registered: ${hotkey}`);
  }
}

// IPC Handlers
ipcMain.on('start-recording', () => {
  console.log('[IPC] Start recording');
  if (pythonProcess && pythonProcess.stdin) {
    pythonProcess.stdin.write('START\n');
  }
});

ipcMain.on('stop-recording', () => {
  console.log('[IPC] Stop recording');
  isRecording = false;
  const duration = Date.now() - recordingStartTime;
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('ptt-end', { duration });
  }
  if (pythonProcess && pythonProcess.stdin) {
    pythonProcess.stdin.write('STOP\n');
  }
});

ipcMain.on('resize-window', (event, size) => {
  console.log('[IPC] Resize window:', size);
  if (mainWindow && !mainWindow.isDestroyed()) {
    const primaryDisplay = screen.getPrimaryDisplay();
    const { width: screenWidth, height: screenHeight } = primaryDisplay.workAreaSize;

    // Keep centered at bottom
    const newX = Math.round((screenWidth - size.width) / 2);
    const newY = screenHeight - size.height - 20;

    mainWindow.setBounds({ x: newX, y: newY, width: size.width, height: size.height });
  }
});

ipcMain.on('set-hotkey', (event, newHotkey) => {
  console.log('[IPC] Set hotkey:', newHotkey);
  setupGlobalHotkey(newHotkey);
});

// App Lifecycle
app.on('ready', () => {
  createWindow();
  startPythonBackend();
  setupGlobalHotkey('Alt+Space');
});

app.on('window-all-closed', () => {
  globalShortcut.unregisterAll();
  if (pythonProcess) pythonProcess.kill();
  if (process.platform !== 'darwin') app.quit();
});

app.on('activate', () => {
  if (mainWindow === null) createWindow();
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
  if (pythonProcess) pythonProcess.kill();
});
const { app, BrowserWindow, ipcMain, globalShortcut, screen } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let mainWindow;
let pythonProcess;
let sessionActive = false;
let backendReady = false;

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

  // Load static HTML directly (no React)
  mainWindow.loadFile(path.join(__dirname, 'ui', 'index.html'));

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  // Open DevTools in development
  if (process.argv.includes('--dev')) {
    mainWindow.webContents.openDevTools({ mode: 'detach' });
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// Start Python Backend using uv (respects project venv)
function startPythonBackend() {
  const projectRoot = path.join(__dirname, '..');
  const pythonScript = path.join(__dirname, 'backend', 'electron_bridge.py');

  console.log('[Python] Starting backend from:', pythonScript);
  console.log('[Python] Project root:', projectRoot);

  try {
    // Use direct venv python to avoid 'uv run' locking issues when main.py is also running
    // Venv path: ../.venv/Scripts/python.exe (Windows)
    const venvPython = path.join(projectRoot, '.venv', 'Scripts', 'python.exe');

    console.log('[Python] Using python executable:', venvPython);

    pythonProcess = spawn(venvPython, [pythonScript], {
      cwd: __dirname,
      stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env },
      shell: true
    });

    pythonProcess.stdout.on('data', (data) => {
      const message = data.toString().trim();
      console.log(`[Python] ${message}`);

      // Check for Backend Readiness (MCP Connected)
      if (message.includes('[READY] Backend ready')) {
        console.log('[Session] Backend is ready for connections');
        backendReady = true;
      }

      // Sync UI state with Python backend status
      if (message.includes('Connected! Start speaking')) {
        console.log('[Session] Connection confirmed, updating UI');
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send('session-started');
        }
      }

      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('python-log', message);
      }
    });

    pythonProcess.stderr.on('data', (data) => {
      const errMsg = data.toString().trim();
      console.error(`[Python Error] ${errMsg}`);
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('python-error', errMsg);
      }
    });

    pythonProcess.on('close', (code) => {
      console.log(`[Python] Process exited with code ${code}`);
      sessionActive = false;
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('session-ended');
      }
    });

    pythonProcess.on('error', (err) => {
      console.error('[Python] Failed to start:', err.message);
    });
  } catch (err) {
    console.error('[Python] Error spawning process:', err);
  }
}

// Toggle session on/off
function toggleSession() {
  if (!pythonProcess || pythonProcess.killed) {
    console.log('[Session] Python process not running, starting...');
    startPythonBackend();
    sessionActive = true;
    return;
  }

  if (sessionActive) {
    // Stop session - SOFT STOP (Don't kill process)
    console.log('[Session] Sending STOP command...');
    if (pythonProcess && !pythonProcess.killed && pythonProcess.stdin) {
      pythonProcess.stdin.write('STOP\n');
    }

    // We do NOT nil pythonProcess or kill it
    // Wait for "Session Stopped" log or assume it works
    sessionActive = false;

    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('session-stopped');
    }
  } else {
    // Start session

    // STRICT CHECK: Cannot start session until backend is ready (MCP connected)
    if (!backendReady) {
      console.log('[Session] Ignored start request - Backend not ready yet');
      if (process.platform === 'win32') {
        // System beep to indicate error
        const { exec } = require('child_process');
        exec('powershell "[console]::beep(500, 300)"');
      }
      return;
    }

    // Session Pooling: Reuse existing process
    if (pythonProcess && !pythonProcess.killed) {
      console.log('[Session] Reusing existing backend...');
      if (pythonProcess.stdin) {
        pythonProcess.stdin.write('START\n');
      }
    } else {
      console.log('[Session] Starting new backend process...');
      startPythonBackend();
    }

    sessionActive = true;

    // Send connecting state immediately to show user we're working on it
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('session-connecting');
    }

    // NOTE: We do NOT send 'session-started' here anymore.
    // We wait for the Python backend to log "Connected! Start speaking"
    // This prevents the UI from showing "Listening" before the connection is ready.
  }
}

// Global Hotkey Setup (Toggle mode, not push-to-talk)
function setupGlobalHotkey(hotkey = 'Alt+Space') {
  globalShortcut.unregisterAll();

  const registered = globalShortcut.register(hotkey, () => {
    console.log('[Hotkey] Alt+Space pressed, toggling session...');
    toggleSession();
  });

  if (!registered) {
    console.error(`[Hotkey] Failed to register: ${hotkey}`);
  } else {
    console.log(`[Hotkey] Registered: ${hotkey}`);
  }
}

// IPC Handlers
ipcMain.on('toggle-session', () => {
  toggleSession();
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

ipcMain.on('set-mode', (event, mode) => {
  console.log('[IPC] Set mode:', mode);
  if (pythonProcess && !pythonProcess.killed && pythonProcess.stdin) {
    pythonProcess.stdin.write(`MODE:${mode}\n`);
  }
});

// App Lifecycle
app.on('ready', () => {
  createWindow();
  startPythonBackend();
  setupGlobalHotkey('Alt+Space');
});

app.on('window-all-closed', () => {
  globalShortcut.unregisterAll();
  if (pythonProcess) {
    if (process.platform === 'win32') {
      const { exec } = require('child_process');
      exec(`taskkill /pid ${pythonProcess.pid} /T /F`);
    } else {
      pythonProcess.kill('SIGKILL');
    }
  }
  if (process.platform !== 'darwin') app.quit();
});

app.on('activate', () => {
  if (mainWindow === null) createWindow();
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
  if (pythonProcess) {
    if (process.platform === 'win32') {
      const { exec } = require('child_process');
      exec(`taskkill /pid ${pythonProcess.pid} /T /F`);
    } else {
      pythonProcess.kill('SIGKILL');
    }
  }
});

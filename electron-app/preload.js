const { contextBridge, ipcRenderer, shell } = require('electron');

// Expose IPC methods to renderer process
contextBridge.exposeInMainWorld('electronAPI', {
    // Session control
    toggleSession: () => ipcRenderer.send('toggle-session'),

    // Window control
    resizeWindow: (size) => ipcRenderer.send('resize-window', size),
    setHotkey: (hotkey) => ipcRenderer.send('set-hotkey', hotkey),
    setMode: (mode) => ipcRenderer.send('set-mode', mode),

    // Settings
    getApiKey: () => ipcRenderer.invoke('get-api-key'),
    setApiKey: (key) => ipcRenderer.invoke('set-api-key', key),
    openExternal: (url) => ipcRenderer.send('open-external', url),

    // MCP Configuration
    getMcpConfig: () => ipcRenderer.send('get-mcp-config'),
    saveMcpConfig: (config) => ipcRenderer.send('save-mcp-config', config),

    // Event listeners
    onSessionConnecting: (callback) => ipcRenderer.on('session-connecting', callback),
    onSessionStarted: (callback) => ipcRenderer.on('session-started', callback),
    onSessionStopped: (callback) => ipcRenderer.on('session-stopped', callback),
    onSessionEnded: (callback) => ipcRenderer.on('session-ended', callback),
    onPythonLog: (callback) => ipcRenderer.on('python-log', (event, message) => callback(message)),
    onPythonError: (callback) => ipcRenderer.on('python-error', (event, message) => callback(message)),

    // Cleanup
    removeAllListeners: () => {
        ipcRenderer.removeAllListeners('session-connecting');
        ipcRenderer.removeAllListeners('session-started');
        ipcRenderer.removeAllListeners('session-stopped');
        ipcRenderer.removeAllListeners('session-ended');
        ipcRenderer.removeAllListeners('python-log');
        ipcRenderer.removeAllListeners('python-error');
    }
});

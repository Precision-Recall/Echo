# ECHO Desktop - Electron Voice Assistant

A minimalist push-to-talk desktop app powered by Gemini Live API.

## Project Structure

```
electron-app/
├── App.tsx                 # Main React component
├── CompactPill.tsx         # Floating pill widget UI
├── ExpandedView.tsx        # Full dashboard view
├── ExpandedView.css        # Dashboard styles
├── hooks-and-services.ts   # Audio recording hooks
├── electron-main.js        # Electron main process
├── types/
│   └── electron.d.ts       # TypeScript declarations
├── package.json
└── tsconfig.json
```

---

## Quick Start

### 1. Install Dependencies

```bash
cd electron-app
npm install --legacy-peer-deps
```

### 1a. (macOS Only) Install Audio Dependencies

If you are on macOS, you must install `portaudio` before installing Python dependencies:

```bash
brew install portaudio
```


### 2. Create Required Files

#### `public/index.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>ECHO Voice Assistant</title>
</head>
<body>
  <div id="root"></div>
</body>
</html>
```

#### `public/preload.js`

```javascript
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('ipcRenderer', {
  send: (channel, data) => ipcRenderer.send(channel, data),
  on: (channel, func) => ipcRenderer.on(channel, (event, ...args) => func(event, ...args)),
  removeAllListeners: (channel) => ipcRenderer.removeAllListeners(channel),
  invoke: (channel, data) => ipcRenderer.invoke(channel, data)
});
```

### 3. Move Main Process File

```bash
# Move electron-main.js to public folder
move electron-main.js public/electron-main.js
```

### 4. Create App.css

```css
.app {
  width: 100%;
  height: 100vh;
  background: #1a1a2e;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
```

### 5. Run Development Server

```bash
npm start
```

This runs:
- React dev server at `http://localhost:3000`
- Electron connects to React automatically

---

## How Electron Works

### Main Process vs Renderer Process

| Main Process (`electron-main.js`) | Renderer Process (React) |
|-----------------------------------|--------------------------|
| Node.js environment | Browser environment |
| Controls app window | Renders UI |
| Spawns Python backend | Displays messages |
| Handles global hotkeys | Manages user interaction |
| Communicates via IPC | Receives events via IPC |

### IPC Communication Flow

```
┌─────────────────────────────────────────────────────────────┐
│ User presses SPACE key                                       │
└──────────────┬──────────────────────────────────────────────┘
               │ iohook detects keydown
               ▼
┌─────────────────────────────────────────────────────────────┐
│ Main Process: sends 'ptt-start' event                        │
└──────────────┬──────────────────────────────────────────────┘
               │ ipcRenderer.on('ptt-start')
               ▼
┌─────────────────────────────────────────────────────────────┐
│ React: setState('listening'), starts audio recording         │
└──────────────┬──────────────────────────────────────────────┘
               │ ipcMain.on('start-recording')
               ▼
┌─────────────────────────────────────────────────────────────┐
│ Main Process: sends 'START' to Python backend                │
└─────────────────────────────────────────────────────────────┘
```

### Key IPC Channels

| Channel | Direction | Purpose |
|---------|-----------|---------|
| `ptt-start` | Main → Renderer | User started pressing PTT key |
| `ptt-end` | Main → Renderer | User released PTT key |
| `start-recording` | Renderer → Main | Begin audio capture |
| `stop-recording` | Renderer → Main | Stop audio capture |
| `python-log` | Main → Renderer | Backend output messages |
| `set-hotkey` | Renderer → Main | Change PTT hotkey |

---

## UI Modes

### Compact Pill (Default)
- **Size**: 280×60px floating widget
- **Features**: Waveform visualization, status orb, live transcription
- **Position**: Always on top, draggable

### Expanded View
- **Size**: Full window dashboard
- **Features**: Chat history, settings panel, tool steps visualization
- **Toggle**: Click expand button on pill

---

## App States & Visual Feedback

| State | Orb Color | Description |
|-------|-----------|-------------|
| `idle` | 🟣 Purple | Ready, waiting for input |
| `listening` | 🟢 Green | Recording user audio |
| `processing` | 🟠 Orange | Sending to Gemini, waiting |
| `speaking` | 🔵 Blue | Playing Gemini response |
| `error` | 🔴 Red | Error occurred |

---

## Backend Integration

The app expects a Python backend at `backend/main.py` that:

1. Reads commands from stdin (`START`, `STOP`)
2. Streams output to stdout with prefixes:
   - `🎤 You: <text>` - User transcription
   - `📝 Echo: <text>` - Gemini response
   - `🔧 Tool: <name>` - Tool execution
   - `✅ Turn complete` - End of turn

---

## Build for Production

```bash
npm run build
```

Creates distributable packages:
- **Windows**: `.exe` installer
- **macOS**: `.dmg` disk image
- **Linux**: `.AppImage`

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Hotkey not working | Install iohook native bindings: `npm rebuild iohook` |
| Blank window | Check React dev server is running at `localhost:3000` |
| Python not starting | Verify `python` is in PATH and backend/main.py exists |
| No transcription | Ensure backend logs use `🎤 You:` prefix |

---

## Environment Variables

Create `.env` in project root:

```env
GOOGLE_API_KEY=your_gemini_api_key_here
```

---

## Development Tips

1. **Hot Reload**: React changes reflect instantly; Electron main process requires restart
2. **DevTools**: Automatically opens in development mode
3. **Logging**: Check terminal for Python backend output
4. **Testing Audio**: Use browser DevTools console to check Web Audio API errors

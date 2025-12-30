# Echo Electron Integration Checklist

## Pre-Flight Checks

Before running the Electron app, verify these requirements:

### 1. Environment Setup

- [ ] **Python 3.12+** installed
  ```bash
  python --version
  ```

- [ ] **Project dependencies** installed
  ```bash
  # From project root
  uv sync
  ```

- [ ] **API Key** configured
  ```bash
  # Check .env file exists in project root
  cat .env | grep GEMINI_API_KEY
  # Should show: GEMINI_API_KEY=AIza...
  ```

- [ ] **Electron dependencies** installed
  ```bash
  cd electron-app
  npm install
  ```

### 2. MCP Server

- [ ] **Windows-MCP** running on port 8000
  ```bash
  # Terminal 1
  uvx windows-mcp --transport streamable-http --port 8000
  ```

- [ ] **Test MCP connection**
  ```bash
  # Should return JSON with tools list
  curl http://127.0.0.1:8000/mcp
  ```

### 3. Audio Devices

- [ ] **Microphone** configured and accessible
- [ ] **Speaker/Headphones** working
- [ ] **PyAudio** installed correctly
  ```bash
  python -c "import pyaudio; print(pyaudio.__version__)"
  ```

---

## Integration Verification

### Backend Standalone Test

Test the Python bridge without Electron:

```bash
cd electron-app/backend
python electron_bridge.py
```

**Expected Output:**
```
[STARTUP] Initializing ECHO backend...
[THOUGHT] 🚀 ECHO Backend Starting...
[THOUGHT] 🔌 Connecting to Windows-MCP server...
[THOUGHT] ✅ Loaded N tools from MCP
[THOUGHT] Available: tool1, tool2, tool3...
[THOUGHT] 📝 Press Alt+Space to toggle listening
[READY] Backend ready
```

**Then type:**
```
START
```

**Expected:**
```
[THOUGHT] 🚀 Starting voice session...
[THOUGHT] 📡 Using model: gemini-2.5-flash-native-audio-preview-12-2025
[THOUGHT] 🎙️ Connecting to Gemini Live...
[THOUGHT] ✅ Connected! Start speaking...
```

**Speak into mic, then type:**
```
STOP
QUIT
```

✅ **Pass Criteria:** Backend starts, connects to MCP and Gemini, processes voice

---

### Electron App Test

Run the full Electron app:

```bash
cd electron-app
npm start
```

**Checklist:**

- [ ] **App window opens** without errors
- [ ] **Backend logs visible** in thinking panel
- [ ] **MCP connection succeeds** (shows tool count)
- [ ] **"Press Alt+Space"** message appears
- [ ] **Alt+Space** toggles listening state
- [ ] **Microphone captures** voice (waveform/indicator)
- [ ] **Gemini responds** with audio
- [ ] **Transcriptions appear** in result panel
- [ ] **Tool calls logged** when asking to control desktop
- [ ] **Stop button** works to end session
- [ ] **Audit log created** at `electron-app/audit.log`

---

## Component Integration Tests

### 1. ElectronLogger → Electron UI

**Test:** Verify log parsing

**File:** `electron_bridge.py` line 50-54

```python
def _electron_callback(self, type_: str, message: str):
    print(f"[{type_.upper()}] {safe_msg}", flush=True)
```

**Electron receives:**
```
[THOUGHT] Test message
[ACTION] Executing tool {"arg": "value"}
[OBSERVATION] ✓ Success
[ERROR] Error message
[RESULT] 📝 Echo: Response text
```

✅ **Pass:** All log types display correctly in UI

---

### 2. SessionManager → GeminiLiveClient

**Test:** Verify client creation with correct parameters

**File:** `electron_bridge.py` lines 144-153

```python
model_config = ModelConfig.get_config(AgentMode.VOICE)
# Should return: gemini-2.5-flash-native-audio-preview-12-2025

client = GeminiLiveClient(
    api_key=self.api_key,           # From .env
    model_name=model_config.model_name,  # From ModelConfig
    logger=self.logger,              # ElectronLogger instance
    mcp_client=self.mcp_client       # Pre-initialized MCP
)
```

✅ **Pass:** Client created with VOICE model and MCP tools

---

### 3. MCP Tools → GenAI Format

**Test:** Verify tool conversion

**File:** `live_client.py` lines 106-133

**MCP Input:**
```python
{
    "name": "launch_application",
    "description": "Launch app",
    "args_schema": {"type": "object", "properties": {...}}
}
```

**GenAI Output:**
```python
FunctionDeclaration(
    name="launch_application",
    description="Launch app",
    parameters={"type": "object", "properties": {...}}
)
```

**Check Logs:**
```
[THOUGHT] 📡 Connecting to Windows-MCP...
[THOUGHT] ✅ MCP connected - N tools available
```

✅ **Pass:** Tools loaded and converted successfully

---

### 4. Audio Loop → Gemini

**Test:** Verify bidirectional audio

**File:** `live_client.py` lines 135-151 (send), 153-212 (receive)

**Check:**
- [ ] `start_recording()` called → mic captures audio
- [ ] Audio chunks sent to Gemini (no errors)
- [ ] Gemini responds with audio data
- [ ] `play_audio_chunk()` called → speaker plays audio

**Log Evidence:**
```
✓ Recording started: 16000Hz, chunk=512
[RESULT] 📝 Echo: I'm listening...
```

✅ **Pass:** Audio streams bidirectionally without errors

---

### 5. Tool Execution → MCP → Response

**Test:** Ask Gemini to execute a tool

**Example:** "Open Calculator"

**Expected Flow:**
1. Speech captured
2. Gemini decides tool: `launch_application`
3. Tool executed via MCP
4. Result sent back to Gemini
5. Gemini responds with confirmation

**Logs:**
```
[THOUGHT] 🎤 You: Open Calculator
[THOUGHT] 🔧 Tool: launch_application
[ACTION] Executing launch_application {"app_name": "calc"}
[OBSERVATION] Result: Application launched successfully
[RESULT] 📝 Echo: I've opened Calculator for you
```

✅ **Pass:** Complete tool execution cycle works

---

## Error Scenario Tests

### 1. MCP Server Not Running

**Setup:** Don't start Windows-MCP

**Expected:**
```
[ERROR] ⚠️ MCP Connection Failed
[THOUGHT] ℹ️ Voice-only mode active (no desktop control)
[THOUGHT] 🚀 Starting voice session...
[THOUGHT] ✅ Connected! Start speaking...
```

✅ **Pass:** Session continues in voice-only mode

---

### 2. Invalid API Key

**Setup:** Set wrong GEMINI_API_KEY

**Expected:**
```
[ERROR] Failed to connect to Gemini: Invalid API key
```

✅ **Pass:** Clear error message, graceful failure

---

### 3. Audio Device Unavailable

**Setup:** Disconnect microphone

**Expected:**
```
[ERROR] ⚠️ Audio device error: ...
```

✅ **Pass:** Error logged, doesn't crash backend

---

## File Structure Verification

Ensure all required files exist:

```
Echo/
├── .env                              # API key
├── electron-app/
│   ├── backend/
│   │   └── electron_bridge.py        # Main entry point
│   ├── ARCHITECTURE.md               # Architecture docs
│   ├── API_REFERENCE.md              # API docs
│   ├── INTEGRATION_CHECKLIST.md      # This file
│   └── audit.log                     # Created at runtime
├── src/
│   └── agent/
│       ├── __init__.py               # Exports
│       ├── live_client.py            # Gemini Live client
│       ├── llm_agent.py              # Model config
│       ├── audio.py                  # Audio manager
│       └── thinking_logger.py        # Logger base
└── Prompts/
    └── prompts/
        └── echo_voice_tui.txt        # System prompt
```

---

## Integration Sign-Off

After completing all checks:

- [ ] All pre-flight checks pass
- [ ] Backend standalone test successful
- [ ] Electron app launches and connects
- [ ] Voice interaction works end-to-end
- [ ] Tool execution successful
- [ ] Error scenarios handled gracefully
- [ ] Logs visible in UI and audit.log
- [ ] Documentation reviewed

**Date:** _______________

**Tester:** _______________

**Notes:**
_______________________________________________
_______________________________________________
_______________________________________________

---

## Troubleshooting Guide

### Issue: "Module not found: src.agent"

**Solution:**
```bash
# Verify PYTHONPATH includes project root
cd electron-app/backend
python -c "import sys; print(sys.path)"
# Should include /path/to/Echo
```

**Fix in electron_bridge.py:**
```python
project_root = os.path.dirname(electron_app_dir)
sys.path.insert(0, project_root)
```

### Issue: "GEMINI_API_KEY not set"

**Solution:**
```bash
# Check .env location
ls -la .env  # Should be in project root, not electron-app/

# Check dotenv loading
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('GEMINI_API_KEY'))"
```

### Issue: "Connection refused on port 8000"

**Solution:**
```bash
# Check if MCP server is running
lsof -i :8000  # Should show python process

# Restart MCP server
uvx windows-mcp --transport streamable-http --port 8000
```

### Issue: "No audio output"

**Solution:**
```bash
# Check PyAudio devices
python -c "import pyaudio; p = pyaudio.PyAudio(); [print(i, p.get_device_info_by_index(i)['name']) for i in range(p.get_device_count())]"

# Test audio playback
python -c "import pyaudio, numpy as np; p = pyaudio.PyAudio(); s = p.open(format=8, channels=1, rate=24000, output=True); s.write((np.sin(2*np.pi*440*np.arange(24000)/24000)*32767).astype(np.int16).tobytes()); s.close(); p.terminate()"
```

### Issue: Electron app freezes

**Solution:**
- Check backend process: `ps aux | grep electron_bridge`
- View audit log: `tail -f electron-app/audit.log`
- Restart app: Kill backend and Electron, restart both

---

## Performance Benchmarks

Expected performance metrics:

| Metric | Target | Acceptable | Notes |
|--------|--------|------------|-------|
| Backend startup | < 3s | < 5s | Including MCP connection |
| Voice to transcription | < 1s | < 2s | Speech recognition latency |
| Tool execution | < 500ms | < 2s | Depends on tool |
| Audio response | < 300ms | < 1s | First audio chunk |
| End-to-end latency | < 2s | < 5s | Voice → Action → Response |

**Test Command:** "What time is it?"

**Measure:**
1. Start speaking → [THOUGHT] User transcription
2. Tool call → [ACTION] timestamp
3. Response → [RESULT] timestamp

✅ **Pass:** Total < 5 seconds

---

## Documentation Review

- [x] `ARCHITECTURE.md` - Complete architecture overview
- [x] `API_REFERENCE.md` - API interfaces and examples
- [x] `INTEGRATION_CHECKLIST.md` - This checklist
- [x] `README.md` - Updated with Electron integration
- [ ] `electron-app/README.md` - Electron-specific setup (if exists)

---

## Final Notes

**Key Integration Points:**
1. **electron_bridge.py** is the entry point - verify it can be run standalone
2. **MCP connection** happens in background - don't block startup
3. **Model selection** via `ModelConfig.get_config(AgentMode.VOICE)`
4. **Audio loops** in GeminiLiveClient - ensure proper cleanup
5. **Logging** flows stdout → Electron → UI

**Success Criteria:**
- Backend connects to MCP and Gemini
- Voice input captured and processed
- Tools execute and return results
- Audio output plays correctly
- All logs visible in Electron UI

**Next Steps:**
- Test on different machines
- Add more robust error handling
- Implement reconnection logic
- Add user settings (audio devices, model selection)
- Create user guide/documentation


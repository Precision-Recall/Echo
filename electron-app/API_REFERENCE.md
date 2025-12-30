# Echo Electron Bridge - API Reference

## Overview

This document describes the key interfaces and APIs used in the Echo Electron app integration.

---

## 1. Python Backend API

### Entry Point: `electron_bridge.py`

#### Command Interface (stdin)

The Electron app communicates with the Python backend via stdin commands:

| Command | Description | Response |
|---------|-------------|----------|
| `START` | Start voice session | Logs session startup and begins listening |
| `STOP` | Stop current session | Gracefully stops session |
| `QUIT` | Shutdown backend | Cleanup and exit process |

**Example:**
```javascript
// In Electron (TypeScript/JavaScript)
backendProcess.stdin.write('START\n');
```

#### Log Output Format (stdout)

All logs are prefixed with type tags for parsing:

```
[TYPE] Message content
```

**Log Types:**

| Type | Format | Purpose | Example |
|------|--------|---------|---------|
| `READY` | `[READY] Backend ready` | Initialization complete | `[READY] Backend ready` |
| `STARTUP` | `[STARTUP] Message` | Startup messages | `[STARTUP] Initializing ECHO backend...` |
| `DEBUG` | `[DEBUG] Message` | Debug information | `[DEBUG] Command: START` |
| `THOUGHT` | `[THOUGHT] Message` | Agent reasoning | `[THOUGHT] 🎙️ Connecting to Gemini Live...` |
| `ACTION` | `[ACTION] Tool params` | Tool execution | `[ACTION] Executing launch_application` |
| `OBSERVATION` | `[OBSERVATION] Result` | Tool result | `[OBSERVATION] ✓ Application launched` |
| `ERROR` | `[ERROR] Error message` | Error messages | `[ERROR] ⚠️ MCP Connection Failed` |
| `RESULT` | `[RESULT] Response` | Agent responses | `[RESULT] 📝 Echo: I've opened Calculator` |
| `SHUTDOWN` | `[SHUTDOWN] Message` | Shutdown messages | `[SHUTDOWN] Backend stopped` |

**Parsing Example (JavaScript):**
```javascript
backendProcess.stdout.on('data', (data) => {
  const line = data.toString();
  const match = line.match(/^\[(\w+)\]\s*(.*)$/);
  
  if (match) {
    const [, type, message] = match;
    
    switch(type) {
      case 'READY':
        console.log('Backend ready!');
        break;
      case 'THOUGHT':
        updateThinkingPanel(message);
        break;
      case 'RESULT':
        updateTranscription(message);
        break;
      case 'ERROR':
        showError(message);
        break;
    }
  }
});
```

---

## 2. Core Python Components

### 2.1 ElectronLogger

**Location:** `electron-app/backend/electron_bridge.py`

**Purpose:** Formats and outputs logs for Electron consumption

```python
class ElectronLogger(ThinkingLogger):
    """Logger that outputs to stdout for Electron to capture"""
    
    def __init__(self):
        super().__init__(ui_callback=self._electron_callback)
        self.audit_file = os.path.join(electron_app_dir, 'audit.log')
```

**Methods:**

```python
def log_thought(self, message: str) -> None:
    """Log agent thinking/reasoning"""
    # Output: [THOUGHT] message

def log_action(self, tool_name: str, params=None) -> None:
    """Log tool execution"""
    # Output: [ACTION] Executing tool_name {"params": ...}

def log_observation(self, result) -> None:
    """Log tool execution result"""
    # Output: [OBSERVATION] ✓ result

def log_error(self, message: str) -> None:
    """Log error messages"""
    # Output: [ERROR] message

def log_result(self, result) -> None:
    """Log final response/transcription"""
    # Output: [RESULT] result
```

**Audit Log:**

All logs are also written to `electron-app/audit.log` with timestamps:
```
[HH:MM:SS] [type] message
```

---

### 2.2 SessionManager

**Location:** `electron-app/backend/electron_bridge.py`

**Purpose:** Manages voice session lifecycle and MCP connection

```python
class SessionManager:
    def __init__(self, api_key: str, logger: ElectronLogger):
        self.api_key = api_key
        self.logger = logger
        self.mcp_client = None
        self.session_task = None
        self.running = False
```

**Key Methods:**

#### `initialize_mcp()`
```python
async def initialize_mcp(self):
    """Initialize MCP connection (called at startup)"""
```
- Connects to Windows-MCP at `http://127.0.0.1:8000/mcp`
- Fetches available tools
- Logs connection status
- Falls back to voice-only mode if MCP unavailable

**Logs:**
- Success: `[THOUGHT] ✅ Loaded N tools from MCP`
- Failure: `[ERROR] ⚠️ MCP Connection Failed`

#### `start_session()`
```python
async def start_session(self):
    """Start voice session"""
```
- Gets model configuration for VOICE mode
- Creates `GeminiLiveClient`
- Starts audio loops
- Manages session lifecycle

**Flow:**
1. Check if session already running
2. Retry MCP connection if previously failed
3. Get model config: `ModelConfig.get_config(AgentMode.VOICE)`
4. Create client with API key, model name, logger, MCP client
5. Call `client.run()`

#### `stop_session()`
```python
async def stop_session(self):
    """Stop session"""
```
- Cancels running session task
- Cleans up resources
- Logs shutdown

---

### 2.3 GeminiLiveClient

**Location:** `src/agent/live_client.py`

**Purpose:** Core Gemini Live interaction handler

```python
class GeminiLiveClient:
    def __init__(
        self, 
        api_key: str, 
        model_name: str, 
        logger, 
        mcp_client: Any = None
    ):
```

**Parameters:**
- `api_key`: Gemini API key (from environment)
- `model_name`: Model to use (from ModelConfig)
- `logger`: ElectronLogger instance
- `mcp_client`: Optional pre-initialized MCP client

**Key Methods:**

#### `run()`
```python
async def run(self):
    """Main loop: Connect -> Audio/Tool Loop"""
```
- Connects to MCP if not provided
- Converts MCP tools to GenAI format
- Loads system prompt
- Establishes Gemini Live session
- Starts bidirectional audio streaming

#### Internal Methods

```python
async def _connect_mcp(self):
    """Connect to MCP server if not already connected"""

async def _get_genai_tools(self) -> List[Tool]:
    """Convert MCP tools to Google GenAI Tool objects"""

async def _send_audio(self, session):
    """Send mic audio to session"""

async def _receive_loop(self, session):
    """Receive audio, transcriptions, and tool calls"""

async def _handle_tool_call(self, session, tool_call):
    """Execute tool and send response"""
```

**Configuration:**

Default Gemini Live config:
```python
config = {
    "response_modalities": ["AUDIO"],
    "tools": tools,  # From MCP
    "system_instruction": system_prompt,
    "speech_config": {
        "voice_config": {
            "prebuilt_voice_config": {
                "voice_name": "Puck"
            }
        }
    },
    "output_audio_transcription": {},
    "enable_affective_dialog": True,
    "thinking_config": types.ThinkingConfig(
        thinking_budget=1024
    )
}
```

---

### 2.4 AudioManager

**Location:** `src/agent/audio.py`

**Purpose:** Handle audio I/O with PyAudio

```python
class AudioManager:
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    INPUT_RATE = 16000   # Mic: 16kHz
    OUTPUT_RATE = 24000  # Gemini: 24kHz
    CHUNK = 512
```

**Key Methods:**

```python
async def start_recording(self):
    """Start capturing microphone input"""
    # Uses callback pattern, non-blocking

async def stop_recording(self):
    """Stop capturing microphone input"""

async def get_audio_chunk(self):
    """Get next chunk from input queue"""
    # Returns: bytes (PCM audio data)

def start_playback(self):
    """Start playing audio"""
    # Uses blocking write in background thread

def stop_playback(self):
    """Stop audio playback"""

def play_audio_chunk(self, data: bytes):
    """Add audio chunk to playback queue"""
    # Auto-starts playback if not running

def close(self):
    """Cleanup resources"""
```

**Audio Format:**
- **Input:** 16kHz, 16-bit PCM, Mono
- **Output:** 24kHz, 16-bit PCM, Mono
- **Chunk Size:** 512 samples (~32ms at 16kHz)

---

### 2.5 ModelConfig

**Location:** `src/agent/llm_agent.py`

**Purpose:** Define model configurations per agent mode

```python
@dataclass
class ModelConfig:
    model_name: str
    temperature: float = 0
    
    @staticmethod
    def get_config(mode: AgentMode) -> 'ModelConfig':
        configs = {
            AgentMode.FAST: ModelConfig(
                "gemini-2.0-flash-exp"
            ),
            AgentMode.REASONING: ModelConfig(
                "gemini-2.0-pro-exp-02-05"
            ), 
            AgentMode.VOICE: ModelConfig(
                "gemini-2.5-flash-native-audio-preview-12-2025"
            ),
        }
        return configs.get(mode, configs[AgentMode.FAST])
```

**Usage:**
```python
# In electron_bridge.py
model_config = ModelConfig.get_config(AgentMode.VOICE)
client = GeminiLiveClient(
    api_key=api_key,
    model_name=model_config.model_name,  # ← Gets voice model
    logger=logger,
    mcp_client=mcp_client
)
```

---

## 3. MCP Integration

### Tool Format

MCP tools are automatically converted from LangChain format to Google GenAI format:

**MCP Tool (LangChain):**
```python
{
    "name": "launch_application",
    "description": "Launch an application by name",
    "args_schema": {
        "type": "object",
        "properties": {
            "app_name": {"type": "string"}
        },
        "required": ["app_name"]
    }
}
```

**Converted to GenAI Tool:**
```python
FunctionDeclaration(
    name="launch_application",
    description="Launch an application by name",
    parameters={
        "type": "object",
        "properties": {
            "app_name": {"type": "string"}
        },
        "required": ["app_name"]
    }
)
```

### Tool Execution Flow

```python
# 1. Receive tool call from Gemini
response.tool_call.function_calls[0]
# → {name: "launch_application", args: {"app_name": "calc"}}

# 2. Find tool in MCP client
tool = tool_map["launch_application"]

# 3. Execute
result = await tool.ainvoke({"app_name": "calc"})

# 4. Send response back to Gemini
FunctionResponse(
    name="launch_application",
    id=function_call.id,
    response={"result": str(result)}
)
```

---

## 4. Environment Variables

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google Gemini API key | `AIza...` |

**Location:** `.env` file in project root (parent of `electron-app/`)

**Loading:**
```python
# electron_bridge.py
load_dotenv(os.path.join(project_root, '.env'))
api_key = os.getenv('GEMINI_API_KEY')
```

---

## 5. Integration Examples

### Starting a Session (Electron → Python)

```typescript
// Electron main process
import { spawn } from 'child_process';

const pythonPath = 'python';  // or full path
const scriptPath = path.join(__dirname, 'backend', 'electron_bridge.py');

const backendProcess = spawn(pythonPath, [scriptPath], {
  cwd: projectRoot,
  env: { ...process.env }
});

// Wait for READY signal
backendProcess.stdout.on('data', (data) => {
  if (data.toString().includes('[READY]')) {
    // Backend is ready, can send START command
    backendProcess.stdin.write('START\n');
  }
});
```

### Handling Log Updates (Python → Electron)

```typescript
// Parse stdout and route to UI
backendProcess.stdout.on('data', (data) => {
  const lines = data.toString().split('\n');
  
  for (const line of lines) {
    const match = line.match(/^\[(\w+)\]\s*(.*)$/);
    if (!match) continue;
    
    const [, type, message] = match;
    
    // Send to renderer via IPC
    mainWindow.webContents.send('backend-log', {
      type: type.toLowerCase(),
      message: message.trim(),
      timestamp: Date.now()
    });
  }
});
```

### Renderer (React Component)

```typescript
// In React component
useEffect(() => {
  const handler = (event: any, log: BackendLog) => {
    switch(log.type) {
      case 'thought':
        addThoughtToPanel(log.message);
        break;
      case 'result':
        updateTranscription(log.message);
        break;
      case 'error':
        showErrorNotification(log.message);
        break;
    }
  };
  
  window.electron.onBackendLog(handler);
  return () => window.electron.offBackendLog(handler);
}, []);
```

---

## 6. Error Handling

### MCP Connection Failure

**Scenario:** Windows-MCP server not running

**Backend Response:**
```
[ERROR] ⚠️ MCP Connection Failed
[THOUGHT] ℹ️ Voice-only mode active (no desktop control)
```

**Handling:**
- Session continues without tool execution
- Voice chat still works
- UI should show warning: "Desktop control unavailable"

### Audio Device Errors

**Scenario:** Microphone or speaker not available

**Backend Response:**
```
[ERROR] ⚠️ Playback error: [Errno -9996] Invalid output device
```

**Handling:**
- Session may crash or continue with degraded functionality
- UI should show error and prompt user to check audio settings

### API Key Missing

**Scenario:** GEMINI_API_KEY not set

**Backend Response:**
```
[ERROR] ❌ GEMINI_API_KEY not set
```

**Handling:**
- Backend exits immediately
- UI should detect process exit and show setup instructions

---

## 7. Testing

### Manual Test (Without Electron)

```bash
cd electron-app/backend
python electron_bridge.py
```

**Then type commands:**
```
START
# Wait for connection...
# Speak into microphone
STOP
QUIT
```

### Check Audit Log

```bash
tail -f electron-app/audit.log
```

### Test MCP Connection

```bash
# Start MCP server first
uvx windows-mcp --transport streamable-http --port 8000

# Test connection
curl http://127.0.0.1:8000/mcp
```

---

## 8. Common Issues

### Issue: Backend doesn't start

**Cause:** Missing dependencies or Python version

**Solution:**
```bash
# From project root
uv sync
python --version  # Should be 3.12+
```

### Issue: MCP tools not loading

**Cause:** Windows-MCP server not running

**Solution:**
```bash
uvx windows-mcp --transport streamable-http --port 8000
```

### Issue: No audio output

**Cause:** Wrong audio device or rate mismatch

**Solution:**
- Check default speaker in system settings
- Verify PyAudio installation: `python -c "import pyaudio; print(pyaudio.__version__)"`

### Issue: API errors

**Cause:** Invalid or missing API key

**Solution:**
- Verify `.env` file in project root
- Check key: `cat .env | grep GEMINI_API_KEY`
- Regenerate key at https://aistudio.google.com/app/apikey

---

## 9. Performance Notes

### Latency Sources

1. **Audio Processing:** ~32ms (chunk size)
2. **Network (Gemini API):** ~100-300ms
3. **MCP Tool Execution:** ~50-500ms (varies by tool)
4. **Total End-to-End:** ~200-800ms

### Optimization Tips

- **Reduce chunk size:** Lower `CHUNK` in audio.py for faster response (but more CPU)
- **Pre-warm MCP:** Initialize MCP before starting session (already implemented)
- **Use faster model:** Switch to `gemini-2.0-flash-exp` for lower latency (trade-off: audio quality)

---

## 10. Security Considerations

### API Key Protection

- Never log API key values
- Store only in `.env` file (gitignored)
- Use environment variables in production

### MCP Server Access

- MCP server runs on localhost only (127.0.0.1)
- No external network exposure
- Tools run with user's permissions (be cautious)

### Audio Privacy

- Audio never saved to disk (in-memory only)
- Transcriptions may be logged to audit.log (review before sharing)

---

## Summary

The Echo Electron bridge provides a clean, stdin/stdout-based interface for integrating Python voice AI with a desktop Electron UI. Key integration points:

- **Commands:** START, STOP, QUIT via stdin
- **Logs:** Type-prefixed messages via stdout
- **Sessions:** Managed by SessionManager
- **Audio:** Bidirectional streaming via AudioManager
- **Tools:** MCP integration with auto-conversion to GenAI format

For detailed architecture, see `ARCHITECTURE.md`.


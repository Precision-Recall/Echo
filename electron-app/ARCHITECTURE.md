# Electron App Architecture

## Overview

The Electron app connects the Echo voice assistant to a desktop interface, enabling voice-controlled desktop automation through Gemini Live and Windows-MCP.

## Architecture Components

### 1. Entry Point: `electron_bridge.py`

**Purpose:** Bridge between Electron UI and Python backend logic

**Responsibilities:**
- Load environment variables (GEMINI_API_KEY from project root `.env`)
- Initialize logging system for Electron
- Manage MCP connection lifecycle
- Handle stdin commands from Electron (START/STOP/QUIT)

**Key Classes:**

#### `ElectronLogger` (extends `ThinkingLogger`)
```python
class ElectronLogger(ThinkingLogger):
    """Logger that outputs to stdout for Electron to capture"""
```
- Forwards all log events to stdout with type prefixes: `[THOUGHT]`, `[ACTION]`, `[OBSERVATION]`, `[ERROR]`, `[RESULT]`
- Writes audit log to `electron-app/audit.log`
- Makes text safe for console output (UTF-8 encoding)

#### `SessionManager`
```python
class SessionManager:
    """Manages the voice session lifecycle with proper MCP initialization"""
```
- **Initialization:** Connects to Windows-MCP server at startup (background task)
- **Session Management:** Creates and manages `GeminiLiveClient` instances
- **MCP Connection:** Establishes connection to `http://127.0.0.1:8000/mcp`
- **Error Handling:** Falls back to voice-only mode if MCP unavailable

**Flow:**
```
1. main() starts
2. Load .env from project root
3. Check GEMINI_API_KEY
4. Create ElectronLogger
5. Create SessionManager
6. Initialize MCP in background (non-blocking)
7. Listen for stdin commands:
   - START → start_session()
   - STOP → stop_session()
   - QUIT → cleanup and exit
```

---

### 2. Core Client: `live_client.py`

**Purpose:** Gemini Live client core - handles voice interaction and tool execution

**Key Class:** `GeminiLiveClient`

**Constructor:**
```python
def __init__(self, api_key: str, model_name: str, logger, mcp_client: Any = None)
```

**Responsibilities:**

1. **MCP Integration:**
   - Accepts pre-initialized `mcp_client` from SessionManager OR
   - Creates its own connection via `_connect_mcp()` if None provided
   - Converts MCP tools to Google GenAI format via `_get_genai_tools()`

2. **Gemini Live Session:**
   - Connects to Gemini Live API with model configuration
   - Sets up bidirectional audio streaming
   - Configures voice (Puck), transcription, and thinking mode

3. **Audio Loop Management:**
   - `_send_audio()`: Captures mic input and sends to Gemini
   - `_receive_loop()`: Receives audio/text/tool calls from Gemini
   - Uses `AudioManager` for hardware I/O

4. **Tool Execution:**
   - `_handle_tool_call()`: Executes MCP tools via LangChain
   - Maps function calls to MCP tools
   - Returns results to Gemini

**Configuration:**
```python
config = {
    "response_modalities": ["AUDIO"],
    "tools": tools,  # From MCP
    "system_instruction": system_prompt,  # From PromptLoader
    "speech_config": {
        "voice_config": {"prebuilt_voice_config": {"voice_name": "Puck"}}
    },
    "output_audio_transcription": {},
    "enable_affective_dialog": True,
    "thinking_config": types.ThinkingConfig(thinking_budget=1024)
}
```

**Audio Loop:**
```
Microphone → AudioManager.input_queue → _send_audio() → Gemini Live
                                                              ↓
Speaker ← AudioManager.output_queue ← _receive_loop() ← Gemini Live
```

---

### 3. Model Configuration: `llm_agent.py`

**Purpose:** Define model configurations and agent modes

**Key Components:**

#### `AgentMode` (Enum)
```python
class AgentMode(Enum):
    FAST = "fast"           # Fast execution
    REASONING = "reasoning" # Better planning
    VOICE = "voice"         # Voice preview model
```

#### `ModelConfig` (DataClass)
```python
@dataclass
class ModelConfig:
    model_name: str
    temperature: float = 0
    
    @staticmethod
    def get_config(mode: AgentMode) -> 'ModelConfig':
        configs = {
            AgentMode.FAST: ModelConfig("gemini-2.0-flash-exp"),
            AgentMode.REASONING: ModelConfig("gemini-2.0-pro-exp-02-05"), 
            AgentMode.VOICE: ModelConfig("gemini-2.5-flash-native-audio-preview-12-2025"),
        }
        return configs.get(mode, configs[AgentMode.FAST])
```

**Usage in electron_bridge.py:**
```python
model_config = ModelConfig.get_config(AgentMode.VOICE)
client = GeminiLiveClient(
    api_key=self.api_key,
    model_name=model_config.model_name,  # ← Gets correct model
    logger=self.logger,
    mcp_client=self.mcp_client
)
```

---

### 4. Audio Management: `audio.py`

**Purpose:** Handle audio input/output with PyAudio

**Key Class:** `AudioManager`

**Specifications:**
- **Format:** 16-bit PCM, Mono
- **Input Rate:** 16kHz (microphone)
- **Output Rate:** 24kHz (Gemini output)
- **Chunk Size:** 512 samples

**Audio Input:**
```python
async def start_recording(self)
    # Uses callback pattern for non-blocking capture
    # Streams to input_queue via asyncio

async def get_audio_chunk(self)
    # Returns next chunk from input_queue
```

**Audio Output:**
```python
def start_playback(self)
    # Uses blocking write in background thread
    # Matches official PyAudio pattern

def play_audio_chunk(self, data: bytes)
    # Adds chunk to output_queue
    # Background thread writes to speaker
```

---

## Data Flow

### Complete Voice Interaction Flow

```
┌──────────────────────────────────────────────────────────────┐
│ Electron App (JavaScript)                                    │
│  - Sends START command via stdin                             │
│  - Receives logs via stdout parsing [TYPE] messages          │
└────────────────────┬─────────────────────────────────────────┘
                     │ stdin/stdout
┌────────────────────▼─────────────────────────────────────────┐
│ electron_bridge.py                                            │
│  - ElectronLogger: Formats logs for Electron                 │
│  - SessionManager: Manages lifecycle                         │
└────────────────────┬─────────────────────────────────────────┘
                     │ creates
┌────────────────────▼─────────────────────────────────────────┐
│ GeminiLiveClient (live_client.py)                            │
│  - Connects to Gemini Live API                               │
│  - Gets tools from MCP                                       │
│  - Manages audio loops                                       │
└──────┬──────────────────────────────┬────────────────────────┘
       │                              │
   ┌───▼────┐                    ┌────▼─────┐
   │  MCP   │                    │  Audio   │
   │ Client │                    │ Manager  │
   └───┬────┘                    └────┬─────┘
       │                              │
   ┌───▼────────┐              ┌──────▼─────────┐
   │ Windows-   │              │ Microphone/    │
   │ MCP Server │              │ Speaker        │
   │ (Tools)    │              │ (Hardware)     │
   └────────────┘              └────────────────┘
```

### Session Startup Sequence

```
1. electron_bridge.py starts
   ├─ Load .env from project root
   ├─ Get GEMINI_API_KEY
   ├─ Create ElectronLogger
   └─ Create SessionManager
   
2. SessionManager.initialize_mcp() [Background Task]
   ├─ Connect to http://127.0.0.1:8000/mcp
   ├─ Get tools list
   └─ Log: "✅ Loaded N tools from MCP"
   
3. User presses Alt+Space (Electron sends "START")
   
4. SessionManager.start_session()
   ├─ Get model config: ModelConfig.get_config(AgentMode.VOICE)
   │  └─ Returns: "gemini-2.5-flash-native-audio-preview-12-2025"
   ├─ Create GeminiLiveClient(api_key, model_name, logger, mcp_client)
   └─ Call client.run()
   
5. GeminiLiveClient.run()
   ├─ _connect_mcp() [Skip if mcp_client provided]
   ├─ _get_genai_tools() → Convert MCP tools to GenAI format
   ├─ Load system prompt from Prompts/prompts/echo_voice_tui.txt
   ├─ Connect to Gemini Live with config
   └─ Start TaskGroup:
      ├─ _send_audio() → Mic → Gemini
      └─ _receive_loop() → Gemini → Speaker/Tools
```

### Tool Execution Flow

```
User speaks: "Open Calculator"
    ↓
Microphone → AudioManager.input_queue
    ↓
_send_audio() → Gemini Live API
    ↓
Gemini processes speech + decides tool call
    ↓
_receive_loop() gets tool_call response
    ↓
_handle_tool_call(session, tool_call)
    ├─ Extract function name & args
    ├─ Find tool in MCP client
    ├─ Execute: await tool.ainvoke(args)
    ├─ Log action/observation
    └─ Send response back to Gemini
    ↓
Gemini generates voice response
    ↓
_receive_loop() gets audio data
    ↓
AudioManager.play_audio_chunk() → Speaker
    ↓
User hears: "I've opened Calculator for you"
```

---

## Configuration

### Environment Variables (`.env` in project root)

```bash
GEMINI_API_KEY=your_api_key_here
```

**Note:** The electron_bridge loads `.env` from the **project root** (parent of `electron-app/`), not from `electron-app/backend/`.

### MCP Server

**URL:** `http://127.0.0.1:8000/mcp`

**Start Command:**
```bash
uvx windows-mcp --transport streamable-http --port 8000
```

**Tool Format:** MCP tools are automatically converted to Google GenAI `FunctionDeclaration` format.

---

## Logging System

### Log Types

| Type | Prefix | Purpose |
|------|--------|---------|
| THOUGHT | `[THOUGHT]` | Agent reasoning/planning |
| ACTION | `[ACTION]` | Tool execution start |
| OBSERVATION | `[OBSERVATION]` | Tool execution result |
| ERROR | `[ERROR]` | Error messages |
| RESULT | `[RESULT]` | Final responses/transcriptions |

### Electron Integration

**Stdout Format:**
```
[TYPE] Message content
```

**Example:**
```
[THOUGHT] 🎙️ Connecting to Gemini Live...
[THOUGHT] ✅ Connected! Start speaking...
[THOUGHT] 🎤 You: Open Calculator
[ACTION] Executing launch_application {"app_name": "calc"}
[OBSERVATION] ✓ Application launched
[RESULT] 📝 Echo: I've opened Calculator for you
```

**Audit Log:** `electron-app/audit.log` - Full session log with timestamps

---

## Error Handling

### MCP Connection Failure

If MCP server is not running:
```python
# SessionManager.initialize_mcp()
self.logger.log_error(f"⚠️ MCP Connection Failed")
self.logger.log_thought("ℹ️ Voice-only mode active (no desktop control)")
self.mcp_client = None
```

**Result:** Session continues in voice-only mode (no tools available)

### Audio Errors

Audio errors are logged but don't crash the session:
```python
# audio.py
except Exception as e:
    if self._is_playing:
        print(f"⚠️ Playback error: {e}")
```

### Tool Execution Errors

Failed tool calls return error response to Gemini:
```python
# live_client.py _handle_tool_call()
except Exception as e:
    self.logger.log_error(f"Tool error: {e}")
    function_responses.append(FunctionResponse(
        name=name,
        id=fc.id,
        response={"error": str(e)}
    ))
```

---

## Key Integration Points

### 1. Electron ↔ Python Bridge

**Communication:** stdin (commands) / stdout (logs)

**Commands:**
- `START` - Start voice session
- `STOP` - Stop current session
- `QUIT` - Shutdown backend

### 2. Python ↔ MCP Server

**Communication:** HTTP requests via `langchain_mcp_adapters.client.MultiServerMCPClient`

**Operations:**
- `get_tools()` - Fetch available tools
- `tool.ainvoke(args)` - Execute tool

### 3. Python ↔ Gemini Live

**Communication:** WebSocket via `google.genai` SDK

**Streams:**
- Audio input (16kHz PCM)
- Audio output (24kHz PCM)
- Tool calls (bidirectional)
- Transcriptions (text)

### 4. Python ↔ Audio Hardware

**Communication:** PyAudio streams

**Modes:**
- Input: Callback mode (non-blocking)
- Output: Blocking write in thread

---

## Debugging

### Check MCP Connection

```python
# In SessionManager.initialize_mcp()
tools = await self.mcp_client.get_tools()
tool_names = [t.name for t in tools]
self.logger.log_thought(f"Available: {', '.join(tool_names)}")
```

### View Audit Log

```bash
tail -f electron-app/audit.log
```

### Test Without Electron

```bash
# From project root
cd electron-app/backend
python electron_bridge.py
# Then type: START
```

---

## Dependencies

### Python Packages

- `google-genai` - Gemini Live SDK
- `langchain_mcp_adapters` - MCP client
- `pyaudio` - Audio I/O
- `python-dotenv` - Environment variables
- `asyncio` - Async/await support

### External Services

- **Windows-MCP Server** - Must be running on port 8000
- **Gemini API** - Requires valid API key

---

## Future Improvements

1. **Reconnection Logic:** Auto-reconnect to MCP if connection drops
2. **Audio Device Selection:** Allow user to choose mic/speaker
3. **Session Persistence:** Save/restore conversation state
4. **Multi-User Support:** Handle multiple simultaneous sessions
5. **Enhanced Error Recovery:** Retry failed tool calls with backoff

---

## Summary

The Electron bridge architecture provides a clean separation of concerns:

- **electron_bridge.py** → Session management, logging, MCP initialization
- **live_client.py** → Core Gemini Live logic, audio loops, tool execution
- **llm_agent.py** → Model configuration and agent modes
- **audio.py** → Low-level audio hardware management

All components work together through well-defined interfaces, making the system modular, testable, and maintainable.


# 🎙️ Echo

> **"Hey Google, but for your Desktop."**

**Echo** transforms your Windows PC into a fully voice-controlled environment. Just speak naturally, and Echo plans and executes complex tasks across your applications in real-time.

Under the hood, Echo combines:
- **Gemini Live**: For ultra-fast, multimodal understanding and reasoning.
- **Computer-MCP**: A robust Model Context Protocol (MCP) server for deep OS integration and control.
- **LangChain**: To orchestrate intelligent, multi-step agent workflows.

---

## 🚀 Quick Start

- Windows 11 (Home, Pro, or Enterprise)
- Python 3.12+
- [Google Gemini API Key](https://aistudio.google.com/app/apikey)
- [Windows-MCP](https://github.com/CursorTouch/Windows-MCP) (auto-installed)

### Installation

```bash
# Clone the repository
cd DesktopAgent

# Install dependencies
uv sync

# Create .env file with your Gemini API key
copy .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### Running

1. **Start the Windows-MCP Server** (Required backend):
   ```bash
   uvx windows-mcp --transport streamable-http --port 8000
   ```

2. **Run the Agent** (in a new terminal):

   **Test Mode** (CLI - no UI):
   ```bash
   # Run a simple command
   uv run python main.py --command "Open Notepad and type Hello World"
   ```

**Electron App Mode** (Desktop UI):
```bash
# 1. Start Windows-MCP server (required)
uvx windows-mcp --transport streamable-http --port 8000

# 2. In a new terminal, navigate to electron-app
cd electron-app

# 3. Install dependencies (first time only)
npm install

# 4. Start the Electron app
npm start
```

The Electron app provides:
- Push-to-talk voice control (Alt+Space)
- Real-time thinking visualization
- Session management UI

The agent will:
1. 💭 Think about the task
2. 🔧 Execute actions on your desktop
3. 👁️ Observe results
4. ✅ Report success

---

## Project Vision

It builds on:

- Modern LLMs (e.g., Gemini) for natural language understanding and planning.
- Existing Windows automation tooling similar to Windows‑Use / Windows‑MCP for actual desktop control.
- Windows Sandbox (and later, container‑based sandboxes) for isolated, disposable execution environments.[1][2]


Traditional desktop automation tools are powerful but:

- They execute directly on your real machine (high risk if something goes wrong).
- They behave like black boxes: you only see the final result, not how the AI decided what to do.
- They usually require scripting, not natural language.[1]

**VoiceFlow Desktop** aims to change that:

1. **Voice‑first**: Control your desktop with natural speech (or text, as a fallback).
2. **Transparent**: See the AI’s step‑by‑step reasoning (“thinking view”) as it plans and executes actions.
3. **Safe**: Optionally run all actions in a sandboxed environment that is isolated and disposable, so your real system is never at risk.[2]

The long‑term goal is a **cross‑platform automation framework** with pluggable backends for Windows, macOS, and Linux. The first implementation targets Windows.

## High‑Level Architecture

### Components Overview

Echo consists of:

**Core Components:**
- **Gemini Live Client** (`src/agent/live_client.py`) - Handles bidirectional audio streaming and tool execution
- **Audio Manager** (`src/agent/audio.py`) - Manages microphone input and speaker output
- **MCP Integration** - Connects to Windows-MCP for desktop automation tools
- **Thinking Logger** (`src/agent/thinking_logger.py`) - Captures and streams agent reasoning

**Interfaces:**
- **CLI Mode** (`main.py`) - Direct command execution for testing
- **Electron App** (`electron-app/`) - Desktop UI with voice control

At a high level, Echo consists of:

1. **Voice & LLM Layer**
   - Capture user speech (or text).
   - Use an LLM (e.g., Gemini) to understand the request, plan a sequence of steps, and decide which desktop actions are needed.[3]

2. **Agent & “Thinking” Layer**
   - An agent loop (inspired by frameworks like LangChain) that:
     - Plans actions.
     - Calls tools to interact with the desktop (open apps, click, type, etc.).
     - Logs each thought, action, and observation into a structured “thinking trace” for visualization.[1]

3. **Execution Backends**
   - **Direct Backend (Fast Mode)**: Runs actions directly on the host, similar in spirit to Windows‑Use / Windows‑MCP.[1]
   - **Sandbox Backend (Safe Mode)**: Spins up an isolated environment (e.g., Windows Sandbox) and runs the same agent inside it, so all actions are contained and ephemeral.[2]

4. **Desktop Automation Tools**
   - A set of MCP‑style tools for:
     - Launching apps.
     - Clicking/moving the mouse.
     - Typing text.
     - Reading window / element state.
     - Executing shell commands.
   - On Windows, these are implemented by integrating with an existing MCP server for desktop use.[1]

5. **Desktop UI (Electron App)**
   - Voice controls (push-to-talk with Alt+Space)
   - Live **Thinking Panel** (AI reasoning stream)
   - Real-time transcription display
   - Session management (start/stop)
   - Status indicators and result view
   
   **Architecture:** The Electron app connects to the Python backend via stdin/stdout:
   - `electron-app/backend/electron_bridge.py` - Python bridge process
   - Receives commands: START, STOP, QUIT
   - Streams logs to Electron via stdout prefixes: `[THOUGHT]`, `[ACTION]`, `[RESULT]`
   
   See `electron-app/ARCHITECTURE.md` for detailed integration documentation.

### Architecture Diagram

```text
┌─────────────────────────────────────────────────────────────┐
│ Electron App (JavaScript)                                   │
│  - UI Controls (Alt+Space to toggle)                        │
│  - Thinking Panel (live reasoning)                          │
│  - Transcription Display                                    │
└───────────────────┬─────────────────────────────────────────┘
                    │ stdin/stdout
┌───────────────────▼─────────────────────────────────────────┐
│ electron_bridge.py (Session Manager)                        │
│  - ElectronLogger: Format logs for UI                       │
│  - Initialize MCP connection                                │
│  - Create GeminiLiveClient on START                         │
└───────────────────┬─────────────────────────────────────────┘
                    │ creates
┌───────────────────▼─────────────────────────────────────────┐
│ GeminiLiveClient (live_client.py)                           │
│  - Connect to Gemini Live API                               │
│  - Load tools from MCP                                      │
│  - Bidirectional audio streaming                            │
│  - Execute tool calls                                       │
└─────┬───────────────────────────────┬───────────────────────┘
      │                               │
┌─────▼──────┐                  ┌─────▼──────────┐
│ MCP Client │                  │ AudioManager   │
│ (Tools)    │                  │ (I/O)          │
└─────┬──────┘                  └─────┬──────────┘
      │                               │
┌─────▼──────────┐            ┌───────▼────────────┐
│ Windows-MCP    │            │ Microphone/Speaker │
│ Server         │            │ (Hardware)         │
│ (Port 8000)    │            │ 16kHz/24kHz PCM    │
└────────────────┘            └────────────────────┘
```

**Voice Interaction Flow:**
1. User speaks → Microphone → AudioManager
2. AudioManager → GeminiLiveClient → Gemini Live API
3. Gemini processes speech + decides actions
4. Tool calls → MCP Client → Windows-MCP → Execute
5. Results → Gemini → Generate voice response
6. Audio response → AudioManager → Speaker
7. All steps logged → ElectronLogger → Electron UI

In **Fast Mode**, the backend calls the MCP tools directly on the host OS.[1]

In **Safe Mode**, the backend talks to an agent running **inside** a sandboxed environment (for example, a Windows Sandbox instance) and proxies commands and results in and out of that environment.[2]

***

## 3. Execution Modes

### 3.1 Fast Mode (Direct Execution)

Fast Mode is the default and simplest mode:

- The agent runs on the host.
- All MCP tools interact directly with the host desktop (e.g., clicking buttons, launching apps).
- Best for:
  - Trusted workflows.
  - Rapid iteration while developing automations.
  - Environments where the user fully controls the machine.[1]

**Pros**

- Very low latency (no sandbox startup overhead).
- Easy to debug.
- Good for demos where you control the environment.

**Cons**

- Any AI mistake affects the real system (file deletions, mis‑clicks, etc.).
- Less suitable for untrusted or experimental tasks.

To reduce risk, Fast Mode should still include:

- **Confirmation prompts** for obviously destructive actions (e.g., deleting files, formatting drives).
- A simple **“undo last action”** concept where possible (e.g., restore from a temp location if files were moved).

### 3.2 Safe Mode (Sandbox Execution)

Safe Mode executes everything in a disposable, isolated environment:

- Uses a sandbox technology such as **Windows Sandbox**, which provides:
  - Hardware‑based virtualization.
  - Isolation from host file system and registry.
  - Automatic teardown of the environment when closed.[4][2]
- The agent and automation tools run **inside** the sandbox.
- The host orchestrator:
  - Launches the sandbox.
  - Sends the user’s command into the sandbox.
  - Streams back results and the thinking trace.
- Ideal for:
  - High‑risk automations.
  - Testing unknown or untrusted workflows.
  - Demonstrating safety properties to users or judges (hackathons).[2]

**Pros**

- Safe by design: when the sandbox is destroyed, all changes vanish.
- Great for experimentation and “what‑if” tasks.
- Strong story for security‑sensitive users and enterprises.[5][2]

**Cons**

- Startup overhead (sandbox needs time to boot).
- Slightly higher latency due to cross‑boundary communication.
- Requires OS features (e.g., Windows 11 Pro/Enterprise with sandbox enabled).[2]

The long‑term plan is to support additional sandbox backends such as containerized GUI environments for Linux/macOS.

***

## 4. Sandbox Approach – Detailed Design

### 4.1 Why Sandbox at All?

AI desktop agents can easily:

- Misinterpret vague instructions.
- Interact with the wrong window or file.
- Execute dangerous shell commands if prompted poorly.

A sandboxed environment dramatically reduces the impact of these mistakes:

- All file changes, registry edits, and app installs are confined to an ephemeral environment.[2]
- When the sandbox closes, everything is reset to a clean state by design.[2]
- The host OS only sees:
  - Structured results (e.g., “summary text”, “generated slide deck” exported via an explicit channel).
  - Optional files copied out of the sandbox via controlled mechanisms (e.g., a shared folder).

This lets users **let the AI “go wild”** while keeping their actual system safe.

### 4.2 Sandbox Backend Responsibilities

The Sandbox Execution Backend is responsible for:

1. **Starting and Stopping Sandbox Environments**
   - Launch a sandbox using the OS‑specific mechanism (e.g., configuration file‑based launch for Windows Sandbox).[4]
   - Optionally keep one sandbox “warm” for faster subsequent tasks.
   - Detect crashes or exits and restart as needed.

2. **Provisioning the Sandbox**
   - Ensure the sandbox has:
     - A Python runtime (or equivalent).
     - The agent runtime and automation tools (e.g., Windows‑Use‑style integration).
     - Network access only as necessary (e.g., to reach the LLM API), or route through the host for more control.[2]
   - This can be done:
     - On each launch (slower, simpler).
     - Or via prepared images / templates (faster startup, more setup work).

3. **Communication with the Agent Inside Sandbox**
   - The host sends a single **task** (complete user query) into the sandbox.
   - The sandbox agent:
     - Interprets the task.
     - Runs the full thought‑plan‑act loop.
     - Logs its thinking steps.
     - Returns final results and a structured trace of its reasoning.
   - Communication channels can be:
     - File‑based (shared folder with JSON messages).[4]
     - Named pipes or a lightweight HTTP server inside the sandbox.
   - For a first version, file‑based message passing is usually easiest.

4. **Security & Isolation**
   - Configure sandbox settings to:
     - Restrict shared folders to a minimal, dedicated path.
     - Turn off unnecessary integration (clipboard, printers) where possible.
     - Limit network access if feasible.[4][2]
   - Never rely on sandbox for secrecy of sensitive data; focus on containment of side effects.

### 4.3 Thinking Visualization in Sandbox Mode

The “thinking view” works the same way in both Fast and Safe modes:

- The agent logs each step:
  - Thought: Why it chose a particular action.
  - Action: Which tool it’s calling (e.g., “Launch app: Calculator”).
  - Observation: What it saw after the action (e.g., “Calculator window detected”).[1]
- In Safe Mode:
  - These logs are written inside the sandbox and streamed out to the host UI through the chosen communication channel.
  - The UI treats them identically to Fast Mode; only the label or status indicator changes (e.g., “Running in sandbox”).

This gives users a consistent mental model: **“The AI always explains itself, regardless of mode; the only difference is where it runs.”**

***

## 5. Desktop Automation Tools (MCP‑Style)

VoiceFlow Desktop uses a set of tools that follow a common schema, inspired by MCP servers such as Windows‑MCP.[1]

### 5.1 Core Tool Categories

Typical tools include:

- **Application Control**
  - Launch an application by name.
  - Focus or close windows.
- **Mouse & Keyboard**
  - Click at coordinates.
  - Move the cursor.
  - Type text in the active window.
  - Press shortcuts (e.g., Ctrl+C, Alt+Tab).[1]
- **State Inspection**
  - Get snapshot of open windows and UI elements.
  - Read text / labels from controls where possible.[1]
- **System & Shell**
  - Execute shell commands (with appropriate safeguards).
  - Query files, processes, and basic system info.

Each tool is defined in a way that can be exposed to an LLM as a callable function (via tool/function calling), letting the model choose which actions to perform based on the current context.[1]

### 5.2 Platform Abstraction

The long‑term plan is to maintain:

- A **unified tool interface** that describes what each tool does in an abstract way.
- Separate **backends** per platform:
  - Windows backend using existing Windows‑focused automation (MCP server / Windows‑Use‑style tools).[1]
  - Future macOS backend (e.g., using AppleScript and accessibility APIs).
  - Future Linux backend (e.g., xdotool + accessibility frameworks).[6][7]

The sandbox mechanism will also be abstracted so that Windows Sandbox on Windows can be replaced by container‑based GUI sandboxes elsewhere.

***

## 6. User Experience

### 6.1 Main UI Concepts

The main application presents:

1. **Mode Selector**
   - **Fast (Direct)** – runs on host.
   - **Safe (Sandbox)** – runs in isolated environment (once implemented).
   - Safe mode may initially be marked as “experimental” or “coming soon,” depending on development stage.

2. **Voice Input Panel**
   - Microphone button or push‑to‑talk key.
   - Live transcript of what the user said.
   - Status indicators:
     - Listening.
     - Thinking.
     - Executing.

3. **Thinking Panel**
   - Real‑time log of:
     - Thoughts (“Analyzing request…”, “Need to open Excel first…”).
     - Actions (“Launching Excel”, “Clicking ‘File → Open’”).
     - Observations (“Found window titled ‘Report.xlsx’”).
   - Color‑coded and time‑stamped to show progression and performance.

4. **Result Panel**
   - Final outcome, e.g.:
     - Summary text.
     - Confirmation that a task was completed.
     - Links or paths to generated files.

5. **Sandbox Status (Safe Mode)**
   - Clear label like “Running in sandbox” when Safe mode is active.
   - Optional controls:
     - Restart sandbox.
     - View sandbox logs.
     - Export artifacts out of the sandbox (e.g., copy a generated presentation to the host).

### 6.2 Safety & Confirmation Flows

Even in Fast Mode, the UI should:

- Flag potentially destructive operations (e.g., file deletions, disk operations).
- Ask for explicit confirmation before proceeding.
- Allow the user to cancel or modify the planned sequence.

In Safe Mode, the UI can embrace more aggressive experiments, since the risk is constrained to the sandbox environment.[2]

***

## 7. Roadmap

### Phase 1 – Fast Mode (Direct Execution)

- Voice input + LLM planning.
- Direct host automation via Windows automation tools.
- Thinking visualization in real time.
- Basic safety:
  - Confirm destructive actions.
  - Log actions and results.

### Phase 2 – Safe Mode (Windows Sandbox Backend)

- Integrate with Windows sandboxing capabilities.[4][2]
- Run agent and tools inside the sandbox.
- Proxy commands and results between host and sandbox.
- UI support for mode switching and sandbox status.

### Phase 3 – Cross‑Platform & Advanced Features

- Add macOS and Linux backends with equivalent toolsets.
- Replace or complement Windows Sandbox with container‑based GUI sandboxes on other platforms.[7][6]
- Provide a workflow library and sharing mechanism.
- Enterprise features:
  - Team collaboration.
  - Audit logging.
  - Policy controls.

***

## 8. Security Considerations

- **Fast Mode**
  - Use confirmations and restricted operations lists to reduce accidental damage.
  - Design with “explainability” in mind: users should be able to see why an action was chosen before it runs.

- **Safe Mode**
  - Rely on OS‑level isolation provided by sandboxing technology.[2]
  - Limit shared resources between host and sandbox to the minimal necessary.
  - Treat network access cautiously and restrict external endpoints where possible.

- **Data Handling**
  - Avoid storing sensitive data in logs.
  - Redact secrets (API keys, passwords) from the thinking trace before rendering.

***

## 9. Use Cases

- Safely testing new automation workflows before applying them to a real system.
- Teaching or demonstrating how AI agents plan and execute desktop tasks.
- Running high‑risk batch operations in a disposable environment.
- Building accessible, voice‑first desktop experiences for users who prefer or require hands‑free interaction.

***

## 10. Summary

VoiceFlow Desktop combines:

- **Natural language + voice** input.
- **Transparent, step‑by‑step thinking visualization.**
- **Dual execution modes**:
  - Fast, direct execution for trusted tasks.
  - Safe, sandboxed execution for experiments and high‑risk automations.



[1](https://github.com/CursorTouch/Windows-MCP)
[2](https://learn.microsoft.com/en-us/windows/security/application-security/application-isolation/windows-sandbox/)
[3](https://developers.googleblog.com/en/gemini-2-0-level-up-your-apps-with-real-time-multimodal-interactions/?linkId=12209698)
[4](https://learn.microsoft.com/en-us/windows/security/application-security/application-isolation/windows-sandbox/windows-sandbox-configure-using-wsb-file)
[5](https://hopx.ai/use-cases/desktop-automation/)
[6](https://www.baeldung.com/linux/docker-container-gui-applications)
[7](https://github.com/mviereck/x11docker)
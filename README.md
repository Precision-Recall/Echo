<div align="center">

# Echo
### The Future of Desktop Computing

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Electron](https://img.shields.io/badge/Electron-33.0.0-47848F?style=for-the-badge&logo=electron&logoColor=white)](https://www.electronjs.org/)
[![Gemini](https://img.shields.io/badge/Gemini-2.0%20Flash-8E75B2?style=for-the-badge&logo=google&logoColor=white)](https://deepmind.google/technologies/gemini/)
[![MCP](https://img.shields.io/badge/MCP-Enabled-orange?style=for-the-badge)](https://modelcontextprotocol.io/introduction)
[![License](https://img.shields.io/badge/License-Private-red?style=for-the-badge)](./LICENSE)

<br/>

**Echo is a multimodal AI agent that lives on your desktop.**  
It doesn't just chat—it *acts*. Using advanced speech-to-speech models and the Model Context Protocol (MCP), Echo listens to your voice, understands your intent, and controls your computer to get things done.

[Features](#-features) • [Installation](#-quick-start) • [Architecture](#-architecture) • [Documentation](#-documentation)

</div>

---

## <img src="https://api.iconify.design/lucide:zap.svg" width="24" /> What is Echo?

Echo bridges the gap between conversational AI and OS-level control. Most assistants are trapped in a browser tab. Echo **integrates with your operating system**, allowing it to:

*   **<img src="https://api.iconify.design/lucide:eye.svg" width="16" /> See** your screen and understand context.
*   **<img src="https://api.iconify.design/lucide:ear.svg" width="16" /> Hear** your voice with sub-second latency (Real-time API).
*   **<img src="https://api.iconify.design/lucide:play.svg" width="16" /> Act** on your apps, files, and workflows using specialized tools.

Whether you're managing a Google Classroom, automating a complex workflow, or building a presentation, Echo acts as your intelligent co-pilot.

## <img src="https://api.iconify.design/lucide:sparkles.svg" width="24" /> Features

### <img src="https://api.iconify.design/lucide:mic.svg" width="20" /> Native Voice Interaction
Speak naturally. Echo uses **Gemini 2.0 Flash**'s native audio capabilities for fluid, interruptible, human-like conversation. No "wake words" or robotic pauses.

### <img src="https://api.iconify.design/lucide:monitor.svg" width="20" /> Full Desktop Control
Echo isn't limited to APIs. It can use your computer like a human:
*   **App Launching**: "Open VS Code and Spotify."
*   **UI Interaction**: Click, type, scroll, and navigate GUI applications.
*   **Screen Perception**: It "sees" what you see to provide context-aware help.

### <img src="https://api.iconify.design/lucide:plug.svg" width="20" /> Model Context Protocol (MCP)
Built on the open standard for AI tools. Echo connects to any MCP server:
*   **FileSystem**: Read/Write files safely.
*   **Terminal**: Execute commands and analyze output.
*   **Browser**: Automate web research and tasks.
*   **Custom**: Add your own tools easily.

### <img src="https://api.iconify.design/lucide:graduation-cap.svg" width="20" /> Google Classroom Assistant
A dedicated module for educators:
*   **Course Management**: Create courses, invite students, and manage rosters.
*   **Assignment Automation**: Draft and publish assignments with attachments.
*   **Smart Forms**: Generate quizzes and feedback forms automatically.

### <img src="https://api.iconify.design/lucide:brain-circuit.svg" width="20" /> Transparent Reasoning
Watch Echo "think" in real-time. The UI visualizes the **Chain of Thought (CoT)**, showing you exactly how the agent plans and executes complex tasks step-by-step.

---

## <img src="https://api.iconify.design/lucide:layers.svg" width="24" /> Architecture

Echo uses a hybrid architecture to combine the best of web technologies and native performance.

```mermaid
graph TD
    User((User)) -->|Voice/Text| ElectronUI[Electron App / TUI]
    
    subgraph Frontend
        ElectronUI -->|WebSocket| Backend
        ElectronUI -->|Render| React[React UI]
    end
    
    subgraph Core ["Echo Backend (Python)"]
        Backend[FastAPI Server] -->|Orchestrate| Agent[Planner Agent]
        Backend -->|Stream| Voice[Gemini Live API]
        
        Agent -->|Think| CoT[Chain of Thought]
        Agent -->|Execute| Tools[Tool Manager]
    end
    
    subgraph Ecosystem ["MCP & APIs"]
        Tools <-->|Connect| MCP[MCP Servers]
        MCP -->|Control| Windows[Windows OS]
        MCP -->|Manage| Classroom[Google Classroom API]
        MCP -->|Access| Files[FileSystem]
    end
```

---

## <img src="https://api.iconify.design/lucide:rocket.svg" width="24" /> Quick Start

### Prerequisites
*   **Python 3.10+**
*   **Node.js 18+**
*   **Google Gemini API Key** (with Live API access)

### Installation

1.  **Clone the repository**
    ```bash
    git clone https://github.com/your-org/echo-desktop-agent.git
    cd echo-desktop-agent
    ```

2.  **Set up the environment**
    Echo uses `uv` for fast Python package management (optional but recommended).
    ```bash
    # Install dependencies
    pip install -r requirements.txt
    
    # Or with uv
    uv sync
    ```

3.  **Configure Credentials**
    Create a `.env` file in the root directory:
    ```env
    GEMINI_API_KEY=your_api_key_here
    # Optional: For Classroom features
    GOOGLE_CLIENT_ID=...
    GOOGLE_CLIENT_SECRET=...
    ```

### Running Echo

#### Option A: Electron App (Recommended)
The full visual experience with Voice UI and Chain-of-Thought visualization.

```bash
# Terminal 1: Start the backend
python src/backend/main.py

# Terminal 2: Start the UI
cd electron-app
npm install
npm start
```

#### Option B: Terminal Interface (TUI)
A lightweight, hacker-friendly interface for the terminal.

```bash
# Voice Mode (Interactive)
python TUI.py --mode voice

# Fast Command Mode
python TUI.py --command "Open Notepad and type Hello World"
```

---

## <img src="https://api.iconify.design/lucide:book-open.svg" width="24" /> Documentation

*   **[Gemini Live MCP](./gemini_live_mcp/README.md)**: Detailed guide for the web frontend and Google Classroom integration.
*   **[Quickstart Guide](./QUICKSTART.md)**: Extended setup instructions.
*   **[MCP Configuration](./mcp_config.json)**: Configure connected tool servers.

---

## <img src="https://api.iconify.design/lucide:folder-tree.svg" width="24" /> Project Structure

```
Echo/
├── TUI.py                 # Terminal User Interface entry point
├── electron-app/          # Desktop UI (Node.js/React)
├── gemini_live_mcp/       # Next.js Web Frontend & Classroom Module
├── src/
│   ├── agent/             # Core Agent Logic (Planner, Executor)
│   ├── tools/             # Native Tool Implementations
│   └── utils/             # Helpers for Audio, MCP, Logging
└── tests/                 # Unit and Integration Tests
```

---

## <img src="https://api.iconify.design/lucide:heart-handshake.svg" width="24" /> Contributing

Echo is currently a private research project. Contributions are limited to the core team.

1.  Create a feature branch (`git checkout -b feature/amazing-feature`)
2.  Commit your changes (`git commit -m 'Add amazing feature'`)
3.  Push to the branch (`git push origin feature/amazing-feature`)
4.  Open a Pull Request

---

<div align="center">
  <sub>Built with <img src="https://api.iconify.design/lucide:heart.svg" width="12" /> by the Echo Team. Powered by Google DeepMind.</sub>
</div>

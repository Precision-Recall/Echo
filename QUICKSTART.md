# 🚀 Quick Start Guide - Echo

Echo ships as **two agents in one**. Follow the guide for whichever agent you want to run.

---

## 📋 Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.10+ | Required for both agents |
| Node.js | 18+ | Required for both agents |
| Gemini API Key | — | [Get one here](https://aistudio.google.com/app/apikey) |
| Google OAuth credentials | — | Only for Google Automation Agent |

---

## ⚙️ Common Setup (Both Agents)

### 1. Clone the Repository
```bash
git clone https://github.com/Precision-Recall/Echo.git
cd Echo
```

### 2. Add Your Gemini API Key
Create a `.env` file in the root directory:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Install Python Dependencies
```bash
# With uv (recommended — faster)
uv sync

# Or with pip
pip install -r requirements.txt
```

---

## 🖥️ Desktop Voice Assistant

Control your Windows PC using natural voice commands. Echo launches apps, types text, presses keyboard shortcuts, and chains multi-step workflows — all hands-free.

### Step 1 — Start the Windows MCP Support Server
Open a terminal and run (keep this window open):
```bash
uvx windows-mcp --transport streamable-http --port 8000
```

### Step 2 — Choose Your Interface

#### Option A: Electron App (Full Visual UI)
```bash
# Terminal 2: Start the backend
python src/backend/main.py

# Terminal 3: Start the Electron UI
cd electron-app
npm install
npm start
```

#### Option B: Terminal Interface (TUI)
```bash
# Voice Mode — speak your commands interactively
python TUI.py --mode voice

# Command Mode — run a single task and exit
python TUI.py --command "Open Notepad and type Hello World"
```

### Example Commands

```bash
# Launch an app
uv run python TUI.py --command "Open Notepad"

# Multi-step workflow
uv run python TUI.py --command "Open Notepad and type Hello World"

# Launch Calculator
uv run python TUI.py --command "Open Calculator"
```

### What the Desktop Agent Can Do

| Capability | Example |
|---|---|
| 🎙️ Real-time voice interaction | Speak hands-free |
| 🚀 App launching | "Open VS Code and Spotify" |
| ⌨️ Type text | "Type Hello World in Notepad" |
| ⌨️ Keyboard shortcuts | "Press Ctrl+S to save" |
| 🔗 Multi-step workflows | "Open Paint, draw a circle, and save" |
| 👁️ Screen perception | Context-aware help based on what's on screen |

### Example Output

```
🤖 Initializing Echo Desktop Agent...
💭 Agent initialized
💭 Task: Open Notepad

🎯 Executing: Open Notepad
============================================================
💭 Task: Open Notepad
🔧 Action: launch_app({"app_name": "notepad"})
👁️ ✓ Launched notepad
✅ Result: I've opened Notepad for you.
============================================================

📊 FINAL RESULT:
   Success: True
   Message: I've opened Notepad for you.
```

---

## ☁️ Google Automation Agent

Automate your entire Google Workspace — Classroom, Forms, Slides, and Drive — using voice or text chat, powered by Gemini AI.

### Step 1 — Set Up Google OAuth Credentials
1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a project and enable the following APIs:
   - Google Classroom API
   - Google Drive API
   - Google Forms API
   - Google Slides API
3. Create **OAuth 2.0 credentials** (Desktop app type).
4. Download `credentials.json` and place it inside `gemini_live_mcp/echo_backend/`.

Add credentials to your `.env` (root directory):
```env
GEMINI_API_KEY=your_gemini_api_key_here
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
```

### Step 2 — Configure Firebase Authentication (Optional but Recommended)
Follow `gemini_live_mcp/echo_frontend/AUTH_SETUP.md` to set up Firebase for user login.

### Step 3 — Start the Backend

> ⚠️ **Always start the backend BEFORE the frontend.**

```bash
cd gemini_live_mcp/echo_backend
pip install -r requirements.txt
python main.py
```

You should see:
```
INFO: Uvicorn running on http://0.0.0.0:8000
```

### Step 4 — Start the Frontend
In a new terminal:
```bash
cd gemini_live_mcp/echo_frontend
npm install
npm run dev
```

Open **http://localhost:3000** in your browser.

### What the Google Automation Agent Can Do

| Google Service | Capabilities |
|---|---|
| 🎓 Google Classroom | Create courses, invite students, publish assignments |
| 📝 Google Forms | Generate quizzes and feedback forms with AI |
| 📊 Google Slides | Build presentations with AI content + images |
| 📁 Google Drive | Upload files, attach to assignments |
| 🎙️ Voice & Chat | Switch between voice and text at any time |

### Example Voice/Chat Commands

```
"Show me all my courses"
"Create a new course called Python 101"
"Create an assignment for course ID 12345"
"Generate a 10-question quiz on photosynthesis"
"Build a presentation about climate change"
```

### How It Works

1. You speak or type a command in the web UI.
2. Gemini plans which Google API calls are needed.
3. Echo executes the actions and shows results in real-time.
4. You see the AI's chain of thought as it works.

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---|---|
| `windows-mcp` not found | Run `pip install windows-mcp` or use `uvx windows-mcp` |
| Backend won't start | Check `GEMINI_API_KEY` is set in `.env` |
| WebSocket connection fails | Ensure backend is running before starting frontend |
| Google API errors | Verify `credentials.json` is in `echo_backend/` and APIs are enabled |
| Firebase auth errors | Check `lib/firebase.ts` matches your Firebase project config |

---

**Need more help?** See the full [README.md](README.md) or the [Gemini Live MCP README](gemini_live_mcp/README.md).

# 🚀 Quick Start Guide - Echo

## Setup (1 minute)

1. **Add your Gemini API key** to `.env`:
   ```bash
   GEMINI_API_KEY=your_key_here
   ```

2. **Get your API key**: [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)

## Run the Agent

### 1. Start Support Server
Open a separate terminal and run:
```bash
uvx windows-mcp --transport streamable-http --port 8000
```
*(Keep this window open)*

### 2. Run Commands (in new terminal)

**Test a simple command:**
```bash
uv run python main.py --command "Open Notepad"
```

**Try more complex tasks:**
```bash
uv run python main.py --command "Open Notepad and type Hello World"
```

```bash
uv run python main.py --command "Open Calculator"
```

## What the Agent Can Do

- ✅ Launch Windows applications (notepad, calc, mspaint, etc.)
- ✅ Type text in focused windows
- ✅ Press keyboard shortcuts (ctrl+s, enter, etc.)
- ✅ Multi-step automation workflows

## How It Works

1. You give a command in natural language
2. Gemini plans the steps needed
3. Agent executes actions (launch, type, press keys)
4. You see the thinking trace in real-time

## Example Output

```
🤖 Initializing VoiceFlow Desktop agent...
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

## Next Steps

- Add voice input (coming soon)
- Build Electron UI for visual control
- Add sandbox mode for safety

---

**Need help?** Check the full [README.md](README.md) for detailed documentation.

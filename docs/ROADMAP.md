# ECHO Development Roadmap

> Last Updated: January 4, 2026

## Current Focus

### ✅ Phase 1: FAST Mode (Complete)
- Gemini Live API integration
- Real-time voice conversation
- MCP tools for Windows automation
- Electron UI with mode toggle

### ⏸️ Phase 2: REASONING Mode (Paused)
MultiAgent architecture with LangGraph - currently paused due to session synchronization issues.

**Issues Identified:**
- WebSocket timeout during long SubAgent execution
- Voice Agent makes random responses during task execution
- Difficult to synchronize real-time voice with background task processing

---

## Upcoming

### 🚀 Phase 2.1: Hybrid Voice Architecture

Replace Gemini Live in REASONING mode with Whisper + TTS:

```
REASONING Mode Flow:
┌─────────────┐     ┌────────┐     ┌──────────────┐     ┌─────┐
│ User Speaks │ --> │ Whisper│ --> │  SubAgent    │ --> │ TTS │
│  (Record)   │     │ (STT)  │     │ (Plan+Execute)│     │     │
└─────────────┘     └────────┘     └──────────────┘     └─────┘
```

**Benefits:**
- No session timeout issues
- Clean separation: Voice I/O doesn't compete with task execution
- Complete utterance captured before processing
- Better for multi-step tasks that take time

**Decisions Needed:**
| Decision | Options | Notes |
|----------|---------|-------|
| Whisper | Local / OpenAI API | Local = faster, API = accurate |
| TTS | edge-tts / pyttsx3 / Google | edge-tts is free + good quality |
| End of Speech | VAD / Push-to-talk / Silence | VAD most natural |

---

## Mode Summary

| Mode | Voice Model | Best For |
|------|-------------|----------|
| **FAST** | Gemini Live | Quick queries, single commands |
| **REASONING** | Whisper + TTS | Multi-step tasks, complex automation |

---

## File Changes Expected

When implementing Phase 2.1:
- `src/agent/whisper_client.py` - New file for Whisper STT
- `src/agent/tts_client.py` - New file for TTS output
- `src/agent/llm_agent.py` - Switch voice handler based on mode
- `electron-app/backend/electron_bridge.py` - Route to correct handler

# Building a Voice-Enabled Desktop Agent with Gemini Live & MCP

This guide details the architecture, implementation steps, and lessons learned while building the `GeminiLiveClient` for Echo. It specifically focuses on integrating Google's **Gemini Multimodal Live API** with the **Model Context Protocol (MCP)**.

## 1. Architecture Overview

The system consists of three main components running asynchronously:

1.  **Audio Manager**: Handles hardware I/O.
    *   **Input**: Microphone capture at **16kHz** (Gemini requirement).
    *   **Output**: Speaker playback at **24kHz** (Gemini high-quality voice).
2.  **MCP Client**: Manages desktop control tools.
    *   Connects to `windows-mcp` server.
    *   Exposes tools (e.g., `click`, `type`, `scrape`) to the LLM.
3.  **Gemini Live Client**: The orchestrator.
    *   Maintains a persistent WebSocket session via `google-genai`.
    *   Streams audio chunks to the model.
    *   Receives audio (text-to-speech) and tool calls.

---

## 2. Key Implementation Principles

### A. Use the Official SDK (`google-genai`)
**Do not use raw WebSockets.**
*   **Why?** The raw WebSocket protocol (`wss://generativelanguage...`) has complex authentication and handshake requirements that change frequently (e.g., protocol versioning, payload structures).
*   **Benefit**: The `google-genai` SDK handles auth, connection keep-alives, and response parsing automatically.

### B. Async Task Groups for Concurrency
Voice interaction requires simultaneous actions:
1.  Listening to the mic.
2.  Receiving audio from the server.
3.  Playing back audio.
4.  Executing tools.

**Pattern**: Use `asyncio.TaskGroup` to manage these lifecycles together. If one fails (e.g., socket disconnect), they all cancel gracefully.

```python
async with self.client.aio.live.connect(...) as session:
    async with asyncio.TaskGroup() as tg:
        tg.create_task(self._send_audio(session))    # Mic -> API
        tg.create_task(self._receive_loop(session))  # API -> Speaker + Tools
        tg.create_task(self._play_audio())           # Queue -> Speaker
```

### C. Audio Sample Rates Matter
Using the wrong sample rate causes "chipmunk voice" or slowed-down audio.
*   **Input (Mic)**: Must be **16,000 Hz** (1 channel, 16-bit PCM).
*   **Output (Speaker)**: Gemini sends **24,000 Hz** audio.
*   **Solution**: Initialize `PyAudio` streams with distinct rates.

---

## 3. Connecting MCP Tools (The "Bridge")

This is the most critical part. We need to "trick" Gemini into thinking it has local tools, when in reality they are remote MCP tools.

### Step 1: Tool Discovery & Schema Conversion
Gemini needs a specific JSON schema for tools. MCP provides a different schema (JSON Schema Draft 2020-12).

**Transformation Logic:**
1.  Fetch tools from MCP: `await mcp_client.get_tools()`
2.  Extract schema: Check if it's a Pydantic model (`args_schema.schema()`) or a raw `dict`.
3.  **Clean the Schema**: Remove `title` and `definitions` keys, which Gemini often rejects.
4.  Wrap in `google.genai.types.Tool`.

### Step 2: Execution & Response
When Gemini wants to call a tool, it sends a `tool_call` event.

1.  **Intercept**: In the receive loop, check `response.tool_call`.
2.  **Execute**:
    *   **Don't** use `mcp_client.call_tool()` if using LangChain adapters (it might not exist or work as expected).
    *   **Do** map the tool name to the LangChain tool object and call `.invoke()` (or `.ainvoke()`).
3.  **Respond**:
    *   You **MUST** send the result back to continue the conversation.
    *   Use strongly typed `FunctionResponse` and `ToolResponse` objects.
    *   Send via `session.send(input=tool_response)`.

```python
# Correct Response Format (SDK)
function_responses.append(FunctionResponse(
    name=name,
    id=fc.id,
    response={"result": str(result)}  # Must be a dict
))
await session.send(input=ToolResponse(function_responses=...))
```

---

## 4. Common Mistakes & Pitfalls

### Mistake 1: Using `send_input` for everything
*   **Issue**: In the configured SDK version, `session.send_input` might be deprecated or behave differently for control signals.
*   **Fix**:
    *   Use `session.send(input=..., end_of_turn=False)` for streaming audio.
    *   Use `session.send(input=tool_response)` for tool results.

### Mistake 2: "Invalid Frame Payload Data" (1007)
*   **Cause**: Sending Text/JSON frames when the server expects Audio (or vice versa) during a specific state, OR using an invalid Model ID.
*   **Fix**: Ensure your `mime_type` is strictly `"audio/pcm"` for audio chunks. Verify your model name (e.g., `gemini-2.5-flash-native-audio-preview-...`) represents a valid Live model.

### Mistake 3: Silent Failures in Background Tasks
*   **Cause**: If the `_receive_loop` crashes (e.g., WebSocket error), the `_send_audio` loop might keep running, making it assume the agent is "deaf."
*   **Fix**: Wrap ALL task bodies in `try/except` blocks and log errors aggressively. Use `TaskGroup` to ensure one failure stops everything.

### Mistake 4: Typos in Tool Response
*   **Issue**: Sending `tool_response` as a distinct keyword argument (`session.send(tool_response=...)`) caused crashes.
*   **Fix**: It must be nested inside `input`: `session.send(input={"tool_response": ...})` or using the typed object `session.send(input=ToolResponse(...))`.

---

## 5. Debugging Checklist

If Voice Mode isn't working:
1.  **Check API Key**: Is `GEMINI_API_KEY` set in `.env`?
2.  **Check Model**: Are you using a reliable model alias (e.g., `gemini-2.0-flash-exp`)?
3.  **Check MCP**: Is the `windows-mcp` server running on port 8000? (`uvx windows-mcp...`)
4.  **Trace Logs**: Look at `agent_trace.json` or console logs.
    *   "Connection closed: 1000" -> Normal closure.
    *   "Connection closed: 1006" -> Abnormal disconnect (network/crash).
    *   "Connection closed: 1007" -> Protocol violation (bad data).

## 6. Future Improvements Implementation
- **Video Input**: The code structure supports video (send image frames as mime_type `image/jpeg`), but it's currently audio-only.
- **Voice Interruption**: Implement "barge-in" by clearing the receiving audio queue when the user starts speaking (VAD - Voice Activity Detection).

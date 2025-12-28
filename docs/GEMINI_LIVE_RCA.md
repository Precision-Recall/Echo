# Gemini Live API - Root Cause Analysis (RCA)

## Overview

This document details the bugs encountered during the implementation of the Gemini Live API voice assistant and their solutions. The debugging session occurred on December 28, 2025.

---

## Executive Summary

| Bug | Severity | Root Cause | Fix |
|-----|----------|------------|-----|
| Multi-turn voice detection failure | Critical | Missing `while True` wrapper | Added loop around `session.receive()` |
| Connection timeout after first turn | High | Wrong API method | Changed to `session.send()` |
| Poor audio quality | Medium | Complex buffer callback | Switched to blocking write |
| Session not starting | Medium | Overly complex config | Simplified to dict format |

---

## Bug 1: Multi-Turn Voice Detection Failure

### Symptom
The Gemini Live API would respond to the first user utterance but fail to detect any subsequent speech. Audio chunks continued to be sent (verified via heartbeat logs), but the model never responded to the second turn.

### Investigation Timeline
1. Initially suspected server-side VAD (Voice Activity Detection) issue
2. Implemented manual VAD with `ActivityEnd` signals - made it worse
3. Verified PyAudio callbacks were working (chunks: 76→155→234)
4. Connection would timeout after ~45 seconds of "no detected speech"

### Root Cause
```python
# BROKEN: Only processes one turn, then exits
async def _receive_loop(self, session):
    async for response in session.receive():  # ← Iterator completes after ONE turn!
        handle_response(response)
```

The `session.receive()` method returns an async iterator that yields responses for **one turn only**. After the model finishes responding (turn_complete), the iterator ends. Without re-calling `session.receive()`, no further turns are processed.

### Solution
```python
# FIXED: Wraps receive in while True for continuous turns
async def _receive_loop(self, session):
    while True:  # ← Critical: Re-call receive() for each new turn
        async for response in session.receive():
            handle_response(response)
```

### Lesson Learned
The Google cookbook example (`Get_started_LiveAPI.py`) includes this pattern, but it's easy to miss. Always wrap `session.receive()` in a `while True` loop for continuous conversation.

---

## Bug 2: Wrong API Method for Sending Audio

### Symptom
Using `send_realtime_input()` with various configurations (including manual VAD) failed to maintain continuous voice detection.

### Investigation
- Tried `send_realtime_input(audio=Blob(...))` - partial success
- Added MIME type with sample rate - no improvement
- Enabled manual VAD and sent `ActivityEnd` - broke first turn too

### Root Cause
The official example uses a different method:
```python
# What we were using (incorrect for continuous streaming)
await session.send_realtime_input(
    audio=Blob(data=chunk, mime_type="audio/pcm;rate=16000")
)

# What the official example uses (correct)
await session.send(
    input={"data": chunk, "mime_type": "audio/pcm"},
    end_of_turn=False
)
```

### Solution
Changed to `session.send()` with `end_of_turn=False`:
```python
await session.send(
    input={"data": chunk, "mime_type": "audio/pcm"},
    end_of_turn=False  # Critical: Keeps stream open for continuous input
)
```

### Lesson Learned
`send_realtime_input()` and `session.send()` have different semantics. For continuous microphone streaming, use `session.send()` with `end_of_turn=False`.

---

## Bug 3: Poor Audio Playback Quality (Choppy/Stuttering)

### Symptom
Audio output from Gemini was choppy and stuttering, with gaps between words.

### Investigation
- Initial implementation used PyAudio callbacks for output
- Callback tried to fill exact buffer size from variable-sized chunks
- Buffer underruns caused silence gaps

### Root Cause
```python
# Complex callback with buffer management issues
def callback(in_data, frame_count, time_info, status):
    bytes_needed = frame_count * 2
    data = b''
    try:
        while len(data) < bytes_needed:
            chunk = self.output_queue.get_nowait()  # ← Can throw Empty
            data += chunk
    except queue.Empty:
        data += b'\x00' * (bytes_needed - len(data))  # ← Silence gaps!
    return (data, pyaudio.paContinue)
```

The callback-based approach couldn't handle variable chunk sizes from Gemini gracefully.

### Solution
Switched to blocking write in a background thread (matches official example):
```python
def start_playback(self):
    self.output_stream = self.p.open(
        format=self.FORMAT, channels=1, rate=24000, output=True
    )
    self._playback_thread = threading.Thread(target=self._playback_loop, daemon=True)
    self._playback_thread.start()

def _playback_loop(self):
    while self._is_playing:
        data = self.output_queue.get(timeout=0.5)  # Blocking wait
        self.output_stream.write(data)  # Blocking write
```

### Lesson Learned
For audio playback with variable-sized chunks, blocking write is simpler and more reliable than callback-based buffering.

---

## Bug 4: Session Fails to Start / Complex Config Issues

### Symptom
Using `LiveConnectConfig` object with various options sometimes caused session initialization issues or unexpected behavior.

### Root Cause
The official example uses a simple dict config:
```python
# What we were using (overly complex)
config = LiveConnectConfig(
    response_modalities=["AUDIO"],
    tools=tools,
    speech_config=VoiceConfig(...),
    realtime_input_config={"automatic_activity_detection": {"disabled": True}}
)

# What works reliably (simple dict)
config = {
    "response_modalities": ["AUDIO"],
    "tools": tools,
    "system_instruction": "...",
    "speech_config": {"voice_config": {"prebuilt_voice_config": {"voice_name": "Puck"}}}
}
```

### Solution
Use simple dict config matching the official example:
```python
config = {
    "response_modalities": ["AUDIO"],
    "tools": tools,
    "system_instruction": "You are Echo, a helpful assistant...",
    "speech_config": {
        "voice_config": {"prebuilt_voice_config": {"voice_name": "Puck"}}
    },
    "output_audio_transcription": {}  # Enable transcription
}
```

### Lesson Learned
Stick to the official example's config format. Complex typed objects may have subtle serialization issues.

---

## Bug 5: Manual VAD Made Everything Worse

### Symptom
Attempting to implement manual Voice Activity Detection by disabling automatic VAD and sending `ActivityEnd` signals broke everything - even the first turn stopped working.

### Investigation
- Set `automatic_activity_detection.disabled = True`
- Implemented client-side silence detection
- Sent `ActivityEnd()` when user stopped speaking
- Result: Model never responded at all

### Root Cause
When disabling automatic VAD, you must send **both** `ActivityStart` and `ActivityEnd`:
```python
# Incomplete implementation (broken)
await session.send_realtime_input(activity_end=ActivityEnd())

# Complete implementation (required if VAD disabled)
await session.send_realtime_input(activity_start=ActivityStart())
# ... send audio ...
await session.send_realtime_input(activity_end=ActivityEnd())
```

### Solution
**Don't disable automatic VAD**. The server-side VAD works well for most use cases:
```python
# Just use default VAD (remove any realtime_input_config)
config = {
    "response_modalities": ["AUDIO"],
    # No realtime_input_config = automatic VAD enabled (default)
}
```

### Lesson Learned
Server-side automatic VAD is well-tuned. Only disable it if you have a specific need and are prepared to implement complete `ActivityStart`/`ActivityEnd` signaling.

---

## Bug 6: WebSocket Keepalive Timeout

### Symptom
Connection would fail with: `sent 1011 (internal error) keepalive ping timeout; no close frame received`

### Root Cause
This error occurred when:
1. Audio was being sent but VAD wasn't detecting speech
2. The server-side connection timed out waiting for valid speech activity
3. Combined with Bug #1 (missing while True), this caused hard failures

### Solution
Fixing Bug #1 (while True wrapper) and Bug #2 (correct send method) resolved this issue. The keepalive timeout was a symptom, not the root cause.

---

## Audio Configuration Reference

### Working Configuration

```python
# Audio constants (audio.py)
FORMAT = pyaudio.paInt16
CHANNELS = 1
INPUT_RATE = 16000   # Mic input: 16kHz (Gemini expects this)
OUTPUT_RATE = 24000  # Gemini output: 24kHz (always)
CHUNK = 512          # Small chunks for responsive detection

# Send format (live_client.py)
await session.send(
    input={"data": chunk, "mime_type": "audio/pcm"},
    end_of_turn=False
)
```

### Config Template

```python
config = {
    "response_modalities": ["AUDIO"],
    "tools": tools,  # From MCP
    "system_instruction": "Your system prompt here",
    "speech_config": {
        "voice_config": {
            "prebuilt_voice_config": {"voice_name": "Puck"}
        }
    },
    "output_audio_transcription": {}  # Enables transcription
}
```

---

## Debugging Tips

1. **Add heartbeat logs** to verify audio is being sent:
   ```python
   chunk_count += 1
   if time.time() - last_heartbeat > 10:
       logger.log(f"Audio stream active: {chunk_count} chunks")
   ```

2. **Check for turn_complete** - after this, `session.receive()` iterator ends

3. **Save traces to JSON** for post-mortem analysis:
   ```python
   with open("agent_trace.json", "w") as f:
       json.dump(trace_log, f, indent=2)
   ```

4. **Test with simple greeting first** - "Hello" should get a response within 2-3 seconds

---

## Files Modified

| File | Changes |
|------|---------|
| `src/agent/live_client.py` | Added while True wrapper, changed to session.send(), simplified config |
| `src/agent/audio.py` | Changed to blocking write playback, CHUNK=512 |

---

## References

- [Gemini Live API Guide](https://ai.google.dev/gemini-api/docs/live-guide)
- [Official Cookbook Example](https://github.com/google-gemini/cookbook/blob/main/quickstarts/Get_started_LiveAPI.py)
- [API Reference - VAD](https://ai.google.dev/api/live#automaticactivitydetection)

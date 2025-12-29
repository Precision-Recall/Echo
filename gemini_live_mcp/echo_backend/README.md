# Echo Backend - Gemini Live API Relay

FastAPI WebSocket server that relays real-time audio/text communication between the frontend and Google's Gemini Live API.

## Architecture

```
Frontend (Next.js) ←→ Backend (FastAPI) ←→ Gemini API
     WebSocket              WebSocket/REST
   
   /ws/live  → GeminiLiveClient    → Gemini Native Audio (Speech-to-Speech)
   /ws/chat  → GeminiChatClient    → Gemini 2.5 Flash (Text & Tools)
```

## Features

- **Real-time Speech-to-Speech**: Continuous bidirectional audio streaming via `/ws/live`
- **Text Chat with Tool Calling**: Streaming text responses and tool execution via `/ws/chat`
- **Google Classroom Integration**: Built-in tools to access Google Classroom data
- **Native Audio Support**: Uses Gemini 2.5 Flash Native Audio for voice
- **Dual Modes**: Separate voice and chat modes with independent connections
- **CORS Enabled**: Configured for localhost:3000 frontend

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Key

Create a `.env` file:

```bash
GEMINI_API_KEY=your_gemini_api_key_here
```

Get your API key from: https://aistudio.google.com/apikey

### 3. Run the Server

```bash
python main.py
```

Or with uvicorn:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The server will start at: http://localhost:8000

## API Endpoints

### WebSocket: `/ws/live`

Voice mode endpoint for real-time audio streaming with Gemini Native Audio.

**Message Protocol:**

**Frontend → Backend:**
```json
{
  "type": "audio",
  "data": "base64_encoded_pcm_audio"
}
```

**Backend → Frontend:**
```json
{
  "type": "audio",
  "data": "base64_encoded_pcm_audio",
  "mime_type": "audio/pcm"
}
```

```json
{
  "type": "turn_complete"
}
```

### WebSocket: `/ws/chat`

Text chat mode endpoint with streaming responses and tool calling.

**Message Protocol:**

**Frontend → Backend:**
```json
{
  "type": "text",
  "text": "List my courses"
}
```

**Backend → Frontend:**
```json
{
  "type": "text_chunk",
  "text": "Here are your courses..."
}
```

```json
{
  "type": "tool_start",
  "tool": "list_courses",
  "args": {}
}
```

```json
{
  "type": "tool_end",
  "tool": "list_courses",
  "result": { "courses": [...] }
}
```

### HTTP: `/`

Health check endpoint.

**Response:**
```json
{
  "status": "running",
  "service": "Echo Backend - Gemini Live API Relay"
}
```

## Configuration

### Voice Mode (`/ws/live`)
- **Model**: `gemini-2.5-flash-native-audio-preview-12-2025`
- **Audio Format**: PCM 16kHz mono, 16-bit
- **System Prompt**: "You are Echo, a helpful AI assistant with access to Google Classroom."

### Chat Mode (`/ws/chat`)
- **Model**: `gemini-2.5-flash`
- **System Prompt**: "You are Echo, a helpful AI assistant. You have access to Google Classroom tools."
- **Tools**: Google Classroom integration (list courses, assignments, students, etc.)

### Server
- **Port**: 8000
- **CORS**: localhost:3000

## Google Classroom Setup

To use Google Classroom tools, place `tokens.json` and optionally `credentials.json` in the parent directory `../../classroom_mcp-main/`.

The `tokens.json` file should contain OAuth2 credentials from the Google Classroom API.

## Development

### Project Structure

```
echo_backend/
├── main.py                 # FastAPI app with dual WebSocket endpoints
├── gemini_client.py        # Gemini Live API client (voice)
├── gemini_chat_client.py   # Gemini Chat client (text)
├── classroom_tools.py      # Google Classroom tool implementations
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (create this)
├── .gitignore             # Git ignore rules
└── README.md              # This file
```

### Testing

Test the WebSocket endpoint:

```bash
# Check health
curl http://localhost:8000

# Test WebSocket (requires wscat or similar)
wscat -c ws://localhost:8000/ws
```

## Troubleshooting

**Connection refused:**
- Ensure the server is running on port 8000
- Check firewall settings

**GEMINI_API_KEY not configured:**
- Create `.env` file with your API key
- Verify the key is valid

**Audio not working:**
- Ensure you're using the correct model: `gemini-2.5-flash-native-audio-preview`
- Check audio format: PCM 16kHz mono

## License

MIT


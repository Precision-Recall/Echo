# Echo Frontend - Gemini Live Chat Interface

Next.js frontend for real-time voice and text conversations with Google's Gemini Live API.

## Features

- **Real-time Voice Chat**: Continuous speech-to-speech communication with Gemini
- **Text Chat**: Traditional text-based messaging
- **Audio Streaming**: Live audio capture and playback
- **Modern UI**: Clean, minimal interface with Tailwind CSS
- **Connection Management**: Auto-reconnect and connection status indicators
- **Dark Mode**: Automatic dark mode support

## Architecture

```
Frontend Components:
├── page.tsx                    # Main chat interface
└── hooks/
    ├── useGeminiWebSocket.ts  # WebSocket connection management
    ├── useAudioCapture.ts     # Microphone audio streaming
    └── useAudioPlayback.ts    # Audio response playback
```

## Setup

### 1. Install Dependencies

```bash
npm install
```

### 2. Configure Backend URL

The frontend connects to the backend at `ws://localhost:8000/ws` by default. If your backend is running on a different port, update the `WEBSOCKET_URL` in `app/hooks/useGeminiWebSocket.ts`.

### 3. Run Development Server

```bash
npm run dev
```

Open http://localhost:3000 in your browser.

## Usage

### Voice Chat

1. Click the microphone button to start recording
2. Speak naturally - audio streams continuously to Gemini
3. Click the microphone button again to stop recording
4. Gemini's voice response will play automatically

### Text Chat

1. Type your message in the input field
2. Press Enter or click the send button
3. Gemini's text response will appear in the chat

## Technical Details

### Audio Configuration

- **Input**: PCM 16kHz mono, 16-bit
- **Output**: PCM 24kHz mono (from Gemini)
- **Chunk Size**: 4096 samples
- **Streaming**: Real-time continuous audio streaming

### WebSocket Protocol

**Messages to Backend:**
```typescript
{
  type: 'audio',
  data: 'base64_encoded_pcm',
  turn_complete: boolean
}

{
  type: 'text',
  text: 'message content',
  turn_complete: boolean
}
```

**Messages from Backend:**
```typescript
{
  type: 'audio',
  data: 'base64_encoded_pcm',
  mime_type: 'audio/pcm'
}

{
  type: 'text',
  text: 'response content'
}

{
  type: 'turn_complete'
}
```

### React Hooks

#### useGeminiWebSocket

Manages WebSocket connection to the backend.

```typescript
const {
  connectionState,  // 'disconnected' | 'connecting' | 'connected' | 'error'
  sendAudio,        // (audioData: string, turnComplete?: boolean) => void
  sendText,         // (text: string, turnComplete?: boolean) => void
  connect,          // () => void
  disconnect        // () => void
} = useGeminiWebSocket(onMessage);
```

#### useAudioCapture

Captures microphone audio and streams it continuously.

```typescript
const {
  isRecording,      // boolean
  startRecording,   // () => Promise<void>
  stopRecording,    // () => void
  error            // string | null
} = useAudioCapture(onAudioData);
```

#### useAudioPlayback

Plays audio responses from Gemini.

```typescript
const {
  isPlaying,       // boolean
  playAudio,       // (base64Audio: string) => Promise<void>
  stopAudio,       // () => void
  error           // string | null
} = useAudioPlayback();
```

## Browser Compatibility

- Chrome/Edge: Full support
- Firefox: Full support
- Safari: Full support (requires HTTPS or localhost)

**Note**: Microphone access requires HTTPS in production or localhost for development.

## Troubleshooting

**Microphone not working:**
- Check browser permissions
- Ensure you're on HTTPS or localhost
- Check browser console for errors

**No audio playback:**
- Check browser audio settings
- Ensure audio is not muted
- Check if backend is sending audio data

**Connection issues:**
- Ensure backend is running on port 8000
- Check browser console for WebSocket errors
- Verify CORS settings in backend

## Development

### Build for Production

```bash
npm run build
npm start
```

### Linting

```bash
npm run lint
```

## License

MIT

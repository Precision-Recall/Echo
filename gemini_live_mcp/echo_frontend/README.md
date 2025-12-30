# Echo Frontend - Gemini Live Chat Interface

Next.js frontend for real-time voice and text conversations with Google's Gemini Live API.

## Features

- **Real-time Voice Chat**: Continuous speech-to-speech communication with Gemini
- **Text Chat**: Traditional text-based messaging with Google Classroom tools with short-term memory
- **Short-term Memory**: Conversation context preserved across messages within a thread
- **Assignment Creation Form**: Dedicated UI for creating Google Classroom assignments with detailed input fields
- **Audio Streaming**: Live audio capture and playback
- **Modern UI**: Clean, minimal interface with Tailwind CSS and smooth auto-scrolling
- **Robust Connection Management**: Auto-reconnect with exponential backoff, no duplicate connections
- **Dual WebSocket Support**: Separate connections for voice (`/ws/live`) and chat (`/ws/chat`)
- **Markdown Rendering**: Full GitHub Flavored Markdown support with proper typography
- **Unified Chain of Thought**: Single expandable view combining AI reasoning steps and tool calls
- **Enhanced Tool Visualization**: See Gemini's tool usage with inputs and results in a clean UI

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
3. Gemini's text response will appear in the chat with smooth auto-scrolling
4. View the chain of thought steps to see AI reasoning (when thinking model is enabled)
5. Expand tool execution steps to see function calls and results

## Technical Details

### Audio Configuration

- **Input**: PCM 16kHz mono, 16-bit
- **Output**: PCM 24kHz mono (from Gemini)
- **Chunk Size**: 4096 samples
- **Streaming**: Real-time continuous audio streaming

### WebSocket Protocol

The frontend maintains **two separate WebSocket connections**:

#### `/ws/live` - Voice Mode (Speech-to-Speech)

**Messages to Backend:**
```typescript
{
  type: 'audio',
  data: 'base64_encoded_pcm',
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
  type: 'turn_complete'
}

{
  type: 'connected',
  data: 'Connected to Gemini Live API'
}
```

#### `/ws/chat` - Text Mode (Text + Tools)

**Messages to Backend:**
```typescript
{
  type: 'text',
  text: 'message content'
}

{
  type: 'ping'
}
```

**Messages from Backend:**
```typescript
{
  type: 'text_chunk',
  text: 'streaming response chunk'
}

{
  type: 'tool_start',
  tool: 'function_name',
  args: { ... }
}

{
  type: 'tool_end',
  tool: 'function_name',
  result: { ... }
}

{
  type: 'connected',
  data: 'Connected to Gemini Chat'
}

{
  type: 'error',
  text: 'error message'
}

{
  type: 'pong'
}

{
  type: 'thought',
  thought: 'AI reasoning step'
}
```

### React Hooks

#### useGeminiWebSocket

Manages WebSocket connection to the backend with automatic reconnection and duplicate connection prevention.

**Key Features:**
- Uses React refs to prevent infinite re-render loops
- Prevents duplicate connections with connection guards
- Automatic reconnection with 3-second delay
- Stable callback pattern for message handling

```typescript
const {
  connectionState,  // 'disconnected' | 'connecting' | 'connected' | 'error'
  sendAudio,        // (audioData: string, turnComplete?: boolean) => void
  sendText,         // (text: string) => void
  lastMessage,      // WebSocketMessage | null
  connect,          // () => void
  disconnect        // () => void
} = useGeminiWebSocket(endpoint, onMessage);

// endpoint: '/ws/live' or '/ws/chat'
// onMessage: Optional callback for handling messages
```

**Implementation Notes:**
- The `onMessage` callback is stored in a ref to prevent dependency issues
- Connection attempts are guarded to prevent race conditions
- Automatically cleans up on component unmount
- Works correctly with React Strict Mode (no duplicate connections)

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

**"Insufficient resources" WebSocket error:**
- ✅ **Fixed** - This was caused by an infinite re-render loop creating hundreds of connections
- The fix uses React refs to stabilize callbacks and prevent duplicate connections
- See [WEBSOCKET_FIX.md](./WEBSOCKET_FIX.md) for technical details
- If you still see this error:
  1. Clear browser cache and reload
  2. Check browser console for other errors
  3. Ensure you're using the latest code with the ref-based callback pattern

**Chat not connecting but voice works:**
- This typically indicates the chat endpoint auto-connect is being called repeatedly
- Check DevTools console - you should only see ONE `✅ Connected to backend /ws/chat` message
- If you see multiple connection attempts, the ref pattern may not be applied correctly
- Restart the dev server: `npm run dev`

## Recent Improvements

### UI Enhancements (Dec 2025)
- ✅ **Markdown rendering** - Full GitHub Flavored Markdown support with tables, lists, code blocks, and more
- ✅ **Smart tool visualization** - Tool name shown once outside bubble as small expandable dropdown
- ✅ **Processing states** - Shows "Processing..." with typing dots after tool execution until response arrives
- ✅ **Enhanced tool details** - Input/output displayed in clean, expandable format with color coding
- ✅ **Minimal loading state** - Shows "Processing your request..." with typing indicator, no border or box
- ✅ **Removed extra border** around the input box for a cleaner look
- ✅ **Auto-scrolling** now triggers on message updates AND loading state changes
- ✅ **Smooth scrolling** behavior for better UX
- ✅ **Modern loading indicator** using prompt-kit Loader component with "typing" variant
- ✅ **User-friendly error messages** - shows concise, helpful errors instead of technical details

### Tool Call Flow
1. Tool name appears above message bubble in small font (e.g., "🔧 Tool used: list_coursework")
2. Click to expand and see input parameters and results
3. After tool execution, shows "Processing..." with animated typing dots
4. When response arrives, the final answer appears in the message bubble

### Assignment Creation
When you type phrases like "create assignment for course 823993365562", the system detects the intent and shows an inline form as an agent message:

**How It Works:**
1. Detects creation intent from your message
2. Extracts course ID if mentioned (e.g., 12-digit numbers)
3. Adds an agent message with "I can help you create an assignment..."
4. Shows inline form directly in the chat

**Form Fields:**
- **Course ID** (required) - Auto-populated if mentioned in the message
- **Assignment Title** (required)
- **Description** - Optional detailed description
- **Due Date** - Optional deadline date
- **Due Time** - Optional deadline time
- **Max Points** - Point value for the assignment (default: 100)
- **Work Type** - Assignment, Short Answer Question, or Multiple Choice Question

**Design:**
- Compact layout optimized for chat interface
- Black buttons (bg-gray-900) for consistency
- Smaller text sizes and tighter spacing
- Cancel option removes the form message
- Submit creates the assignment and removes the form

The form validates input and sends a structured request to create the assignment via Google Classroom API.

### Short-term Memory
Each conversation is assigned a unique thread ID that persists context across messages:
- Conversations remember previous interactions within the same session
- Memory automatically trims old messages to stay within context window limits
- Estimated token usage: ~4 characters = 1 token
- Maximum messages: 20 per thread (first message always kept)
- Maximum estimated tokens: 4000 per thread

**Memory Management:**
- Automatic trimming when limits are reached
- Keeps first message (often contains important context) and recent messages
- Thread ID is automatically generated per session

### Loader Animations
The app uses the prompt-kit Loader component with custom keyframe animations defined in `globals.css`:
- **typing** - Three dots that bounce up and down in sequence (used for processing states)
- **bounce-dots** - Dots that scale in and out
- **wave** - Bars that create a wave effect
- **pulse-dot** - Pulsing dot animation
- **thin-pulse** - Subtle pulsing effect

All animations are smooth and provide clear visual feedback during loading states.

### Markdown Support
The chat interface now supports full Markdown formatting including:
- **Headers** (H1-H6)
- **Bold**, *italic*, and ~~strikethrough~~ text
- Ordered and unordered lists
- Code blocks with syntax highlighting
- Inline `code`
- Tables
- Links and more

Example coursework list is properly formatted with bullets, dates, and IDs.

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

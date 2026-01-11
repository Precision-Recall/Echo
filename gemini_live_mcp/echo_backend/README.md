# Echo Backend - Gemini Live API Relay

FastAPI WebSocket server that relays real-time audio/text communication between the frontend and Google's Gemini API.

**Now powered by LangChain for robust tool calling!**

## Architecture

```
Frontend (Next.js) ←→ Backend (FastAPI) ←→ Gemini API
     WebSocket              WebSocket/REST
   
   /ws/live  → GeminiLiveClient    → Gemini Native Audio (Speech-to-Speech)
   /ws/chat  → GeminiChatClient    → Gemini 2.5 Flash (Text & Tools)
```

## Features

- **Dual API Support**: Switch between free API key (Google AI Studio) and paid Vertex AI
- **Real-time Speech-to-Speech**: Continuous bidirectional audio streaming via `/ws/live`
- **Text Chat with Tool Calling**: Streaming text responses and tool execution via `/ws/chat`
- **Short-term Memory**: Thread-based conversation memory with automatic trimming and context management
- **Thinking Model with Chain of Thought**: AI shows step-by-step reasoning process before answers
- **Google Classroom Integration**: Built-in tools to access and create Google Classroom assignments, coursework, and announcements with form-based selection
- **Google Docs Creator**: Generate professionally formatted Google Docs with native styles (headings, bold, italic, lists)
- **Google Sheets Creator**: Create structured Google Sheets with headers and data
- **AI-Powered Google Forms Studio**: Dedicated page for creating and editing Google Forms with AI assistance
  - Natural language form creation (e.g., "Create a quiz on machine learning with 15 questions")
  - Split-view interface: Live form preview (left) + AI chat for editing (right)
  - AI-powered form editing with natural language (e.g., "Add a question about neural networks")
  - Support for multiple question types: Multiple Choice, Text, Paragraph, Linear Scale
- **Assignment & Course Creation**: Structured forms for creating classroom content
- **Student List Management**: Create and manage student lists by department, year, and section
- **Automated Course Invitations**: Send beautiful HTML email invitations to student lists when creating courses
- **AI-Powered Description Generator**: Enhance assignment descriptions with AI (50-100 words, preserves meaning)
- **File Upload for Assignments**: Upload files to Google Drive and attach them to assignments
- **Native Audio Support**: Uses Gemini 2.5 Flash Native Audio for voice
- **Dual Modes**: Separate voice and chat modes with independent connections
- **Flexible CORS**: Environment-configurable for any frontend domain
- **Robust WebSocket Handling**: Proper exception handling and graceful disconnection management
- **Concurrent WebSocket Support**: Both endpoints can run simultaneously without interference
- **User-Friendly Error Messages**: Converts technical errors into concise, actionable messages for end users
- **Memory Management API**: REST endpoints for clearing and inspecting conversation memory
- **Firebase Token Storage**: Secure per-user OAuth token management in Firestore
- **Cost Optimization**: Choose between free tier and paid API based on your needs

## Setup

### 1. Install Dependencies

All dependencies are pinned to specific versions for security and reproducibility:

```bash
pip install -r requirements.txt
```

**Security Note**: All dependencies use exact version pinning (`==`) to prevent supply-chain attacks and ensure consistent behavior across environments.

### 2. Configure Environment

The backend supports **two API modes**: Free (Google AI Studio) and Paid (Vertex AI).

#### Option A: Free API Key (Default)

Edit `.env` and set:

```bash
API_KEY_TYPE=free
GEMINI_API_KEY=your_gemini_api_key_here
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

Get your API key from: https://aistudio.google.com/apikey

**Rate Limits:** 15 RPM, 1M TPM, 1,500 requests/day  
**Cost:** $0 (Free)


**Rate Limits:** Much higher (varies by quota)  
**Cost:** ~$5-10/month for 500 requests/day

📖 **See [API_CONFIGURATION.md](./API_CONFIGURATION.md) for detailed setup instructions**

**Available Environment Variables:**
- `API_KEY_TYPE` (optional): "free" or "paid" (default: "free")
- `GEMINI_API_KEY` (required for free): Your Gemini API key from AI Studio
- `GOOGLE_APPLICATION_CREDENTIALS_JSON` (required for paid): Service account JSON as single-line string
- `GEMINI_LOCATION` (optional for paid): Vertex AI region (default: "us-central1")
- `ALLOWED_ORIGINS` (optional): Comma-separated CORS origins
- `GOOGLE_CLIENT_ID` (optional): For Google Classroom OAuth
- `GOOGLE_CLIENT_SECRET` (optional): For Google Classroom OAuth
- `CLASSROOM_DATA_DIR` (optional): Directory containing tokens.json
- `GMAIL_USER` (required for email invitations): Gmail address for sending course invitations
- `GMAIL_APP_PASSWORD` (required for email invitations): Gmail App Password (not regular password)
- `TOKEN_SERVICE_URL` (optional): Firebase backend URL (default: "http://localhost:8001")

### 3. Configure Gmail for Course Invitations (Optional)

To enable automated email invitations when creating courses:

1. **Enable 2-Factor Authentication** on your Gmail account
2. **Generate an App Password**:
   - Go to https://myaccount.google.com/apppasswords
   - Select "Mail" and "Other (Custom name)"
   - Name it "Echo Backend"
   - Copy the 16-character password
3. **Add to `.env`**:
   ```bash
   GMAIL_USER=your-email@gmail.com
   GMAIL_APP_PASSWORD=your-16-char-app-password
   ```

**Note:** Never use your regular Gmail password. Always use an App Password.

### 4. Run the Server

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

Health check endpoint with configuration status.

**Response:**
```json
{
  "status": "running",
  "service": "Echo Backend - Gemini Live API Relay",
  "api_key_configured": true,
  "allowed_origins": ["http://localhost:3000"]
}
```

## Short-term Memory System

The backend implements thread-based conversation memory that automatically manages context across messages.

### Memory Management

**Features:**
- Thread-based storage: Each conversation has a unique `thread_id`
- Automatic trimming: Keeps memory within token limits (max 4000 tokens estimated)
- Message retention: Stores up to 20 messages per thread
- First message preservation: Always keeps the first message for context
- Automatic cleanup: Old messages removed when limits exceeded

**Memory Manager:**
```python
from memory_manager import memory_manager

# Add a message
memory_manager.add_message(thread_id, role="user", content="Hello")

# Get conversation history
history = memory_manager.get_history(thread_id)

# Get context string for AI
context = memory_manager.get_context_string(thread_id)

# Clear thread memory
memory_manager.clear_thread(thread_id)
```

### REST API Endpoints

#### `POST /api/memory/clear/{thread_id}`
Clear all conversation memory for a specific thread.

**Response:**
```json
{
  "status": "ok",
  "thread_id": "thread_123",
  "message": "Memory cleared"
}
```

#### `GET /api/memory/stats/{thread_id}`
Get memory statistics for a thread.

**Response:**
```json
{
  "thread_id": "thread_123",
  "message_count": 12,
  "estimated_tokens": 2847,
  "total_characters": 11388
}
```

#### `GET /api/memory/history/{thread_id}?last_n=5`
Get conversation history for a thread.

**Parameters:**
- `last_n` (optional): Return only the last N messages

**Response:**
```json
{
  "thread_id": "thread_123",
  "messages": [
    {
      "role": "user",
      "content": "List my courses",
      "timestamp": 1703001234.567
    },
    {
      "role": "model",
      "content": "Here are your courses...",
      "timestamp": 1703001235.123
    }
  ]
}
```

### Integration

The memory system is automatically integrated into the `/ws/chat` endpoint:

1. Each message includes a `thread_id` (default: "default")
2. User messages are stored in memory before processing
3. Conversation context is added to AI prompts
4. AI responses are stored in memory after completion
5. Memory is automatically trimmed when limits are reached

**Example WebSocket Message with Thread ID:**
```json
{
  "type": "text",
  "text": "What courses do I have?",
  "thread_id": "thread_user123_session456"
}
```

### REST: `POST /api/generate-description`

AI-powered description generator for assignments. Takes user input and generates a concise, professional 50-100 word description.

**Request:**
```json
{
  "query": "create a lab about python loops"
}
```

**Response:**
```json
{
  "success": true,
  "description": "Complete a hands-on lab exploring Python loops. You will implement for loops, while loops, and nested iterations to solve practical programming challenges. Focus on loop control, iteration patterns, and efficient algorithm design. Submit your Python code with clear comments explaining your logic. This assignment reinforces fundamental programming concepts essential for data processing and automation tasks.",
  "word_count": 58
}
```

**Features:**
- Preserves core meaning and intent
- Professional educational tone
- Strictly 50-100 words
- Can enhance existing text or generate from scratch
- Uses same Gemini model as chat (respects API_KEY_TYPE setting)

## Code Quality & Security

This backend implements several best practices:

**Error Handling:**
- All tool functions return consistent data structures
- Success responses wrapped in descriptive keys (e.g., `{"course": ...}`)
- Errors always use `{"error": "message"}` format
- Uniform error handling across all Google Classroom tools

**Dependency Management:**
- All dependencies pinned to exact versions (`==`)
- Prevents supply-chain attacks from malicious package updates
- Ensures reproducible builds across all environments
- Explicit, reviewable upgrades instead of automatic

**Code Quality:**
- No unused imports or dead code
- Proper type hints where applicable
- Comprehensive error logging with tracebacks
- Follows FastAPI and asyncio best practices

See [CODE_QUALITY_IMPROVEMENTS.md](./CODE_QUALITY_IMPROVEMENTS.md) for detailed information.

## Configuration

### Voice Mode (`/ws/live`)
- **Model**: `gemini-2.5-flash-native-audio-preview-12-2025`
- **Audio Format**: PCM 16kHz mono, 16-bit
- **System Prompt**: "You are Echo, a helpful AI assistant with access to Google Classroom."

### Chat Mode (`/ws/chat`)
- **Model**: `gemini-2.5-flash-lite`
- **System Prompt**: "You are Echo, a helpful AI assistant. You have access to Google Classroom tools."
- **Tools**: Google Classroom integration (list courses, assignments, students, etc.)

### Server
- **Port**: 8000 (default)
- **CORS**: Configurable via `ALLOWED_ORIGINS` environment variable

## AI-Powered Tools

Echo includes several intelligent tools that the AI can use to help users:

### 📚 Google Classroom Tools
- `list_courses` - View all classroom courses
- `get_course` - Get details of a specific course
- `list_coursework` - View assignments in a course
- `get_coursework` - Get assignment details
- `list_announcements` - View course announcements
- `list_students` - View enrolled students
- `list_submissions` - View student submissions
- `create_coursework` - Create new assignments
- `create_course` - Create new courses
- `show_assignment_form` / `show_course_form` - Display creation forms in UI

### 📄 Google Docs Creator
**Tool**: `create_google_doc(title, content)`

Creates professionally formatted Google Docs with native formatting:
- **TITLE style** - Document title at top
- **HEADING_1/2/3** - Proper heading hierarchy with appropriate font sizes
- **Bold/Italic** - Inline text emphasis
- **Bulleted Lists** - Native bullet formatting
- **Numbered Lists** - Automatic numbering
- **Paragraph Spacing** - Proper spacing between sections

**Example Usage:**
```
User: "Create a 1-page document about Machine Learning"
AI: Generates comprehensive content with headings, lists, and formatting
Tool: Creates Google Doc with native styles
Result: Returns shareable Google Docs link
```

**Formatting Syntax:**
The AI uses these markers (parsed into native Google Docs formatting):
- `# Heading 1` → HEADING_1 style (20pt, bold)
- `## Heading 2` → HEADING_2 style (16pt, bold)
- `### Heading 3` → HEADING_3 style (14pt, bold)
- `**bold text**` → Bold formatting
- `*italic text*` → Italic formatting
- `- bullet` → Bulleted list
- `1. item` → Numbered list

### 📊 Google Sheets Creator
**Tool**: `create_google_sheet(title, headers, data)`

Creates Google Spreadsheets with structured data:
- Optional column headers
- Optional data rows
- Professional formatting
- Ready to edit and share
- **Smart Row Count**: AI respects user-specified row counts (e.g., "create 50 rows")

**Example Usage:**
```
User: "Create a spreadsheet with 30 rows to track student grades"
AI: Determines appropriate structure (Name, Email, Assignment 1, Assignment 2, Final)
Tool: Creates Google Sheet with headers and EXACTLY 30 rows of sample data
Result: Returns shareable Google Sheets link
```

### 📋 Google Forms Creator
**Tool**: `create_google_form(title, description, questions)`

Creates intelligent Google Forms with multiple question types:
- **8 Question Types**: TEXT, PARAGRAPH_TEXT, MULTIPLE_CHOICE, CHECKBOXES, DROPDOWN, LINEAR_SCALE, DATE, TIME
- **Smart Generation**: AI generates appropriate questions based on form purpose
- **Flexible Input**: Provide specific questions or describe the purpose
- **Auto-Configuration**: AI chooses best question types and options

**Example Usage:**
```
User: "Create a customer satisfaction survey"
AI: Generates appropriate questions with ratings, multiple choice, and feedback
Tool: Creates Google Form with:
  - "What is your name?" (TEXT, required)
  - "How satisfied are you?" (MULTIPLE_CHOICE: Very Satisfied to Very Dissatisfied)
  - "Rate our service 1-10" (LINEAR_SCALE with labels)
  - "Additional comments" (PARAGRAPH_TEXT)
Result: Returns public form link and edit link
```

**Question Types:**
- **TEXT** - Short answer
- **PARAGRAPH_TEXT** - Long answer
- **MULTIPLE_CHOICE** - Single selection
- **CHECKBOXES** - Multiple selections
- **DROPDOWN** - Compact selection
- **LINEAR_SCALE** - Rating (1-5, 1-10, etc.)
- **DATE** / **TIME** - Date/time pickers

**Common Use Cases:**
- Customer feedback surveys
- Event registration forms
- Quiz and assessments
- Course evaluations
- Opinion surveys

### 🔐 Authentication
All tools use OAuth tokens stored in Firebase Firestore:
- Per-user authentication
- Secure token storage
- Automatic token refresh
- No credentials exposed to frontend

### 📚 Documentation
- **Docs/Sheets**: [GOOGLE_DOCS_SHEETS_TOOLS.md](./GOOGLE_DOCS_SHEETS_TOOLS.md)
- **Google Forms**: [GOOGLE_FORMS_FEATURE.md](./GOOGLE_FORMS_FEATURE.md)
- **Sheets Row Count Fix**: [SHEETS_ROW_COUNT_FIX.md](./SHEETS_ROW_COUNT_FIX.md)

## Google Classroom Setup (Optional)

The Google Classroom tools are optional and only required if you want to access Classroom data.

### Option 1: Quick Setup (Same Directory)
Place `tokens.json` and `credentials.json` in the `echo_backend/` directory.

### Option 2: Custom Directory
Set the environment variable:
```bash
CLASSROOM_DATA_DIR=/path/to/your/oauth/files
```

### Getting OAuth Credentials
1. Create a Google Cloud project at https://console.cloud.google.com
2. Enable the Google Classroom API
3. Create OAuth 2.0 credentials (Desktop app)
4. Download as `credentials.json`
5. Run OAuth flow to generate `tokens.json`

**⚠️ Security Warning**: Never commit `tokens.json` or `credentials.json` to version control!

For detailed setup instructions, see [SETUP.md](./SETUP.md).

## WebSocket Implementation

### Connection Management

The server implements robust WebSocket handling following FastAPI best practices:

**Exception Handling:**
- All WebSocket connections properly catch `WebSocketDisconnect` exceptions
- Background tasks handle cancellation gracefully with `asyncio.CancelledError`
- Task exceptions are properly retrieved and logged to prevent "Task exception was never retrieved" errors

**Live Audio Endpoint (`/ws/live`):**
- Uses two concurrent background tasks: `relay_frontend_to_live` and `relay_live_to_frontend`
- Tasks are properly cancelled when one completes or an error occurs
- Completed tasks are checked for exceptions to ensure proper error reporting

**Chat Text Endpoint (`/ws/chat`):**
- Single-threaded message processing for turn-based chat
- Proper error handling during streaming responses
- JSON validation with graceful error messages

**Concurrent WebSocket Support:**
Both `/ws/live` and `/ws/chat` can be used simultaneously by different clients without interference. Each connection maintains its own:
- Gemini API session
- Message queue
- Error handling context

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

**Server won't start / "API Key missing" error:**
- Create `.env` file from `.env.example`
- Set `GEMINI_API_KEY` in `.env`
- Verify the key is valid at https://aistudio.google.com/apikey

**CORS errors in browser:**
- Add your frontend URL to `ALLOWED_ORIGINS` in `.env`
- Example: `ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com`
- Restart the server after changing `.env`

**Chat endpoint disconnects immediately:**
- Check server logs for initialization errors
- Verify Gemini API key is valid
- Ensure all dependencies are installed: `pip install -r requirements.txt`

**WebSocket disconnection errors or "Task exception was never retrieved":**
- This has been fixed with proper exception handling in background tasks
- Ensure you're running the latest version of the code
- If issues persist, restart the server and check for Python version compatibility (Python 3.9+ required)

**"async_generator can't be used in 'await' expression" error:**
- ✅ **Fixed** - This was caused by incorrectly awaiting an async generator in chat client
- The `send_message_stream()` method returns an async generator, not a coroutine
- Fixed by removing the `await` keyword (line 33 in `gemini_chat_client.py`)
- If you see this error, ensure you're using the latest code

**"GenerateContentResponse.text only supports text parts" error:**
- ✅ **Fixed** - This occurred when trying to access `chunk.text` on chunks with function calls
- The fix: Check individual `part.text` instead of `chunk.text`
- Now properly handles chunks containing both text and function_call parts
- Tool calling and text streaming now work together correctly

**"tokens.json not found" error:**
- This only affects Google Classroom features
- Either set up OAuth credentials (see SETUP.md) or ignore if not using Classroom tools
- The error won't prevent the server from running

**Live audio endpoint works but chat doesn't:**
- Check that `google-genai` package is version 0.3.0+
- Try reinstalling: `pip install --upgrade google-genai`

**Both endpoints fail in production:**
- Check environment variables are set correctly
- Verify CORS origins match your frontend domain
- Check server logs: `journalctl -u echo-backend -f`

## License

MIT


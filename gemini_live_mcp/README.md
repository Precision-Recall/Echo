# Echo - AI-Powered Google Classroom Assistant

Echo is an intelligent assistant that helps you manage Google Classroom using natural language. It features voice interaction, text chat, and AI-powered tool calling to perform classroom operations.

## 🚀 Quick Start

**⚠️ IMPORTANT: Start the backend BEFORE the frontend to avoid connection errors.**

See **[STARTUP_GUIDE.md](./STARTUP_GUIDE.md)** for detailed startup instructions.

### Quick Commands

```bash
# Terminal 1: Start Backend
cd echo_backend
python main.py

# Terminal 2: Start Frontend (after backend is running)
cd echo_frontend
npm run dev
```

Then open: http://localhost:3000

## ✨ Features

### 🎯 Core Features
- **Dual Mode Interface**: Switch between voice and text chat
- **Real-time Voice Interaction**: Native speech-to-speech with Gemini
- **Thinking Model**: See AI's chain of thought before answers
- **Short-term Memory**: Conversation context maintained per thread
- **Firebase Authentication**: Secure user login with email or Google

### 📚 Google Classroom Integration
- **List Courses**: View all your courses
- **List Coursework**: See assignments for any course
- **Create Assignments**: AI-guided assignment creation with forms
- **Create Courses**: Set up new courses with structured forms
- **Dynamic Dropdowns**: Automatically populated course selection

### 🛠️ Technical Features
- **Tool Calling**: AI can invoke tools to perform actions
- **WebSocket Streaming**: Real-time bidirectional communication
- **User-Friendly Errors**: Technical errors converted to simple messages
- **Markdown Rendering**: Rich text display for responses
- **Protected Routes**: Authentication-based access control

## 📁 Project Structure

```
gemini_live_mcp/
├── echo_backend/          # FastAPI WebSocket server
│   ├── main.py           # Entry point & WebSocket endpoints
│   ├── gemini_client.py  # Gemini Live API client
│   ├── gemini_chat_client.py # Gemini Chat client
│   ├── classroom_tools.py # Google Classroom integration
│   ├── memory_manager.py # Conversation memory
│   └── requirements.txt  # Python dependencies
│
├── echo_frontend/        # Next.js React application
│   ├── app/
│   │   ├── page.tsx              # Root redirect page
│   │   ├── ChatInterface.tsx    # Main chat interface
│   │   ├── landing/page.tsx     # Landing page
│   │   ├── login/page.tsx       # Login page
│   │   ├── chat/page.tsx        # Protected chat page
│   │   ├── contexts/            # React contexts
│   │   ├── components/          # React components
│   │   └── hooks/               # Custom hooks
│   └── lib/firebase.ts          # Firebase config
│
├── STARTUP_GUIDE.md      # Detailed startup instructions
├── AUTH_SETUP.md         # Firebase authentication setup
└── README.md             # This file
```

## 📚 Documentation

- **[STARTUP_GUIDE.md](./STARTUP_GUIDE.md)** - Complete startup instructions
- **[AUTH_SETUP.md](./AUTH_SETUP.md)** - Firebase authentication setup
- **[echo_backend/README.md](./echo_backend/README.md)** - Backend API documentation
- **[AUTHENTICATION_IMPLEMENTATION.md](./AUTHENTICATION_IMPLEMENTATION.md)** - Auth implementation details

## 🔧 Setup

### Prerequisites

- Python 3.9+
- Node.js 18+
- Google Gemini API key
- Firebase project (for authentication)
- Google Classroom API credentials (optional)

### 1. Backend Setup

```bash
cd echo_backend

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add:
# - GEMINI_API_KEY
# - GOOGLE_CLIENT_ID (optional)
# - GOOGLE_CLIENT_SECRET (optional)
```

### 2. Frontend Setup

```bash
cd echo_frontend

# Install dependencies
npm install

# Configure Firebase (see AUTH_SETUP.md)
# Edit lib/firebase.ts with your Firebase config
```

### 3. Google Classroom (Optional)

To use Classroom features:

1. Set up Google Cloud Project
2. Enable Classroom API
3. Create OAuth credentials
4. Download `credentials.json`
5. Place in `echo_backend/` directory
6. Run authentication flow (see backend README)

## 🎮 Usage

### Voice Mode

1. Click microphone icon
2. Speak naturally
3. AI responds with voice
4. Click again to stop

### Text Chat Mode

1. Click text icon
2. Type your message
3. AI responds with text and tools

### Example Commands

**List Courses:**
```
Show me all my courses
```

**Create Assignment:**
```
Create an assignment for course ID 12345
```
→ Opens structured form with course dropdown

**Create Course:**
```
Create a new course
```
→ Opens course creation form

**General Questions:**
```
What is machine learning?
Explain quantum computing
Write me a Python function
```

## 🔒 Security

- All Python dependencies pinned to specific versions
- Firebase Authentication for user management
- Environment variables for sensitive data
- CORS configured for frontend origin
- No API keys exposed to client

## 🐛 Troubleshooting

### WebSocket Connection Fails

1. Verify backend is running FIRST
2. Check backend console shows: `INFO: Uvicorn running...`
3. Refresh browser

### Authentication Issues

1. Check Firebase configuration in `lib/firebase.ts`
2. Verify Authentication is enabled in Firebase Console
3. Check browser console for specific errors

### Tool Calling Errors

1. Verify Google Classroom credentials are set up
2. Check `tokens.json` exists and is valid
3. Ensure required scopes are granted

See **[STARTUP_GUIDE.md](./STARTUP_GUIDE.md)** for more troubleshooting tips.

## 🏗️ Architecture

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Browser   │ ◄─────► │ FastAPI      │ ◄─────► │ Gemini API  │
│  (Next.js)  │ WebSocket│ Backend      │ HTTP/WS │             │
│             │         │              │         │             │
│ - Auth      │         │ - WebSocket  │         │ - LLM       │
│ - UI/UX     │         │ - Memory     │         │ - Tools     │
│ - Forms     │         │ - Tools      │         │ - Thinking  │
└─────────────┘         └──────────────┘         └─────────────┘
       │                       │
       │                       ▼
       │                ┌──────────────┐
       │                │  Classroom   │
       └───────────────►│  API         │
        OAuth           └──────────────┘
```

## 🛣️ Roadmap

- [ ] Long-term memory with vector database
- [ ] Multi-modal input (images, documents)
- [ ] Assignment grading assistance
- [ ] Student progress analytics
- [ ] Mobile app support
- [ ] Offline mode

## 📝 License

This project is private and not licensed for public use.

## 🤝 Contributing

This is a private project. For questions or issues, contact the development team.

---

**Built with:**
- [FastAPI](https://fastapi.tiangolo.com/) - Backend framework
- [Next.js](https://nextjs.org/) - Frontend framework
- [Google Gemini](https://ai.google.dev/) - AI model
- [Firebase](https://firebase.google.com/) - Authentication
- [Google Classroom API](https://developers.google.com/classroom) - Classroom integration

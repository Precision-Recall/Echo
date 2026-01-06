# Echo 

> Your AI-powered Google Classroom assistant

Echo is a modern web application that lets educators and students interact with Google Classroom using natural language. Powered by Google's Gemini AI, Echo transforms classroom management from tedious clicks into simple conversations- .

![Next.js](https://img.shields.io/badge/Next.js-16.1.1-black?logo=next.js)
![React](https://img.shields.io/badge/React-19-blue?logo=react)
![TypeScript](https://img.shields.io/badge/TypeScript-5-blue?logo=typescript)
![Tailwind CSS](https://img.shields.io/badge/Tailwind-4-38bdf8?logo=tailwindcss)

## Features

### Natural Conversations
Chat naturally to create assignments, manage courses, and get classroom insights—no complex menus or forms needed.

### Instant Actions
Create assignments and courses with intuitive forms, powered by AI that understands your intent.

### Google Classroom Integration
Seamlessly connected to your Google Classroom for real-time updates and management.

### Voice Chat (Experimental)
Real-time speech-to-speech communication with Gemini for hands-free interaction.

### Smart Context
Conversation memory preserves context across messages, so Echo remembers what you discussed.

---

## Quick Start

### Prerequisites

- Node.js 18+
- npm or yarn
- Google Cloud project with Classroom API enabled
- Firebase project for authentication

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd echo_frontend

# Install dependencies
npm install

# Set up environment variables
cp .env.example .env.local
# Edit .env.local with your credentials

# Start development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Environment Variables

Create a `.env.local` file with:

```env
NEXT_PUBLIC_FIREBASE_API_KEY=your_firebase_api_key
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your_project.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=your_project_id
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

See [ENV_TEMPLATE.md](./ENV_TEMPLATE.md) for detailed configuration.

---

## Usage

### Text Chat

1. Sign in with your Google account
2. Type naturally: *"Show me my courses"* or *"Create an assignment for Math 101"*
3. Echo will understand your intent and take action
4. View AI reasoning in the expandable chain-of-thought panel

### Assignment Creation

When you mention creating an assignment, Echo shows an inline form:

- **Auto-detects** course IDs from your message
- **Smart forms** with all necessary fields (title, description, due date, points)
- **Validation** ensures correct input before submission

### Voice Mode

1. Click the microphone button to start
2. Speak your request naturally
3. Echo responds with voice and executes actions
4. Click again to stop recording

---

## Architecture

```
echo_frontend/
├── app/
│   ├── landing/          # Landing page
│   ├── login/            # Authentication
│   ├── chat/             # Main chat interface
│   ├── contexts/         # React contexts (Auth)
│   ├── hooks/            # Custom hooks
│   │   ├── useGeminiWebSocket.ts
│   │   ├── useAudioCapture.ts
│   │   └── useAudioPlayback.ts
│   └── components/       # Shared components
├── components/ui/        # Shadcn UI components
├── lib/                  # Utilities
└── public/               # Static assets
```

### WebSocket Connections

Echo maintains two separate WebSocket connections:

| Endpoint | Purpose | Use Case |
|----------|---------|----------|
| `/ws/chat` | Text-based chat | Main conversation interface |
| `/ws/live` | Voice streaming | Real-time audio communication |

---

## Development

### Available Scripts

```bash
npm run dev      # Start development server
npm run build    # Build for production
npm run start    # Start production server
npm run lint     # Run ESLint
```

### Deployment

Echo is configured for standalone deployment (Docker, Appwrite, etc.):

```bash
npm run build
# Output is in .next/standalone
```

---

## Documentation

| Guide | Description |
|-------|-------------|
| [SETUP_GUIDE.md](./SETUP_GUIDE.md) | Complete setup instructions |
| [AUTH_SETUP.md](./AUTH_SETUP.md) | Firebase authentication setup |
| [GOOGLE_CLASSROOM_SETUP.md](./GOOGLE_CLASSROOM_SETUP.md) | Classroom API configuration |
| [ENV_TEMPLATE.md](./ENV_TEMPLATE.md) | Environment variables reference |

---

## Troubleshooting

<details>
<summary><strong>Connection issues</strong></summary>

- Ensure backend is running on the configured port
- Check browser console for WebSocket errors
- Verify CORS settings in backend

</details>

<details>
<summary><strong>Microphone not working</strong></summary>

- Check browser permissions
- Ensure you're on HTTPS or localhost
- Only Chrome, Firefox, and Safari supported

</details>

<details>
<summary><strong>Authentication errors</strong></summary>

- Verify Firebase configuration
- Check Google OAuth consent screen settings
- Ensure redirect URIs are correctly configured

</details>

---

## Contributing

Contributions are welcome! Please read our contributing guidelines before submitting pull requests.

---
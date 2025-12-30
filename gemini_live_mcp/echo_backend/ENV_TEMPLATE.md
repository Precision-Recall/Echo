# Echo Backend - Environment Configuration

Copy the content below into a `.env` file in this directory.

```bash
# =============================================================================
# Echo Backend - Environment Configuration
# =============================================================================

# -----------------------------------------------------------------------------
# Google Gemini API
# -----------------------------------------------------------------------------
# Required: Get your API key from https://aistudio.google.com/app/apikey
GEMINI_API_KEY=your-gemini-api-key-here

# -----------------------------------------------------------------------------
# Google OAuth (for Classroom API)
# -----------------------------------------------------------------------------
# Get from Google Cloud Console: https://console.cloud.google.com/
# Go to APIs & Services > Credentials
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret

# -----------------------------------------------------------------------------
# Token Service Configuration
# -----------------------------------------------------------------------------
# URL of the token service (echo_backend_firebase)
TOKEN_SERVICE_URL=http://localhost:8001

# -----------------------------------------------------------------------------
# Google Classroom Configuration
# -----------------------------------------------------------------------------
# Optional: Directory containing tokens.json and credentials.json for legacy mode
# Leave empty to use current directory
CLASSROOM_DATA_DIR=

# -----------------------------------------------------------------------------
# Server Configuration
# -----------------------------------------------------------------------------
# Port for the main backend server
PORT=8000

# CORS: Comma-separated list of allowed origins
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001

# -----------------------------------------------------------------------------
# Optional: Logging
# -----------------------------------------------------------------------------
# Set to "DEBUG" for verbose logging
LOG_LEVEL=INFO
```

## Setup Instructions

1. **Copy to .env file:**
   ```bash
   cp ENV_TEMPLATE.md .env
   # Edit .env and replace placeholder values
   ```

2. **Get Gemini API Key:**
   - Visit: https://aistudio.google.com/app/apikey
   - Create a new API key
   - Copy and paste into `GEMINI_API_KEY`

3. **Get Google OAuth Credentials:**
   - Visit: https://console.cloud.google.com/
   - Go to **APIs & Services** > **Credentials**
   - Create or use existing **OAuth 2.0 Client ID**
   - Copy Client ID and Client Secret

4. **Ensure Token Service is Running:**
   ```bash
   # In another terminal:
   cd ../echo_backend_firebase
   python main.py
   # Should start on http://localhost:8001
   ```

5. **Start the Backend:**
   ```bash
   python main.py
   # Should start on http://localhost:8000
   ```

## Required Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | ✅ Yes | Your Google Gemini API key |
| `GOOGLE_CLIENT_ID` | ✅ Yes | OAuth 2.0 Client ID |
| `GOOGLE_CLIENT_SECRET` | ✅ Yes | OAuth 2.0 Client Secret |
| `TOKEN_SERVICE_URL` | ✅ Yes | URL of token service |
| `ALLOWED_ORIGINS` | ⚠️ Recommended | CORS origins |
| `CLASSROOM_DATA_DIR` | ❌ Optional | Legacy tokens directory |
| `PORT` | ❌ Optional | Server port (default: 8000) |
| `LOG_LEVEL` | ❌ Optional | Logging level (default: INFO) |

## Troubleshooting

### "GEMINI_API_KEY not found"
- Make sure .env file exists in this directory
- Check that variable name is exactly `GEMINI_API_KEY`
- Restart the server after editing .env

### "Cannot connect to token service"
- Ensure `echo_backend_firebase` is running
- Check `TOKEN_SERVICE_URL` points to correct address
- Default should be: `http://localhost:8001`

### "Google OAuth credentials not configured"
- Set both `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`
- Get from Google Cloud Console
- Enable required APIs (Classroom, Drive, etc.)


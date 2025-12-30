# Echo Backend Firebase - Environment Configuration

Copy the content below into a `.env` file in this directory.

```bash
# =============================================================================
# Echo Backend Firebase - Token Service Configuration
# =============================================================================

# -----------------------------------------------------------------------------
# Firebase Configuration
# -----------------------------------------------------------------------------
# REQUIRED: Firebase Admin SDK credentials as JSON string
# Copy the entire JSON content from your Firebase Admin SDK credentials file
# and paste it as a single line (or use proper escaping for multiline)
FIREBASE_CREDENTIALS={"type":"service_account","project_id":"your-project-id","private_key_id":"your-private-key-id","private_key":"-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n","client_email":"firebase-adminsdk-xxxxx@your-project.iam.gserviceaccount.com","client_id":"your-client-id","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs","client_x509_cert_url":"https://www.googleapis.com/robot/v1/metadata/x509/...","universe_domain":"googleapis.com"}

# -----------------------------------------------------------------------------
# Google OAuth Configuration
# -----------------------------------------------------------------------------
# Get from Google Cloud Console: https://console.cloud.google.com/
# Go to APIs & Services > Credentials
# MUST be the same OAuth credentials used in the frontend
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret

# -----------------------------------------------------------------------------
# Server Configuration
# -----------------------------------------------------------------------------
# Port for the token service
PORT=8001

# CORS: Comma-separated list of allowed origins
# Should include your frontend URL
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001

# -----------------------------------------------------------------------------
# Optional: Logging
# -----------------------------------------------------------------------------
LOG_LEVEL=INFO
```

## Setup Instructions

1. **Get Firebase Admin SDK Credentials:**
   - Go to https://console.firebase.google.com/
   - Select your project (create one if needed)
   - Go to **Project Settings** (gear icon) > **Service Accounts** tab
   - Click **"Generate New Private Key"**
   - Download the JSON file

2. **Format credentials for .env:**
   
   **Option A: Single-line JSON (Recommended):**
   ```bash
   # Open the downloaded JSON file
   # Copy the ENTIRE content
   # Remove all newlines and extra spaces
   # Paste as single line:
   FIREBASE_CREDENTIALS={"type":"service_account","project_id":"echooo-482613",...}
   ```

   **Option B: Multi-line JSON (if your .env supports it):**
   ```bash
   FIREBASE_CREDENTIALS={
     "type": "service_account",
     "project_id": "echooo-482613",
     "private_key_id": "...",
     "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
     "client_email": "firebase-adminsdk-...@....iam.gserviceaccount.com",
     ...
   }
   ```

3. **Verify JSON format:**
   ```bash
   # Test that your JSON is valid:
   echo $FIREBASE_CREDENTIALS | python -m json.tool
   ```

2. **Get Google OAuth Credentials:**
   - Visit: https://console.cloud.google.com/
   - Go to **APIs & Services** > **Credentials**
   - Create **OAuth 2.0 Client ID** (Web application)
   - Add authorized origins:
     - `http://localhost:3000`
     - `https://yourdomain.com` (production)
   - Copy Client ID and Client Secret

3. **Create .env file:**
   ```bash
   # Copy template
   cp ENV_TEMPLATE.md .env
   
   # Edit with your actual values
   nano .env
   ```

4. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Start the Token Service:**
   ```bash
   python main.py
   # Should start on http://localhost:8001
   ```

## Required Files

| File | Required | Description |
|------|----------|-------------|
| `.env` | ✅ Yes | Environment variables (includes Firebase credentials) |
| `requirements.txt` | ✅ Yes | Python dependencies |
| `main.py` | ✅ Yes | FastAPI application |

**Note:** No separate credential files needed - everything is in `.env`

## Required Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `FIREBASE_CREDENTIALS` | ✅ Yes | Firebase Admin SDK credentials as JSON string |
| `GOOGLE_CLIENT_ID` | ✅ Yes | OAuth 2.0 Client ID |
| `GOOGLE_CLIENT_SECRET` | ✅ Yes | OAuth 2.0 Client Secret |
| `ALLOWED_ORIGINS` | ⚠️ Recommended | CORS origins (comma-separated) |
| `PORT` | ❌ Optional | Server port (default: 8001) |

## API Endpoints

Once running, the following endpoints will be available:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/api/oauth/exchange` | POST | Exchange auth code for tokens |
| `/api/tokens/store` | POST | Store user tokens in Firestore |
| `/api/tokens/retrieve` | GET | Get user tokens from Firestore |
| `/api/tokens/status` | GET | Check if user has tokens |
| `/api/tokens/delete` | DELETE | Delete user tokens |

## Troubleshooting

### "FIREBASE_CREDENTIALS environment variable is required"
- Make sure you've created `.env` file in this directory
- Verify `FIREBASE_CREDENTIALS` is set in `.env`
- Restart the server after editing `.env`

### "Failed to parse FIREBASE_CREDENTIALS JSON"
- Check that the JSON is properly formatted
- Ensure all quotes are escaped correctly
- For single-line: Remove all newlines from the JSON
- Test JSON validity: `echo $FIREBASE_CREDENTIALS | python -m json.tool`
- Common issues:
  - Newlines in private_key should be `\n` not actual newlines
  - All property names must be in double quotes
  - No trailing commas

### "Firebase initialization error"
- Verify the JSON contains all required fields:
  - `type`, `project_id`, `private_key_id`
  - `private_key`, `client_email`, `client_id`
- Check that the service account has appropriate permissions
- Ensure Firestore is enabled in your Firebase project

### "Google OAuth not configured"
- Set both `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`
- Ensure they match the credentials in your frontend
- Verify they're from the same Google Cloud project

### "CORS error"
- Add your frontend URL to `ALLOWED_ORIGINS`
- Format: comma-separated list (no spaces)
- Example: `http://localhost:3000,https://yourdomain.com`

### Port already in use
- Change `PORT` to a different value
- Update `TOKEN_SERVICE_URL` in echo_backend accordingly
- Update `NEXT_PUBLIC_TOKEN_SERVICE_URL` in frontend

## Firebase Firestore Structure

Tokens are stored in Firestore with the following structure:

```
users/
  {user-email}/
    access_token: string
    refresh_token: string
    expires_in: number
    scope: string
    last_updated: string (ISO 8601)
```

## Deployment to Production

All major platforms support JSON credentials via environment variables:

**Heroku:**
```bash
heroku config:set FIREBASE_CREDENTIALS='{"type":"service_account",...}'
heroku config:set GOOGLE_CLIENT_ID=your-client-id
heroku config:set GOOGLE_CLIENT_SECRET=your-secret
heroku config:set ALLOWED_ORIGINS=https://yourdomain.com
```

**Vercel:**
```bash
# In Vercel Dashboard > Project Settings > Environment Variables
# Add as "Secret" type for sensitive values
FIREBASE_CREDENTIALS: {"type":"service_account",...}
GOOGLE_CLIENT_ID: your-client-id
GOOGLE_CLIENT_SECRET: your-secret
ALLOWED_ORIGINS: https://yourdomain.com
```

**Railway / Render / Fly.io:**
- Add environment variables in dashboard
- Paste JSON credentials as-is
- Mark as "secret" or "sensitive"
- No file uploads needed

**Docker:**
```dockerfile
# In docker-compose.yml
environment:
  - FIREBASE_CREDENTIALS={"type":"service_account",...}
  - GOOGLE_CLIENT_ID=your-client-id
  - GOOGLE_CLIENT_SECRET=your-secret
  - ALLOWED_ORIGINS=https://yourdomain.com
```

**Benefits of JSON in Environment Variables:**
- ✅ No file management
- ✅ Works on all platforms
- ✅ Easy to update/rotate
- ✅ Built-in secrets management
- ✅ No git commits of sensitive files

## Security Notes

1. **Never commit .env to git**
   - Already in .gitignore
   - Contains sensitive credentials (Firebase keys, OAuth secrets)
   - Use platform-specific secrets management in production

2. **Keep client secret secure**
   - Never expose in frontend code
   - Only used in backend for token exchange

3. **Use HTTPS in production**
   - Required for OAuth 2.0
   - Protects token transmission

4. **Set up Firestore security rules**
   ```javascript
   rules_version = '2';
   service cloud.firestore {
     match /databases/{database}/documents {
       match /users/{email} {
         allow read, write: if request.auth != null 
                           && request.auth.token.email == email;
       }
     }
   }
   ```


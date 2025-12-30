# Echo Frontend - Environment Configuration

Copy the content below into a `.env.local` file in this directory.

```bash
# =============================================================================
# Echo Frontend - Environment Configuration
# =============================================================================

# -----------------------------------------------------------------------------
# Google OAuth Configuration
# -----------------------------------------------------------------------------
# Get from Google Cloud Console: https://console.cloud.google.com/
# Go to APIs & Services > Credentials
# MUST be the same OAuth Client ID used in the backend
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com

# -----------------------------------------------------------------------------
# Backend Services
# -----------------------------------------------------------------------------
# URL of the token service (echo_backend_firebase)
NEXT_PUBLIC_TOKEN_SERVICE_URL=http://localhost:8001

# URL of the main backend (echo_backend)
# Optional: Used if you need to configure WebSocket URL
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000

# -----------------------------------------------------------------------------
# Firebase Configuration (Optional - if not in lib/firebase.ts)
# -----------------------------------------------------------------------------
# You can configure Firebase here OR directly in lib/firebase.ts
# If using environment variables, uncomment and fill these:

# NEXT_PUBLIC_FIREBASE_API_KEY=your-api-key
# NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
# NEXT_PUBLIC_FIREBASE_PROJECT_ID=your-project-id
# NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=your-project.appspot.com
# NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=your-sender-id
# NEXT_PUBLIC_FIREBASE_APP_ID=your-app-id

# -----------------------------------------------------------------------------
# Optional: Development Configuration
# -----------------------------------------------------------------------------
# Set to 'development' or 'production'
NODE_ENV=development

# Custom port (default is 3000)
# PORT=3001
```

## Setup Instructions

1. **Create .env.local file:**
   ```bash
   # Copy template
   cp ENV_TEMPLATE.md .env.local
   
   # Edit with your actual values
   nano .env.local
   ```

2. **Get Google OAuth Client ID:**
   - Visit: https://console.cloud.google.com/
   - Go to **APIs & Services** > **Credentials**
   - Use the SAME Client ID as in your backends
   - Copy just the Client ID (not the secret)

3. **Configure Firebase:**
   
   **Option A: Using lib/firebase.ts (Recommended)**
   ```typescript
   // Edit lib/firebase.ts
   const firebaseConfig = {
     apiKey: "AIzaSyCqZ6Xc2XXK-6uR_EtMx8kJ9mmLekYSzLA",
     authDomain: "echoooo-12.firebaseapp.com",
     projectId: "echoooo-12",
     storageBucket: "echoooo-12.firebasestorage.app",
     messagingSenderId: "287978920748",
     appId: "1:287978920748:web:bcbf309eaa7ae1b0f86a89"
   };
   ```
   
   **Option B: Using Environment Variables**
   ```bash
   # Uncomment Firebase variables in .env.local
   NEXT_PUBLIC_FIREBASE_API_KEY=...
   NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=...
   # etc.
   
   # Then use in lib/firebase.ts:
   const firebaseConfig = {
     apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
     authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
     // ...
   };
   ```

4. **Install Dependencies:**
   ```bash
   npm install
   ```

5. **Start Development Server:**
   ```bash
   npm run dev
   # Should start on http://localhost:3000
   ```

## Required Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_GOOGLE_CLIENT_ID` | ✅ Yes | OAuth 2.0 Client ID |
| `NEXT_PUBLIC_TOKEN_SERVICE_URL` | ✅ Yes | Token service URL |
| Firebase Config | ✅ Yes | Either in .env.local OR lib/firebase.ts |
| `NEXT_PUBLIC_BACKEND_URL` | ❌ Optional | Main backend URL |

## Important Notes

### NEXT_PUBLIC_ Prefix

All variables that need to be accessible in the browser MUST have the `NEXT_PUBLIC_` prefix:

```bash
# ✅ Correct - Will be available in browser
NEXT_PUBLIC_GOOGLE_CLIENT_ID=...

# ❌ Wrong - Will NOT be available in browser
GOOGLE_CLIENT_ID=...
```

### .env.local vs .env

- `.env.local` - For local development (gitignored)
- `.env.production` - For production builds
- `.env` - Default values (usually committed)

**Use `.env.local` for sensitive values!**

### Firebase Configuration

**Current configuration in `lib/firebase.ts`:**
```typescript
const firebaseConfig = {
  apiKey: "AIzaSyCqZ6Xc2XXK-6uR_EtMx8kJ9mmLekYSzLA",
  authDomain: "echoooo-12.firebaseapp.com",
  projectId: "echoooo-12",
  storageBucket: "echoooo-12.firebasestorage.app",
  messagingSenderId: "287978920748",
  appId: "1:287978920748:web:bcbf309eaa7ae1b0f86a89"
};
```

**If you want to use your own Firebase project:**
1. Go to Firebase Console > Project Settings
2. Scroll down to "Your apps"
3. Copy the config object
4. Replace values in `lib/firebase.ts` OR use environment variables

## WebSocket Configuration

The WebSocket URL is configured in `app/hooks/useGeminiWebSocket.ts`:

```typescript
const WEBSOCKET_BASE_URL = 'ws://localhost:8000';
```

To make it configurable:
1. Add to .env.local:
   ```bash
   NEXT_PUBLIC_WEBSOCKET_URL=ws://localhost:8000
   ```

2. Update useGeminiWebSocket.ts:
   ```typescript
   const WEBSOCKET_BASE_URL = process.env.NEXT_PUBLIC_WEBSOCKET_URL || 'ws://localhost:8000';
   ```

## Available Scripts

```bash
# Development server
npm run dev

# Production build
npm run build

# Start production server
npm start

# Linting
npm run lint
```

## Troubleshooting

### "Google Client ID not configured"
- Check that `NEXT_PUBLIC_GOOGLE_CLIENT_ID` is set in `.env.local`
- Ensure it has the `NEXT_PUBLIC_` prefix
- Restart the dev server after editing `.env.local`

### "Token service unreachable"
- Ensure `echo_backend_firebase` is running on port 8001
- Check `NEXT_PUBLIC_TOKEN_SERVICE_URL` value
- Verify CORS is configured in token service

### "Firebase not initialized"
- Check configuration in `lib/firebase.ts`
- If using env vars, ensure they all have `NEXT_PUBLIC_` prefix
- Restart dev server after changes

### WebSocket connection fails
- Ensure `echo_backend` is running on port 8000
- Check browser console for specific error
- Verify backend CORS includes `http://localhost:3000`

### OAuth popup blocked
- Allow popups in browser settings
- Use HTTPS in production (required by Google)

## Production Deployment

### Vercel (Recommended for Next.js)

1. **Add environment variables in Vercel dashboard:**
   - Go to Project Settings > Environment Variables
   - Add all `NEXT_PUBLIC_*` variables

2. **Update URLs for production:**
   ```bash
   NEXT_PUBLIC_TOKEN_SERVICE_URL=https://your-token-service.com
   NEXT_PUBLIC_BACKEND_URL=https://your-backend.com
   ```

3. **Update Google OAuth:**
   - Add production URL to authorized origins
   - Add production URL to authorized redirects

### Other Platforms

For other platforms, ensure:
- All environment variables are set
- URLs point to production backends
- OAuth credentials configured for production domain
- Use HTTPS everywhere

## Security Best Practices

1. **Never commit .env.local**
   - Already in .gitignore
   - Contains sensitive configuration

2. **Don't expose secrets in browser**
   - Only use `NEXT_PUBLIC_` for non-sensitive values
   - Client ID is public (OK to expose)
   - Client SECRET must NEVER be in frontend

3. **Use environment-specific configs**
   - Different values for dev/staging/production
   - Separate Firebase projects for each environment

4. **Rotate credentials regularly**
   - Update OAuth credentials periodically
   - Update Firebase API keys if compromised

## Example Complete .env.local

```bash
# Google OAuth
NEXT_PUBLIC_GOOGLE_CLIENT_ID=123456789-abcdefghijklmnop.apps.googleusercontent.com

# Backend Services
NEXT_PUBLIC_TOKEN_SERVICE_URL=http://localhost:8001
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000

# Optional: Firebase (if not in lib/firebase.ts)
# NEXT_PUBLIC_FIREBASE_API_KEY=AIzaSyD...
# NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=my-app.firebaseapp.com
# NEXT_PUBLIC_FIREBASE_PROJECT_ID=my-app
# NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=my-app.appspot.com
# NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=123456789
# NEXT_PUBLIC_FIREBASE_APP_ID=1:123456789:web:abc123
```

## Getting Help

If you encounter issues:
1. Check browser console for errors
2. Check backend logs
3. Verify all services are running
4. Review CORS configuration
5. Ensure environment variables are loaded (restart dev server)

For more details, see:
- `GOOGLE_CLASSROOM_SETUP.md` - OAuth setup guide
- `AUTH_SETUP.md` - Firebase authentication setup
- `WEBSOCKET_FIX.md` - WebSocket troubleshooting


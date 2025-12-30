# Google Classroom OAuth Setup

This guide explains how to set up Google Classroom OAuth authorization in Echo.

## Overview

Echo uses Google OAuth 2.0 to request permissions for Google Classroom and Google Workspace APIs. When a user logs in, they will be prompted to authorize access to their Google Classroom data.

## Architecture

```
User Login → Firebase Auth → Classroom Auth Prompt → Google OAuth → Store Tokens in Firestore
```

## Setup Steps

### 1. Configure Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the following APIs:
   - Google Classroom API
   - Google Drive API
   - Google Docs API
   - Google Sheets API
   - Google Slides API
   - Apps Script API

### 2. Create OAuth 2.0 Credentials

1. Go to **APIs & Services** > **Credentials**
2. Click **Create Credentials** > **OAuth 2.0 Client ID**
3. Configure the consent screen:
   - User type: **External** (or Internal for workspace)
   - App name: **Echo**
   - User support email: Your email
   - Developer contact: Your email
   - Scopes: Add all required scopes (see below)
4. Application type: **Web application**
5. Authorized JavaScript origins:
   ```
   http://localhost:3000
   https://yourdomain.com
   ```
6. Authorized redirect URIs:
   ```
   http://localhost:3000
   https://yourdomain.com
   ```
7. Download the JSON credentials

### 3. Required Scopes

Add these scopes in the OAuth consent screen:

**Google Classroom:**
- `https://www.googleapis.com/auth/classroom.courses`
- `https://www.googleapis.com/auth/classroom.rosters`
- `https://www.googleapis.com/auth/classroom.coursework.students`
- `https://www.googleapis.com/auth/classroom.courseworkmaterials`
- `https://www.googleapis.com/auth/classroom.announcements`
- `https://www.googleapis.com/auth/classroom.topics`
- `https://www.googleapis.com/auth/classroom.profile.emails`
- `https://www.googleapis.com/auth/classroom.profile.photos`
- `https://www.googleapis.com/auth/classroom.guardianlinks.students`

**Google Workspace:**
- `https://www.googleapis.com/auth/script.projects`
- `https://www.googleapis.com/auth/documents`
- `https://www.googleapis.com/auth/presentations`
- `https://www.googleapis.com/auth/spreadsheets`

### 4. Configure Frontend Environment

Create `.env.local` file in `echo_frontend/`:

```bash
# Google OAuth Configuration
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-client-id-here.apps.googleusercontent.com

# Token Service URL
NEXT_PUBLIC_TOKEN_SERVICE_URL=http://localhost:8001
```

**Important:** Replace `your-client-id-here` with your actual Client ID from Google Cloud Console.

### 5. Configure Backend Environment

Create `.env` file in `echo_backend_firebase/`:

```bash
# Firebase Configuration
FIREBASE_CREDENTIALS_PATH=firebase-credentials.json

# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret-here

# Server Configuration
PORT=8001
ALLOWED_ORIGINS=http://localhost:3000
```

**Important:** Replace with your actual credentials from Google Cloud Console.

### 6. Download Firebase Admin Credentials

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project
3. Go to **Project Settings** > **Service Accounts**
4. Click **Generate New Private Key**
5. Save as `firebase-credentials.json` in `echo_backend_firebase/`

## User Flow

### First Login

1. User logs in via Firebase (email/password or Google)
2. Redirected to `/chat`
3. **Classroom Auth Prompt** appears (if no tokens stored)
4. User clicks "Authorize Google Classroom"
5. Google OAuth popup opens
6. User grants permissions
7. Authorization code exchanged for tokens
8. Tokens stored in Firestore under `users/{email}`
9. User can now use Classroom features

### Subsequent Logins

1. User logs in via Firebase
2. System checks for existing tokens in Firestore
3. If tokens exist, chat interface loads directly
4. No re-authorization needed (unless tokens expired)

## Firestore Structure

```
users/
  {user-email}/
    access_token: "ya29.a0..."
    refresh_token: "1//0g..."
    expires_in: 3599
    scope: "https://www.googleapis.com/auth/classroom..."
    last_updated: "2024-01-15T10:30:00.000Z"
```

## Token Management

### Token Storage
- Tokens are stored in Firestore for persistence
- Only the authenticated user can access their own tokens
- Firebase ID token required for all API calls

### Token Retrieval
- Main backend (`echo_backend`) retrieves tokens when calling Classroom APIs
- Token service validates Firebase ID token before returning tokens
- Automatic token refresh handled by Google OAuth client libraries

### Token Deletion
- User can revoke access from settings (future feature)
- Tokens deleted from Firestore on revocation

## Security Considerations

1. **Client Secret**: Never expose in frontend code
   - Backend handles token exchange securely
   - Frontend only sends authorization code

2. **Firebase ID Token**: Required for all token API calls
   - Validates user identity
   - Prevents unauthorized access to tokens

3. **Firestore Rules**: Should restrict access to user's own data
   ```javascript
   match /users/{userId} {
     allow read, write: if request.auth != null && request.auth.token.email == userId;
   }
   ```

4. **HTTPS**: Use HTTPS in production
   - Required for OAuth
   - Protects token transmission

## Testing

### Test Authorization Flow

1. Start backend_firebase:
   ```bash
   cd echo_backend_firebase
   python main.py
   ```

2. Start frontend:
   ```bash
   cd echo_frontend
   npm run dev
   ```

3. Open browser: http://localhost:3000
4. Log in with Firebase
5. Click "Authorize Google Classroom" when prompted
6. Grant permissions in Google popup
7. Verify success message

### Verify Token Storage

```bash
# Check Firestore in Firebase Console
# Go to Firestore Database
# Navigate to: users > {your-email}
# Verify fields: access_token, refresh_token, last_updated
```

### Test Token Retrieval API

```bash
# Get your Firebase ID token from browser console:
# > await firebase.auth().currentUser.getIdToken()

curl -X GET "http://localhost:8001/api/tokens/retrieve?email=your-email@example.com" \
  -H "Authorization: Bearer YOUR_FIREBASE_ID_TOKEN"
```

## Troubleshooting

### "Google Identity Services not loaded"

**Solution:** Wait for page to fully load. The Google script loads after page mount.

### "Token exchange failed"

**Possible causes:**
1. Client secret not configured in backend
2. Incorrect redirect URI
3. Authorization code already used (codes are single-use)

**Solution:** Check backend `.env` configuration

### "Access denied: You can only retrieve your own tokens"

**Cause:** Email mismatch between Firebase token and requested email

**Solution:** Ensure you're requesting tokens for your own email

### "No tokens found for this user"

**Cause:** User hasn't authorized Classroom access yet

**Solution:** Complete the authorization flow first

## Production Deployment

### Frontend
- Update `NEXT_PUBLIC_TOKEN_SERVICE_URL` to production backend URL
- Use production Google OAuth credentials
- Enable HTTPS

### Backend
- Deploy `echo_backend_firebase` to cloud service (Cloud Run, Heroku, etc.)
- Set environment variables in cloud platform
- Upload `firebase-credentials.json` securely (use secrets manager)

### OAuth Consent Screen
- Complete verification process for production use
- Submit for review if using sensitive scopes
- Add production redirect URIs

## API Reference

See [echo_backend_firebase/README.md](../echo_backend_firebase/README.md) for detailed API documentation.


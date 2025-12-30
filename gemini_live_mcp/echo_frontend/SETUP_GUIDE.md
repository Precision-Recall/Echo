# Echo Frontend - Setup Guide

## 🔧 Fixed Issues

### ✅ Issue 1: Module Import Paths (FIXED)
- **Error**: `Module not found: Can't resolve '@/components/prompt-kit/loader'`
- **Fix**: Updated all imports from `@/components/prompt-kit/*` to `@/components/ui/*`
- **Files Updated**:
  - `app/chat/page.tsx`
  - `app/components/ClassroomAuthPrompt.tsx`

### ✅ Issue 2: Google Classroom OAuth Scopes
- **Issue**: Firebase login didn't request Classroom scopes
- **Explanation**: This is **by design**! There are TWO separate authentication flows:
  1. **Firebase Authentication** - For app login (basic Google sign-in)
  2. **Google Classroom OAuth** - For API access with specific scopes

## 📋 Required Setup Steps

### Step 1: Create `.env.local` File

Create a file named `.env.local` in the `echo_frontend` directory with the following content:

```bash
# =============================================================================
# Echo Frontend - Environment Configuration
# =============================================================================

# -----------------------------------------------------------------------------
# Google OAuth Configuration (Required)
# -----------------------------------------------------------------------------
# Get from: https://console.cloud.google.com/
# Go to: APIs & Services > Credentials
# Create: OAuth 2.0 Client ID (Web application type)
# Add JavaScript origins: http://localhost:3000
# Add redirect URIs: http://localhost:3000, postmessage
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com

# -----------------------------------------------------------------------------
# Backend Services (Required)
# -----------------------------------------------------------------------------
NEXT_PUBLIC_TOKEN_SERVICE_URL=http://localhost:8001
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000

# -----------------------------------------------------------------------------
# Firebase Configuration (Required)
# -----------------------------------------------------------------------------
# Get from: https://console.firebase.google.com/
# Go to: Project Settings > General > Your apps > Web app
NEXT_PUBLIC_FIREBASE_API_KEY=your-firebase-api-key
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=your-project-id
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=your-project.appspot.com
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=123456789
NEXT_PUBLIC_FIREBASE_APP_ID=1:123456789:web:abc123def456

# -----------------------------------------------------------------------------
# Development
# -----------------------------------------------------------------------------
NODE_ENV=development
```

### Step 2: Configure Google Cloud Console

#### Create OAuth 2.0 Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project or create a new one
3. Navigate to **APIs & Services > Credentials**
4. Click **Create Credentials > OAuth 2.0 Client ID**
5. Choose **Web application** as the application type
6. Add **Authorized JavaScript origins**:
   - `http://localhost:3000`
   - `http://127.0.0.1:3000`
7. Add **Authorized redirect URIs**:
   - `http://localhost:3000`
   - `postmessage` (important for popup flow)
8. Save and copy the **Client ID**
9. Paste it into `NEXT_PUBLIC_GOOGLE_CLIENT_ID` in `.env.local`

#### Enable Required APIs

Enable the following APIs in Google Cloud Console:
- Google Classroom API
- Google Drive API
- Google Docs API
- Google Sheets API
- Google Slides API

### Step 3: Configure Firebase

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project or create a new one
3. Go to **Project Settings > General**
4. Scroll down to **Your apps** section
5. Click on **Web app** (or add one if not exists)
6. Copy the Firebase configuration values
7. Paste them into the `.env.local` file

### Step 4: Configure OAuth Consent Screen

1. In Google Cloud Console, go to **APIs & Services > OAuth consent screen**
2. Add the following **scopes**:
   - `https://www.googleapis.com/auth/classroom.courses`
   - `https://www.googleapis.com/auth/classroom.rosters`
   - `https://www.googleapis.com/auth/classroom.coursework.students`
   - `https://www.googleapis.com/auth/classroom.courseworkmaterials`
   - `https://www.googleapis.com/auth/classroom.announcements`
   - `https://www.googleapis.com/auth/classroom.topics`
   - `https://www.googleapis.com/auth/classroom.profile.emails`
   - `https://www.googleapis.com/auth/classroom.profile.photos`
   - `https://www.googleapis.com/auth/classroom.guardianlinks.students`
   - `https://www.googleapis.com/auth/script.projects`
   - `https://www.googleapis.com/auth/documents`
   - `https://www.googleapis.com/auth/presentations`
   - `https://www.googleapis.com/auth/spreadsheets`
   - `openid`
   - `email`
   - `profile`

3. Add test users if your app is in testing mode

## 🚀 Running the Application

### 1. Start Backend Services (in order)

```bash
# Terminal 1: Start Firebase token service
cd echo_backend_firebase
python -m uvicorn main:app --reload --port 8001

# Terminal 2: Start main backend
cd echo_backend
python -m uvicorn main:app --reload --port 8000

# Terminal 3: Start frontend
cd echo_frontend
npm run dev
```

### 2. Authentication Flow

When you run the application, here's what happens:

#### Step 1: Firebase Login
1. Open `http://localhost:3000`
2. You'll see a login page
3. Click **Sign in with Google**
4. This uses **Firebase Authentication** for basic app login
5. You'll be redirected to the chat page

#### Step 2: Classroom Authorization (Separate!)
1. After logging in, you'll see a prompt: **"Connect Google Classroom"**
2. Click **"Authorize Google Classroom"**
3. A **popup** will appear requesting **additional permissions**
4. This is the **Google OAuth flow** with Classroom-specific scopes
5. Accept the permissions
6. The tokens will be stored in Firebase Firestore

Now you can use all Classroom features!

## 🔍 Troubleshooting

### Build Error: Module not found
**Fixed!** All imports have been updated to use `@/components/ui/*`

### Google Classroom scopes not being requested
This is **correct behavior**:
- Firebase login = Basic authentication
- Classroom authorization = Separate OAuth flow with specific API scopes

The prompt will appear **after** login asking you to authorize Classroom access.

### Popup blocked
If the OAuth popup is blocked:
1. Allow popups for `localhost:3000` in your browser
2. Try clicking the "Authorize" button again

### "Google Identity Services not loaded"
Make sure the Google Identity Services script is loaded in `app/layout.tsx`:
```typescript
<script src="https://accounts.google.com/gsi/client" async defer></script>
```

### Backend connection errors
Verify that both backend services are running:
- `echo_backend_firebase` on port 8001
- `echo_backend` on port 8000

Check the console for connection errors and verify `.env.local` URLs are correct.

## 📚 Additional Documentation

- [Google Classroom API Setup](./GOOGLE_CLASSROOM_SETUP.md)
- [Firebase Authentication Setup](./AUTH_SETUP.md)
- [Environment Variables Template](./ENV_TEMPLATE.md)

## ✅ Verification Checklist

- [ ] `.env.local` file created with all required values
- [ ] Google OAuth Client ID configured in Cloud Console
- [ ] All required Google APIs enabled
- [ ] OAuth consent screen configured with all scopes
- [ ] Firebase project configured
- [ ] Backend services (`echo_backend_firebase` and `echo_backend`) are running
- [ ] Frontend builds without errors (`npm run dev`)
- [ ] Can log in with Firebase (basic Google sign-in)
- [ ] Classroom authorization prompt appears after login
- [ ] Popup opens and requests additional permissions
- [ ] Can successfully authorize Classroom access

---

**Need Help?** Check the error messages in browser console and backend logs for specific issues.


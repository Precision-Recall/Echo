# Authentication Setup Guide

## 🎯 Overview
This guide will help you set up Firebase Authentication with a minimalistic Perplexity-style UI.

## 📦 Installation

### 1. Install Firebase,
```bash
npm install firebase
```

## 🔧 File Structure

The following files have been created:

```
app/
├── contexts/
│   └── AuthContext.tsx          # Firebase auth context & hooks
├── components/
│   ├── ProtectedRoute.tsx       # Route protection wrapper
│   └── UserMenu.tsx             # User dropdown menu
├── landing/
│   └── page.tsx                 # Public landing page
├── login/
│   └── page.tsx                 # Login/signup page
├── chat/
│   └── page.tsx                 # Protected chat interface
├── redirect.tsx                 # Root redirect logic
└── layout.tsx                   # Updated with AuthProvider

lib/
└── firebase.ts                   # Firebase configuration
```

## 🚀 Quick Start

### Step 1: Modify Root page.tsx

Replace the content of `app/page.tsx` with:

```tsx
import RedirectPage from './redirect';

export default RedirectPage;
```

### Step 2: Extract Chat Interface (Optional but Recommended)

If you want to keep your current chat interface, create `app/ChatInterface.tsx` and move all the chat logic there. The `app/chat/page.tsx` already imports it.

Or simply update `app/chat/page.tsx` to include your current page.tsx content inside the `<ChatInterface />` component.

### Step 3: Start the Application

```bash
npm run dev
```

## 📱 User Flow

### For New Users:
1. Visit `http://localhost:3000` → Redirects to `/landing`
2. Click "Get Started" or "Sign in"
3. → Goes to `/login`
4. Sign up with Google or Email/Password
5. → Redirected to `/chat` (protected route)

### For Authenticated Users:
1. Visit `http://localhost:3000` → Directly redirects to `/chat`
2. Chat interface loads with user menu in header

### Logout:
1. Click user avatar in top-right
2. Click "Sign out"
3. → Redirected to `/landing`

## 🎨 UI Design Features

### Landing Page (`/landing`)
- ✅ Minimalistic white theme
- ✅ Hero section with clear value proposition
- ✅ Feature cards highlighting key capabilities
- ✅ Clean header with sign-in button
- ✅ Responsive design

### Login Page (`/login`)
- ✅ Minimalistic Perplexity-style design
- ✅ Google OAuth (one-click sign-in)
- ✅ Email/Password authentication
- ✅ Toggle between Sign In / Sign Up
- ✅ Error handling with user-friendly messages
- ✅ Responsive layout

### Chat Interface (`/chat`)
- ✅ Protected route (requires authentication)
- ✅ User menu in header
- ✅ Logout functionality
- ✅ Your existing chat features

## 🔐 Firebase Setup (Already Configured)

The Firebase configuration is already set up in `lib/firebase.ts` with your credentials:

```typescript
const firebaseConfig = {
  apiKey: "AIzaSyCqZ6Xc2XXK-6uR_EtMx8kJ9mmLekYSzLA",
  authDomain: "echoooo-12.firebaseapp.com",
  projectId: "echoooo-12",
  // ... rest of config
};
```

### Enable Authentication Methods in Firebase Console:

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project "echoooo-12"
3. Navigate to **Authentication** → **Sign-in method**
4. Enable:
   - ✅ **Email/Password**
   - ✅ **Google** (Add your app's OAuth client ID)

## 🎯 Authentication Hooks

Use the `useAuth` hook anywhere in your app:

```tsx
import { useAuth } from './contexts/AuthContext';

function MyComponent() {
  const { user, loading, signIn, signUp, signInWithGoogle, logout } = useAuth();
  
  if (loading) return <div>Loading...</div>;
  if (!user) return <div>Not authenticated</div>;
  
  return (
    <div>
      <p>Welcome {user.email}</p>
      <button onClick={logout}>Sign Out</button>
    </div>
  );
}
```

## 📋 Available Auth Functions

```typescript
const {
  user,              // Current user object or null
  loading,           // Boolean: auth state loading
  signIn,            // (email, password) => Promise
  signUp,            // (email, password) => Promise
  signInWithGoogle,  // () => Promise
  logout,            // () => Promise
  resetPassword      // (email) => Promise
} = useAuth();
```

## 🔒 Protecting Routes

Wrap any page that requires authentication:

```tsx
import { ProtectedRoute } from '@/app/components/ProtectedRoute';

export default function MyProtectedPage() {
  return (
    <ProtectedRoute>
      <YourContent />
    </ProtectedRoute>
  );
}
```

## 🎨 Customization

### Colors (Already Perplexity-style)
- Background: `bg-white`
- Primary: `bg-gray-900`
- Borders: `border-gray-200`
- Text: `text-gray-900`, `text-gray-600`

### Button Styles
- Primary: `bg-gray-900 hover:bg-gray-800`
- Secondary: `border-gray-300 hover:bg-gray-50`

## 🐛 Troubleshooting

### Issue: Firebase not installed
```bash
npm install firebase
```

### Issue: Authentication not working
- Check Firebase Console → Authentication → Sign-in methods are enabled
- Verify Firebase config in `lib/firebase.ts`
- Check browser console for errors

### Issue: Redirect loop
- Clear browser localStorage: `localStorage.clear()`
- Check that AuthProvider is in `layout.tsx`

### Issue: Google Sign-In not working
- Enable Google provider in Firebase Console
- Add authorized domains in Firebase Console → Authentication → Settings
- For local development, `localhost` should already be authorized

## 📝 Next Steps

1. ✅ Install Firebase: `npm install firebase`
2. ✅ Update `app/page.tsx` to use RedirectPage
3. ✅ Enable authentication methods in Firebase Console
4. ✅ Test the complete flow:
   - Landing → Login → Chat → Logout

## 🎉 Features Included

- ✅ Email/Password authentication
- ✅ Google OAuth
- ✅ Protected routes
- ✅ User menu with logout
- ✅ Loading states
- ✅ Error handling
- ✅ Responsive design
- ✅ Minimalistic white theme
- ✅ Perplexity-inspired UI

---

**Need Help?** Check the Firebase documentation: https://firebase.google.com/docs/auth


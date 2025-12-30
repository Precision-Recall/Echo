/**
 * Google OAuth Helper
 * Handles Google OAuth 2.0 flow with specific scopes for Classroom API
 */

// Required Google Classroom and Workspace scopes
export const GOOGLE_SCOPES = [
  'https://www.googleapis.com/auth/classroom.courses',
  'https://www.googleapis.com/auth/classroom.rosters',
  'https://www.googleapis.com/auth/classroom.coursework.students',
  'https://www.googleapis.com/auth/classroom.courseworkmaterials',
  'https://www.googleapis.com/auth/classroom.announcements',
  'https://www.googleapis.com/auth/classroom.topics',
  'https://www.googleapis.com/auth/classroom.profile.emails',
  'https://www.googleapis.com/auth/classroom.profile.photos',
  'https://www.googleapis.com/auth/classroom.guardianlinks.students',
  'https://www.googleapis.com/auth/script.projects',
  'https://www.googleapis.com/auth/documents',
  'https://www.googleapis.com/auth/presentations',
  'https://www.googleapis.com/auth/spreadsheets',
  'openid',
  'email',
  'profile'
].join(' ');

export interface GoogleOAuthTokens {
  access_token: string;
  refresh_token?: string;
  expires_in: number;
  scope: string;
  token_type: string;
}

export interface GoogleUserInfo {
  email: string;
  name: string;
  picture: string;
  sub: string;
}

const TOKEN_SERVICE_URL = process.env.NEXT_PUBLIC_TOKEN_SERVICE_URL || 'http://localhost:8001';

/**
 * Initialize Google OAuth client
 * Must be called after Google Identity Services script is loaded
 */
export function initGoogleOAuth(clientId: string) {
  if (typeof window === 'undefined' || !window.google) {
    console.error('Google Identity Services not loaded');
    return;
  }

  window.google.accounts.oauth2.initCodeClient({
    client_id: clientId,
    scope: GOOGLE_SCOPES,
    ux_mode: 'popup',
    callback: () => {}, // Will be set in requestGoogleAuth
  });
}

/**
 * Request Google OAuth authorization
 * Opens popup for user consent and returns authorization code
 */
export async function requestGoogleAuth(clientId: string): Promise<string> {
  return new Promise((resolve, reject) => {
    if (typeof window === 'undefined' || !window.google) {
      reject(new Error('Google Identity Services not loaded'));
      return;
    }

    const client = window.google.accounts.oauth2.initCodeClient({
      client_id: clientId,
      scope: GOOGLE_SCOPES,
      ux_mode: 'popup',
      callback: (response: any) => {
        if (response.error) {
          reject(new Error(response.error));
          return;
        }
        resolve(response.code);
      },
    });

    client.requestCode();
  });
}

/**
 * Exchange authorization code for tokens
 * This should be done on the backend for security
 */
export async function exchangeCodeForTokens(
  code: string,
  clientId: string,
  clientSecret: string,
  redirectUri: string = window.location.origin
): Promise<GoogleOAuthTokens> {
  const tokenEndpoint = 'https://oauth2.googleapis.com/token';

  const params = new URLSearchParams({
    code,
    client_id: clientId,
    client_secret: clientSecret,
    redirect_uri: redirectUri,
    grant_type: 'authorization_code',
  });

  const response = await fetch(tokenEndpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: params.toString(),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(`Token exchange failed: ${error.error_description || error.error}`);
  }

  return response.json();
}

/**
 * Get user info from Google using access token
 */
export async function getGoogleUserInfo(accessToken: string): Promise<GoogleUserInfo> {
  const response = await fetch('https://www.googleapis.com/oauth2/v3/userinfo', {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });

  if (!response.ok) {
    throw new Error('Failed to get user info');
  }

  return response.json();
}

/**
 * Store OAuth tokens in Firestore via backend API
 */
export async function storeTokensInFirestore(
  email: string,
  accessToken: string,
  refreshToken: string,
  expiresIn: number,
  scope: string,
  firebaseIdToken: string
): Promise<void> {
  const response = await fetch(`${TOKEN_SERVICE_URL}/api/tokens/store`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${firebaseIdToken}`,
    },
    body: JSON.stringify({
      email,
      access_token: accessToken,
      refresh_token: refreshToken,
      expires_in: expiresIn,
      scope,
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to store tokens');
  }
}

/**
 * Retrieve OAuth tokens from Firestore via backend API
 */
export async function retrieveTokensFromFirestore(
  email: string,
  firebaseIdToken: string
): Promise<GoogleOAuthTokens> {
  const response = await fetch(
    `${TOKEN_SERVICE_URL}/api/tokens/retrieve?email=${encodeURIComponent(email)}`,
    {
      headers: {
        'Authorization': `Bearer ${firebaseIdToken}`,
      },
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to retrieve tokens');
  }

  const data = await response.json();
  return {
    access_token: data.access_token,
    refresh_token: data.refresh_token,
    expires_in: data.expires_in || 3600,
    scope: data.scope || '',
    token_type: 'Bearer',
  };
}

/**
 * Check if user has OAuth tokens stored
 */
export async function checkTokenStatus(
  email: string,
  firebaseIdToken: string
): Promise<boolean> {
  try {
    const response = await fetch(
      `${TOKEN_SERVICE_URL}/api/tokens/status?email=${encodeURIComponent(email)}`,
      {
        headers: {
          'Authorization': `Bearer ${firebaseIdToken}`,
        },
      }
    );

    if (!response.ok) {
      return false;
    }

    const data = await response.json();
    return data.data?.has_tokens || false;
  } catch (error) {
    console.error('Error checking token status:', error);
    return false;
  }
}

// Type declarations for Google Identity Services
declare global {
  interface Window {
    google: {
      accounts: {
        oauth2: {
          initCodeClient: (config: any) => any;
        };
      };
    };
  }
}


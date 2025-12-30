"use client";

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { GOOGLE_SCOPES, storeTokensInFirestore, checkTokenStatus } from '@/lib/googleOAuth';

const TOKEN_SERVICE_URL = process.env.NEXT_PUBLIC_TOKEN_SERVICE_URL || 'http://localhost:8001';
const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || '';

export interface ClassroomAuthStatus {
  hasTokens: boolean;
  loading: boolean;
  error: string | null;
}

export function useClassroomAuth() {
  const { user } = useAuth();
  const [status, setStatus] = useState<ClassroomAuthStatus>({
    hasTokens: false,
    loading: true,
    error: null,
  });

  /**
   * Check if user has Google Classroom tokens stored
   */
  const checkStatus = useCallback(async () => {
    if (!user || !user.email) {
      setStatus({ hasTokens: false, loading: false, error: null });
      return;
    }

    try {
      const idToken = await user.getIdToken();
      const hasTokens = await checkTokenStatus(user.email, idToken);
      setStatus({ hasTokens, loading: false, error: null });
    } catch (error: any) {
      console.error('Error checking classroom auth status:', error);
      setStatus({ hasTokens: false, loading: false, error: error.message });
    }
  }, [user]);

  /**
   * Request Google Classroom authorization
   */
  const authorize = useCallback(async () => {
    if (!user || !user.email) {
      throw new Error('User must be logged in to authorize Classroom access');
    }

    if (!GOOGLE_CLIENT_ID) {
      throw new Error('Google Client ID not configured');
    }

    try {
      setStatus(prev => ({ ...prev, loading: true, error: null }));

      // Request authorization code using Google Identity Services
      const authCode = await requestAuthorizationCode();

      // Exchange code for tokens via backend
      const response = await fetch(`${TOKEN_SERVICE_URL}/api/oauth/exchange`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          code: authCode,
          redirect_uri: 'postmessage',
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to exchange authorization code');
      }

      const tokens = await response.json();

      // Store tokens in Firestore
      const idToken = await user.getIdToken();
      await storeTokensInFirestore(
        user.email,
        tokens.access_token,
        tokens.refresh_token,
        tokens.expires_in,
        tokens.scope,
        idToken
      );

      console.log('✅ Google Classroom tokens stored successfully');
      setStatus({ hasTokens: true, loading: false, error: null });
    } catch (error: any) {
      console.error('Error authorizing Classroom:', error);
      setStatus(prev => ({ ...prev, loading: false, error: error.message }));
      throw error;
    }
  }, [user]);

  /**
   * Request authorization code from Google
   */
  const requestAuthorizationCode = (): Promise<string> => {
    return new Promise((resolve, reject) => {
      if (typeof window === 'undefined' || !window.google) {
        reject(new Error('Google Identity Services not loaded'));
        return;
      }

      const client = window.google.accounts.oauth2.initCodeClient({
        client_id: GOOGLE_CLIENT_ID,
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
  };

  // Check status on mount and when user changes
  useEffect(() => {
    checkStatus();
  }, [checkStatus]);

  return {
    ...status,
    authorize,
    checkStatus,
  };
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


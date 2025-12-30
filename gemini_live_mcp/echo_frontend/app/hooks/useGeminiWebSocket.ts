"use client";

import { useEffect, useRef, useState, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';

export type ConnectionState = 'disconnected' | 'connecting' | 'connected' | 'error';

export interface WebSocketMessage {
  type: 'audio' | 'text' | 'turn_complete' | 'connected' | 'error' | 'pong' | 'text_chunk' | 'tool_start' | 'tool_end' | 'thought' | 'show_assignment_form' | 'show_course_form' | 'auth_success' | 'auth_error';
  data?: any;
  text?: string;
  thought?: string;
  mime_type?: string;
  tool?: string;
  args?: any;
  result?: any;
}

export interface UseGeminiWebSocketReturn {
  connectionState: ConnectionState;
  sendAudio: (audioData: string, turnComplete?: boolean) => void;
  sendText: (text: string, threadId?: string) => void;
  lastMessage: WebSocketMessage | null;
  connect: () => void;
  disconnect: () => void;
}

const WEBSOCKET_BASE_URL = 'ws://localhost:8000';
const RECONNECT_DELAY = 3000;

export function useGeminiWebSocket(
  endpoint: string,
  onMessage?: (message: WebSocketMessage) => void
): UseGeminiWebSocketReturn {
  const { user } = useAuth();
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const shouldReconnectRef = useRef(true);
  const onMessageRef = useRef(onMessage);
  const isConnectingRef = useRef(false);

  // Update the ref when onMessage changes
  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  const connect = useCallback(() => {
    shouldReconnectRef.current = true;

    // Prevent duplicate connections
    if (wsRef.current?.readyState === WebSocket.OPEN || isConnectingRef.current) {
      return;
    }

    isConnectingRef.current = true;
    setConnectionState('connecting');
    
    try {
      const ws = new WebSocket(`${WEBSOCKET_BASE_URL}${endpoint}`);
      
      ws.onopen = async () => {
        console.log(`✅ Connected to backend ${endpoint}`);
        setConnectionState('connected');
        isConnectingRef.current = false;
        
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = null;
        }
        
        // Send authentication message for chat endpoint
        if (endpoint === '/ws/chat' && user) {
          try {
            const idToken = await user.getIdToken();
            const authMessage = {
              type: 'auth',
              user_email: user.email,
              firebase_token: idToken
            };
            ws.send(JSON.stringify(authMessage));
            console.log(`🔐 Sent auth credentials for ${user.email}`);
          } catch (error) {
            console.error('Failed to send auth credentials:', error);
          }
        }
      };
      
      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          setLastMessage(message);
          
          // Use the ref to get the latest onMessage callback
          if (onMessageRef.current) {
            onMessageRef.current(message);
          }
        } catch (error) {
          console.error('Error parsing message:', error);
        }
      };
      
      ws.onerror = (error) => {
        // WebSocket errors are typically non-descriptive in the browser
        // The actual error details will come in the onclose event
        console.error('WebSocket error occurred');
        setConnectionState('error');
        isConnectingRef.current = false;
      };
      
      ws.onclose = (event) => {
        const reason = event.code === 1000 ? 'Normal closure' : 
                      event.code === 1001 ? 'Going away' :
                      event.code === 1006 ? 'Connection closed abnormally' :
                      `Close code: ${event.code}`;
        console.log(`❌ Disconnected from backend ${endpoint} (${reason})`);
        setConnectionState('disconnected');
        wsRef.current = null;
        isConnectingRef.current = false;
        
        // Only auto-reconnect if not a normal closure and reconnect is enabled
        if (shouldReconnectRef.current && event.code !== 1000) {
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log('🔄 Attempting to reconnect...');
            connect();
          }, RECONNECT_DELAY);
        }
      };
      
      wsRef.current = ws;
    } catch (error) {
      console.error('Error creating WebSocket:', error);
      setConnectionState('error');
      isConnectingRef.current = false;
    }
  }, [endpoint]);

  const disconnect = useCallback(() => {
    shouldReconnectRef.current = false;
    
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    setConnectionState('disconnected');
  }, []);

  const sendAudio = useCallback((audioData: string, turnComplete: boolean = false) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'audio',
        data: audioData,
        turn_complete: turnComplete
      }));
    } else {
      console.warn('WebSocket not connected, cannot send audio');
    }
  }, []);

  const sendText = useCallback((text: string, threadId: string = 'default') => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'text',
        text: text,
        thread_id: threadId
      }));
    } else {
      console.warn('WebSocket not connected, cannot send text');
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      shouldReconnectRef.current = false;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return {
    connectionState,
    sendAudio,
    sendText,
    lastMessage,
    connect,
    disconnect
  };
}

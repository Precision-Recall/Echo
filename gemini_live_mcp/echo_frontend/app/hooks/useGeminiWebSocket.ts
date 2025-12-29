"use client";

import { useEffect, useRef, useState, useCallback } from 'react';

export type ConnectionState = 'disconnected' | 'connecting' | 'connected' | 'error';

export interface WebSocketMessage {
  type: 'audio' | 'text' | 'turn_complete' | 'connected' | 'error' | 'pong' | 'text_chunk' | 'tool_start' | 'tool_end';
  data?: string;
  text?: string;
  mime_type?: string;
  tool?: string;
  args?: any;
  result?: any;
}

export interface UseGeminiWebSocketReturn {
  connectionState: ConnectionState;
  sendAudio: (audioData: string, turnComplete?: boolean) => void;
  sendText: (text: string) => void;
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
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const shouldReconnectRef = useRef(true);

  const connect = useCallback(() => {
    shouldReconnectRef.current = true;

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setConnectionState('connecting');
    
    try {
      const ws = new WebSocket(`${WEBSOCKET_BASE_URL}${endpoint}`);
      
      ws.onopen = () => {
        console.log(`✅ Connected to backend ${endpoint}`);
        setConnectionState('connected');
        
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = null;
        }
      };
      
      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          setLastMessage(message);
          
          if (onMessage) {
            onMessage(message);
          }
        } catch (error) {
          console.error('Error parsing message:', error);
        }
      };
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnectionState('error');
      };
      
      ws.onclose = () => {
        console.log(`❌ Disconnected from backend ${endpoint}`);
        setConnectionState('disconnected');
        wsRef.current = null;
        
        if (shouldReconnectRef.current) {
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
    }
  }, [endpoint, onMessage]);

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

  const sendText = useCallback((text: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'text',
        text: text
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

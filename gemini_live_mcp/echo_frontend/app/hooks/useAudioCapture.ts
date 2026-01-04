"use client";

import { useRef, useState, useCallback, useEffect } from 'react';

export interface UseAudioCaptureReturn {
  isRecording: boolean;
  startRecording: () => Promise<void>;
  stopRecording: () => void;
  error: string | null;
}

const SAMPLE_RATE = 16000;

export function useAudioCapture(
  onAudioData: (audioData: string, turnComplete?: boolean) => void
): UseAudioCaptureReturn {
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const workletNodeRef = useRef<AudioWorkletNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const isContextReadyRef = useRef(false);

  // Initialize context once
  const initContext = useCallback(async () => {
    if (audioContextRef.current && isContextReadyRef.current) return;

    try {
      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      const ctx = new AudioContextClass({ sampleRate: SAMPLE_RATE });
      audioContextRef.current = ctx;
      
      await ctx.audioWorklet.addModule('/pcm-processor.js');
      isContextReadyRef.current = true;
    } catch (err) {
      console.error('Failed to initialize AudioContext:', err);
      throw err;
    }
  }, []);

  const startRecording = useCallback(async () => {
    try {
      setError(null);
      
      // Ensure context is ready
      await initContext();
      const ctx = audioContextRef.current;
      if (!ctx) throw new Error('AudioContext not initialized');

      if (ctx.state === 'suspended') {
        await ctx.resume();
      }

      // Request microphone
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });
      
      mediaStreamRef.current = stream;
      
      const source = ctx.createMediaStreamSource(stream);
      sourceRef.current = source;
      
      const workletNode = new AudioWorkletNode(ctx, 'pcm-processor');
      workletNodeRef.current = workletNode;
      
      workletNode.port.onmessage = (event) => {
        const int16Data = event.data;
        const base64 = arrayBufferToBase64(int16Data.buffer);
        onAudioData(base64);
      };
      
      source.connect(workletNode);
      workletNode.connect(ctx.destination);
      
      setIsRecording(true);
      console.log(`🎤 Recording started at ${ctx.sampleRate}Hz`);
      
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to access microphone';
      setError(errorMessage);
      console.error('Error starting recording:', err);
    }
  }, [onAudioData, initContext]);

  const stopRecording = useCallback(() => {
    setIsRecording(false);
    
    // Disconnect nodes but keep context alive
    if (workletNodeRef.current) {
      workletNodeRef.current.disconnect();
      workletNodeRef.current = null;
    }
    
    if (sourceRef.current) {
      sourceRef.current.disconnect();
      sourceRef.current = null;
    }
    
    // Stop tracks
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => track.stop());
      mediaStreamRef.current = null;
    }
    
    // Don't close context, just let it be (or suspend if needed)
    // Suspending saves battery
    if (audioContextRef.current && audioContextRef.current.state === 'running') {
      audioContextRef.current.suspend();
    }
    
    console.log('🎤 Recording stopped');
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, []);

  return {
    isRecording,
    startRecording,
    stopRecording,
    error
  };
}

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

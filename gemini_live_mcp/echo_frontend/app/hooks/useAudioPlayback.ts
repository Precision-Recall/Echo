"use client";

import { useRef, useState, useCallback, useEffect } from 'react';

export interface UseAudioPlaybackReturn {
  isPlaying: boolean;
  playAudio: (base64Audio: string) => Promise<void>;
  stopAudio: () => void;
  error: string | null;
}

const SAMPLE_RATE = 24000; // Gemini outputs at 24kHz

export function useAudioPlayback(): UseAudioPlaybackReturn {
  const [isPlaying, setIsPlaying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const audioContextRef = useRef<AudioContext | null>(null);
  const nextStartTimeRef = useRef<number>(0);
  const activeSourcesRef = useRef<AudioBufferSourceNode[]>([]);
  const isPlayingRef = useRef(false);

  // Initialize audio context
  useEffect(() => {
    // Check for window.AudioContext or webkitAudioContext
    const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
    audioContextRef.current = new AudioContextClass({
      sampleRate: SAMPLE_RATE
    });
    
    return () => {
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, []);

  const playAudio = useCallback(async (base64Audio: string) => {
    try {
      setError(null);
      
      if (!audioContextRef.current) {
        throw new Error('Audio context not initialized');
      }

      // Resume context if suspended (browser autoplay policy)
      if (audioContextRef.current.state === 'suspended') {
        await audioContextRef.current.resume();
      }
      
      // Decode base64 to ArrayBuffer
      const binaryString = atob(base64Audio);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }
      
      // Convert PCM Int16 to Float32
      const pcmData = new Int16Array(bytes.buffer);
      const floatData = new Float32Array(pcmData.length);
      let maxAmp = 0;
      for (let i = 0; i < pcmData.length; i++) {
        // Normalize to [-1.0, 1.0]
        floatData[i] = pcmData[i] / 32768.0;
        if (Math.abs(floatData[i]) > maxAmp) maxAmp = Math.abs(floatData[i]);
      }
      
      if (maxAmp > 0.01) {
        console.log(`🔊 Playing chunk: ${floatData.length} samples, Peak: ${maxAmp.toFixed(3)}`);
      } else {
        console.warn('⚠️ Playing silent/quiet chunk');
      }
      
      // Create audio buffer
      const audioBuffer = audioContextRef.current.createBuffer(
        1, // mono
        floatData.length,
        SAMPLE_RATE
      );
      
      audioBuffer.getChannelData(0).set(floatData);
      
      // Schedule playback
      const source = audioContextRef.current.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(audioContextRef.current.destination);
      
      // Calculate start time
      // If nextStartTime is in the past (gap in speech), reset to currentTime
      const currentTime = audioContextRef.current.currentTime;
      if (nextStartTimeRef.current < currentTime) {
        nextStartTimeRef.current = currentTime;
      }
      
      source.start(nextStartTimeRef.current);
      
      // Update next start time
      nextStartTimeRef.current += audioBuffer.duration;
      
      // Track source
      activeSourcesRef.current.push(source);
      
      // Update state
      if (!isPlayingRef.current) {
        isPlayingRef.current = true;
        setIsPlaying(true);
      }
      
      // Cleanup when done
      source.onended = () => {
        activeSourcesRef.current = activeSourcesRef.current.filter(s => s !== source);
        if (activeSourcesRef.current.length === 0) {
          isPlayingRef.current = false;
          setIsPlaying(false);
        }
      };
      
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to play audio';
      setError(errorMessage);
      console.error('Error playing audio:', err);
    }
  }, []);

  const stopAudio = useCallback(() => {
    // Stop all active sources
    activeSourcesRef.current.forEach(source => {
      try {
        source.stop();
        source.disconnect();
      } catch (err) {
        // Ignore errors
      }
    });
    
    activeSourcesRef.current = [];
    nextStartTimeRef.current = 0;
    isPlayingRef.current = false;
    setIsPlaying(false);
    
    console.log('🔇 Audio stopped');
  }, []);

  return {
    isPlaying,
    playAudio,
    stopAudio,
    error
  };
}

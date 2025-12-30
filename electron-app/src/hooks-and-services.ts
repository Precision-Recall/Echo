// src/hooks/useAudioManager.ts
import { useCallback } from 'react';

export const useAudioManager = () => {
  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const audioContext = new AudioContext();
      const mediaStream = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(4096, 1, 1);

      processor.onaudioprocess = (event) => {
        const audioData = event.inputBuffer.getChannelData(0);
        window.ipcRenderer?.send('audio-chunk', audioData);
      };

      mediaStream.connect(processor);
      processor.connect(audioContext.destination);
    } catch (error) {
      console.error('Microphone access denied:', error);
    }
  }, []);

  const stopRecording = useCallback(() => {
    window.ipcRenderer?.send('stop-recording');
  }, []);

  const playAudio = useCallback(async (audioData?: ArrayBuffer) => {
    if (!audioData) {
      // Audio playback triggered but no data provided - may be handled elsewhere
      return;
    }
    try {
      const audioContext = new AudioContext();
      const buffer = await audioContext.decodeAudioData(audioData);
      const source = audioContext.createBufferSource();
      source.buffer = buffer;
      source.connect(audioContext.destination);
      source.start(0);
    } catch (error) {
      console.error('Playback error:', error);
    }
  }, []);

  return { startRecording, stopRecording, playAudio };
};
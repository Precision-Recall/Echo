import { ipcRenderer } from 'electron';

export class BackendService {
  private pythonProcess: any;

  startSession() {
    ipcRenderer.send('start-recording');
  }

  stopSession() {
    ipcRenderer.send('stop-recording');
  }

  sendAudioChunk(chunk: ArrayBuffer) {
    ipcRenderer.send('send-audio-chunk', chunk);
  }

  setHotkey(hotkey: string) {
    ipcRenderer.send('set-hotkey', hotkey);
  }

  toggleTranscription(enabled: boolean) {
    ipcRenderer.send('toggle-transcription', enabled);
  }

  toggleReasoning(enabled: boolean) {
    ipcRenderer.send('toggle-reasoning', enabled);
  }

  // Listen for backend messages
  onPythonLog(callback: (message: string) => void) {
    ipcRenderer.on('python-log', (_, message) => callback(message));
  }

  onPythonError(callback: (error: string) => void) {
    ipcRenderer.on('python-error', (_, error) => callback(error));
  }

  onPTTStart(callback: () => void) {
    ipcRenderer.on('ptt-start', callback);
  }

  onPTTEnd(callback: (duration: number) => void) {
    ipcRenderer.on('ptt-end', (_, data) => callback(data.duration));
  }

  cleanup() {
    ipcRenderer.removeAllListeners('python-log');
    ipcRenderer.removeAllListeners('python-error');
    ipcRenderer.removeAllListeners('ptt-start');
    ipcRenderer.removeAllListeners('ptt-end');
  }
}

export const backendService = new BackendService();


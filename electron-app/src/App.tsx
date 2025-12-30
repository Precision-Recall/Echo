import React, { useState, useEffect } from 'react';
import './App.css';
import BottomBar from './BottomBar';
import ChainOfThought from './ChainOfThought';
import { useAudioManager } from './hooks-and-services';

type AppState = 'idle' | 'listening' | 'processing' | 'speaking' | 'error';

interface ThinkingStep {
  id: string;
  type: 'thought' | 'tool' | 'result' | 'error';
  content: string;
  timestamp: number;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  timestamp: number;
}

// Use ipcRenderer exposed by preload.js via contextBridge
const getIpcRenderer = () => {
  if (typeof window !== 'undefined' && window.ipcRenderer) {
    return window.ipcRenderer;
  }
  return null;
};

const App: React.FC = () => {
  const [expanded, setExpanded] = useState(false);
  const [state, setState] = useState<AppState>('idle');
  const [messages, setMessages] = useState<Message[]>([]);
  const [thinkingSteps, setThinkingSteps] = useState<ThinkingStep[]>([]);
  const [currentTranscription, setCurrentTranscription] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [settings] = useState({
    hotkey: 'Alt+Space',
    releaseDelay: 100,
    voiceActivityDetection: true,
    transcriptionEnabled: true
  });

  const { startRecording, stopRecording, playAudio } = useAudioManager();
  const ipcRenderer = getIpcRenderer();

  // Listen for IPC events
  useEffect(() => {
    if (!ipcRenderer) return;

    const handlePTTStart = () => {
      setIsRecording(true);
      setState('listening');
      startRecording();
      ipcRenderer.send('start-recording');
      addThinkingStep('thought', '🎤 Listening...');
    };

    const handlePTTEnd = (_event: any, data: { duration: number }) => {
      setIsRecording(false);
      stopRecording();
      ipcRenderer.send('stop-recording');
      setState('processing');
      addThinkingStep('thought', '⏳ Processing audio...');
    };

    const handlePythonLog = (_event: any, message: string) => {
      console.log('[Backend]', message);
      handleBackendMessage(message);
    };

    ipcRenderer.on('ptt-start', handlePTTStart);
    ipcRenderer.on('ptt-end', handlePTTEnd);
    ipcRenderer.on('python-log', handlePythonLog);

    return () => {
      ipcRenderer.removeAllListeners('ptt-start');
      ipcRenderer.removeAllListeners('ptt-end');
      ipcRenderer.removeAllListeners('python-log');
    };
  }, [ipcRenderer, startRecording, stopRecording]);

  const addThinkingStep = (type: ThinkingStep['type'], content: string) => {
    const step: ThinkingStep = {
      id: `step-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      type,
      content,
      timestamp: Date.now()
    };
    setThinkingSteps(prev => [...prev, step]);
  };

  const handleBackendMessage = (message: string) => {
    // User transcription
    if (message.includes('🎤 You:') || message.includes('[USER]')) {
      const text = message.replace('🎤 You:', '').replace('[USER]', '').trim();
      setCurrentTranscription(text);
      if (text) {
        addMessage('user', text);
        addThinkingStep('thought', `📝 You said: "${text}"`);
      }
    }
    // Assistant response
    else if (message.includes('📝 Echo:') || message.includes('[ECHO]')) {
      const text = message.replace('📝 Echo:', '').replace('[ECHO]', '').trim();
      setState('speaking');
      addMessage('assistant', text);
      addThinkingStep('result', `🗣️ ${text}`);
      playAudio();
    }
    // Tool call
    else if (message.includes('🔧 Tool:') || message.includes('[TOOL]')) {
      const toolName = message.replace('🔧 Tool:', '').replace('[TOOL]', '').trim();
      addThinkingStep('tool', `🔧 Calling: ${toolName}`);
    }
    // Tool result
    else if (message.includes('[RESULT]') || message.includes('📊 Result:')) {
      const result = message.replace('[RESULT]', '').replace('📊 Result:', '').trim();
      addThinkingStep('result', `✅ ${result.substring(0, 100)}...`);
    }
    // Turn complete
    else if (message.includes('✅ Turn complete') || message.includes('[COMPLETE]')) {
      setState('idle');
      setCurrentTranscription('');
      addThinkingStep('thought', '✅ Turn complete');
    }
    // Error
    else if (message.includes('ERROR') || message.includes('❌') || message.includes('[ERROR]')) {
      setState('error');
      addThinkingStep('error', message);
      setTimeout(() => setState('idle'), 3000);
    }
  };

  const addMessage = (role: 'user' | 'assistant', text: string) => {
    const newMessage: Message = {
      id: `msg-${Date.now()}`,
      role,
      text,
      timestamp: Date.now()
    };
    setMessages(prev => [...prev, newMessage]);
  };

  const handleToggleExpand = () => {
    setExpanded(!expanded);
    // Resize window
    if (ipcRenderer) {
      ipcRenderer.send('resize-window', expanded
        ? { width: 500, height: 80 }
        : { width: 500, height: 500 }
      );
    }
  };

  return (
    <div className="app" data-expanded={expanded}>
      {/* Chain of Thought Panel (when expanded) */}
      {expanded && (
        <ChainOfThought
          steps={thinkingSteps}
          messages={messages}
          currentTranscription={currentTranscription}
        />
      )}

      {/* Bottom Bar */}
      <BottomBar
        state={state}
        hotkey={settings.hotkey}
        expanded={expanded}
        onToggleExpand={handleToggleExpand}
      />
    </div>
  );
};

export default App;
import React, { useState, useRef, useEffect } from 'react';
import './ExpandedView.css';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  timestamp: number;
}

interface ToolStep {
  id: string;
  name: string;
  status: 'pending' | 'executing' | 'completed' | 'error';
  result?: string;
  timestamp: number;
}

interface ExpandedViewProps {
  messages: Message[];
  state: 'idle' | 'listening' | 'processing' | 'speaking' | 'error';
  toolSteps: ToolStep[];
  isRecording: boolean;
  currentTranscription: string;
  hotkey: string;
  settings: {
    hotkey: string;
    releaseDelay: number;
    voiceActivityDetection: boolean;
    transcriptionEnabled: boolean;
  };
  onModeToggle: () => void;
  onSettingsChange: (key: string, value: any) => void;
}

const ExpandedView: React.FC<ExpandedViewProps> = ({
  messages,
  state,
  toolSteps,
  isRecording,
  currentTranscription,
  hotkey,
  settings,
  onModeToggle,
  onSettingsChange
}) => {
  const [showSettings, setShowSettings] = useState(false);
  const [waveformBars, setWaveformBars] = useState<number[]>(Array(32).fill(0.1));
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Waveform animation
  useEffect(() => {
    let interval: NodeJS.Timeout;

    if (state === 'listening' || state === 'speaking') {
      interval = setInterval(() => {
        setWaveformBars(Array(32).fill(0).map(() => 0.2 + Math.random() * 0.8));
      }, 70);
    } else {
      setWaveformBars(Array(32).fill(0.1));
    }

    return () => clearInterval(interval);
  }, [state]);

  const stateColors: Record<string, string> = {
    idle: '#7C3AED',
    listening: '#10B981',
    processing: '#F59E0B',
    speaking: '#3B82F6',
    error: '#EF4444'
  };

  return (
    <div className="expanded-container">
      {/* Header */}
      <header className="ev-header">
        <div className="ev-header-left">
          <div
            className="ev-status-dot"
            style={{ backgroundColor: stateColors[state] }}
          />
        </div>
        <button
          className="ev-settings-btn"
          onClick={() => setShowSettings(!showSettings)}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="3" />
            <path d="M12 1v4M12 19v4M4.2 4.2l2.8 2.8M17 17l2.8 2.8M1 12h4M19 12h4M4.2 19.8l2.8-2.8M17 7l2.8-2.8" />
          </svg>
        </button>
      </header>

      {/* Chat Messages */}
      <div className="ev-chat">
        {messages.length === 0 ? (
          <div className="ev-empty">
            <div className="ev-empty-icon">🎙️</div>
            <p>Hold <strong>{hotkey.toUpperCase()}</strong> to start</p>
          </div>
        ) : (
          messages.map(msg => (
            <div key={msg.id} className={`ev-message ev-message-${msg.role}`}>
              <div className="ev-bubble">{msg.text}</div>
            </div>
          ))
        )}

        {/* Live Waveform */}
        {(state === 'listening' || state === 'speaking') && (
          <div className="ev-waveform">
            {waveformBars.map((h, i) => (
              <div
                key={i}
                className="ev-wave-bar"
                style={{
                  height: `${h * 100}%`,
                  backgroundColor: stateColors[state]
                }}
              />
            ))}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* PTT Button Section */}
      <div className="ev-ptt-section">
        <button
          className={`ev-ptt-btn ${state}`}
          style={{
            borderColor: stateColors[state],
            boxShadow: state === 'listening' ? `0 0 30px ${stateColors[state]}40` : 'none'
          }}
        >
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
            <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
            <line x1="12" y1="19" x2="12" y2="23" />
            <line x1="8" y1="23" x2="16" y2="23" />
          </svg>
        </button>
        <span className="ev-ptt-label">Hold {hotkey.toUpperCase()}</span>
      </div>

      {/* Settings Panel */}
      {showSettings && (
        <div className="ev-settings-overlay" onClick={() => setShowSettings(false)}>
          <div className="ev-settings-panel" onClick={e => e.stopPropagation()}>
            <h2>Settings</h2>

            <div className="ev-setting">
              <label>Hotkey</label>
              <input
                type="text"
                className="ev-input"
                value={settings.hotkey}
                onChange={e => onSettingsChange('hotkey', e.target.value)}
                placeholder="Keyboard recorder"
              />
            </div>

            <div className="ev-setting">
              <label>Audio Input</label>
              <select className="ev-select">
                <option>Default</option>
              </select>
            </div>

            <div className="ev-setting">
              <label>Audio Output</label>
              <select className="ev-select">
                <option>Default</option>
              </select>
            </div>

            <div className="ev-setting">
              <label>Release Delay</label>
              <div className="ev-slider-row">
                <input
                  type="range"
                  min="20"
                  max="200"
                  value={settings.releaseDelay}
                  onChange={e => onSettingsChange('releaseDelay', parseInt(e.target.value))}
                  className="ev-slider"
                />
                <span className="ev-slider-val">{settings.releaseDelay}ms</span>
              </div>
            </div>

            <div className="ev-setting ev-toggle-row">
              <label>Voice Activity Detection</label>
              <label className="ev-toggle">
                <input
                  type="checkbox"
                  checked={settings.voiceActivityDetection}
                  onChange={e => onSettingsChange('voiceActivityDetection', e.target.checked)}
                />
                <span className="ev-toggle-slider"></span>
              </label>
            </div>

            <div className="ev-setting ev-toggle-row">
              <label>Transcription</label>
              <label className="ev-toggle">
                <input
                  type="checkbox"
                  checked={settings.transcriptionEnabled}
                  onChange={e => onSettingsChange('transcriptionEnabled', e.target.checked)}
                />
                <span className="ev-toggle-slider"></span>
              </label>
            </div>
          </div>
        </div>
      )}

      {/* Minimize */}
      <button className="ev-minimize" onClick={onModeToggle}>−</button>
    </div>
  );
};

export default ExpandedView;

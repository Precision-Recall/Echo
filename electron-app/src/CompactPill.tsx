import React, { useState, useEffect } from 'react';
import './CompactPill.css';

type AppState = 'idle' | 'listening' | 'processing' | 'speaking' | 'error';

interface CompactPillProps {
  state: AppState;
  currentTranscription: string;
  hotkey: string;
  onModeToggle: () => void;
  onRecordingStateChange: (isRecording: boolean) => void;
}

const CompactPill: React.FC<CompactPillProps> = ({
  state,
  currentTranscription,
  hotkey,
  onModeToggle,
  onRecordingStateChange
}) => {
  const [waveformBars, setWaveformBars] = useState<number[]>(Array(16).fill(0.2));

  // Animate waveform based on state
  useEffect(() => {
    let interval: NodeJS.Timeout;

    if (state === 'listening') {
      interval = setInterval(() => {
        setWaveformBars(Array(16).fill(0).map(() => 0.3 + Math.random() * 0.7));
      }, 60);
    } else if (state === 'speaking') {
      interval = setInterval(() => {
        setWaveformBars(Array(16).fill(0).map(() => 0.2 + Math.random() * 0.6));
      }, 80);
    } else if (state === 'processing') {
      // Pulsing dots effect
      interval = setInterval(() => {
        setWaveformBars(prev => {
          const newBars = [...prev];
          newBars.forEach((_, i) => {
            newBars[i] = 0.15 + Math.sin(Date.now() / 150 + i * 0.4) * 0.15;
          });
          return newBars;
        });
      }, 50);
    } else {
      // Idle - minimal bars
      setWaveformBars(Array(16).fill(0.15));
    }

    return () => clearInterval(interval);
  }, [state]);

  // State color configurations
  const stateConfig = {
    idle: {
      orb: '#7C3AED',
      glow: 'rgba(124, 58, 237, 0.5)',
      wave: '#7C3AED'
    },
    listening: {
      orb: '#10B981',
      glow: 'rgba(16, 185, 129, 0.6)',
      wave: '#10B981'
    },
    processing: {
      orb: '#F59E0B',
      glow: 'rgba(245, 158, 11, 0.5)',
      wave: '#F59E0B'
    },
    speaking: {
      orb: '#3B82F6',
      glow: 'rgba(59, 130, 246, 0.5)',
      wave: '#3B82F6'
    },
    error: {
      orb: '#EF4444',
      glow: 'rgba(239, 68, 68, 0.6)',
      wave: '#EF4444'
    }
  };

  const colors = stateConfig[state];

  return (
    <div className="compact-pill" onClick={onModeToggle}>
      {/* Status Orb */}
      <div
        className={`orb orb-${state}`}
        style={{
          background: colors.orb,
          boxShadow: `0 0 16px ${colors.glow}, 0 0 32px ${colors.glow}`
        }}
      >
        {state === 'processing' && (
          <div className="processing-spinner" />
        )}
        {state === 'error' && (
          <span className="error-icon">!</span>
        )}
      </div>

      {/* Waveform Visualizer */}
      <div className="waveform">
        {waveformBars.map((h, i) => (
          <div
            key={i}
            className="wave-bar"
            style={{
              height: `${h * 100}%`,
              backgroundColor: colors.wave,
              opacity: 0.5 + h * 0.5
            }}
          />
        ))}
      </div>

      {/* Hotkey Badge */}
      <div className="hotkey-badge">
        {hotkey.toUpperCase()}
      </div>
    </div>
  );
};

export default CompactPill;
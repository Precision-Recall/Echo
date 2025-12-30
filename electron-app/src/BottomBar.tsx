import React, { useState, useEffect } from 'react';
import './BottomBar.css';

type AppState = 'idle' | 'listening' | 'processing' | 'speaking' | 'error';

interface BottomBarProps {
    state: AppState;
    hotkey: string;
    expanded: boolean;
    onToggleExpand: () => void;
}

const BottomBar: React.FC<BottomBarProps> = ({
    state,
    hotkey,
    expanded,
    onToggleExpand
}) => {
    const [waveformBars, setWaveformBars] = useState<number[]>(Array(20).fill(0.15));

    // Animate waveform
    useEffect(() => {
        let interval: NodeJS.Timeout;

        if (state === 'listening') {
            interval = setInterval(() => {
                setWaveformBars(Array(20).fill(0).map(() => 0.3 + Math.random() * 0.7));
            }, 60);
        } else if (state === 'speaking') {
            interval = setInterval(() => {
                setWaveformBars(Array(20).fill(0).map(() => 0.2 + Math.random() * 0.5));
            }, 80);
        } else if (state === 'processing') {
            interval = setInterval(() => {
                setWaveformBars(prev => prev.map((_, i) =>
                    0.15 + Math.sin(Date.now() / 150 + i * 0.4) * 0.15
                ));
            }, 50);
        } else {
            setWaveformBars(Array(20).fill(0.15));
        }

        return () => clearInterval(interval);
    }, [state]);

    const stateConfig = {
        idle: { orb: '#7C3AED', glow: 'rgba(124, 58, 237, 0.5)', wave: '#7C3AED' },
        listening: { orb: '#10B981', glow: 'rgba(16, 185, 129, 0.6)', wave: '#10B981' },
        processing: { orb: '#F59E0B', glow: 'rgba(245, 158, 11, 0.5)', wave: '#F59E0B' },
        speaking: { orb: '#3B82F6', glow: 'rgba(59, 130, 246, 0.5)', wave: '#3B82F6' },
        error: { orb: '#EF4444', glow: 'rgba(239, 68, 68, 0.6)', wave: '#EF4444' }
    };

    const colors = stateConfig[state];

    return (
        <div className="bottom-bar">
            {/* Status Orb */}
            <div
                className={`bb-orb bb-orb-${state}`}
                style={{
                    background: colors.orb,
                    boxShadow: `0 0 16px ${colors.glow}, 0 0 32px ${colors.glow}`
                }}
            >
                {state === 'processing' && <div className="bb-spinner" />}
                {state === 'error' && <span className="bb-error">!</span>}
            </div>

            {/* Waveform */}
            <div className="bb-waveform">
                {waveformBars.map((h, i) => (
                    <div
                        key={i}
                        className="bb-wave-bar"
                        style={{
                            height: `${h * 100}%`,
                            backgroundColor: colors.wave,
                            opacity: 0.5 + h * 0.5
                        }}
                    />
                ))}
            </div>

            {/* Hotkey Badge */}
            <div className="bb-hotkey">{hotkey.toUpperCase()}</div>

            {/* Expand/Collapse Button */}
            <button
                className={`bb-expand ${expanded ? 'bb-expanded' : ''}`}
                onClick={onToggleExpand}
                title={expanded ? 'Collapse' : 'Show chain of thought'}
            >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points={expanded ? "18 15 12 9 6 15" : "6 9 12 15 18 9"} />
                </svg>
            </button>
        </div>
    );
};

export default BottomBar;

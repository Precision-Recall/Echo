// ECHO Voice Assistant - Renderer Script

// State
let state = 'idle'; // idle, connecting, listening, processing, speaking, error
let expanded = false;
let mode = 'fast';
let waveformBars = [];

// DOM Elements
const app = document.getElementById('app');
const statusOrb = document.getElementById('statusOrb');
const waveform = document.getElementById('waveform');
const expandBtn = document.getElementById('expandBtn');
const expandIcon = document.getElementById('expandIcon');
const modeBtn = document.getElementById('modeBtn');
const cotPanel = document.getElementById('cotPanel');
const cotStatus = document.getElementById('cotStatus');
const mainContent = document.getElementById('mainContent'); // Left panel
const logContent = document.getElementById('logContent');   // Right panel

// Initialize waveform bars
function initWaveform() {
    for (let i = 0; i < 20; i++) {
        const bar = document.createElement('div');
        bar.className = 'wave-bar';
        bar.style.height = '15%';
        waveform.appendChild(bar);
        waveformBars.push(bar);
    }
}

// Update waveform animation
let waveformInterval = null;

function animateWaveform() {
    if (waveformInterval) clearInterval(waveformInterval);

    if (state === 'listening') {
        waveformInterval = setInterval(() => {
            waveformBars.forEach(bar => {
                const height = 30 + Math.random() * 70;
                bar.style.height = `${height}%`;
                bar.style.background = '#10B981';
            });
        }, 60);
    } else if (state === 'speaking') {
        waveformInterval = setInterval(() => {
            waveformBars.forEach(bar => {
                const height = 20 + Math.random() * 50;
                bar.style.height = `${height}%`;
                bar.style.background = '#3B82F6';
            });
        }, 80);
    } else if (state === 'processing') {
        waveformInterval = setInterval(() => {
            waveformBars.forEach((bar, i) => {
                const height = 15 + Math.sin(Date.now() / 150 + i * 0.4) * 15;
                bar.style.height = `${height}%`;
                bar.style.background = '#F59E0B';
            });
        }, 50);
    } else if (state === 'connecting') {
        // Connecting state - slow pulsing orange
        waveformInterval = setInterval(() => {
            waveformBars.forEach((bar, i) => {
                const height = 10 + Math.sin(Date.now() / 300 + i * 0.2) * 10;
                bar.style.height = `${height}%`;
                bar.style.background = '#F59E0B';
                bar.style.opacity = '0.6';
            });
        }, 100);
    } else {
        // Idle state
        waveformBars.forEach(bar => {
            bar.style.height = '15%';
            bar.style.background = '#7C3AED';
            bar.style.opacity = '1';
        });
    }
}

// Update state
function setState(newState) {
    state = newState;

    // Update orb class
    statusOrb.className = 'orb';
    if (newState !== 'idle') {
        statusOrb.classList.add(newState);
    }

    // Update status text
    cotStatus.className = 'cot-status';
    if (newState !== 'idle') {
        cotStatus.classList.add(newState);
    }

    const statusTexts = {
        idle: 'Idle',
        connecting: 'Connecting...',
        listening: 'Listening...',
        processing: 'Processing...',
        speaking: 'Speaking...',
        error: 'Error'
    };
    cotStatus.textContent = statusTexts[newState] || 'Idle';

    // Animate waveform
    animateWaveform();
}

// Add log entry to specific container
function addLog(message, type = 'thought', target = 'main') {
    const container = target === 'log' ? logContent : mainContent;

    // Check if user is near bottom BEFORE adding new content
    const threshold = 50;
    const isAtBottom = container.scrollHeight - container.scrollTop - container.clientHeight < threshold;

    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    entry.textContent = message;

    container.appendChild(entry);

    // Auto-scroll only if user was already at/near bottom
    if (isAtBottom) {
        container.scrollTo({
            top: container.scrollHeight,
            behavior: 'smooth'
        });
    }
}

// Toggle mode
function toggleMode() {
    mode = mode === 'fast' ? 'reasoning' : 'fast';
    modeBtn.textContent = mode === 'fast' ? '⚡' : '🧠';
    modeBtn.classList.toggle('mode-reasoning', mode === 'reasoning');
    modeBtn.title = mode === 'fast' ? 'Fast Mode (Flash)' : 'Reasoning Mode (Multi-Agent)';

    if (window.electronAPI) {
        window.electronAPI.setMode(mode);
        addLog(`Switched to ${mode === 'fast' ? 'Fast' : 'Reasoning'} Mode`, 'thought', 'main');
    }
}

// Toggle expand/collapse
function toggleExpand() {
    expanded = !expanded;
    app.dataset.expanded = expanded;
    expandBtn.classList.toggle('expanded', expanded);
    expandIcon.setAttribute('points', expanded ? '18 15 12 9 6 15' : '6 9 12 15 18 9');

    // Resize window
    const size = expanded
        ? { width: 500, height: 500 }
        : { width: 500, height: 80 };

    if (window.electronAPI) {
        window.electronAPI.resizeWindow(size);
    }
}

// Parse Python log messages
function handlePythonMessage(rawMessage) {
    // Strip emojis for cleaner UI (unicode ranges for emojis)
    const message = rawMessage.replace(/[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F1E0}-\u{1F1FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}\u{1F900}-\u{1F9FF}\u{1F018}-\u{1F270}]/gu, '').trim();

    // User transcription
    if (rawMessage.includes('You:') || rawMessage.includes('[USER]')) { // Check raw for keywords
        const text = message.replace('You:', '').replace('[USER]', '').trim();
        if (text) {
            addLog(`You: ${text}`, 'user', 'main');
            setState('processing');
        }
    }
    // Assistant response
    else if (rawMessage.includes('Echo:') || rawMessage.includes('[ECHO]')) {
        const text = message.replace('Echo:', '').replace('[ECHO]', '').trim();
        if (text) {
            addLog(`Echo: ${text}`, 'assistant', 'main');
            setState('speaking');
        }
    }
    // Tool call
    else if (rawMessage.includes('Tool:') || rawMessage.includes('[TOOL]')) {
        const toolName = message.replace('Tool:', '').replace('[TOOL]', '').trim();
        addLog(`Tool: ${toolName}`, 'tool', 'log');
        setState('processing');
    }
    // Tool result
    else if (rawMessage.includes('[RESULT]') || rawMessage.includes('Result:')) {
        const result = message.replace('[RESULT]', '').replace('Result:', '').trim();
        addLog(`Result: ${result.substring(0, 150)}...`, 'result', 'log');
    }
    // Turn complete
    else if (rawMessage.includes('Turn complete') || rawMessage.includes('[COMPLETE]')) {
        setState('listening');
    }
    // Connected / System Status - ROUTE TO LOG PANEL (but DON'T change state for startup logs)
    else if (rawMessage.includes('Connected') || rawMessage.includes('Ready') || rawMessage.includes('Connecting')) {
        addLog(message, 'thought', 'log'); // Changed to log panel
        // Only switch to listening when ACTUAL voice session connects
        // NOT when backend startup says "Backend ready"
        if (rawMessage.includes('Start speaking')) {
            setState('listening');
        }
    }
    // Error
    else if (rawMessage.includes('ERROR') || rawMessage.includes('❌') || rawMessage.includes('[ERROR]')) {
        addLog(message, 'error', 'log');
        setState('error');
        setTimeout(() => setState('idle'), 3000);
    }
    // Debug / Commands - ROUTE TO LOG PANEL
    else if (rawMessage.includes('[DEBUG]') || rawMessage.includes('Command:')) {
        addLog(message, 'thought', 'log');
    }
    // General message / Thought
    else if (message) {
        // Assume purely technical logs go to right, conceptual thoughts go to left
        // For now, let's put generic thoughts in left panel, but maybe lighter?
        addLog(message, 'thought', 'main');
    }
}

// Initialize
function init() {
    initWaveform();
    animateWaveform();

    // Event listeners
    expandBtn.addEventListener('click', toggleExpand);
    modeBtn.addEventListener('click', toggleMode);
    statusOrb.addEventListener('click', () => {
        if (window.electronAPI) {
            window.electronAPI.toggleSession();
        }
    });

    // IPC listeners
    if (window.electronAPI) {
        window.electronAPI.onSessionConnecting(() => {
            addLog('Connecting...', 'thought', 'log');
            setState('connecting');
        });

        window.electronAPI.onSessionStarted(() => {
            addLog('Ready!', 'thought', 'log');
            setState('listening');
        });

        window.electronAPI.onSessionStopped(() => {
            addLog('Session stopped', 'thought', 'main');
            setState('idle');
        });

        window.electronAPI.onSessionEnded(() => {
            addLog('Session ended', 'thought', 'main');
            setState('idle');
        });

        window.electronAPI.onPythonLog((message) => {
            handlePythonMessage(message);
        });

        window.electronAPI.onPythonError((message) => {
            addLog(`Error: ${message}`, 'error', 'log');
        });
    }

    console.log('ECHO UI initialized');
}

// Start when DOM is ready
document.addEventListener('DOMContentLoaded', init);

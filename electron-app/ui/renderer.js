// ECHO Voice Assistant - Renderer Script

// State
let state = 'idle'; // idle, connecting, listening, processing, speaking, error
let expanded = false;
let mode = 'fast';
let waveformBars = [];

// DOM Elements (initialized in init())
let app, statusOrb, waveform, expandBtn, expandIcon, modeBtn, cotPanel, cotStatus, cotTimeline;

// SVG Icons (as strings for easy injection)
const ICONS = {
    thinking: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/></svg>',
    tool: '<svg viewBox="0 0 24 24"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>',
    response: '<svg viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
    user: '<svg viewBox="0 0 24 24"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
    error: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
    chevron: '<svg class="cot-step-chevron" viewBox="0 0 24 24"><polyline points="6 9 12 15 18 9"/></svg>'
};

// Track current step for appending items
let currentStep = null;

// Response buffer for accumulating streamed responses
let responseBuffer = '';
let userBuffer = '';  // Buffer for user transcription
let responseStep = null;

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
        listening: 'Listening',
        processing: 'Processing',
        speaking: 'Speaking',
        error: 'Error'
    };
    cotStatus.textContent = statusTexts[newState] || 'Idle';

    // Animate waveform
    animateWaveform();
}

// Create a new timeline step
function addStep(type, title) {
    // Ensure timeline is available
    if (!cotTimeline) {
        console.warn('Timeline not ready, skipping step:', title);
        return null;
    }

    // Check if user is near bottom BEFORE adding
    const threshold = 50;
    const isAtBottom = cotTimeline.scrollHeight - cotTimeline.scrollTop - cotTimeline.clientHeight < threshold;

    const step = document.createElement('div');
    step.className = `cot-step ${type}`;

    step.innerHTML = `
        <div class="cot-step-icon">${ICONS[type] || ICONS.thinking}</div>
        <div class="cot-step-header">
            <span class="cot-step-title">${title}</span>
            ${ICONS.chevron}
        </div>
        <div class="cot-step-content"></div>
    `;

    // Make header clickable to toggle collapse
    const header = step.querySelector('.cot-step-header');
    header.addEventListener('click', () => {
        step.classList.toggle('collapsed');
    });

    cotTimeline.appendChild(step);
    currentStep = step;

    // Smart scroll - only if at bottom
    if (isAtBottom) {
        cotTimeline.scrollTo({ top: cotTimeline.scrollHeight, behavior: 'smooth' });
    }

    return step;
}

// Add item to current step's content
function addStepItem(text, isMonospace = false) {
    if (!currentStep) {
        addStep('thinking', 'Processing');
    }

    const content = currentStep.querySelector('.cot-step-content');
    const item = document.createElement('div');
    item.className = 'cot-step-item' + (isMonospace ? ' monospace' : '');
    item.textContent = text;
    content.appendChild(item);
}

// Add message bubble (user or AI)
// Add message bubble (user or AI)
let currentAIMessage = null;  // Track current AI message for streaming
let currentUserMessage = null; // Track current User message for streaming

function addMessage(text, isUser = false) {
    if (!cotTimeline) return null;

    const threshold = 50;
    const isAtBottom = cotTimeline.scrollHeight - cotTimeline.scrollTop - cotTimeline.clientHeight < threshold;

    const msg = document.createElement('div');
    msg.className = `cot-message ${isUser ? 'user' : 'ai'}`;

    msg.innerHTML = `
        <div class="cot-message-avatar">${isUser ? 'You' : 'AI'}</div>
        <div class="cot-message-bubble">${text}</div>
    `;

    cotTimeline.appendChild(msg);

    if (isAtBottom) {
        cotTimeline.scrollTo({ top: cotTimeline.scrollHeight, behavior: 'smooth' });
    }

    return msg;
}

// Update AI message bubble text (for streaming)
function updateAIMessage(text) {
    if (currentAIMessage) {
        const bubble = currentAIMessage.querySelector('.cot-message-bubble');
        if (bubble) {
            bubble.textContent = text;
        }
    }
}

// Update User message bubble text (for streaming)
function updateUserMessage(text) {
    if (currentUserMessage) {
        const bubble = currentUserMessage.querySelector('.cot-message-bubble');
        if (bubble) {
            bubble.textContent = text;
        }
    }
}

// Track current tool for updating status
let currentTool = null;

// Add tool call component
function addToolCall(name, status = 'running') {
    if (!cotTimeline) return null;

    const threshold = 50;
    const isAtBottom = cotTimeline.scrollHeight - cotTimeline.scrollTop - cotTimeline.clientHeight < threshold;

    const tool = document.createElement('div');
    tool.className = 'cot-tool';
    tool.dataset.toolName = name;

    tool.innerHTML = `
        <div class="cot-tool-icon">
            <svg viewBox="0 0 24 24">
                <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>
            </svg>
        </div>
        <span class="cot-tool-name">${name}</span>
        <span class="cot-tool-status ${status}">${status === 'running' ? 'Running' : status === 'completed' ? 'Completed' : 'Error'}</span>
        <svg class="cot-tool-chevron" viewBox="0 0 24 24">
            <polyline points="6 9 12 15 18 9"/>
        </svg>
        <div class="cot-tool-result"></div>
    `;

    // Make chevron toggle collapse
    const chevron = tool.querySelector('.cot-tool-chevron');
    chevron.addEventListener('click', () => {
        tool.classList.toggle('collapsed');
    });

    cotTimeline.appendChild(tool);
    currentTool = tool;

    if (isAtBottom) {
        cotTimeline.scrollTo({ top: cotTimeline.scrollHeight, behavior: 'smooth' });
    }

    return tool;
}

// Update tool status and result
function updateToolStatus(status, result = null) {
    if (!currentTool) return;

    const statusEl = currentTool.querySelector('.cot-tool-status');
    statusEl.className = `cot-tool-status ${status}`;
    statusEl.textContent = status === 'running' ? 'Running' : status === 'completed' ? 'Completed' : 'Error';

    if (result) {
        const resultEl = currentTool.querySelector('.cot-tool-result');
        resultEl.textContent = result.substring(0, 200);
    }
}

// Toggle mode (updated to not use emoji)
function toggleMode() {
    mode = mode === 'fast' ? 'reasoning' : 'fast';
    modeBtn.innerHTML = mode === 'fast'
        ? '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>'
        : '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a10 10 0 1 0 10 10H12V2z"/><path d="M12 2a10 10 0 0 1 10 10"/></svg>';
    modeBtn.classList.toggle('mode-reasoning', mode === 'reasoning');
    modeBtn.title = mode === 'fast' ? 'Fast Mode' : 'Reasoning Mode';

    if (window.electronAPI) {
        window.electronAPI.setMode(mode);
        addStep('thinking', `Switched to ${mode === 'fast' ? 'Fast' : 'Reasoning'} Mode`);
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
    // Skip DEBUG messages from display but process transcription
    if (rawMessage.includes('[DEBUG]')) {
        // Extract transcription for streaming
        if (rawMessage.includes('input_transcription received:')) {
            const match = rawMessage.match(/received:\s*'([^']+)'/);
            if (match) {
                userBuffer += match[1];

                // If starting new message, create bubble
                if (!currentUserMessage) {
                    if (userBuffer.trim()) {
                        currentUserMessage = addMessage(userBuffer.trim(), true);
                        setState('processing');
                    }
                } else {
                    // Update existing bubble
                    updateUserMessage(userBuffer);
                }
            }
        }
        return;  // Don't show DEBUG in UI
    }

    // Strip emojis for cleaner UI (unicode ranges for emojis)
    const message = rawMessage.replace(/[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F1E0}-\u{1F1FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}\u{1F900}-\u{1F9FF}\u{1F018}-\u{1F270}]/gu, '').trim();

    // User transcription complete (final confirm from backend)
    if (rawMessage.includes('You:') || rawMessage.includes('[USER]')) {
        // Use buffered transcription if available, otherwise use message
        const text = userBuffer.trim() || message.replace('You:', '').replace('[USER]', '').trim();

        if (text) {
            if (currentUserMessage) {
                updateUserMessage(text);
                currentUserMessage = null; // Finalized
            } else {
                addMessage(text, true);
            }

            userBuffer = '';  // Clear buffer
            setState('processing');
        }
    }
    // Assistant response - stream in real-time
    else if (rawMessage.includes('Echo:') || rawMessage.includes('[ECHO]')) {

        // Ensure user message is finalized if we start receiving AI response
        if (currentUserMessage) {
            currentUserMessage = null;
            userBuffer = '';
        }

        // Strip all markers: [RESULT], Echo:, [ECHO]
        let text = message
            .replace('[RESULT]', '')
            .replace('Echo:', '')
            .replace('[ECHO]', '')
            .trim();

        if (text) {
            // If starting new response, create bubble
            if (!currentAIMessage) {
                currentAIMessage = addMessage('', false);
            }

            // Accumulate response text with space separator
            responseBuffer += (responseBuffer ? ' ' : '') + text;

            // Update UI in real-time
            updateAIMessage(responseBuffer);

            setState('speaking');
        }
    }
    // Tool call - show as tool component
    else if (rawMessage.includes('Tool:') || rawMessage.includes('[TOOL]')) {
        const toolName = message.replace('Tool:', '').replace('[TOOL]', '').trim();
        addToolCall(toolName, 'running');
        setState('processing');
    }
    // Tool result - update tool status
    else if (rawMessage.includes('[RESULT]') || rawMessage.includes('Result:')) {
        const result = message.replace('[RESULT]', '').replace('Result:', '').trim();
        // Skip if result contains "Echo:" - it's a response being streamed
        if (!result.includes('Echo:') && !result.includes('[ECHO]')) {
            updateToolStatus('completed', result);
        }
    }
    // Turn complete - flush/reset buffers
    else if (rawMessage.includes('Turn complete') || rawMessage.includes('[COMPLETE]')) {
        // We streamed it already, just reset buffers
        responseBuffer = '';
        currentAIMessage = null;
        currentUserMessage = null; // Ensure user buffer is cleared
        userBuffer = '';
        setState('listening');
    }
    // Connected / System Status
    else if (rawMessage.includes('Connected') || rawMessage.includes('Ready') || rawMessage.includes('Connecting')) {
        addStep('thinking', 'System');
        addStepItem(message);
        if (rawMessage.includes('Start speaking')) {
            setState('listening');
        }
    }
    // Error
    else if (rawMessage.includes('ERROR') || rawMessage.includes('[ERROR]')) {
        let errorMsg = message;

        // Handle specific 1008 Policy Violation error from Gemini
        if (rawMessage.includes('policy violation') || rawMessage.includes('1008')) {
            errorMsg = "⚠️ **Gemini API Policy Violation (Error 1008)**\n\n" +
                "This usually means:\n" +
                "1. **Geo-blocking**: Gemini Live might not be available in your region.\n" +
                "2. **Audio Config**: The voice format might be unsupported.\n" +
                "3. **Model Issue**: The selected model might not support this feature.\n\n" +
                "Try switching models or checking your region/VPN.";

            // Force error state to persist longer for reading
            addStep('error', 'API Error');
            addStepItem(errorMsg);
            setState('error');
            setTimeout(() => setState('idle'), 8000); // 8 seconds to read
            return;
        }

        addStep('error', 'Error');
        addStepItem(errorMsg);
        setState('error');
        setTimeout(() => setState('idle'), 3000);
    }
    // Thought / THOUGHT marker
    else if (rawMessage.includes('[THOUGHT]')) {
        const thought = message.replace('[THOUGHT]', '').trim();
        addStep('thinking', 'Thinking');
        addStepItem(thought);
    }
    // MCP Configuration Data
    else if (rawMessage.includes('[CONFIG]')) {
        try {
            const jsonStr = message.replace('[CONFIG]', '').trim();
            currentMcpConfig = JSON.parse(jsonStr);
            renderMCPList(currentMcpConfig);

            // Sync toggle state
            const diagToggle = document.getElementById('diagnosticToolsToggle');
            if (diagToggle) {
                diagToggle.checked = currentMcpConfig.enable_diagnostic_tools !== false;
            }
            console.log("MCP Config Loaded:", currentMcpConfig);
        } catch (e) {
            console.error("Failed to parse MCP config:", e);
        }
    }
    // General message
    else if (message && message.length > 3) {
        // Append to current step if exists, otherwise create thinking step
        if (currentStep) {
            addStepItem(message);
        } else {
            addStep('thinking', 'Processing');
            addStepItem(message);
        }
    }
}

// Initialize
function init() {
    // Initialize DOM elements
    app = document.getElementById('app');
    statusOrb = document.getElementById('statusOrb');
    waveform = document.getElementById('waveform');
    expandBtn = document.getElementById('expandBtn');
    expandIcon = document.getElementById('expandIcon');
    modeBtn = document.getElementById('modeBtn');
    cotPanel = document.getElementById('cotPanel');
    cotStatus = document.getElementById('cotStatus');
    cotTimeline = document.getElementById('cotTimeline');

    initWaveform();
    animateWaveform();

    // Settings DOM elements
    const settingsBtn = document.getElementById('settingsBtn');
    const settingsModal = document.getElementById('settingsModal');
    const settingsOverlay = document.getElementById('settingsOverlay');
    const settingsClose = document.getElementById('settingsClose');
    const settingsCancel = document.getElementById('settingsCancel');
    const settingsSave = document.getElementById('settingsSave');
    const apiKeyInput = document.getElementById('apiKeyInput');
    const toggleKeyVisibility = document.getElementById('toggleKeyVisibility');
    const settingsStatus = document.getElementById('settingsStatus');
    const googleAILink = document.getElementById('googleAILink');

    // Open settings modal
    let wasExpanded = false;

    async function openSettings() {
        // Remember if was expanded, then expand window to show modal
        wasExpanded = expanded;
        settingsModal.classList.add('visible');
        settingsStatus.className = 'settings-status';
        settingsStatus.textContent = '';

        // Resize window to show the modal fully
        if (window.electronAPI) {
            window.electronAPI.resizeWindow({ width: 500, height: 550 });
        }

        // Load current API key
        if (window.electronAPI) {
            try {
                const result = await window.electronAPI.getApiKey();
                if (result.exists) {
                    apiKeyInput.value = result.key;
                    apiKeyInput.type = 'password';
                } else {
                    apiKeyInput.value = '';
                    apiKeyInput.placeholder = 'Enter your API key...';
                }
            } catch (err) {
                console.error('Error loading API key:', err);
            }
        }
    }

    // Close settings modal
    function closeSettings() {
        settingsModal.classList.remove('visible');
        apiKeyInput.type = 'password';

        // Restore window size
        if (window.electronAPI) {
            const size = wasExpanded
                ? { width: 500, height: 500 }
                : { width: 500, height: 80 };
            window.electronAPI.resizeWindow(size);
        }
    }

    function notifyRestartRequired() {
        settingsStatus.className = 'settings-status success';
        settingsStatus.style.display = 'block';
        settingsStatus.innerHTML = 'Changes Saved! <button id="restartGenBtn" class="restart-btn">Restart App</button>';
        const btn = document.getElementById('restartGenBtn');
        if (btn) {
            btn.addEventListener('click', () => {
                if (window.electronAPI) window.electronAPI.restartApp();
            });
        }
    }

    // Save API key
    async function saveApiKey() {
        const newKey = apiKeyInput.value.trim();

        if (!newKey) {
            settingsStatus.className = 'settings-status error';
            settingsStatus.textContent = 'Please enter an API key';
            return;
        }

        if (!newKey.startsWith('AIza')) {
            settingsStatus.className = 'settings-status error';
            settingsStatus.textContent = 'Invalid key format (should start with AIza)';
            return;
        }

        if (window.electronAPI) {
            try {
                const result = await window.electronAPI.setApiKey(newKey);
                if (result.success) {
                    settingsStatus.className = 'settings-status success';

                    if (result.restartRequired) {
                        settingsStatus.innerHTML = '✓ Saved! <button id="restartNowBtn" class="restart-btn">Restart Now</button>';
                        const btn = document.getElementById('restartNowBtn');
                        btn.onclick = () => {
                            if (window.electronAPI && window.electronAPI.restartApp) {
                                window.electronAPI.restartApp();
                            }
                        };
                        // Don't auto-close if restart is needed
                    } else {
                        settingsStatus.textContent = '✓ API key saved!';
                        setTimeout(closeSettings, 1500);
                    }
                } else {
                    settingsStatus.className = 'settings-status error';
                    settingsStatus.textContent = result.error || 'Failed to save';
                }
            } catch (err) {
                settingsStatus.className = 'settings-status error';
                settingsStatus.textContent = 'Error: ' + err.message;
            }
        }
    }

    // Toggle key visibility
    function toggleVisibility() {
        apiKeyInput.type = apiKeyInput.type === 'password' ? 'text' : 'password';
        // Use SVG icons instead of emoji
        toggleKeyVisibility.innerHTML = apiKeyInput.type === 'password'
            ? '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>'
            : '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>';
    }

    // Settings event listeners
    settingsBtn.addEventListener('click', openSettings);
    settingsOverlay.addEventListener('click', closeSettings);
    settingsClose.addEventListener('click', closeSettings);
    settingsCancel.addEventListener('click', closeSettings);
    settingsSave.addEventListener('click', saveApiKey);
    toggleKeyVisibility.addEventListener('click', toggleVisibility);

    // Google AI Studio link
    googleAILink.addEventListener('click', (e) => {
        e.preventDefault();
        if (window.electronAPI) {
            window.electronAPI.openExternal('https://aistudio.google.com/app/apikey');
        }
    });

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
            addStep('thinking', 'Connecting');
            addStepItem('Establishing connection to Gemini...');
            setState('connecting');
        });

        window.electronAPI.onSessionStarted(() => {
            addStep('thinking', 'Ready');
            addStepItem('Voice session active');
            setState('listening');
        });

        window.electronAPI.onSessionStopped(() => {
            addStep('thinking', 'Session Stopped');
            setState('idle');
        });

        window.electronAPI.onSessionEnded(() => {
            addStep('thinking', 'Session Ended');
            setState('idle');
        });

        window.electronAPI.onPythonLog((message) => {
            handlePythonMessage(message);
        });

        window.electronAPI.onPythonError((message) => {
            addStep('error', 'Error');
            addStepItem(message);
        });

        // Initialize MCP Settings Logic
        setupMCPSettings();
    }

    console.log('ECHO UI initialized');
}

// ==========================================
// MCP Settings Logic
// ==========================================
let currentMcpConfig = { mcp_servers: {} };

function renderMCPList(config) {
    const listContainer = document.getElementById('mcpServerList');
    if (!listContainer) return;

    listContainer.innerHTML = '';
    const servers = config.mcp_servers || {};

    if (Object.keys(servers).length === 0) {
        listContainer.innerHTML = '<div class="settings-hint" style="text-align:center;">No servers configured</div>';
        return;
    }

    for (const [name, details] of Object.entries(servers)) {
        const item = document.createElement('div');
        item.className = 'mcp-item';

        const isEnabled = details.enabled !== false;
        const transport = details.transport || 'http';

        item.innerHTML = `
            <label class="mcp-toggle" title="Enable/Disable">
                <input type="checkbox" ${isEnabled ? 'checked' : ''} data-server="${name}">
                <span class="mcp-toggle-slider"></span>
            </label>
            <div class="mcp-info ${!isEnabled ? 'mcp-disabled' : ''}">
                <span class="mcp-name">${name}</span>
                <span class="mcp-badge">${transport}</span>
            </div>
            <button class="mcp-delete" data-server="${name}" title="Delete">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
            </button>
        `;

        // Add toggle event
        const checkbox = item.querySelector('input[type="checkbox"]');
        checkbox.addEventListener('change', async (e) => {
            const serverName = e.target.dataset.server;
            if (currentMcpConfig.mcp_servers[serverName]) {
                currentMcpConfig.mcp_servers[serverName].enabled = e.target.checked;
                renderMCPList(currentMcpConfig);
                await window.electronAPI.saveMcpConfig(currentMcpConfig);
                notifyRestartRequired();
            }
        });

        // Add delete event
        const deleteBtn = item.querySelector('.mcp-delete');
        deleteBtn.addEventListener('click', async (e) => {
            const serverName = e.currentTarget.dataset.server;
            if (confirm(`Delete '${serverName}'?`)) {
                delete currentMcpConfig.mcp_servers[serverName];
                renderMCPList(currentMcpConfig);
                await window.electronAPI.saveMcpConfig(currentMcpConfig);
                notifyRestartRequired();
            }
        });

        listContainer.appendChild(item);
    }
}

// Global delete function (kept for backwards compat)
window.deleteMcpServer = async function (name) {
    if (confirm(`Remove MCP server '${name}'?`)) {
        if (currentMcpConfig.mcp_servers && currentMcpConfig.mcp_servers[name]) {
            delete currentMcpConfig.mcp_servers[name];
            renderMCPList(currentMcpConfig);
            await window.electronAPI.saveMcpConfig(currentMcpConfig);
            notifyRestartRequired();
        }
    }
};

function setupMCPSettings() {
    const addBtn = document.getElementById('addMcpServerBtn');
    const addForm = document.getElementById('addMcpForm');
    const cancelAdd = document.getElementById('cancelAddMcp');
    const confirmAdd = document.getElementById('confirmAddMcp');
    const transportSelect = document.getElementById('mcpTransport');
    const cmdUrlInput = document.getElementById('mcpCommandUrl');
    const argsInput = document.getElementById('mcpArgs');
    const nameInput = document.getElementById('mcpName');

    const settingsBtn = document.getElementById('settingsBtn');
    const saveBtn = document.getElementById('settingsSave');
    const diagToggle = document.getElementById('diagnosticToolsToggle');

    // Load config when opening settings
    if (settingsBtn) {
        settingsBtn.addEventListener('click', () => {
            if (window.electronAPI) window.electronAPI.getMcpConfig();
        });
    }

    // Toggle Form Visibility
    if (addBtn) {
        addBtn.addEventListener('click', () => {
            if (addForm) {
                const isHidden = addForm.style.display === 'none';
                addForm.style.display = isHidden ? 'block' : 'none';
                // Dynamically resize window when form toggles
                if (window.electronAPI) {
                    const height = isHidden ? 700 : 550;
                    window.electronAPI.resizeWindow({ width: 500, height: height });
                }
            }
        });
    }

    if (cancelAdd) {
        cancelAdd.addEventListener('click', () => {
            if (addForm) addForm.style.display = 'none';
            if (nameInput) nameInput.value = '';
            if (cmdUrlInput) cmdUrlInput.value = '';
            if (argsInput) argsInput.value = '';
            // Shrink window back
            if (window.electronAPI) {
                window.electronAPI.resizeWindow({ width: 500, height: 550 });
            }
        });
    }

    // Transport Change Logic
    if (transportSelect) {
        transportSelect.addEventListener('change', () => {
            const isStdio = transportSelect.value === 'stdio';
            if (cmdUrlInput) cmdUrlInput.placeholder = isStdio ? 'Command (e.g. npx)' : 'URL (e.g. http://localhost:8000/sse)';
            if (argsInput) argsInput.style.display = isStdio ? 'block' : 'none';
        });
    }

    // Add Server Logic
    if (confirmAdd) {
        confirmAdd.addEventListener('click', () => {
            const name = nameInput ? nameInput.value.trim() : '';
            const transport = transportSelect ? transportSelect.value : 'http';
            const cmdUrl = cmdUrlInput ? cmdUrlInput.value.trim() : '';
            let args = argsInput ? argsInput.value.trim() : '';

            if (!name || !cmdUrl) {
                alert("Name and Command/URL are required");
                return;
            }

            const count = Object.keys(currentMcpConfig.mcp_servers || {}).length;
            if (count >= 5) {
                alert("Max 5 MCP servers allowed.");
                return;
            }

            if (!currentMcpConfig.mcp_servers) currentMcpConfig.mcp_servers = {};

            const newServer = {
                transport: transport,
                enabled: true
            };

            if (transport === 'stdio') {
                newServer.command = cmdUrl;
                if (args) {
                    newServer.args = args.split(' ').filter(a => a.length > 0);
                }
            } else {
                newServer.url = cmdUrl;
            }

            currentMcpConfig.mcp_servers[name] = newServer;
            renderMCPList(currentMcpConfig);

            // Reset form
            if (addForm) addForm.style.display = 'none';
            if (nameInput) nameInput.value = '';
            if (cmdUrlInput) cmdUrlInput.value = '';
            if (argsInput) argsInput.value = '';
        });
    }

    // Save Config override
    if (saveBtn) {
        saveBtn.addEventListener('click', () => {
            // Update diag toggle
            if (diagToggle && currentMcpConfig) {
                currentMcpConfig.enable_diagnostic_tools = diagToggle.checked;
            }
            // Send config to backend
            if (window.electronAPI) {
                window.electronAPI.saveMcpConfig(currentMcpConfig);
            }
        });
    }
}

// Start when DOM is ready
document.addEventListener('DOMContentLoaded', init);

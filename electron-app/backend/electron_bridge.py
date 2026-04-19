#!/usr/bin/env python3
"""
Electron Bridge for ECHO Voice Assistant

Uses DesktopAgent facade to ensure identical behavior to TUI.
"""

import asyncio
import sys
import os
import io
from datetime import datetime

# Force UTF-8 encoding for stdout/stderr on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 1. Setup Environment and Path
current_file = os.path.abspath(__file__)
backend_dir = os.path.dirname(current_file)     # .../electron-app/backend
electron_app_dir = os.path.dirname(backend_dir) # .../electron-app
project_root = os.path.dirname(electron_app_dir) # .../DesktopAgent (root)

sys.path.insert(0, project_root)
os.chdir(project_root)  # Critical for PromptLoader

from dotenv import load_dotenv

def load_api_key_with_fallback(project_root: str) -> str:
    """
    Load Gemini API key with multiple fallback mechanisms.
    
    Priority order:
    1. Environment variable (already set)
    2. .env in project root
    3. .env in current directory
    4. .env in user home directory
    5. GOOGLE_API_KEY as alias
    
    Returns:
        API key string or None if not found
    """
    # Check if already set in environment (e.g., from system env vars)
    api_key = os.getenv('GEMINI_API_KEY')
    if api_key:
        return api_key
    
    # Define potential .env file locations
    env_locations = [
        os.path.join(project_root, '.env'),                          # Project root
        os.path.join(os.path.dirname(project_root), '.env'),         # Parent dir
        os.path.join(os.getcwd(), '.env'),                           # Current working dir
        os.path.join(os.path.expanduser('~'), '.env'),               # User home
        os.path.join(os.path.expanduser('~'), '.gemini', '.env'),    # ~/.gemini/.env
        os.path.join(os.getenv('APPDATA', ''), 'Echo', '.env'),      # Windows AppData
    ]
    
    # Try loading from each location
    for env_path in env_locations:
        if env_path and os.path.exists(env_path):
            load_dotenv(env_path)
            api_key = os.getenv('GEMINI_API_KEY')
            if api_key:
                print(f"[ENV] Loaded API key from: {env_path}", flush=True)
                return api_key
    
    # Fallback: Check for GOOGLE_API_KEY alias
    api_key = os.getenv('GOOGLE_API_KEY')
    if api_key:
        print("[ENV] Using GOOGLE_API_KEY as fallback", flush=True)
        os.environ['GEMINI_API_KEY'] = api_key  # Set for consistency
        return api_key
    
    # Fallback: Check for numbered backup keys (GEMINI_API_KEY_1, _2, etc.)
    for i in range(1, 5):
        backup_key = os.getenv(f'GEMINI_API_KEY_{i}')
        if backup_key:
            print(f"[ENV] Using GEMINI_API_KEY_{i} as fallback", flush=True)
            os.environ['GEMINI_API_KEY'] = backup_key
            return backup_key
    
    return None

# Load API key with fallback
GEMINI_API_KEY = load_api_key_with_fallback(project_root)

# 2. Key Code Imports
from src.agent import DesktopAgent, ThinkingLogger, AgentMode
from src.utils.mcp_config import MCPConfigManager
import json

class ElectronLogger(ThinkingLogger):
    """Logger that outputs to stdout for Electron to capture"""
    
    def __init__(self):
        super().__init__(ui_callback=self._electron_callback)
        self.audit_file = os.path.join(electron_app_dir, 'audit.log')
        # Clear audit file on startup
        try:
            with open(self.audit_file, 'w', encoding='utf-8') as f:
                f.write(f"Audit started at {datetime.now()}\n")
        except: pass

    def _electron_callback(self, type_: str, message: str):
        """Forward messages to stdout for Electron"""
        safe_msg = self._make_safe(message)
        print(f"[{type_.upper()}] {safe_msg}", flush=True)
        
        # Log to file for debugging
        try:
            with open(self.audit_file, 'a', encoding='utf-8') as f:
                f.write(f"[{datetime.now().strftime('%H:%M:%S')}] [{type_}] {safe_msg}\n")
        except: pass

    def _make_safe(self, text: str) -> str:
        try: return text.encode('utf-8').decode('utf-8')
        except: return text.encode('ascii', 'replace').decode('ascii')


class BridgeSession:
    """Manages DesktopAgent lifecycle"""
    
    def __init__(self):
        self.logger = ElectronLogger()
        self.api_key = GEMINI_API_KEY  # Use pre-loaded key with fallback
        self.agent = None
        self.running = False
        self.session_task = None
        self.config_manager = MCPConfigManager(project_root)
        
        if not self.api_key:
            self.logger.log_error("❌ GEMINI_API_KEY not found in any location")
            self.logger.log_error("   Checked: .env (project/home), GOOGLE_API_KEY, system env")

    async def initialize(self):
        """Initialize Agent and MCP Connection"""
        try:
            self.logger.log_thought("⚙️ Initializing Agent...")
            
            # Create Agent instance
            # Create Agent instance with dynamic config
            config = self.config_manager.load_config()
            
            self.agent = DesktopAgent(
                gemini_api_key=self.api_key,
                thinking_logger=self.logger,
                mode=AgentMode.FAST,
                mcp_config=config  # Pass loaded config
            )
            
            # This connects to MCP (matches main.py logic)
            await self.agent.initialize()
            
            self.logger.log_thought("✅ Agent Initialized & MCP Connected")
            
        except Exception as e:
            # If it's a known handled error from agent, just log as thought to avoid duplicate UI error bubble
            if "MCP Connection Failed" in str(e) or "Failed to initialize agent" in str(e):
                 self.logger.log_thought(f"Initialization sequence ended with error: {e}")
            else:
                 self.logger.log_error(f"Initialization Failed: {e}")
            self.agent = None

    async def start_session(self):
        """Start voice loop"""
        if self.running: return
        self.running = True
        
        try:
            if not self.agent:
                await self.initialize()
                
            if self.agent:
                self.logger.log_thought("🚀 Starting Voice Session...")
                # This uses the PRE-CONNECTED mcp_client from initialize()
                await self.agent.run_voice_session()
                
        except asyncio.CancelledError:
            self.logger.log_thought("👋 Input loop cancelled")
        except Exception as e:
            self.logger.log_error(f"Runtime Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.running = False
            self.logger.log_thought("⏹️ Session Stopped")

    async def stop(self):
        if self.session_task:
            self.session_task.cancel()
            try: await self.session_task
            except: pass
        self.running = False


async def stdin_reader(bridge):
    """Command loop"""
    # Bug 5: Use get_running_loop() instead of deprecated get_event_loop()
    loop = asyncio.get_running_loop()
    print("[READY] Backend ready", flush=True)
    
    while True:
        try:
            # Bug 5: Wrap blocking stdin.readline with a watchdog timeout
            # so the process does not idle indefinitely if Electron crashes
            try:
                line = await asyncio.wait_for(
                    loop.run_in_executor(None, sys.stdin.readline),
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                # Stdin silent for 30s -- if bridge is not running, exit
                if not bridge.running:
                    continue
                continue
            if not line: break
            
            cmd = line.strip().upper()
            if cmd == 'START':
                if not bridge.running:
                    bridge.session_task = asyncio.create_task(bridge.start_session())
            elif cmd == 'STOP':
                await bridge.stop()
            elif cmd.startswith('MODE:'):
                try:
                    mode_str = cmd.split(':', 1)[1].strip()
                    if bridge.agent:
                        bridge.agent.set_mode(mode_str)
                except Exception as e:
                    print(f"[Bridge] Error setting mode: {e}", flush=True)
            elif cmd == 'QUIT':
                await bridge.stop()
                break
            elif cmd == 'GET_CONFIG':
                try:
                    config = bridge.config_manager.load_config()
                    print(f"[CONFIG] {json.dumps(config)}", flush=True)
                except Exception as e:
                    print(f"[ERROR] Failed to get config: {e}", flush=True)
            elif cmd.startswith('SAVE_CONFIG '):
                try:
                    payload = line.strip()[12:] # Remove SAVE_CONFIG prefix
                    config = json.loads(payload)
                    bridge.config_manager.save_config(config)
                    # Bug 12: Clean up existing agent before nullifying
                    if bridge.agent:
                        await bridge.agent.cleanup()
                    bridge.agent = None  # Force reload on next session
                    print("[CONFIG] Saved", flush=True)
                except Exception as e:
                    print(f"[ERROR] Failed to save config: {e}", flush=True)
                
        except Exception as e:
            print(f"[ERROR] Loop: {e}", flush=True)

async def main():
    bridge = BridgeSession()
    # Pre-initialize to warm up connection
    await bridge.initialize()
    
    await stdin_reader(bridge)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"[FATAL] {e}", flush=True)
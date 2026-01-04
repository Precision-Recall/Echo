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
load_dotenv(os.path.join(project_root, '.env'))

# 2. Key Code Imports
from src.agent import DesktopAgent, ThinkingLogger, AgentMode

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
        self.api_key = os.getenv('GEMINI_API_KEY')
        self.agent = None
        self.running = False
        self.session_task = None
        
        if not self.api_key:
            self.logger.log_error("❌ GEMINI_API_KEY not set")

    async def initialize(self):
        """Initialize Agent and MCP Connection"""
        try:
            self.logger.log_thought("⚙️ Initializing Agent...")
            
            # Create Agent instance
            self.agent = DesktopAgent(
                gemini_api_key=self.api_key,
                thinking_logger=self.logger,
                mode=AgentMode.FAST  # Default to FAST, UI toggle can switch to REASONING
            )
            
            # This connects to MCP (matches main.py logic)
            await self.agent.initialize()
            
            self.logger.log_thought("✅ Agent Initialized & MCP Connected")
            
        except Exception as e:
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
    loop = asyncio.get_event_loop()
    print("[READY] Backend ready", flush=True)
    
    while True:
        try:
            line = await loop.run_in_executor(None, sys.stdin.readline)
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
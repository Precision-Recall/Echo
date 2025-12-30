#!/usr/bin/env python3
"""
Electron Bridge for ECHO Voice Assistant

Fixed version with proper MCP connection handling.
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

# Add project root to path
# Add project root to path
# __file__ is likely relative (backend/electron_bridge.py)
# We need absolute path to accurately find project root
current_file = os.path.abspath(__file__)
backend_dir = os.path.dirname(current_file)     # .../electron-app/backend
electron_app_dir = os.path.dirname(backend_dir) # .../electron-app
project_root = os.path.dirname(electron_app_dir) # .../DesktopAgent (root)

sys.path.insert(0, project_root)

from dotenv import load_dotenv

# Load environment variables from project root
load_dotenv(os.path.join(project_root, '.env'))

from src.agent import ThinkingLogger, ModelConfig, AgentMode


class ElectronLogger(ThinkingLogger):
    """Logger that outputs to stdout for Electron to capture"""
    
    def __init__(self):
        super().__init__(ui_callback=self._electron_callback)
        # Check explicit path for audit log
        self.audit_file = os.path.join(electron_app_dir, 'audit.log')
        # Clear audit file on startup
        with open(self.audit_file, 'w', encoding='utf-8') as f:
            f.write(f"Audit started at {datetime.now()}\n")
            f.write(f"Project Root: {project_root}\n")
    
    def _electron_callback(self, type_: str, message: str):
        """Forward messages to stdout for Electron"""
        safe_msg = self._make_safe(message)
        # Prefix with type for Electron parsing
        print(f"[{type_.upper()}] {safe_msg}", flush=True)
        
        # Audit log
        try:
            with open(self.audit_file, 'a', encoding='utf-8') as f:
                f.write(f"[{datetime.now().strftime('%H:%M:%S')}] [{type_}] {safe_msg}\n")
        except:
            pass
    
    def log_thought(self, message: str) -> None:
        super().log_thought(message)
    
    def log_action(self, tool_name: str, params=None) -> None:
        super().log_action(tool_name, params)
    
    def log_observation(self, result) -> None:
        super().log_observation(result)
    
    def log_error(self, message: str) -> None:
        super().log_error(message)
    
    def log_result(self, result) -> None:
        super().log_result(result)
    
    def _make_safe(self, text: str) -> str:
        """Make text safe for Windows console"""
        try:
            return text.encode('utf-8').decode('utf-8')
        except:
            return text.encode('ascii', 'replace').decode('ascii')


class SessionManager:
    """Manages the voice session lifecycle with proper MCP initialization"""
    
    def __init__(self, api_key: str, logger: ElectronLogger):
        self.api_key = api_key
        self.logger = logger
        self.mcp_client = None
        self.session_task = None
        self.running = False
        
    async def initialize_mcp(self):
        """Initialize MCP connection (called at startup)"""
        if self.mcp_client:
            return
            
        try:
            self.logger.log_thought("🔌 Connecting to Windows-MCP server...")
            
            from langchain_mcp_adapters.client import MultiServerMCPClient
            
            # Connect to Windows-MCP (IPv4)
            self.mcp_client = MultiServerMCPClient({
                "windows-mcp": {
                    "transport": "http",
                    "url": "http://127.0.0.1:8000/mcp",
                }
            })
            
            # Test connection
            tools = await self.mcp_client.get_tools()
            tool_names = [t.name for t in tools]
            
            if tools:
                self.logger.log_thought(f"✅ Loaded {len(tools)} tools from MCP")
                self.logger.log_thought(f"Available: {', '.join(tool_names)}")
            else:
                self.logger.log_thought("⚠️ MCP connected but no tools returned")
                
        except Exception as e:
            self.logger.log_error(f"⚠️ MCP Connection Failed")
            self.logger.log_error(f"Details: {str(e)}")
            self.logger.log_thought("ℹ️ Voice-only mode active (no desktop control)")
            self.mcp_client = None
        
    async def start_session(self):
        """Start voice session"""
        if self.running:
            self.logger.log_thought("⚠️ Session already running")
            return
            
        self.running = True
        self.logger.log_thought("🚀 Starting voice session...")
        
        try:
            # Re-init MCP if it failed previously (optional retry)
            if not self.mcp_client:
                await self.initialize_mcp()
                
            model_config = ModelConfig.get_config(AgentMode.VOICE)
            self.logger.log_thought(f"📡 Using model: {model_config.model_name}")
            
            # Create Client
            client = GeminiLiveClient(
                api_key=self.api_key,
                model_name=model_config.model_name,
                logger=self.logger,
                mcp_client=self.mcp_client
            )
            
            await client.run()
            
        except asyncio.CancelledError:
            self.logger.log_thought("👋 Session cancelled")
        except Exception as e:
            self.logger.log_error(f"Session error: {e}")
            import traceback
            self.logger.log_error(traceback.format_exc())
        finally:
            self.running = False
            self.logger.log_thought("✅ Session ended")
    
    async def stop_session(self):
        """Stop session"""
        if not self.running:
            return
            
        self.running = False
        self.logger.log_thought("🛑 Stopping session...")
        
        if self.session_task and not self.session_task.done():
            self.session_task.cancel()
            try:
                await self.session_task
            except asyncio.CancelledError:
                pass


async def stdin_reader(session_manager: SessionManager):
    """Read commands from stdin"""
    loop = asyncio.get_event_loop()
    
    def read_line():
        try:
            return sys.stdin.readline()
        except:
            return None
    
    print("[READY] Backend ready", flush=True)
    
    while True:
        try:
            line = await loop.run_in_executor(None, read_line)
            if line is None:
                await asyncio.sleep(0.1)
                continue
                
            command = line.strip().upper()
            if not command: continue
            
            print(f"[DEBUG] Command: {command}", flush=True)
            
            if command == 'START':
                if not session_manager.running:
                    session_manager.session_task = asyncio.create_task(session_manager.start_session())
            elif command == 'STOP':
                await session_manager.stop_session()
            elif command == 'QUIT':
                await session_manager.stop_session()
                break
                
        except Exception as e:
            print(f"[ERROR] stdin: {e}", flush=True)
            await asyncio.sleep(0.5)


async def main():
    """Main entry point"""
    print("[STARTUP] Initializing ECHO backend...", flush=True)
    
    # 1. Setup Logger
    logger = ElectronLogger()
    
    # 2. Check API Key
    api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
    if not api_key:
        logger.log_error("❌ GEMINI_API_KEY not set")
        return
        
    logger.log_thought("🚀 ECHO Backend Starting...")
    
    # 3. Create Session Manager
    session_manager = SessionManager(api_key, logger)
    
    # 4. START MCP INITIALIZATION IMMEDIATELY (Background)
    # This ensures tools are ready when user starts session
    asyncio.create_task(session_manager.initialize_mcp())
    
    logger.log_thought("📝 Press Alt+Space to toggle listening")

    # 5. Start Input Loop
    try:
        await stdin_reader(session_manager)
    except KeyboardInterrupt:
        logger.log_thought("👋 Shutting down...")
    except Exception as e:
        logger.log_error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("[SHUTDOWN] Backend stopped", flush=True)


if __name__ == '__main__':
    try:
        # Import Client here to verify imports
        from src.agent.live_client import GeminiLiveClient
        asyncio.run(main())
    except Exception as e:
        print(f"[FATAL] Startup failed: {e}", flush=True)
        import traceback
        traceback.print_exc()
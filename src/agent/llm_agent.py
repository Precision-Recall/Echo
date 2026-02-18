"""
Desktop Agent using LangChain + Windows-MCP
Simplified implementation using langchain-mcp-adapters
"""

import os
import asyncio
from typing import Dict, Any
from dotenv import load_dotenv
from enum import Enum
from dataclasses import dataclass

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage

from .thinking_logger import ThinkingLogger

class AgentMode(Enum):
    FAST = "fast"           # Fast execution (Default)
    REASONING = "reasoning" # Multi-agent planning
    VOICE = "voice"         # Voice interaction via Gemini Live

@dataclass
class ModelConfig:
    model_name: str
    temperature: float = 0
    
    @staticmethod
    def get_config(mode: AgentMode) -> 'ModelConfig':
        # Unified config for Sub-Agents (FAST)
        # We use Flash 2.0 for both Fast and Reasoning execution layers
        return ModelConfig("gemini-2.5-flash")

class DesktopAgent:
    """Desktop automation agent powered by LangChain + Windows-MCP"""
    
    def __init__(
        self,
        gemini_api_key: str,
        thinking_logger: ThinkingLogger,
        mcp_url: str = "http://localhost:8000/mcp",
        mode: AgentMode = AgentMode.FAST,
        mcp_config: Dict[str, Any] = None
    ):
        """
        Initialize agent
        
        Args:
            gemini_api_key: Google Gemini API key
            thinking_logger: Logger for thinking trace
            mcp_url: Windows-MCP server URL (Legacy)
            mode: Agent execution mode (FAST, REASONING, VOICE)
            mcp_config: Standard MCP configuration dict
        """
        self.logger = thinking_logger
        self.gemini_api_key = gemini_api_key
        self.mcp_url = mcp_url
        self.mcp_config = mcp_config
        self.config = ModelConfig.get_config(mode)
        self.current_mode = mode
        
        self.mcp_client: MultiServerMCPClient = None
        self.agent_executor: Runnable = None

        
    async def initialize(self):
        """Initialize MCP client and LangGraph agent"""
        try:
            self.logger.log_thought("Connecting to MCP servers...")
            
            # Use provided config or fallback to default
            if self.mcp_config and "mcp_servers" in self.mcp_config:
                # Need to convert internal storage format to LangChain MCP format
                # But wait, electron_bridge passes the raw storage config
                from src.utils.mcp_config import MCPConfigManager
                # Extract valid servers
                manager = MCPConfigManager() # Temp manager to use helper? 
                # Actually, better to just modify config here if needed, 
                # but electron_bridge passes the raw json.
                # We need to filter for enabled servers.
                
                # RE-READ config using manager to get clean format
                # Or implemented helper in DesktopAgent?
                # Best approach: Use the passed dict directly if it matches format
                
                # The mcp_config structure from JSON:
                # { "mcp_servers": { "name": { "transport": "...", "enabled": true } } }
                
                # MultiServerMCPClient expects:
                # { "name": { "transport": "...", "url": "..." } }
                
                # We interpret the passed config:
                server_config = {}
                servers = self.mcp_config.get("mcp_servers", {})
                for name, details in servers.items():
                    if details.get("enabled", True):
                        # Filter to only known client params
                        client_params = {k:v for k,v in details.items() if k in ["transport", "url", "command", "args", "env"]}
                        
                        # PATCH: bundled environment fix
                        # If command is "python" and we are bundled, use sys.executable
                        if client_params.get("transport") == "stdio" and client_params.get("command") == "python":
                            import sys
                            # Always use current interpreter (works for venv and bundled exe)
                            client_params["command"] = sys.executable
                            
                            # PATCH: Fix module name if it's the default "windows_mcp"
                            # In bundled env, it might need to run the directory as a module if possible, 
                            # or we rely on the fact that we added it to sys.path in electron_bridge.
                            # But subprocess starts a NEW process.
                            # So we need the args to be correct.
                            if "args" in client_params and "-m" in client_params["args"]:
                                try:
                                    idx = client_params["args"].index("windows_mcp")
                                    # If windows_mcp module doesn't exist but directory does?
                                    # Actually, let's keep it as is, but ensure sys.executable is used.
                                    pass
                                except ValueError:
                                    pass

                        server_config[name] = client_params
                
                self.mcp_client = MultiServerMCPClient(server_config)
                
            else:
                # Legacy fallback
                self.mcp_client = MultiServerMCPClient({
                    "windows-mcp": {
                        "transport": "http",
                        "url": self.mcp_url,
                    }
                })
            
            # Get all available tools from Windows-MCP
            tools = await self.mcp_client.get_tools()
            self.logger.log_thought(f"✓ Loaded {len(tools)} tools from Windows-MCP")
            
            # Log available tools
            tool_names = [tool.name for tool in tools]
            self.logger.log_thought(f"Available tools: {', '.join(tool_names)}")
            
            # Create Gemini LLM via LangChain
            llm = ChatGoogleGenerativeAI(
                model=self.config.model_name,
                google_api_key=self.gemini_api_key,
                temperature=self.config.temperature,
                convert_system_message_to_human=True  
            )
            
            # Create LangGraph agent with ReAct prompt
            system_prompt = """You are a Windows desktop automation assistant.

Available tools allow you to:
- Get desktop state (State-Tool)
- Launch applications (Launch-Tool)
- Switch between apps (Switch-Tool) 
- Type text (Type-Tool)
- Click at coordinates (Click-Tool)
- Press keyboard shortcuts (Shortcut-Tool)
- Execute PowerShell commands (Powershell-Tool)

Always think step-by-step:
1. Check desktop state first if needed
2. Plan your actions
3. Execute actions in sequence
4. Verify results

Be precise with coordinates and wait appropriately between actions."""
            
            # Create agent using LangGraph
            self.agent_executor = create_react_agent(
                llm,
                tools,
                prompt=system_prompt
            )
            
            self.logger.log_thought("✓ Agent initialized successfully")
            
        except Exception as e:
            # Try to unwrap ExceptionGroup/TaskGroup to find the root cause
            root_error = e
            if hasattr(e, 'exceptions'):
                # It's an ExceptionGroup or similar
                errors = e.exceptions
                if errors:
                    # Log fully but return the first meaningful error
                    for err in errors:
                        self.logger.log_thought(f"Checking sub-error: {type(err).__name__}: {str(err)}")
                        
                        # Prioritize connection errors (including ConnectError from httpx)
                        err_str = str(err)
                        if "Connection refused" in err_str or "ClientConnectorError" in err_str or "ConnectError" in err_str:
                            root_error = err
                            break
                    
                    if root_error == e:
                        root_error = errors[0]

            error_msg = f"Failed to initialize agent: {type(root_error).__name__}: {str(root_error)}"
            
            # Explicitly mention MCP if relevant
            root_str = str(root_error)
            if "Connection refused" in root_str or "ClientConnectorError" in root_str or "ConnectError" in root_str:
                error_msg = f"MCP Connection Failed: {root_str}"
                
            self.logger.log_error(error_msg)
            raise RuntimeError(error_msg)
    
    async def execute_task(self, user_command: str) -> Dict[str, Any]:
        """
        Execute a desktop automation task
        
        Args:
            user_command: Natural language command from user
            
        Returns:
            Result dictionary with success status and message
        """
        try:
            self.logger.log_thought(f"Task: {user_command}")
            
            # Execute via LangGraph agent
            messages = [HumanMessage(content=user_command)]
            result = await self.agent_executor.ainvoke({"messages": messages})
            
            # Extract final response
            final_message = result.get("messages", [])[-1]
            output = final_message.content if hasattr(final_message, 'content') else str(final_message)
            
            self.logger.log_result(output)
            
            return {
                "success": True,
                "result": output,
                "trace": self.logger.get_full_trace()
            }
            
        except Exception as e:
            error = f"Error executing task: {str(e)}"
            self.logger.log_error(error)
            return {
                "success": False,
                "error": error,
                "trace": self.logger.get_full_trace()
            }
    
    def set_mode(self, mode_str: str):
        """Set agent execution mode"""
        try:
            # Handle 'fast' and 'reasoning' strings
            new_mode = AgentMode(mode_str.lower())
            self.current_mode = new_mode
            self.logger.log_thought(f"🔄 Mode switched to: {new_mode.value.upper()}")
        except ValueError:
            self.logger.log_error(f"❌ Invalid mode: {mode_str}")

    async def run_voice_session(self):
        """Run a Gemini Live voice session"""
        if not self.mcp_client:
            await self.initialize()
            
        from src.agent.live_client import GeminiLiveClient
        from src.agent.state_graph import MultiAgentGraph
        
        # Initialize Reasoning Agent Graph
        multi_agent_graph = MultiAgentGraph(
            api_key=self.gemini_api_key,
            mcp_client=self.mcp_client,
            logger=self.logger
        )
        
        # Determine configuration based on mode
        # Use Native Audio model for Voice Client
        voice_model = "gemini-2.5-flash-native-audio-preview-12-2025" 
        
        # LOGIC:
        # FAST Mode -> LiveClient has MCP tools, executes directly.
        # REASONING Mode -> LiveClient has NO tools. Routes to SubAgent (MultiAgentGraph).
        
        # Brief yield to allow any pending mode IPC commands to be processed
        await asyncio.sleep(0.1)
        
        mode_str = self.current_mode.value  # "fast", "reasoning", or "voice"
        self.logger.log_thought(f"📍 Session Mode: {mode_str.upper()}")
        
        # VOICE mode behaves like FAST mode (direct tool execution)
        use_direct_tools = mode_str in ("fast", "voice")
        
        # Create Voice Client with explicit mode
        client = GeminiLiveClient(
            api_key=self.gemini_api_key,
            model_name=voice_model,
            logger=self.logger,
            mode="fast" if use_direct_tools else "reasoning",  # Map voice -> fast
            mcp_client=self.mcp_client if use_direct_tools else None,
            multi_agent_graph=multi_agent_graph
        )
        
        await client.run()

    async def cleanup(self):
        """Clean up resources"""
        if self.mcp_client:
            # MultiServerMCPClient cleanup if needed
            pass
        self.logger.log_thought("Agent cleanup complete")
"""
Desktop Agent using LangChain + Windows-MCP
Simplified implementation using langchain-mcp-adapters
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage

from .thinking_logger import ThinkingLogger



class DesktopAgent:
    """Desktop automation agent powered by LangChain + Windows-MCP"""
    
    def __init__(
        self,
        gemini_api_key: str,
        thinking_logger: ThinkingLogger,
        mcp_url: str = "http://localhost:8000/mcp",
        model_name: str = "gemini-2.5-flash"
    ):
        """
        Initialize agent
        
        Args:
            gemini_api_key: Google Gemini API key
            thinking_logger: Logger for tracking agent reasoning
            mcp_url: URL of Windows-MCP server (default: http://localhost:8000/mcp)
            model_name: Gemini model to use
        """
        self.logger = thinking_logger
        self.gemini_api_key = gemini_api_key
        self.mcp_url = mcp_url
        self.model_name = model_name
        
        self.mcp_client: MultiServerMCPClient = None
        self.agent_executor: Runnable = None # Changed type hint from AgentExecutor to Runnable
        
    async def initialize(self):
        """Initialize MCP client and LangGraph agent"""
        try:
            self.logger.log_thought("Connecting to Windows-MCP server...")
            
            # Connect to Windows-MCP via HTTP
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
                model=self.model_name,
                google_api_key=self.gemini_api_key,
                temperature=0,
                convert_system_message_to_human=True  # Gemini compatibility
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
- And more...

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
            error_msg = f"Failed to initialize agent: {str(e)}"
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
    
    async def cleanup(self):
        """Clean up resources"""
        if self.mcp_client:
            # MultiServerMCPClient cleanup if needed
            pass
        self.logger.log_thought("Agent cleanup complete")

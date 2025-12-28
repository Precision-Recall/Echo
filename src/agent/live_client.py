import asyncio
import base64
import json
import logging
from typing import List, Dict, Any, Optional

from google import genai
from google.genai.types import (
    LiveConnectConfig,
    PrebuiltVoiceConfig,
    VoiceConfig,
    VoiceConfig,
    Tool,
    FunctionDeclaration,
    LiveClientToolResponse,
    FunctionResponse
)

from src.agent.audio import AudioManager

class GeminiLiveClient:
    """
    Voice client using official google-genai SDK.
    Handles bidirectional audio and tool execution via MCP.
    """
    
    def __init__(self, api_key: str, model_name: str, mcp_client: Any, logger):
        self.client = genai.Client(api_key=api_key, http_options={'api_version': 'v1alpha'})
        self.model_name = model_name
        self.mcp_client = mcp_client
        self.logger = logger
        self.audio = AudioManager()
        
    async def run(self):
        """Main loop: Connect -> Audio/Tool Loop"""
        
        # 1. Get MCP Tools and convert to GenAI format
        tools = await self._get_genai_tools()
        
        config = {
            "response_modalities": ["AUDIO"],
            "tools": tools,
            "system_instruction": "You are Echo, a helpful Windows desktop assistant. Use tools to control the computer.",
        }
        
        self.logger.log_thought(f"🎙️ Connecting to Gemini Live ({self.model_name})...")
        
        try:
            async with self.client.aio.live.connect(
                model=self.model_name,
                config=config
            ) as session:
                self.logger.log_thought("✅ Connected! Start speaking...")
                
                async with asyncio.TaskGroup() as tg:
                    tg.create_task(self._send_audio(session))
                    tg.create_task(self._receive_loop(session))
                    tg.create_task(self._play_audio())
                    
        except Exception as e:
            self.logger.log_error(f"Live Session Error: {e}")

    async def _get_genai_tools(self) -> List[Tool]:
        """Convert MCP tools to Google GenAI Tool objects"""
        langchain_tools = await self.mcp_client.get_tools()
        declarations = []
        
        for t in langchain_tools:
            # Handle Schema
            schema = {}
            if hasattr(t, 'args_schema') and t.args_schema:
                 if hasattr(t.args_schema, 'schema'):
                     schema = t.args_schema.schema()
                 elif isinstance(t.args_schema, dict):
                     schema = t.args_schema
            
            # Remove title/definitions if present
            if "title" in schema: del schema["title"]
            if "definitions" in schema: del schema["definitions"]
            
            declarations.append(FunctionDeclaration(
                name=t.name,
                description=t.description,
                parameters=schema
            ))
            
        return [Tool(function_declarations=declarations)]

    async def _send_audio(self, session):
        """Send mic audio to session"""
        try:
            async with self.audio as audio:
                await audio.start_recording()
                while True:
                    chunk = await audio.get_audio_chunk()
                    # Send raw PCM, SDK handles wrapping
                    await session.send(input={"data": chunk, "mime_type": "audio/pcm"}, end_of_turn=False)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.log_error(f"Send Audio Error: {e}")
            raise e

    async def _play_audio(self):
        """Play audio from queue"""
        # AudioManager handles queue internally
        while True:
            # We access the queue directly or need an interface
            # The original AudioManager uses blocking queue for output. 
            # We need to bridge the session receive loop to AudioManager's play_audio_chunk 
            await asyncio.sleep(0.1) # Placeholder, actual logic in _receive_loop

    async def _receive_loop(self, session):
        """Receive audio and tool calls"""
        while True:
            try:
                async for response in session.receive():
                    # 1. Handle Audio
                    if response.server_content:
                        model_turn = response.server_content.model_turn
                        if model_turn:
                            for part in model_turn.parts:
                                if part.inline_data:
                                    self.audio.play_audio_chunk(part.inline_data.data)

                    # 2. Handle Tool Calls
                    if response.tool_call:
                        await self._handle_tool_call(session, response.tool_call)
                        
            except Exception as e:
                self.logger.log_error(f"Receive error: {e}")
                break

    async def _handle_tool_call(self, session, tool_call):
        """Execute tool and send response"""
        # 1. Map available tools
        langchain_tools = await self.mcp_client.get_tools()
        tool_map = {t.name: t for t in langchain_tools}
        
        function_responses = []
        
        for fc in tool_call.function_calls:
            name = fc.name
            args = fc.args
            
            self.logger.log_thought(f"🔧 Live Tool: {name}")
            
            try:
                if name not in tool_map:
                    raise ValueError(f"Tool {name} not found")
                
                # Execute via LangChain Tool
                # Use ainvoke if available, else invoke
                tool = tool_map[name]
                if hasattr(tool, "ainvoke"):
                    result = await tool.ainvoke(args)
                else:
                    result = await asyncio.to_thread(tool.invoke, args)
                
                # Result might be a string or object
                content = str(result)
                
                function_responses.append(FunctionResponse(
                    name=name,
                    id=fc.id,
                    response={"result": content}
                ))
                
            except Exception as e:
                function_responses.append(FunctionResponse(
                    name=name,
                    id=fc.id,
                    response={"error": str(e)}
                ))
                
        # Send result back
        tool_response = LiveClientToolResponse(function_responses=function_responses)
        await session.send(input=tool_response)


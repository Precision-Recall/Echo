import asyncio
import base64
from google.genai import types
from typing import List, Any

from google import genai
from google.genai.types import (
    LiveConnectConfig,
    PrebuiltVoiceConfig,
    VoiceConfig,
    Tool,
    FunctionDeclaration,
    LiveClientToolResponse,
    FunctionResponse
)

from src.agent.audio import AudioManager
from Prompts.promptLoader import PromptLoader

# Default MCP configuration
MCP_CONFIG = {
    "windows-mcp": {
        "transport": "http",
        "url": "http://127.0.0.1:8000/mcp",
    }
}

class GeminiLiveClient:
    """
    Voice client using official google-genai SDK.
    Handles bidirectional audio and tool execution via MCP.
    
    MCP connection is handled internally - caller just provides API key.
    """
    
    def __init__(self, api_key: str, model_name: str, logger, mcp_client: Any = None):
        self.client = genai.Client(api_key=api_key, http_options={'api_version': 'v1alpha'})
        self.model_name = model_name
        self.mcp_client = mcp_client  # Will be initialized in run() if None
        self.logger = logger
        self.audio = AudioManager()
        self.prompt_loader = PromptLoader("Prompts/prompts") 
        
    async def run(self):
        """Main loop: Connect -> Audio/Tool Loop"""
        
        # 0. Connect to MCP (if not provided)
        await self._connect_mcp()
        
        # 1. Get MCP Tools and convert to GenAI format
        tools = await self._get_genai_tools()
        system_prompt = self.prompt_loader.load_prompt("echo_voice_tui.txt")
        # Working config pattern - simple dict
        config = {
            "response_modalities": ["AUDIO"],
            "tools": tools,
            "system_instruction": system_prompt,
            "speech_config": {
                "voice_config": {"prebuilt_voice_config": {"voice_name": "Puck"}}
            },
            # Enable transcription
            "output_audio_transcription": {},
            "enable_affective_dialog": True,
            "thinking_config": types.ThinkingConfig(
                thinking_budget=1024,
            )
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
                    
        except asyncio.CancelledError:
            self.logger.log_thought("Session cancelled")
        except Exception as e:
            self.logger.log_error(f"Live Session Error: {e}")
            import traceback
            self.logger.log_error(traceback.format_exc())
        finally:
            self.audio.close()

    async def _connect_mcp(self):
        """Connect to MCP server if not already connected"""
        if self.mcp_client:
            return  # Already have a client
            
        try:
            from langchain_mcp_adapters.client import MultiServerMCPClient
            self.logger.log_thought("📡 Connecting to Windows-MCP...")
            self.mcp_client = MultiServerMCPClient(MCP_CONFIG)
            tools = await self.mcp_client.get_tools()
            self.logger.log_thought(f"✅ MCP connected - {len(tools)} tools available")
        except Exception as e:
            self.logger.log_thought(f"⚠️ MCP not available - voice only mode")
            self.mcp_client = None

    async def _get_genai_tools(self) -> List[Tool]:
        """Convert MCP tools to Google GenAI Tool objects"""
        # Handle case where MCP client is not available
        if not self.mcp_client:
            return []
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
            
            # Remove title/definitions if present (not supported by GenAI)
            if "title" in schema: del schema["title"]
            if "definitions" in schema: del schema["definitions"]
            
            declarations.append(FunctionDeclaration(
                name=t.name,
                description=t.description,
                parameters=schema
            ))
            
        return [Tool(function_declarations=declarations)]

    async def _send_audio(self, session):
        """Send mic audio to session (working pattern)"""
        try:
            async with self.audio as audio:
                await audio.start_recording()
                while True:
                    chunk = await audio.get_audio_chunk()
                    # Send raw PCM with end_of_turn=False for continuous streaming
                    await session.send(
                        input={"data": chunk, "mime_type": "audio/pcm"},
                        end_of_turn=False
                    )
        except asyncio.CancelledError:
            self.logger.log_thought("Audio sending cancelled")
        except Exception as e:
            self.logger.log_error(f"Send Audio Error: {e}")
            raise

    async def _receive_loop(self, session):
        """Receive audio, transcriptions, and tool calls"""
        try:
            # CRITICAL: while True wrapper for multi-turn conversation!
            # session.receive() returns an iterator for ONE turn only
            while True:
                async for response in session.receive():
                    # 1. Handle server content (audio/text from model)
                    if response.server_content:
                        server_content = response.server_content
                        
                        # Handle model turn (audio/text)
                        if server_content.model_turn:
                            for part in server_content.model_turn.parts:
                                # Audio data
                                if part.inline_data:
                                    audio_data = part.inline_data.data
                                    # Decode if base64
                                    if isinstance(audio_data, str):
                                        audio_data = base64.b64decode(audio_data)
                                    self.audio.play_audio_chunk(audio_data)
                                
                                # Text data (transcription or direct text)
                                if part.text:
                                    self.logger.log_result(f"🗣️ {part.text}")
                        
                        # Handle output audio transcription
                        if hasattr(server_content, 'output_transcription') and server_content.output_transcription:
                            transcript = server_content.output_transcription.text
                            if transcript:
                                self.logger.log_result(f"📝 Echo: {transcript}")
                        
                        # Handle input audio transcription (what user said)
                        if hasattr(server_content, 'input_transcription') and server_content.input_transcription:
                            transcript = server_content.input_transcription.text
                            if transcript:
                                self.logger.log_thought(f"🎤 You: {transcript}")
                        
                        # Handle turn complete - just log, don't break!
                        if server_content.turn_complete:
                            self.logger.log_thought("✅ Turn complete")
                            # Stop playback after turn completes
                            await asyncio.sleep(0.3)
                            self.audio.stop_playback()
                        
                        # Handle interruption
                        if hasattr(server_content, 'interrupted') and server_content.interrupted:
                            self.logger.log_thought("🛑 Interrupted")
                            self.audio.stop_playback()
                    
                    # 2. Handle tool calls
                    if response.tool_call:
                        await self._handle_tool_call(session, response.tool_call)
                        
        except asyncio.CancelledError:
            self.logger.log_thought("Receive loop cancelled")
        except Exception as e:
            self.logger.log_error(f"Receive error: {e}")
            import traceback
            self.logger.log_error(traceback.format_exc())

    async def _handle_tool_call(self, session, tool_call):
        """Execute tool and send response"""
        # 1. Map available tools
        langchain_tools = await self.mcp_client.get_tools()
        tool_map = {t.name: t for t in langchain_tools}
        
        function_responses = []
        
        for fc in tool_call.function_calls:
            name = fc.name
            args = fc.args
            
            self.logger.log_thought(f"🔧 Tool: {name}")
            self.logger.log_action(f"Executing {name}", args)
            
            try:
                if name not in tool_map:
                    raise ValueError(f"Tool {name} not found")
                
                # Execute via LangChain Tool
                tool = tool_map[name]
                if hasattr(tool, "ainvoke"):
                    result = await tool.ainvoke(args)
                else:
                    result = await asyncio.to_thread(tool.invoke, args)
                
                content = str(result)
                self.logger.log_observation(f"Result: {content[:200]}...")
                
                function_responses.append(FunctionResponse(
                    name=name,
                    id=fc.id,
                    response={"result": content}
                ))
                
            except Exception as e:
                self.logger.log_error(f"Tool error: {e}")
                function_responses.append(FunctionResponse(
                    name=name,
                    id=fc.id,
                    response={"error": str(e)}
                ))
                
        # Send result back
        tool_response = LiveClientToolResponse(function_responses=function_responses)
        await session.send(input=tool_response)
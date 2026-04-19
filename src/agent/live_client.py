import asyncio
import base64
from google.genai import types
from typing import List, Any, Optional

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

from .task_router import TaskRouter, TaskComplexity

from .audio import AudioManager
from pathlib import Path

# Import granular diagnostic tools
import sys
sys.path.insert(0, 'system-diagnosis-mcp')
try:
    from granular_diagnostic_tools import (
        MCP_TOOL_DEFINITIONS,
        get_cpu_usage, get_memory_usage, get_disk_usage, get_disk_io,
        get_network_status, get_battery_info, get_process_info, kill_process,
        check_windows_defender, check_firewall, check_windows_updates,
        flush_dns, renew_ip, test_internet_connection, find_large_files
    )
    DIAGNOSTIC_TOOLS_AVAILABLE = True
except ImportError as e:
    print(f"[WARNING] Granular diagnostic tools not available: {e}", flush=True)
    DIAGNOSTIC_TOOLS_AVAILABLE = False
    MCP_TOOL_DEFINITIONS = []

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
    
    In FAST mode: Has tools, executes directly.
    In REASONING mode: No tools, routes to SubAgent (MultiAgentGraph).
    """
    
    def __init__(
        self, 
        api_key: str, 
        model_name: str, 
        logger, 
        mode: str = "fast",  # "fast" or "reasoning"
        mcp_client: Any = None,
        task_router: Optional[TaskRouter] = None,
        multi_agent_graph: Any = None  # SubAgent for REASONING mode
    ):
        self.client = genai.Client(api_key=api_key, http_options={'api_version': 'v1alpha'})
        self.model_name = model_name
        self.mode = mode.lower()  # "fast" or "reasoning"
        self.mcp_client = mcp_client if self.mode == "fast" else None  # Only FAST has MCP
        self.logger = logger
        self.audio = AudioManager()
        self._prompts_dir = Path(__file__).resolve().parents[2] / "Prompts" / "prompts"
        
        # Task routing for complex tasks
        self.task_router = task_router or TaskRouter(api_key)
        self.multi_agent_graph = multi_agent_graph
        self._pending_transcript = ""  # Input transcript (what user said)
        self._output_transcript = ""   # Output transcript (model's echo for context)
        self._session = None  # Store session reference for speaking responses
        
        # Bug 1: Replace boolean _muted with asyncio.Lock for mutual exclusion
        self._subagent_lock = asyncio.Lock()
        
        # Bug 7: Serialize all session.send() calls to prevent WebSocket corruption
        self._send_lock = asyncio.Lock()
        
        # Bug 4: Track background graph task to cancel in-flight runs
        self._graph_task: asyncio.Task = None
        
        # Bug 16: Track greeting task for cleanup on teardown
        self._greeting_task: asyncio.Task = None
        
        # Cache for tools to avoid multiple MCP connections
        self._langchain_tools_cache = None
        self._genai_tools_cache = None
        
    async def run(self):
        """Main loop: Connect -> Audio/Tool Loop"""
        print("[DEBUG] GeminiLiveClient.run() started", flush=True)
        
        # 0. Connect to MCP (if not provided)
        print("[DEBUG] Calling _connect_mcp...", flush=True)
        await self._connect_mcp()
        
        # 1. Get MCP Tools and convert to GenAI format
        tools = await self._get_genai_tools()
        system_prompt = (self._prompts_dir / "echo_voice_tui.txt").read_text(encoding="utf-8").strip()
        # Working config pattern - simple dict
        config = {
            "response_modalities": ["AUDIO"],
            "tools": tools,
            "system_instruction": system_prompt,
            "speech_config": {
                "voice_config": {"prebuilt_voice_config": {"voice_name": "Puck"}}
            },
            # Enable transcription - BOTH input and output
            "output_audio_transcription": {},
            "input_audio_transcription": {},  # Required to get user's speech as text
            "enable_affective_dialog": True,
        }
        
        self.logger.log_thought(f"🎙️ Connecting to Gemini Live ({self.model_name})...")
        print(f"[DEBUG] Connecting to Gemini Live API with model {self.model_name}...", flush=True)
        
        try:
            async with self.client.aio.live.connect(
                model=self.model_name,
                config=config
            ) as session:
                self.logger.log_thought("✅ Connected! Start speaking...")

                # Store session reference for other methods
                self._session = session
                
                # Trigger Intro Greeting IMMEDIATELY
                # Bug 16: Store greeting task reference for teardown cleanup
                self._greeting_task = asyncio.create_task(self._send_instant_greeting(session))
                
                async with asyncio.TaskGroup() as tg:
                    tg.create_task(self._send_audio(session))
                    tg.create_task(self._receive_loop(session))
                    tg.create_task(self._heartbeat_loop(session))  # Keep session alive
                    
        except asyncio.CancelledError:
            self.logger.log_thought("Session cancelled")
        except Exception as e:
            # Graceful handling for session disconnection
            err_str = str(e).lower()
            if "close" in err_str or "aborted" in err_str or "no close frame" in err_str:
                self.logger.log_thought("🔌 Session timed out - reconnect with Alt+Space")
            else:
                self.logger.log_error(f"Live Session Error: {e}")
        finally:
            # Bug 16: Cancel orphaned greeting task on teardown
            if self._greeting_task and not self._greeting_task.done():
                self._greeting_task.cancel()
            # Bug 4: Cancel any in-flight graph task
            if self._graph_task and not self._graph_task.done():
                self._graph_task.cancel()
            self.audio.close()

    async def _connect_mcp(self):
        """Connect to MCP server if not already connected"""
        # REASONING mode: Skip MCP connection (SubAgent handles tools)
        if self.mode == "reasoning":
            self.logger.log_thought("🧠 REASONING Mode | Voice-only (SubAgent has tools)")
            return
            
        print(f"[DEBUG] _connect_mcp called. Current mcp_client: {self.mcp_client}", flush=True)
        if self.mcp_client:
            return  # Already have a client
            
        try:
            print("[DEBUG] Importing MultiServerMCPClient...", flush=True)
            from langchain_mcp_adapters.client import MultiServerMCPClient
            self.logger.log_thought("📡 Connecting to Windows-MCP...")
            
            print(f"[DEBUG] Connecting to MCP config: {MCP_CONFIG}", flush=True)
            self.mcp_client = MultiServerMCPClient(MCP_CONFIG)
            
            print("[DEBUG] Fetching tools...", flush=True)
            tools = await self.mcp_client.get_tools()
            
            self.logger.log_thought(f"✅ MCP connected - {len(tools)} tools available")
            print(f"[DEBUG] MCP Connected. Tools: {len(tools)}", flush=True)
        except Exception as e:
            print(f"[DEBUG] MCP CONNECTION ERROR: {e}", flush=True)
            import traceback
            traceback.print_exc()
            # Bug 8: Remove duplicate log + assignment (was dead code)
            self.logger.log_thought(f"⚠️ MCP not available - voice only mode")
            self.logger.log_error(f"MCP Error: {e}")
            self.mcp_client = None

    async def _get_genai_tools(self) -> List[Tool]:
        """Convert MCP tools to Google GenAI Tool objects"""
        # REASONING mode: No tools (SubAgent handles execution)
        if self.mode == "reasoning":
            return []

        # Handle case where MCP client is not available
        if not self.mcp_client:
            return []
        
        # Return cached tools if available
        if self._genai_tools_cache is not None:
            return self._genai_tools_cache
        
        # Get and cache langchain tools
        if self._langchain_tools_cache is None:
            self._langchain_tools_cache = await self.mcp_client.get_tools()
        langchain_tools = self._langchain_tools_cache
        declarations = []
        
        # Fields not supported by GenAI FunctionDeclaration
        unsupported_fields = {
            "title", "definitions", "$schema", "$defs",
            "additionalProperties", "additional_properties",
            "default", "examples", "format"
        }
        
        def clean_schema(obj):
            """Recursively remove unsupported fields from schema"""
            if isinstance(obj, dict):
                # Create a new dict without unsupported fields
                cleaned = {}
                for key, value in obj.items():
                    if key not in unsupported_fields:
                        cleaned[key] = clean_schema(value)
                return cleaned
            elif isinstance(obj, list):
                return [clean_schema(item) for item in obj]
            else:
                return obj
        
        for t in langchain_tools:
            # Handle Schema
            schema = {}
            if hasattr(t, 'args_schema') and t.args_schema:
                if hasattr(t.args_schema, 'schema'):
                    raw_schema = t.args_schema.schema()
                    schema = clean_schema(raw_schema)
                elif isinstance(t.args_schema, dict):
                    schema = clean_schema(t.args_schema)
            
            declarations.append(FunctionDeclaration(
                name=t.name,
                description=t.description,
                parameters=schema
            ))
            
        # Add local diagnostic tools if available
        if DIAGNOSTIC_TOOLS_AVAILABLE:
            declarations.extend(self._get_diagnostic_tool_declarations())
        
        # Cache and return
        self._genai_tools_cache = [Tool(function_declarations=declarations)]
        return self._genai_tools_cache
    
    def _get_diagnostic_tool_declarations(self) -> List[FunctionDeclaration]:
        """Get declarations for granular diagnostic tools from MCP_TOOL_DEFINITIONS"""
        declarations = []
        
        for tool_def in MCP_TOOL_DEFINITIONS:
            # Get parameters if defined, otherwise use empty object
            params = tool_def.get("parameters", {"type": "object", "properties": {}, "required": []})
            
            declarations.append(FunctionDeclaration(
                name=tool_def["name"],
                description=tool_def["description"],
                parameters=params
            ))
        
        self.logger.log_thought(f"📋 Loaded {len(declarations)} diagnostic tools")
        return declarations

    async def _send_instant_greeting(self, session):
        """Trigger instant greeting - runs in background for faster startup."""
        try:
            # Bug 7: Serialize session sends through _send_lock
            async with self._send_lock:
                await session.send(input="Say 'Hello! I am Echo. How can I help you?' to the user.", end_of_turn=True)
        except asyncio.CancelledError:
            pass  # Normal teardown
        except Exception as e:
            print(f"[ERROR] Failed to send intro: {e}", flush=True)
    
    async def _heartbeat_loop(self, session):
        """Send periodic empty/silence audio to keep connection alive during SubAgent execution."""
        try:
            while True:
                await asyncio.sleep(5)  # Every 5 seconds
                # Send empty audio frame to keep connection alive
                try:
                    silence = b'\x00' * 512  # 512 bytes of silence
                    # Bug 7: Serialize session sends through _send_lock
                    async with self._send_lock:
                        await session.send(
                            input={"data": silence, "mime_type": "audio/pcm"},
                            end_of_turn=False
                        )
                except:
                    pass  # Ignore send errors during shutdown
        except asyncio.CancelledError:
            pass  # Normal shutdown

    async def _send_audio(self, session):
        """Send mic audio to session (working pattern)"""
        try:
            async with self.audio as audio:
                await audio.start_recording()
                while True:
                    chunk = await audio.get_audio_chunk()
                    # Bug 7: Serialize session sends through _send_lock
                    async with self._send_lock:
                        await session.send(
                            input={"data": chunk, "mime_type": "audio/pcm"},
                            end_of_turn=False
                        )
        except asyncio.CancelledError:
            self.logger.log_thought("Audio sending cancelled")
        except Exception as e:
            # Graceful handling for WebSocket disconnection
            err_str = str(e).lower()
            if "policy violation" in err_str or "1008" in err_str:
                self.logger.log_error(f"⚠️ Gemini Policy Violation (1008): {e}")
                self.logger.log_thought(f"⚠️ Connection closed due to policy violation (1008)")
            elif "close" in err_str or "aborted" in err_str or "1007" in err_str or "1011" in err_str:
                self.logger.log_thought("🔌 Session disconnected")
            else:
                self.logger.log_error(f"Send Audio Error: {e}")
            raise

    async def _receive_loop(self, session):
        """Receive audio, transcriptions, and tool calls"""
        try:
            # CRITICAL: while True wrapper for multi-turn conversation!
            # session.receive() returns an iterator for ONE turn only
            while True:
                async for response in session.receive():
                    # Bug 1: Skip processing while SubAgent holds the lock
                    if self._subagent_lock.locked():
                        continue
                        
                    # 1. Handle server content (audio/text from model)
                    if response.server_content:
                        server_content = response.server_content
                        
                        # Handle model turn (audio/text)
                        if server_content.model_turn:
                            for part in server_content.model_turn.parts:
                                # Audio data
                                if part.inline_data and part.inline_data.data:
                                    # Queue audio for playback
                                    audio_data = part.inline_data.data
                                    if isinstance(audio_data, str):
                                        import base64
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
                                # Store for fallback routing context
                                self._output_transcript = transcript
                        
                        # Handle input audio transcription (what user said)
                        if hasattr(server_content, 'input_transcription') and server_content.input_transcription:
                            transcript = server_content.input_transcription.text
                            # DEBUG: Log all input transcriptions
                            print(f"[DEBUG] input_transcription received: '{transcript}'", flush=True)
                            if transcript and len(transcript.strip()) > 5:
                                self.logger.log_thought(f"🎤 You: {transcript}")
                                
                                # REASONING MODE: Delegate to SubAgent immediately
                                if self.mode == "reasoning" and self.multi_agent_graph:
                                    # Acknowledge and delegate (don't await - let it run in background)
                                    asyncio.create_task(
                                        self._delegate_to_subagent(session, transcript.strip())
                                    )
                                else:
                                    # FAST mode: Store for potential tool execution
                                    self._pending_transcript = transcript
                        
                        # Handle turn complete
                        if server_content.turn_complete:
                            self.logger.log_thought("✅ Turn complete")
                            # Stop playback after turn completes
                            await asyncio.sleep(0.3)
                            self.audio.stop_playback()
                            # Clear pending transcript after turn completes
                            self._pending_transcript = None

                        
                        # Handle interruption
                        if hasattr(server_content, 'interrupted') and server_content.interrupted:
                            self.logger.log_thought("🛑 Interrupted")
                            self.audio.stop_playback()
                    
                    # 2. Handle tool calls
                    if response.tool_call:
                        tool_names = [fc.name for fc in response.tool_call.function_calls]
                        print(f"[DEBUG] ✅ Tool call received: {tool_names}", flush=True)
                        
                        # Check if any tool is a diagnostic tool - if so, skip routing
                        diagnostic_tool_names = {t["name"] for t in MCP_TOOL_DEFINITIONS} if DIAGNOSTIC_TOOLS_AVAILABLE else set()
                        is_diagnostic_call = any(name in diagnostic_tool_names for name in tool_names)
                        
                        # INTERCEPT: Check routing ONLY for non-diagnostic tools
                        if not is_diagnostic_call and self._pending_transcript and self.multi_agent_graph:
                            handled = await self._route_complex_task(session)
                            if handled:
                                # Send dummy response to satisfy the tool call turn
                                dummy_responses = [
                                    FunctionResponse(name=fc.name, id=fc.id, response={"result": "Task escalated to Reasoning Agent."}) 
                                    for fc in response.tool_call.function_calls
                                ]
                                try:
                                    # Bug 7: Serialize session sends through _send_lock
                                    async with self._send_lock:
                                        await session.send(input=LiveClientToolResponse(function_responses=dummy_responses))
                                except Exception as e:
                                    self.logger.log_error(f"Failed to clear tool call: {e}")
                                continue
                        
                        # Bug 6: Run tool calls in background so receive loop
                        # continues consuming messages. Safe because Bug 7's
                        # _send_lock serializes all session.send() calls.
                        asyncio.create_task(self._handle_tool_call(session, response.tool_call))
                        
        except asyncio.CancelledError:
            self.logger.log_thought("Receive loop cancelled")
        except Exception as e:
            # Graceful handling for WebSocket disconnection
            err_str = str(e).lower()
            if "close" in err_str or "aborted" in err_str or "no close frame" in err_str or "1007" in err_str or "1011" in err_str:
                self.logger.log_thought("🔌 Session ended (timeout or disconnect)")
            else:
                self.logger.log_error(f"Receive error: {e}")
                import traceback
                self.logger.log_error(traceback.format_exc())

    async def _handle_tool_call(self, session, tool_call):
        """Execute tool and send response"""
        # Build map of diagnostic tools from MCP_TOOL_DEFINITIONS
        diagnostic_tools = {}
        if DIAGNOSTIC_TOOLS_AVAILABLE:
            for tool_def in MCP_TOOL_DEFINITIONS:
                diagnostic_tools[tool_def["name"]] = tool_def["function"]
        
        # Bug 11: Reuse cached tools instead of fetching on every call
        if self._langchain_tools_cache is None and self.mcp_client:
            self._langchain_tools_cache = await self.mcp_client.get_tools()
        langchain_tools = self._langchain_tools_cache or []
        tool_map = {t.name: t for t in langchain_tools}
        
        function_responses = []
        
        for fc in tool_call.function_calls:
            name = fc.name
            args = fc.args or {}
            
            self.logger.log_thought(f"🔧 Tool: {name}")
            self.logger.log_action(f"Executing {name}", args)
            
            try:
                # Check diagnostic tools first
                if name in diagnostic_tools:
                    self.logger.log_thought(f"🏥 Running diagnostic: {name}")
                    tool_func = diagnostic_tools[name]
                    # Execute with timeout to prevent WebSocket disconnect
                    try:
                        if args:
                            result = await asyncio.wait_for(
                                asyncio.to_thread(tool_func, **args), 
                                timeout=30.0
                            )
                        else:
                            result = await asyncio.wait_for(
                                asyncio.to_thread(tool_func), 
                                timeout=30.0
                            )
                    except asyncio.TimeoutError:
                        result = f"Tool '{name}' timed out after 30 seconds. Try a more specific path."
                        self.logger.log_error(result)
                    content = str(result)
                    self.logger.log_observation(f"Result: {content[:200]}...")
                    function_responses.append(FunctionResponse(
                        name=name,
                        id=fc.id,
                        response={"result": content}
                    ))
                    continue
                
                # Fall back to MCP tools
                if name not in tool_map:
                    raise ValueError(f"Tool {name} not found")
                
                # Execute via LangChain Tool with timeout
                tool = tool_map[name]
                try:
                    if hasattr(tool, "ainvoke"):
                        result = await asyncio.wait_for(tool.ainvoke(args), timeout=45.0)
                    else:
                        result = await asyncio.wait_for(
                            asyncio.to_thread(tool.invoke, args), 
                            timeout=45.0
                        )
                except asyncio.TimeoutError:
                    result = f"Tool execution timed out after 45 seconds"
                    self.logger.log_error(result)
                
                content = str(result)
                # Truncate large results to prevent WebSocket payload errors
                MAX_RESULT_LENGTH = 8000
                if len(content) > MAX_RESULT_LENGTH:
                    content = content[:MAX_RESULT_LENGTH] + f"... [truncated, {len(str(result))} total chars]"
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
                
        # Send result back with connection error handling
        try:
            tool_response = LiveClientToolResponse(function_responses=function_responses)
            # Bug 7: Serialize session sends through _send_lock
            async with self._send_lock:
                await session.send(input=tool_response)
        except Exception as e:
            self.logger.log_error(f"Failed to send tool response: {e}")
    
    async def _delegate_to_subagent(self, session, transcript: str):
        """
        REASONING MODE: Delegate user input to SubAgent.
        
        Bug 1: Uses asyncio.Lock for mutual exclusion. If a second call
        arrives while the first is still running, it will wait rather than
        racing on mute/unmute state.
        
        Flow:
        1. Acquire lock (mutes Voice Agent)
        2. Quick acknowledgement  
        3. Run SubAgent
        4. Say "Done!" and release lock (unmutes)
        """
        self.logger.log_thought(f"🧠 Delegating to SubAgent: {transcript[:50]}...")
        
        # Bug 1: Acquire lock -- acts as mute guard with mutual exclusion
        async with self._subagent_lock:
            self.audio.pause_recording()  # Stop mic to prevent noise
            
            try:
                # 1. Quick acknowledgement
                await self._speak_response(session, "On it!")
                
                # 2. Run SubAgent
                self.logger.log_thought("⚙️ SubAgent executing...")
                result = await self.multi_agent_graph.run_for_voice(transcript)
                
                # 3. Simple completion acknowledgement
                self.logger.log_thought(f"✅ SubAgent result: {result[:80]}...")
                try:
                    await self._speak_response(session, "Done!")
                except Exception as speak_err:
                    self.logger.log_thought(f"📢 Could not speak 'Done' (session may have closed)")
                
            except Exception as e:
                self.logger.log_error(f"SubAgent error: {e}")
                try:
                    await self._speak_response(session, "Error occurred.")
                except:
                    pass
            finally:
                # Resume recording when lock is released (unmute)
                self.audio.resume_recording()
    
    async def _route_complex_task(self, session):
        """
        Route task to multi-agent graph if needed.
        
        In REASONING mode (tools=[]), ALWAYS escalate.
        In FAST mode, only escalate if complexity is detected.
        """
        # Get transcript: prefer input, fallback to output
        transcript = self._pending_transcript
        if not transcript and self._output_transcript:
            transcript = self._output_transcript
            self.logger.log_thought(f"📨 Using model echo as context: {transcript[:50]}...")
        
        self._pending_transcript = ""  # Clear pending
        self._output_transcript = ""   # Clear output
        
        if not transcript or not self.multi_agent_graph:
            self.logger.log_thought(f"🔍 Route check: transcript='{transcript[:30] if transcript else 'EMPTY'}', graph={self.multi_agent_graph is not None}")
            return False
        
        # Skip very short transcripts (likely intro greeting echoes, not user commands)
        if len(transcript.strip()) < 10:
            self.logger.log_thought(f"⏭️ Skipping short transcript: '{transcript.strip()}'")
            return False
        
        # REASONING Mode: Force escalation (no complexity check)
        if self.mode == "reasoning":
            self.logger.log_thought(f"🧠 REASONING: Forcing SubAgent route | {transcript[:50]}...")
        else:
            # FAST Mode: Check complexity before escalating
            from src.agent.task_router import TaskComplexity
            
            routing = await self.task_router.get_routing_strategy(transcript)
            
            if routing == TaskComplexity.SIMPLE:
                # Simple tasks handled by main loop - no escalation
                self.task_router.reset_failure_count()
                return False
        
        # Escalate to multi-agent graph
        self.logger.log_thought(f"🔀 Escalating to multi-agent: {transcript[:50]}...")
        
        # Run in background to avoid blocking the receive loop (which causes timeouts)
        # Bug 4: Cancel any in-flight graph task before starting a new one
        if self._graph_task and not self._graph_task.done():
            self._graph_task.cancel()
        self._graph_task = asyncio.create_task(
            self._run_graph_in_background(session, transcript)
        )
        
        self.task_router.reset_failure_count()
        return True

    async def _run_graph_in_background(self, session, transcript):
        """Run multi-agent graph without blocking the main loop"""
        try:
            # Run through planner + executor
            response = await self.multi_agent_graph.run_for_voice(transcript)
            
            # Speak the response back to user
            await self._speak_response(session, response)
            
        except Exception as e:
            self.logger.log_error(f"Multi-agent error: {e}")
            try:
                await self._speak_response(session, "Sorry, I encountered an error completing that task.")
            except:
                pass
    
    async def _speak_response(self, session, text: str):
        """Send text to Gemini Live to speak back to user."""
        try:
            # Bug 7: Serialize session sends through _send_lock
            async with self._send_lock:
                await session.send(input=text, end_of_turn=True)
        except Exception as e:
            self.logger.log_error(f"Failed to speak response: {e}")
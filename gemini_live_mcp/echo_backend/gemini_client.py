"""
Gemini Live API Client using Google GenAI SDK
Handles real-time speech-to-speech communication
Supports both free API key and paid Vertex AI
"""

import asyncio
import json
import logging
from typing import Callable, Any, Optional

from google import genai
from google.genai import types
from google.oauth2 import service_account

from classroom_tools import CLASSROOM_TOOLS_DEF, TOOL_FUNCTIONS

class GeminiLiveClient:
    """Client for Gemini Live API using official SDK"""
    
    def __init__(self, api_key: Optional[str] = None, project_id: Optional[str] = None, 
                 location: Optional[str] = None, credentials_json: Optional[str] = None):
        """
        Initialize Gemini Live Client
        
        For free API (Google AI Studio):
            api_key: Your API key from AI Studio
        
        For paid Vertex AI:
            project_id: GCP project ID
            location: Region (e.g., 'us-central1')
            credentials_json: Service account credentials as JSON string
        """
        if project_id and credentials_json:
            # Vertex AI (Paid)
            print(f"🔐 Initializing Gemini Live with Vertex AI (Project: {project_id}, Location: {location})")
            credentials_dict = json.loads(credentials_json)
            
            # Define required OAuth scopes for Vertex AI and Generative AI
            scopes = [
                "https://www.googleapis.com/auth/generative-language",
                "https://www.googleapis.com/auth/cloud-platform",
            ]
            
            # Load credentials with explicit scopes
            credentials = service_account.Credentials.from_service_account_info(
                credentials_dict,
                scopes=scopes
            )
            
            self.client = genai.Client(
                vertexai=True,
                project=project_id,
                location=location,
                credentials=credentials
            )
        elif api_key:
            # Free API Key (Google AI Studio)
            print(f"🔑 Initializing Gemini Live with free API key")
            self.client = genai.Client(api_key=api_key, http_options={'api_version': 'v1beta'})
        else:
            raise ValueError("Must provide either api_key OR (project_id + credentials_json)")
        
        self.model = "gemini-live-2.5-flash-native-audio"
        self.system_prompt = """You are a helpful, friendly AI assistant having a natural voice conversation. 
Respond naturally and conversationally, as if talking to a friend. Keep responses concise and engaging. 
Listen carefully and respond appropriately to what the user says. You can be interrupted at any time."""
        self.session = None
        self._ctx = None
        self._response_queue = asyncio.Queue()
        
    async def start_session(self):
        """Start the Live API session with automatic VAD"""
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Puck"
                    )
                )
            ),
            system_instruction=types.Content(
                parts=[types.Part(text=self.system_prompt)]
            ),
            # Enable automatic VAD for natural conversation
            realtime_input_config=types.RealtimeInputConfig(
                automatic_activity_detection=types.AutomaticActivityDetection(
                    prefix_padding_ms=100,      # Capture speech onset (100ms)
                    silence_duration_ms=300     # Detect speech completion (300ms)
                )
            )
            # Note: Tools removed from Live API config due to known issues with function calling
            # causing sessions to hang or disconnect. Tools are available in Chat API instead.
            # tools=[CLASSROOM_TOOLS_DEF]
        )
        
        # Start session using manual context management
        self._ctx = self.client.aio.live.connect(
            model=self.model,
            config=config
        )
        self.session = await self._ctx.__aenter__()
        print("✅ Connected to Gemini Live API via SDK")
        return self.session

    async def send_audio(self, audio_data: str, turn_complete: bool = False):
        """Send audio chunk to Gemini"""
        if not self.session:
            raise RuntimeError("Session not started")
            
        import base64
        try:
            if audio_data:
                pcm_data = base64.b64decode(audio_data)
                await self.session.send(
                    input={"data": pcm_data, "mime_type": "audio/pcm;rate=16000"}, 
                    end_of_turn=turn_complete
                )
            elif turn_complete:
                # Send text "." to signal end of turn explicitly
                # This forces the model to process the accumulated audio context
                await self.session.send(input=".", end_of_turn=True)
                
        except asyncio.CancelledError:
            print("Send audio cancelled")
            raise
        except Exception as e:
            print(f"Error sending audio: {e}")
            import traceback
            traceback.print_exc()
            raise

    async def receive_loop(self, callback: Callable[[dict], Any]):
        """Listen for responses from Gemini - runs indefinitely until cancelled"""
        if not self.session:
            raise RuntimeError("Session not started")
            
        print("🎧 Starting receive loop...")
        try:
            async for response in self.session.receive():
                try:
                    server_content = response.server_content
                    if server_content is None:
                        # Check for tool call on response object (fallback)
                        tool_call = getattr(response, 'tool_call', None)
                        if tool_call:
                            print(f"🛠️ Tool call received in response")
                            for fc in tool_call.function_calls:
                                await self._handle_function_call(fc)
                        continue

                    model_turn = server_content.model_turn
                    if model_turn:
                        for part in model_turn.parts:
                            # Handle Audio
                            if part.inline_data:
                                print("🎵 Received audio chunk from Gemini")
                                import base64
                                b64_data = base64.b64encode(part.inline_data.data).decode('utf-8')
                                await callback({
                                    "type": "audio",
                                    "data": b64_data,
                                    "mime_type": "audio/pcm"
                                })
                            
                            # Handle Function Call (Standard Part)
                            if part.function_call:
                                print(f"🛠️ Function call received in part: {part.function_call.name}")
                                await self._handle_function_call(part.function_call)

                    # Handle Tool Call (Top-level Response field if available)
                    tool_call = getattr(response, 'tool_call', None)
                    if tool_call:
                        print(f"🛠️ Tool call received in response")
                        for fc in tool_call.function_calls:
                            await self._handle_function_call(fc)

                    if server_content.turn_complete:
                        print("🏁 Turn complete received")
                        await callback({"type": "turn_complete"})
                        # Continue listening for next turn - don't return!
                        
                except asyncio.CancelledError:
                    print("Receive loop cancelled")
                    raise
                except Exception as e:
                    print(f"Error processing response in receive loop: {e}")
                    import traceback
                    traceback.print_exc()
                    # Continue processing other messages
            
            # If the async for loop ends naturally (connection closed by server)
            print("🔌 Gemini Live API closed the connection")
                    
        except asyncio.CancelledError:
            print("Receive loop cancelled")
            raise
        except Exception as e:
            print(f"Fatal error in receive loop: {e}")
            import traceback
            traceback.print_exc()
            raise

    async def _handle_function_call(self, fc):
        """Execute a function call and send the response"""
        function_responses = []
        
        handler = TOOL_FUNCTIONS.get(fc.name)
        if handler:
            print(f"🛠️ Executing tool: {fc.name}")
            try:
                # Extract arguments
                args = fc.args
                # Ensure args is a dict (SDK might return a specific type)
                if hasattr(args, 'to_dict'):
                    args = args.to_dict()
                elif not isinstance(args, dict):
                    # If None or other, empty dict
                    args = {}
                    
                result = await handler(**args)
                print(f"✅ Tool execution successful")
            except Exception as e:
                result = {"error": str(e)}
                print(f"❌ Tool execution failed: {e}")
        else:
            print(f"❌ Unknown tool: {fc.name}")
            result = {"error": f"Unknown tool: {fc.name}"}

        function_responses.append(types.FunctionResponse(
            id=fc.id,
            name=fc.name,
            response=result
        ))
        
            # Send tool response
        if function_responses:
            print(f"📤 Sending tool response")
            try:
                # Try specific method for tool responses first (likely for v1beta)
                if hasattr(self.session, 'send_tool_response'):
                    await self.session.send_tool_response(function_responses=function_responses)
                    return

                # Fallback to send() with manual Part construction if method missing
                # Note: send() seems to struggle with Content/List inputs in some versions
                parts = [types.Part(function_response=fr) for fr in function_responses]
                await self.session.send(input=parts, end_of_turn=True)
                
            except Exception as e:
                print(f"Error sending tool response: {e}")
                # Last resort: Try send_client_content (low-level)
                try:
                    parts = [types.Part(function_response=fr) for fr in function_responses]
                    await self.session.send_client_content(
                        turns=[types.Turn(parts=parts)],
                        turn_complete=True
                    )
                    print("✅ Sent via send_client_content")
                except Exception as e2:
                    print(f"Critical error sending tool response: {e2}")

    async def close(self):
        """Close the session"""
        if self._ctx:
            try:
                await self._ctx.__aexit__(None, None, None)
            except Exception as e:
                print(f"Error closing Gemini Live session: {e}")
            finally:
                self._ctx = None
                self.session = None
                print("✅ Gemini Live session closed")

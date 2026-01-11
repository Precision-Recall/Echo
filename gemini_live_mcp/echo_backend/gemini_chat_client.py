import asyncio
import json
import logging
from typing import Optional
from google import genai
from google.genai import types
from google.oauth2 import service_account
from classroom_tools import CLASSROOM_TOOLS_DEF, TOOL_FUNCTIONS


def get_user_friendly_error(error_message: str) -> str:
    """Extract user-friendly error message from exception"""
    error_str = str(error_message).lower()
    
    # Rate limit / quota errors
    if '429' in error_str or 'quota' in error_str or 'resource_exhausted' in error_str:
        return 'Rate limit reached. Please try again in a moment.'
    
    # Authentication errors
    if '401' in error_str or 'unauthorized' in error_str or 'api key' in error_str:
        return 'Authentication error. Please check API configuration.'
    
    # Network/connection errors
    if 'network' in error_str or 'connection' in error_str or 'timeout' in error_str:
        return 'Connection error. Please check your internet and try again.'
    
    # Generic error
    return 'An error occurred. Please try again.'


class GeminiChatClient:
    def __init__(self, api_key: Optional[str] = None,
                 project_id: Optional[str] = None, location: Optional[str] = None, 
                 credentials_json: Optional[str] = None):
        """
        Initialize Gemini Chat Client
        
        For free API (Google AI Studio):
            api_key: Your API key from AI Studio
        
        For paid Vertex AI:
            project_id: GCP project ID
            location: Region (e.g., 'us-central1')
            credentials_json: Service account credentials as JSON string
        """
        if project_id and credentials_json:
            # Vertex AI (Paid)
            print(f"🔐 Initializing Gemini Chat with Vertex AI (Project: {project_id}, Location: {location})")
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
            print(f"🔑 Initializing Gemini Chat with free API key")
            self.client = genai.Client(api_key=api_key)
        else:
            raise ValueError("Must provide either api_key OR (project_id + credentials_json)")
        
        # Use gemini-2.5-flash-lite for higher rate limits
        self.model = "gemini-2.5-flash-lite" 
        
        # User credentials for Firestore token retrieval
        self.user_email = None
        self.firebase_token = None
        
        # System prompt
        system_prompt = (
            "You are Echo, an AI assistant for Google Workspace education tools.\n\n"
            
            "# Core Behavior\n"
            "1. LIST/VIEW requests: Call tool → Present results in a clear list → STOP\n"
            "2. CREATE requests: Call the appropriate form tool immediately\n"
            "3. FORM tools: Call directly without generating explanatory text first\n"
            "4. Multi-step workflows: Call all tools in sequence without text between them\n\n"
            
            "# Tools (call by exact name, no prefixes)\n"
            "Classroom: list_courses, show_coursework_form, show_announcements_form, show_assignment_form, show_course_form, create_course\n"
            "Docs: create_google_doc | Sheets: create_google_sheet | Forms: create_google_form\n\n"
            
            "# Examples\n"
            "User: 'list courses' → Call list_courses() → Display: '1. Course A\\n2. Course B' → STOP\n"
            "User: 'create assignment' → Call show_assignment_form() → STOP (no text needed)\n"
            "User: 'show assignments' → Call show_coursework_form() → STOP (no text needed)\n"
            "User: 'view announcements' → Call show_announcements_form() → STOP (no text needed)\n"
            "User: 'create course' → Call show_course_form() → STOP (no text needed)\n"
            "User: 'List all coursework for course ID: 123' → Call list_coursework(course_id='123') → Display results → STOP\n"
            "User: 'List all announcements for course ID: 123' → Call list_announcements(course_id='123') → Display results → STOP\n\n"
            
            "# File Attachments\n"
            "When creating assignments, if the user message contains 'File IDs: xxx,yyy,zzz':\n"
            "1. Extract the comma-separated file IDs from the message\n"
            "2. Pass them as the 'file_ids' parameter to create_coursework()\n"
            "Example: If message has 'File IDs: 1ABC,2DEF', call create_coursework(file_ids='1ABC,2DEF')\n\n"
            
            "# Response Format\n"
            "Use markdown: **bold**, - bullets, # headings, ``` code\n\n"
            
            "# Examples\n"
            "✓ 'list courses' → Call list_courses(), show results, STOP\n"
            "✓ 'create assignment' → Call show_assignment_form(), form appears with courses\n"
            "✓ 'create course' → Call show_course_form(), form appears with student lists\n"
            "✓ 'create study guide on Python' → create_google_doc() with content\n"
            "✓ 'show them' (after listing) → Display already retrieved data"
        )
        
        config_params = {
            "tools": [CLASSROOM_TOOLS_DEF],
            "system_instruction": system_prompt,
            "temperature": 0.7,
            "automatic_function_calling": types.AutomaticFunctionCallingConfig(disable=True)
        }
        
        self.chat = self.client.aio.chats.create(
            model=self.model,
            config=types.GenerateContentConfig(**config_params)
        )
    
    def set_user_credentials(self, user_email: str, firebase_token: str):
        """
        Store user credentials for Firestore token retrieval.
        These will be passed to classroom tools when they are called.
        
        Args:
            user_email: User's email address
            firebase_token: Firebase ID token for authentication
        """
        self.user_email = user_email
        self.firebase_token = firebase_token
        print(f"✅ User credentials set for: {user_email}")
    
    async def send_message(self, message_input, callback):
        """
        Send message and stream response + tool calls.
        message_input: str (text) or list of Parts (tool responses)
        """
        try:
            current_input = message_input
            
            while True:
                # We use send_message_stream. The SDK manages history.
                # Note: send_message_stream returns a coroutine that needs to be awaited
                response_stream = await self.chat.send_message_stream(current_input)
                
                tool_calls = []
                
                async for chunk in response_stream:
                    # Check for function calls first (in candidates)
                    if chunk.candidates:
                        for cand in chunk.candidates:
                            if cand.content and cand.content.parts:
                                for part in cand.content.parts:
                                    # Check if this part is a thought (thinking process)
                                    if hasattr(part, 'thought') and part.thought:
                                        await callback({
                                            "type": "thought",
                                            "thought": part.thought
                                        })
                                    # Check if this part is a function call
                                    elif part.function_call:
                                        tool_calls.append(part.function_call)
                                    # Check if this part is text
                                    elif part.text:
                                        await callback({"type": "text_chunk", "text": part.text})
                
                # If no tool calls, we are done with this turn
                if not tool_calls:
                    break
                
                # Execute tools
                function_responses = []
                for fc in tool_calls:
                    print(f"🤖 Chat Tool Call: {fc.name}")
                    
                    # Convert args for UI display
                    args_dict = {}
                    if hasattr(fc.args, 'to_dict'): args_dict = fc.args.to_dict()
                    elif isinstance(fc.args, dict): args_dict = fc.args
                    
                    # Notify UI: Tool Started
                    await callback({
                        "type": "tool_start", 
                        "tool": fc.name, 
                        "args": args_dict
                    })
                    
                    handler = TOOL_FUNCTIONS.get(fc.name)
                    result = {"error": "Unknown tool"}
                    if handler:
                        try:
                            print(f"  📥 Tool args: {list(args_dict.keys())}")
                            
                            # Add user credentials to tool arguments if available
                            # This allows tools to retrieve tokens from Firestore
                            if self.user_email and self.firebase_token:
                                args_dict["user_email"] = self.user_email
                                args_dict["firebase_token"] = self.firebase_token
                                print(f"  🔐 Passing user credentials to tool: {self.user_email}")
                            
                            result = await handler(**args_dict)
                        except Exception as e:
                            print(f"❌ Error executing tool {fc.name}: {e}")
                            import traceback
                            traceback.print_exc()
                            result = {"error": str(e)}
                    
                    # Notify UI: Tool Finished
                    await callback({
                        "type": "tool_end", 
                        "tool": fc.name, 
                        "result": result
                    })
                    
                    function_responses.append(types.FunctionResponse(
                        id=fc.id,
                        name=fc.name,
                        response=result
                    ))
                
                # Prepare inputs for the NEXT loop iteration (Tool Responses)
                current_input = [types.Part(function_response=fr) for fr in function_responses]
                
        except asyncio.CancelledError:
            print("GeminiChatClient message processing cancelled")
            raise
        except Exception as e:
            print(f"Error in GeminiChatClient: {e}")
            import traceback
            traceback.print_exc()
            try:
                friendly_error = get_user_friendly_error(str(e))
                await callback({"type": "error", "text": friendly_error})
            except:
                pass  # Don't raise if callback fails
            raise  # Re-raise the original exception


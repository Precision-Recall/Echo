import asyncio
import json
import logging
from google import genai
from google.genai import types
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
    def __init__(self, api_key, enable_thinking=True):
        self.client = genai.Client(api_key=api_key)
        # Use gemini-2.5-flash with thinking enabled via system instruction
        self.model = "gemini-2.5-flash" 
        self.enable_thinking = enable_thinking
        
        # User credentials for Firestore token retrieval
        self.user_email = None
        self.firebase_token = None
        
        # Use .aio for async client
        system_prompt = (
            "You are Echo, a helpful AI assistant. You have access to Google Classroom tools. "
            "When solving complex problems, think through them step by step before providing your answer. "
            "\n\n**CRITICAL Assignment Creation Workflow**: "
            "When a user wants to create an assignment, coursework, homework, or task, follow these EXACT steps:"
            "\n1. Call list_courses()"
            "\n2. Extract the 'courses' array from the response"
            "\n3. Call show_assignment_form(courses_data=<the courses array>)"
            "\n\n**CRITICAL Course Creation Workflow**: "
            "When a user wants to create a NEW COURSE or NEW CLASS:"
            "\n1. Call show_course_form() - This will show them a form to fill in"
            "\n2. Do NOT ask for details conversationally"
            "\n3. Only use create_course when you receive completed form data"
            "\n\n**CRITICAL**: "
            "\n- For assignments: Need to call list_courses first to show dropdown"
            "\n- For courses: Just call show_course_form directly (no prerequisite)"
            "\n- Pass ARRAY of course objects for assignments, NOT the entire response object"
            "\n\nDo NOT: Ask for details conversationally, use create_* tools directly without forms."
            "\n\nBe concise and helpful."
        ) if enable_thinking else (
            "You are Echo, a helpful AI assistant. You have access to Google Classroom tools. "
            "\n\n**CRITICAL Assignment Creation Workflow**: "
            "When a user wants to create an assignment, coursework, homework, or task, follow these EXACT steps:"
            "\n1. Call list_courses()"
            "\n2. Extract the 'courses' array from the response"
            "\n3. Call show_assignment_form(courses_data=<the courses array>)"
            "\n\n**CRITICAL Course Creation Workflow**: "
            "When a user wants to create a NEW COURSE or NEW CLASS:"
            "\n1. Call show_course_form() - This will show them a form to fill in"
            "\n2. Do NOT ask for details conversationally"
            "\n3. Only use create_course when you receive completed form data"
            "\n\n**CRITICAL**: "
            "\n- For assignments: Need to call list_courses first to show dropdown"
            "\n- For courses: Just call show_course_form directly (no prerequisite)"
            "\n- Pass ARRAY of course objects for assignments, NOT the entire response object"
            "\n\nDo NOT: Ask for details conversationally, use create_* tools directly without forms."
            "\n\nBe concise and helpful."
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
                # Note: send_message_stream returns an async generator, don't await it
                response_stream = self.chat.send_message_stream(current_input)
                
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
                            if fc.name == "show_assignment_form":
                                print(f"  📋 courses_data length: {len(args_dict.get('courses_data', []))}")
                            
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


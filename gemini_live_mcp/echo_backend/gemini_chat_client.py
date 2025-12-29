import asyncio
import json
import logging
from google import genai
from google.genai import types
from classroom_tools import CLASSROOM_TOOLS_DEF, TOOL_FUNCTIONS

class GeminiChatClient:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash" 
        # Use .aio for async client
        self.chat = self.client.aio.chats.create(
            model=self.model,
            config=types.GenerateContentConfig(
                tools=[CLASSROOM_TOOLS_DEF],
                system_instruction="You are Echo, a helpful AI assistant. You have access to Google Classroom tools. Be concise and helpful.",
                temperature=0.7,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
            )
        )
    
    async def send_message(self, message_input, callback):
        """
        Send message and stream response + tool calls.
        message_input: str (text) or list of Parts (tool responses)
        """
        try:
            current_input = message_input
            
            while True:
                # We use send_message_stream. The SDK manages history.
                response_stream = await self.chat.send_message_stream(current_input)
                
                tool_calls = []
                
                async for chunk in response_stream:
                    # Check for text content
                    if chunk.text:
                        await callback({"type": "text_chunk", "text": chunk.text})
                    
                    # Check for function calls
                    # In v1beta/standard, we look in candidates
                    if chunk.candidates:
                        for cand in chunk.candidates:
                            if cand.content and cand.content.parts:
                                for part in cand.content.parts:
                                    if part.function_call:
                                        tool_calls.append(part.function_call)
                
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
                            result = await handler(**args_dict)
                        except Exception as e:
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
                
        except Exception as e:
            print(f"Error in GeminiChatClient: {e}")
            await callback({"type": "error", "text": f"Chat Error: {str(e)}"})


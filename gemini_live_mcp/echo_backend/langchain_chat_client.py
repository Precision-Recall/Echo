"""
LangChain-based Chat Client for Echo
Uses proper tool definitions and agent for reliable tool calling
"""
import asyncio
import json
from typing import Optional, Callable, Any, Dict, List
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_vertexai import ChatVertexAI

# Import existing tool functions
from classroom_tools import (
    list_courses as _list_courses,
    get_course as _get_course,
    show_coursework_form as _show_coursework_form,
    list_coursework as _list_coursework,
    get_coursework as _get_coursework,
    show_announcements_form as _show_announcements_form,
    list_announcements as _list_announcements,
    list_submissions as _list_submissions,
    create_coursework as _create_coursework,
    show_assignment_form as _show_assignment_form,
    create_course as _create_course,
    show_course_form as _show_course_form,
    create_google_doc as _create_google_doc,
    create_google_sheet as _create_google_sheet,
)


def get_user_friendly_error(error_message: str) -> str:
    """Extract user-friendly error message from exception"""
    error_str = str(error_message).lower()
    
    if '429' in error_str or 'quota' in error_str or 'resource_exhausted' in error_str:
        return 'Rate limit reached. Please try again in a moment.'
    if '401' in error_str or 'unauthorized' in error_str or 'api key' in error_str:
        return 'Authentication error. Please check API configuration.'
    if 'network' in error_str or 'connection' in error_str or 'timeout' in error_str:
        return 'Connection error. Please check your internet and try again.'
    return 'An error occurred. Please try again.'


class LangChainChatClient:
    """LangChain-based chat client with proper tool calling"""
    
    def __init__(self, api_key: Optional[str] = None,
                 project_id: Optional[str] = None, location: Optional[str] = None,
                 credentials_json: Optional[str] = None):
        """
        Initialize LangChain Chat Client
        
        For free API (Google AI Studio):
            api_key: Your API key from AI Studio
        
        For paid Vertex AI:
            project_id: GCP project ID
            location: Region (e.g., 'us-central1')
            credentials_json: Service account credentials as JSON string
        """
        self.user_email = None
        self.firebase_token = None
        self.message_history: List = []
        
        # Model configuration
        model_name = "gemini-2.0-flash"
        
        if project_id and credentials_json:
            # Vertex AI (Paid)
            print(f"🔐 Initializing LangChain Chat with Vertex AI (Project: {project_id}, Location: {location})")
            from google.oauth2 import service_account
            
            credentials_dict = json.loads(credentials_json)
            
            # Create proper credentials object with scopes
            credentials = service_account.Credentials.from_service_account_info(
                credentials_dict,
                scopes=[
                    "https://www.googleapis.com/auth/generative-language",
                    "https://www.googleapis.com/auth/cloud-platform",
                ]
            )
            
            self.llm = ChatVertexAI(
                model=model_name,
                project=project_id,
                location=location,
                credentials=credentials,  # Pass credentials object, not dict
                temperature=0.7,
                max_output_tokens=8192,
                streaming=True,
            )
        elif api_key:
            # Free API Key (Google AI Studio)
            print(f"🔑 Initializing LangChain Chat with free API key")
            self.llm = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key,
                temperature=0.7,
                max_output_tokens=8192,
                streaming=True,
            )
        else:
            raise ValueError("Must provide either api_key OR (project_id + credentials_json)")
        
        # Create tools with bound credentials
        self.tools = self._create_tools()
        
        # Bind tools to the model
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        
        # System prompt
        self.system_prompt = """You are Echo, a friendly AI assistant for Google Workspace education tools.

# Core Behavior
1. Be conversational and friendly - respond naturally to greetings and casual messages
2. Only use tools when the user explicitly requests an action
3. Never call tools automatically without a clear user request
4. For greetings (hi, hello, hey), respond warmly without calling any tools
5. For questions about capabilities, explain what you can do without calling tools

# CRITICAL: Form Tools
When calling these form tools, DO NOT generate ANY text before or after the tool call:
- show_assignment_form
- show_course_form
- show_coursework_form
- show_announcements_form

These tools display forms to the user. Just call the tool directly without any explanatory text.

# When to Use Tools
ONLY call tools when the user clearly requests one of these actions:
- "list courses" / "show courses" → Call list_courses()
- "create assignment" / "new assignment" → Call show_assignment_form() (NO TEXT, just call the tool)
- "show assignments" / "view coursework" → Call show_coursework_form() (NO TEXT, just call the tool)
- "view announcements" → Call show_announcements_form() (NO TEXT, just call the tool)
- "create course" / "new course" → Call show_course_form() (NO TEXT, just call the tool)
- "create doc" / "make document" → Call create_google_doc()
- "create sheet" / "make spreadsheet" → Call create_google_sheet()

# Available Tools
- list_courses: List all courses
- show_coursework_form: Show form to select course for viewing assignments (NO TEXT)
- show_announcements_form: Show form to select course for viewing announcements (NO TEXT)
- show_assignment_form: Show form to create assignment (NO TEXT)
- show_course_form: Show form to create course (NO TEXT)
- create_course: Create a Google Classroom course
- create_coursework: Create an assignment
- list_coursework: List assignments for a course
- list_announcements: List announcements for a course
- create_google_doc: Create a Google Doc
- create_google_sheet: Create a Google Sheet

# Examples
User: 'hi' → "Hello! I'm Echo, your Google Workspace assistant. I can help you manage courses, create assignments, and more. What would you like to do?"
User: 'what can you do?' → Explain capabilities without calling tools
User: 'list courses' → Call list_courses() → Display results
User: 'create assignment' → Call show_assignment_form() (NO TEXT, JUST TOOL CALL)
User: 'show assignments' → Call show_coursework_form() (NO TEXT, JUST TOOL CALL)

# Response Format
Use markdown: **bold**, - bullets, # headings
Be concise and friendly"""
        
        print("✅ LangChain Chat client initialized")
    
    def _create_tools(self):
        """Create LangChain tools from existing functions"""
        client = self  # Reference to self for accessing credentials
        
        @tool
        async def list_courses() -> dict:
            """List all Google Classroom courses for the authenticated user."""
            return await _list_courses(
                user_email=client.user_email,
                firebase_token=client.firebase_token
            )
        
        @tool
        async def get_course(course_id: str) -> dict:
            """Get details of a specific course by ID."""
            return await _get_course(
                course_id=course_id,
                user_email=client.user_email,
                firebase_token=client.firebase_token
            )
        
        @tool
        async def show_coursework_form() -> dict:
            """Show a form to select which course's assignments to view. Call this when user wants to view or list coursework/assignments."""
            return await _show_coursework_form(
                user_email=client.user_email,
                firebase_token=client.firebase_token
            )
        
        @tool
        async def list_coursework(course_id: str) -> dict:
            """List all coursework/assignments for a specific course."""
            return await _list_coursework(
                course_id=course_id,
                user_email=client.user_email,
                firebase_token=client.firebase_token
            )
        
        @tool
        async def show_announcements_form() -> dict:
            """Show a form to select which course's announcements to view. Call this when user wants to view announcements."""
            return await _show_announcements_form(
                user_email=client.user_email,
                firebase_token=client.firebase_token
            )
        
        @tool
        async def list_announcements(course_id: str) -> dict:
            """List all announcements for a specific course."""
            return await _list_announcements(
                course_id=course_id,
                user_email=client.user_email,
                firebase_token=client.firebase_token
            )
        
        @tool
        async def show_assignment_form() -> dict:
            """Show a form to create a new assignment. This automatically fetches available courses for selection. Call this when user wants to create an assignment."""
            return await _show_assignment_form(
                user_email=client.user_email,
                firebase_token=client.firebase_token
            )
        
        @tool
        async def show_course_form() -> dict:
            """Show a form to create a new course. This automatically fetches available student lists for selection. Call this when user wants to create a course."""
            return await _show_course_form(
                user_email=client.user_email,
                firebase_token=client.firebase_token
            )
        
        @tool
        async def create_course(
            name: str,
            section: str = "",
            description_heading: str = "",
            description: str = "",
            room: str = "",
            student_list_id: str = ""
        ) -> dict:
            """Create a new Google Classroom course with the given details."""
            return await _create_course(
                name=name,
                section=section,
                description_heading=description_heading,
                description=description,
                room=room,
                student_list_id=student_list_id,
                user_email=client.user_email,
                firebase_token=client.firebase_token
            )
        
        @tool
        async def create_coursework(
            course_id: str,
            title: str,
            description: str = "",
            due_date: str = "",
            due_time: str = "",
            max_points: int = 100,
            work_type: str = "ASSIGNMENT",
            file_ids: str = ""
        ) -> dict:
            """Create a new assignment/coursework in Google Classroom."""
            return await _create_coursework(
                course_id=course_id,
                title=title,
                description=description,
                due_date=due_date,
                due_time=due_time,
                max_points=max_points,
                work_type=work_type,
                file_ids=file_ids,
                user_email=client.user_email,
                firebase_token=client.firebase_token
            )
        
        @tool
        async def create_google_doc(title: str, content: str = "") -> dict:
            """Create a new Google Doc with the given title and content."""
            return await _create_google_doc(
                title=title,
                content=content,
                user_email=client.user_email,
                firebase_token=client.firebase_token
            )
        
        @tool
        async def create_google_sheet(
            title: str,
            headers: str = "",
            data: str = ""
        ) -> dict:
            """Create a new Google Sheet with headers and data.
            
            Args:
                title: The title of the spreadsheet
                headers: Comma-separated list of column headers (e.g., "Name,Age,Email")
                data: JSON string of data rows (e.g., '[["John",25,"john@example.com"],["Jane",30,"jane@example.com"]]')
            """
            # Parse headers and data
            headers_list = [h.strip() for h in headers.split(",")] if headers else []
            
            import json
            try:
                data_list = json.loads(data) if data else []
            except:
                data_list = []
            
            return await _create_google_sheet(
                title=title,
                headers=headers_list,
                data=data_list,
                user_email=client.user_email,
                firebase_token=client.firebase_token
            )
        
        return [
            list_courses,
            get_course,
            show_coursework_form,
            list_coursework,
            show_announcements_form,
            list_announcements,
            show_assignment_form,
            show_course_form,
            create_course,
            create_coursework,
            create_google_doc,
            create_google_sheet,
        ]
    
    def set_user_credentials(self, user_email: str, firebase_token: str):
        """Store user credentials for tool execution."""
        self.user_email = user_email
        self.firebase_token = firebase_token
        print(f"✅ User credentials set for: {user_email}")
    
    async def send_message(self, message_input: str, callback: Callable):
        """
        Send message and stream response with tool calls.
        
        Args:
            message_input: User's message text
            callback: Async function to call with response chunks
        """
        try:
            # Build messages list
            messages = [SystemMessage(content=self.system_prompt)]
            messages.extend(self.message_history)
            messages.append(HumanMessage(content=message_input))
            
            # Process the message with potential tool calls
            while True:
                # Stream the response
                response_chunks = []
                tool_calls = []
                
                async for chunk in self.llm_with_tools.astream(messages):
                    # Collect response content
                    if chunk.content:
                        response_chunks.append(chunk.content)
                        await callback({"type": "text_chunk", "text": chunk.content})
                    
                    # Collect tool calls
                    if hasattr(chunk, 'tool_calls') and chunk.tool_calls:
                        tool_calls.extend(chunk.tool_calls)
                    
                    # Check for tool call chunks (streaming tool calls)
                    if hasattr(chunk, 'tool_call_chunks') and chunk.tool_call_chunks:
                        for tc_chunk in chunk.tool_call_chunks:
                            # Tool call chunk handling for streaming
                            pass
                
                # If no tool calls, we're done
                if not tool_calls:
                    # Add assistant response to history
                    full_response = "".join(response_chunks)
                    if full_response:
                        self.message_history.append(HumanMessage(content=message_input))
                        self.message_history.append(AIMessage(content=full_response))
                    break
                
                # Execute tool calls
                ai_message = AIMessage(content="".join(response_chunks), tool_calls=tool_calls)
                messages.append(ai_message)
                
                for tc in tool_calls:
                    tool_name = tc["name"]
                    tool_args = tc.get("args", {})
                    tool_id = tc.get("id", str(id(tc)))
                    
                    print(f"🤖 Chat Tool Call: {tool_name}")
                    print(f"  📥 Tool args: {list(tool_args.keys())}")
                    
                    # Notify UI: Tool Started
                    await callback({
                        "type": "tool_start",
                        "tool": tool_name,
                        "args": tool_args
                    })
                    
                    # Find and execute the tool
                    result = {"error": "Unknown tool"}
                    for tool_func in self.tools:
                        if tool_func.name == tool_name:
                            try:
                                # Execute the async tool
                                result = await tool_func.ainvoke(tool_args)
                            except Exception as e:
                                print(f"❌ Error executing tool {tool_name}: {e}")
                                import traceback
                                traceback.print_exc()
                                result = {"error": str(e)}
                            break
                    
                    # Notify UI: Tool Finished
                    await callback({
                        "type": "tool_end",
                        "tool": tool_name,
                        "result": result
                    })
                    
                    # Add tool response to messages
                    messages.append(ToolMessage(
                        content=json.dumps(result) if isinstance(result, dict) else str(result),
                        tool_call_id=tool_id
                    ))
                
        except asyncio.CancelledError:
            print("LangChainChatClient message processing cancelled")
            raise
        except Exception as e:
            print(f"Error in LangChainChatClient: {e}")
            import traceback
            traceback.print_exc()
            try:
                friendly_error = get_user_friendly_error(str(e))
                await callback({"type": "error", "text": friendly_error})
            except:
                pass
            raise


"""
FastAPI WebSocket Relay Server
Relays real-time audio/text between frontend and Gemini Live API
Supports both free API key and paid Vertex AI
"""

import asyncio
import json
import os
from typing import Optional, List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Header, HTTPException, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from pydantic import BaseModel

from gemini_client import GeminiLiveClient
from langchain_chat_client import LangChainChatClient, get_user_friendly_error
from memory_manager import memory_manager
from classroom_tools import upload_file_to_drive
import config
import base64
from forms_endpoints import router as forms_router
from slides_endpoints import router as slides_router

# Load environment variables
load_dotenv()

app = FastAPI(title="Echo Backend - Gemini Live API Relay")

# Configure CORS - Support multiple environments
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS", 
    "http://localhost:3000,http://127.0.0.1:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include forms router
app.include_router(forms_router)
app.include_router(slides_router)


@app.on_event("startup")
async def startup_event():
    """Validate configuration on startup"""
    is_valid, message = config.validate_configuration()
    if not is_valid:
        print(f"⚠️  WARNING: {message}")
    else:
        print(f"✅ {message}")
    
    print(f"✅ CORS origins: {ALLOWED_ORIGINS}")


@app.get("/")
async def root():
    """Health check endpoint"""
    is_valid, message = config.validate_configuration()
    api_type = config.get_api_type()
    
    return {
        "status": "running",
        "service": "Echo Backend - Gemini Live API Relay",
        "api_type": api_type,
        "api_configured": is_valid,
        "config_message": message,
        "allowed_origins": ALLOWED_ORIGINS
    }


# --- MEMORY MANAGEMENT ENDPOINTS ---
@app.post("/api/memory/clear/{thread_id}")
async def clear_memory(thread_id: str):
    """Clear conversation memory for a specific thread"""
    memory_manager.clear_thread(thread_id)
    return {"status": "ok", "thread_id": thread_id, "message": "Memory cleared"}

@app.get("/api/memory/stats/{thread_id}")
async def get_memory_stats(thread_id: str):
    """Get memory statistics for a thread"""
    stats = memory_manager.get_stats(thread_id)
    return {"thread_id": thread_id, **stats}

@app.get("/api/memory/history/{thread_id}")
async def get_conversation_history(thread_id: str, last_n: Optional[int] = None):
    """Get conversation history for a thread"""
    history = memory_manager.get_history(thread_id, last_n)
    return {
        "thread_id": thread_id,
        "messages": [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp
            }
            for msg in history
        ]
    }


# --- FILE UPLOAD ENDPOINT ---
@app.post("/api/upload-files")
async def upload_files_endpoint(
    request: Request,
    authorization: str = Header(None),
    x_user_email: str = Header(None, alias="X-User-Email")
):
    """
    Upload files to Google Drive and return Drive file IDs.
    Files are uploaded to the user's Drive and permissions are set.
    
    Accepts multipart/form-data with files.
    
    Returns:
        JSON with array of uploaded file objects containing id, title, mimeType
    """
    if not authorization or not x_user_email:
        raise HTTPException(status_code=401, detail="Missing authorization or user email")
    
    # Extract Firebase token
    firebase_token = authorization.replace("Bearer ", "")
    
    uploaded_files = []
    
    try:
        # Parse multipart form data
        form = await request.form()
        
        # Extract all files from the form
        files_to_upload = []
        for key, value in form.items():
            if hasattr(value, 'filename'):  # It's a file
                files_to_upload.append(value)
        
        if not files_to_upload:
            raise HTTPException(status_code=400, detail="No files provided")
        
        print(f"📁 Received {len(files_to_upload)} file(s) for upload")
        
        for upload_file in files_to_upload:
            # Read file content
            content = await upload_file.read()
            base64_content = base64.b64encode(content).decode('utf-8')
            
            # Prepare file data
            file_data = {
                'name': upload_file.filename,
                'content': base64_content,
                'mimeType': upload_file.content_type or 'application/octet-stream'
            }
            
            # Upload to Drive
            print(f"📁 Uploading {upload_file.filename} to Drive...")
            drive_file = await upload_file_to_drive(file_data, x_user_email, firebase_token)
            uploaded_files.append(drive_file)
            print(f"✅ Uploaded: {drive_file['title']} (ID: {drive_file['id']})")
        
        return JSONResponse({
            "success": True,
            "files": uploaded_files,
            "count": len(uploaded_files)
        })
        
    except Exception as e:
        print(f"❌ Error uploading files: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# --- DESCRIPTION GENERATOR ENDPOINT ---
class DescriptionRequest(BaseModel):
    query: str

@app.post("/api/generate-description")
async def generate_description(request: DescriptionRequest):
    """
    Generate or enhance assignment descriptions using Gemini.
    Takes user input and returns a concise 50-100 word description.
    """
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    try:
        print(f"✨ Generating description for: {request.query[:50]}...")
        
        # Get client configuration
        client_config = config.get_client_config()
        
        # Initialize Gemini client based on API type
        if client_config["api_type"] == "free":
            from google import genai
            client = genai.Client(api_key=client_config["api_key"])
        else:  # paid
            from google import genai
            from google.oauth2 import service_account
            import json
            
            # Parse credentials JSON string to dict
            credentials_dict = json.loads(client_config["credentials_json"])
            
            credentials = service_account.Credentials.from_service_account_info(
                credentials_dict,
                scopes=[
                    "https://www.googleapis.com/auth/generative-language",
                    "https://www.googleapis.com/auth/cloud-platform",
                ]
            )
            client = genai.Client(
                vertexai=True,
                project=client_config["project_id"],
                location=client_config["location"],
                credentials=credentials
            )
        
        # Create prompt for description generation
        prompt = f"""You are an expert educator creating assignment descriptions for Google Classroom.

User input: "{request.query}"

Task: Generate a clear, concise assignment description or question based on the user's input.

Requirements:
- STRICTLY 50-100 words
- Professional and educational tone
- Clear and actionable
- Preserve the core meaning and intent
- If input is vague, create a well-structured question/description
- Do not add any preamble or explanation, just the description
- IMPORTANT: Return PLAIN TEXT ONLY - no markdown formatting, no asterisks, no special characters
- Do not use bold (**text**), italic (*text*), or any markdown syntax
- Use proper paragraph breaks (blank lines) between sections
- If using bullet points, start each line with "- " or "• "
- Keep natural line breaks for readability

Generate the description now:"""

        # Generate description using Gemini
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=prompt
        )
        
        generated_text = response.text.strip()
        
        # Remove any markdown formatting that might slip through, but preserve newlines
        import re
        # Remove bold (**text** or __text__)
        generated_text = re.sub(r'\*\*(.+?)\*\*', r'\1', generated_text)
        generated_text = re.sub(r'__(.+?)__', r'\1', generated_text)
        # Remove italic (*text* or _text_) - but not bullet points (- at start of line)
        generated_text = re.sub(r'(?<!\n)\*(.+?)\*', r'\1', generated_text)  # italic, not at line start
        generated_text = re.sub(r'(?<!\n)_(.+?)_', r'\1', generated_text)    # italic, not at line start
        # Remove code blocks (```text```)
        generated_text = re.sub(r'```.*?```', '', generated_text, flags=re.DOTALL)
        generated_text = re.sub(r'`(.+?)`', r'\1', generated_text)
        # Remove headers (# text) but keep the text
        generated_text = re.sub(r'^#+\s+', '', generated_text, flags=re.MULTILINE)
        # Clean up excessive blank lines (more than 2 consecutive newlines)
        generated_text = re.sub(r'\n{3,}', '\n\n', generated_text)
        # Clean up spaces at start/end of lines
        generated_text = '\n'.join(line.strip() for line in generated_text.split('\n'))
        
        word_count = len(generated_text.split())
        
        print(f"✅ Generated description ({word_count} words)")
        
        return JSONResponse({
            "success": True,
            "description": generated_text,
            "word_count": word_count
        })
        
    except Exception as e:
        print(f"❌ Error generating description: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate description: {str(e)}")


# --- LIVE AUDIO ENDPOINT ---
@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    """
    WebSocket endpoint for Gemini Live (Audio)
    """
    await websocket.accept()
    print("✅ Frontend connected to /ws/live")
    
    # Validate configuration
    is_valid, message = config.validate_configuration()
    if not is_valid:
        await websocket.close(code=1008, reason=message)
        return
    
    # Initialize Live Client based on API type
    client_config = config.get_client_config()
    if client_config["api_type"] == "free":
        gemini_live = GeminiLiveClient(api_key=client_config["api_key"])
    else:  # paid
        gemini_live = GeminiLiveClient(
            project_id=client_config["project_id"],
            location=client_config["location"],
            credentials_json=client_config["credentials_json"]
        )
    
    try:
        await gemini_live.start_session()
        print("✅ Connected to Gemini Live API")
        
        await websocket.send_json({
            "type": "connected",
            "data": "Connected to Gemini Live API"
        })
        
        # Tasks for Live Relay
        frontend_task = asyncio.create_task(relay_frontend_to_live(websocket, gemini_live))
        gemini_task = asyncio.create_task(relay_live_to_frontend(gemini_live, websocket))
        
        done, pending = await asyncio.wait(
            [frontend_task, gemini_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Cancel pending tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Check for exceptions in completed tasks
        for task in done:
            try:
                task.result()  # This will raise any exception that occurred
            except WebSocketDisconnect:
                print("❌ WebSocket disconnected in background task")
            except Exception as e:
                print(f"❌ Error in background task: {e}")
                raise
        
    except WebSocketDisconnect:
        print("❌ Frontend disconnected from /ws/live")
    except Exception as e:
        print(f"❌ Error in /ws/live: {e}")
        try:
            await websocket.send_json({"type": "error", "data": str(e)})
        except:
            pass
    finally:
        await gemini_live.close()
        try:
            await websocket.close()
        except:
            pass
        print("🔌 Live connection closed")


# --- CHAT TEXT ENDPOINT ---
@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket endpoint for Gemini Chat (Text + Tools)
    Supports user authentication for Firestore token retrieval
    """
    await websocket.accept()
    print("✅ Frontend connected to /ws/chat")
    
    # Validate configuration
    is_valid, message = config.validate_configuration()
    if not is_valid:
        try:
            await websocket.send_json({
                "type": "error",
                "data": f"Server configuration error: {message}"
            })
        except:
            pass
        await websocket.close(code=1008, reason=message)
        return
    
    # Initialize LangChain Chat Client (One per connection)
    gemini_chat = None
    try:
        client_config = config.get_client_config()
        if client_config["api_type"] == "free":
            gemini_chat = LangChainChatClient(api_key=client_config["api_key"])
        else:  # paid
            gemini_chat = LangChainChatClient(
                project_id=client_config["project_id"],
                location=client_config["location"],
                credentials_json=client_config["credentials_json"]
            )
        print("✅ LangChain Chat client initialized")
    except Exception as e:
        print(f"❌ Failed to initialize chat client: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "data": f"Failed to initialize chat: {str(e)}"
            })
        except:
            pass
        await websocket.close(code=1011, reason="Chat initialization failed")
        return
    
    try:
        await websocket.send_json({
            "type": "connected",
            "data": "Connected to Gemini Chat"
        })
        
        while True:
            # Receive messages from frontend
            try:
                message = await websocket.receive_text()
                data = json.loads(message)
                
                message_type = data.get("type")
                
                if message_type == "auth":
                    # Receive and store authentication credentials
                    user_email = data.get("user_email")
                    firebase_token = data.get("firebase_token")
                    
                    if user_email and firebase_token:
                        print(f"🔐 User authenticated: {user_email}")
                        # Store credentials in chat client
                        gemini_chat.set_user_credentials(user_email, firebase_token)
                        await websocket.send_json({
                            "type": "auth_success",
                            "data": "Authentication successful"
                        })
                    else:
                        print(f"⚠️  Incomplete auth data received")
                        await websocket.send_json({
                            "type": "auth_error",
                            "data": "Missing email or token"
                        })
                
                elif message_type == "text":
                    text = data.get("text")
                    thread_id = data.get("thread_id", "default")
                    if text:
                        print(f"💬 Chat message received (thread: {thread_id}): {text[:50]}...")
                        
                        # Store user message in memory
                        memory_manager.add_message(thread_id, "user", text)
                        
                        # Process message with memory context
                        await process_chat_message(gemini_chat, websocket, text, thread_id)
                
                elif message_type == "ping":
                    await websocket.send_json({"type": "pong"})
                    
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON received: {e}")
                await websocket.send_json({
                    "type": "error",
                    "data": "Invalid JSON format"
                })

    except WebSocketDisconnect:
        print("❌ Frontend disconnected from /ws/chat")
    except Exception as e:
        print(f"❌ Error in /ws/chat: {e}")
        try:
            friendly_error = get_user_friendly_error(str(e))
            await websocket.send_json({
                "type": "error",
                "data": friendly_error
            })
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass
        print("🔌 Chat connection closed")


# --- HELPERS ---

async def relay_frontend_to_live(frontend_ws: WebSocket, gemini_live: GeminiLiveClient):
    """Relay messages from frontend WebSocket to Gemini Live API"""
    try:
        while True:
            message = await frontend_ws.receive_text()
            data = json.loads(message)
            
            if data.get("type") == "audio":
                audio_data = data.get("data", "")
                turn_complete = data.get("turn_complete", False)
                await gemini_live.send_audio(audio_data, turn_complete)
                
            elif data.get("type") == "ping":
                await frontend_ws.send_json({"type": "pong"})
                
    except WebSocketDisconnect:
        print("Frontend WebSocket disconnected in relay_frontend_to_live")
        # Don't re-raise, just return to end the task gracefully
        return
    except asyncio.CancelledError:
        print("relay_frontend_to_live task cancelled")
        raise
    except Exception as e:
        print(f"Error in relay_frontend_to_live: {e}")
        raise

async def relay_live_to_frontend(gemini_live: GeminiLiveClient, frontend_ws: WebSocket):
    """Relay messages from Gemini Live API to frontend WebSocket"""
    async def handle_message(data: dict):
        try:
            if data["type"] == "audio":
                await frontend_ws.send_json(data)
                print(".", end="", flush=True)
            elif data["type"] == "turn_complete":
                print("\n")
                await frontend_ws.send_json(data)
        except Exception as e:
            print(f"Error handling Gemini message: {e}")
            raise  # Re-raise to stop the receive loop

    try:
        await gemini_live.receive_loop(handle_message)
    except asyncio.CancelledError:
        print("relay_live_to_frontend task cancelled")
        raise
    except Exception as e:
        print(f"Error in relay_live_to_frontend: {e}")
        # Don't re-raise - let the task end gracefully
        return

async def process_chat_message(chat_client: LangChainChatClient, ws: WebSocket, text: str, thread_id: str = "default"):
    """Process a chat message and stream response back to frontend"""
    response_text = ""
    
    async def callback(msg):
        nonlocal response_text
        try:
            # Check if this is a tool_end message with the special show_form action
            if msg.get("type") == "tool_end":
                result = msg.get("result", {})
                if isinstance(result, dict) and result.get("action") == "show_form":
                    form_type = result.get("form_type")
                    
                    if form_type == "assignment":
                        # Send assignment form message
                        courses = result.get("courses", [])
                        print(f"📤 Sending assignment form to frontend with {len(courses)} courses")
                        if len(courses) > 0:
                            print(f"   First course: {courses[0].get('name', 'Unknown')}")
                        await ws.send_json({
                            "type": "show_assignment_form",
                            "data": {
                                "course_id": result.get("course_id", ""),
                                "courses": courses
                            }
                        })
                    elif form_type == "course":
                        # Send course form message with student lists
                        await ws.send_json({
                            "type": "show_course_form",
                            "data": {
                                "student_lists": result.get("student_lists", [])
                            }
                        })
                    elif form_type == "coursework":
                        # Send coursework selection form
                        courses = result.get("courses", [])
                        print(f"📤 Sending coursework form to frontend with {len(courses)} courses")
                        await ws.send_json({
                            "type": "show_coursework_form",
                            "data": {
                                "courses": courses
                            }
                        })
                    elif form_type == "announcements":
                        # Send announcements selection form
                        courses = result.get("courses", [])
                        print(f"📤 Sending announcements form to frontend with {len(courses)} courses")
                        await ws.send_json({
                            "type": "show_announcements_form",
                            "data": {
                                "courses": courses
                            }
                        })
                    
                    # DON'T send the regular tool_end message to prevent duplicate form
                    # Instead, send a modified tool_end without the form data
                    await ws.send_json({
                        "type": "tool_end",
                        "tool": msg.get("tool"),
                        "result": {"message": "Form displayed"}
                    })
                    return
            
            await ws.send_json(msg)
            
            # Collect response text chunks for memory
            if msg.get("type") == "text_chunk":
                response_text += msg.get("text", "")
        except WebSocketDisconnect:
            print("WebSocket disconnected during chat message processing")
            raise  # Re-raise to stop processing
        except Exception as e:
            print(f"Error sending chat response to frontend: {e}")
            raise  # Re-raise to stop processing

    try:
        # Get conversation context from memory
        context = memory_manager.get_context_string(thread_id)
        
        # Add context to the message if there's history
        if context:
            enhanced_text = f"[Conversation Context]\n{context}\n\n[Current Query]\n{text}"
        else:
            enhanced_text = text
        
        await chat_client.send_message(enhanced_text, callback)
        
        # Store AI response in memory
        if response_text:
            memory_manager.add_message(thread_id, "model", response_text)
        
    except WebSocketDisconnect:
        raise  # Re-raise to the main handler
    except Exception as e:
        print(f"Error processing chat message: {e}")
        try:
            friendly_error = get_user_friendly_error(str(e))
            await ws.send_json({
                "type": "error",
                "data": friendly_error
            })
        except:
            pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

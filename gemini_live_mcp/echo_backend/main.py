"""
FastAPI WebSocket Relay Server
Relays real-time audio/text between frontend and Gemini Live API
"""

import asyncio
import json
import os
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from gemini_client import GeminiLiveClient
from gemini_chat_client import GeminiChatClient, get_user_friendly_error
from memory_manager import memory_manager

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


@app.on_event("startup")
async def startup_event():
    """Validate configuration on startup"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("⚠️  WARNING: GEMINI_API_KEY not set in environment!")
    else:
        print("✅ GEMINI_API_KEY configured")
    
    print(f"✅ CORS origins: {ALLOWED_ORIGINS}")


@app.get("/")
async def root():
    """Health check endpoint"""
    api_key = os.getenv("GEMINI_API_KEY")
    return {
        "status": "running",
        "service": "Echo Backend - Gemini Live API Relay",
        "api_key_configured": bool(api_key),
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


# --- LIVE AUDIO ENDPOINT ---
@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    """
    WebSocket endpoint for Gemini Live (Audio)
    """
    await websocket.accept()
    print("✅ Frontend connected to /ws/live")
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        await websocket.close(code=1008, reason="API Key missing")
        return
    
    # Initialize Live Client
    gemini_live = GeminiLiveClient(api_key)
    
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
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        try:
            await websocket.send_json({
                "type": "error",
                "data": "Server configuration error: API Key missing"
            })
        except:
            pass
        await websocket.close(code=1008, reason="API Key missing")
        return
    
    # Initialize Chat Client (One per connection)
    gemini_chat = None
    try:
        gemini_chat = GeminiChatClient(api_key)
        print("✅ Chat client initialized")
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

async def process_chat_message(chat_client: GeminiChatClient, ws: WebSocket, text: str, thread_id: str = "default"):
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
                        await ws.send_json({
                            "type": "show_assignment_form",
                            "data": {
                                "course_id": result.get("course_id", ""),
                                "courses": result.get("courses", [])
                            }
                        })
                    elif form_type == "course":
                        # Send course form message
                        await ws.send_json({
                            "type": "show_course_form",
                            "data": {}
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

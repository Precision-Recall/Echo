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
from gemini_chat_client import GeminiChatClient

# Load environment variables
load_dotenv()

app = FastAPI(title="Echo Backend - Gemini Live API Relay")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "service": "Echo Backend - Gemini Live API Relay"
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
        
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
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
    """
    await websocket.accept()
    print("✅ Frontend connected to /ws/chat")
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        await websocket.close(code=1008, reason="API Key missing")
        return
    
    # Initialize Chat Client (One per connection)
    gemini_chat = GeminiChatClient(api_key)
    
    try:
        await websocket.send_json({
            "type": "connected",
            "data": "Connected to Gemini Chat"
        })
        
        while True:
            # Receive text from frontend
            message = await websocket.receive_text()
            data = json.loads(message)
            
            message_type = data.get("type")
            
            if message_type == "text":
                text = data.get("text")
                if text:
                    print(f"💬 Chat message received: {text[:50]}...")
                    # Process message (awaiting here blocks next message, but fine for turn-based chat)
                    # For streaming, we pass a callback that sends to WS
                    await process_chat_message(gemini_chat, websocket, text)
            
            elif message_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        print("❌ Frontend disconnected from /ws/chat")
    except Exception as e:
        print(f"❌ Error in /ws/chat: {e}")
    finally:
        try:
            await websocket.close()
        except:
            pass
        print("🔌 Chat connection closed")


# --- HELPERS ---

async def relay_frontend_to_live(frontend_ws: WebSocket, gemini_live: GeminiLiveClient):
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
        raise
    except Exception as e:
        print(f"Error in relay_frontend_to_live: {e}")
        raise

async def relay_live_to_frontend(gemini_live: GeminiLiveClient, frontend_ws: WebSocket):
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

    await gemini_live.receive_loop(handle_message)

async def process_chat_message(chat_client: GeminiChatClient, ws: WebSocket, text: str):
    """Process a chat message and stream response back to frontend"""
    async def callback(msg):
        try:
            await ws.send_json(msg)
        except Exception as e:
            print(f"Error sending chat response to frontend: {e}")

    await chat_client.send_message(text, callback)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

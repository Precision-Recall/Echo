"""
FastAPI backend for managing user OAuth tokens in Firebase Firestore.

This service provides REST endpoints to store and retrieve Google OAuth credentials
for users authenticated via Firebase Authentication.
"""

import os
import json
import re
from datetime import datetime
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import firebase_admin
from firebase_admin import credentials, firestore, auth as firebase_auth
from dotenv import load_dotenv
import httpx

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI(
    title="Echo OAuth Token Service",
    description="API for managing Google OAuth tokens in Firestore",
    version="1.0.0"
)

# CORS configuration
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Firebase Admin SDK
try:
    # Load Firebase credentials from FIREBASE_CREDENTIALS environment variable
    firebase_creds_json = os.getenv("FIREBASE_CREDENTIALS")
    
    if not firebase_creds_json:
        raise ValueError("FIREBASE_CREDENTIALS environment variable is required")
    
    # Parse JSON credentials
    creds_dict = json.loads(firebase_creds_json)
    
    # Initialize Firebase with credentials
    cred = credentials.Certificate(creds_dict)
    firebase_admin.initialize_app(cred)
    
    print("✅ Firebase initialized successfully")
    print(f"   Project: {creds_dict.get('project_id', 'Unknown')}")
    print(f"   Service Account: {creds_dict.get('client_email', 'Unknown')}")
    
except json.JSONDecodeError as e:
    print(f"❌ Failed to parse FIREBASE_CREDENTIALS JSON: {e}")
    print("   Make sure FIREBASE_CREDENTIALS contains valid JSON")
    raise
except ValueError as e:
    print(f"❌ Configuration error: {e}")
    print("   Set FIREBASE_CREDENTIALS environment variable with your Firebase credentials JSON")
    raise
except Exception as e:
    print(f"❌ Firebase initialization error: {e}")
    raise

# Firestore client
db = firestore.client()

# Pydantic models
class CodeExchangeRequest(BaseModel):
    """Request to exchange authorization code for tokens"""
    code: str
    redirect_uri: str = "postmessage"

class TokenData(BaseModel):
    """OAuth token data to be stored"""
    email: EmailStr
    access_token: str
    refresh_token: str
    expires_in: Optional[int] = None
    scope: Optional[str] = None

class TokenResponse(BaseModel):
    """Response model for token retrieval"""
    email: str
    access_token: str
    refresh_token: str
    last_updated: str
    expires_in: Optional[int] = None
    scope: Optional[str] = None

class StatusResponse(BaseModel):
    """Generic status response"""
    success: bool
    message: str
    data: Optional[dict] = None

class StudentListCreate(BaseModel):
    """Request model for creating a student list"""
    department_name: str
    department_year: str
    section: str
    emails_text: str  # Raw text containing emails (can be comma/space/newline separated)

class StudentListResponse(BaseModel):
    """Response model for student list"""
    id: str
    department_name: str
    department_year: str
    section: str
    emails: List[str]
    created_by: str
    created_at: str
    updated_at: str

# Helper functions
def parse_emails_from_text(text: str) -> List[str]:
    """
    Extract email addresses from text using regex.
    Handles comma, space, newline, and semicolon separated emails.
    
    Args:
        text: Raw text containing email addresses
    
    Returns:
        List of unique, valid email addresses
    """
    # Email regex pattern
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    
    # Find all emails in the text
    emails = re.findall(email_pattern, text)
    
    # Remove duplicates and convert to lowercase
    unique_emails = list(set(email.lower() for email in emails))
    
    # Sort for consistency
    unique_emails.sort()
    
    return unique_emails

async def verify_firebase_token(authorization: str) -> dict:
    """
    Verify Firebase ID token from Authorization header.
    
    Args:
        authorization: Bearer token from request header
    
    Returns:
        Decoded token with user info
    
    Raises:
        HTTPException: If token is invalid
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    
    id_token = authorization.split("Bearer ")[1]
    
    try:
        decoded_token = firebase_auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid Firebase token: {str(e)}")

# API Endpoints
@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Echo OAuth Token Service",
        "status": "running",
        "version": "1.0.0"
    }

@app.post("/api/oauth/exchange")
async def exchange_code_for_tokens(request: CodeExchangeRequest):
    """
    Exchange Google OAuth authorization code for access and refresh tokens.
    
    This endpoint securely exchanges the authorization code for tokens using
    the client secret, which should never be exposed to the frontend.
    """
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=500,
            detail="Google OAuth not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET"
        )
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": request.code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": request.redirect_uri,
                    "grant_type": "authorization_code",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            
            if response.status_code != 200:
                error_data = response.json()
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Token exchange failed: {error_data.get('error_description', error_data.get('error'))}"
                )
            
            tokens = response.json()
            print(f"✅ Successfully exchanged authorization code for tokens")
            return tokens
    
    except httpx.HTTPError as e:
        print(f"❌ HTTP error during token exchange: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to exchange code: {str(e)}")
    except Exception as e:
        print(f"❌ Error exchanging code: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to exchange code: {str(e)}")

@app.post("/api/tokens/store", response_model=StatusResponse)
async def store_tokens(
    token_data: TokenData,
    authorization: str = Header(None)
):
    """
    Store OAuth tokens for a user in Firestore.
    
    Requires Firebase ID token in Authorization header.
    User email from token must match the email in token_data.
    """
    # Verify Firebase authentication
    decoded_token = await verify_firebase_token(authorization)
    user_email = decoded_token.get("email")
    
    # Verify email matches
    if user_email != token_data.email:
        raise HTTPException(
            status_code=403,
            detail="Email mismatch: You can only store tokens for your own account"
        )
    
    try:
        # Store tokens in Firestore under users/{email}
        doc_ref = db.collection("users").document(user_email)
        
        token_doc = {
            "access_token": token_data.access_token,
            "refresh_token": token_data.refresh_token,
            "last_updated": datetime.utcnow().isoformat(),
        }
        
        if token_data.expires_in:
            token_doc["expires_in"] = token_data.expires_in
        
        if token_data.scope:
            token_doc["scope"] = token_data.scope
        
        doc_ref.set(token_doc, merge=True)
        
        print(f"✅ Stored tokens for user: {user_email}")
        
        return StatusResponse(
            success=True,
            message="Tokens stored successfully",
            data={"email": user_email}
        )
    
    except Exception as e:
        print(f"❌ Error storing tokens: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to store tokens: {str(e)}")

@app.get("/api/tokens/retrieve", response_model=TokenResponse)
async def retrieve_tokens(
    email: EmailStr,
    authorization: str = Header(None)
):
    """
    Retrieve OAuth tokens for a user from Firestore.
    
    Requires Firebase ID token in Authorization header.
    Users can only retrieve their own tokens.
    """
    # Verify Firebase authentication
    decoded_token = await verify_firebase_token(authorization)
    user_email = decoded_token.get("email")
    
    # Verify email matches
    if user_email != email:
        raise HTTPException(
            status_code=403,
            detail="Access denied: You can only retrieve your own tokens"
        )
    
    try:
        # Retrieve tokens from Firestore
        doc_ref = db.collection("users").document(email)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(
                status_code=404,
                detail="No tokens found for this user. Please authenticate with Google Classroom first."
            )
        
        data = doc.to_dict()
        
        if not data.get("access_token") or not data.get("refresh_token"):
            raise HTTPException(
                status_code=404,
                detail="Incomplete token data. Please re-authenticate with Google Classroom."
            )
        
        return TokenResponse(
            email=email,
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            last_updated=data.get("last_updated", "Unknown"),
            expires_in=data.get("expires_in"),
            scope=data.get("scope")
        )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error retrieving tokens: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve tokens: {str(e)}")

@app.delete("/api/tokens/delete", response_model=StatusResponse)
async def delete_tokens(
    email: EmailStr,
    authorization: str = Header(None)
):
    """
    Delete OAuth tokens for a user from Firestore.
    
    Requires Firebase ID token in Authorization header.
    Users can only delete their own tokens.
    """
    # Verify Firebase authentication
    decoded_token = await verify_firebase_token(authorization)
    user_email = decoded_token.get("email")
    
    # Verify email matches
    if user_email != email:
        raise HTTPException(
            status_code=403,
            detail="Access denied: You can only delete your own tokens"
        )
    
    try:
        # Delete token fields from Firestore
        doc_ref = db.collection("users").document(email)
        doc_ref.update({
            "access_token": firestore.DELETE_FIELD,
            "refresh_token": firestore.DELETE_FIELD,
            "expires_in": firestore.DELETE_FIELD,
            "scope": firestore.DELETE_FIELD,
            "last_updated": firestore.DELETE_FIELD
        })
        
        print(f"✅ Deleted tokens for user: {email}")
        
        return StatusResponse(
            success=True,
            message="Tokens deleted successfully",
            data={"email": email}
        )
    
    except Exception as e:
        print(f"❌ Error deleting tokens: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete tokens: {str(e)}")

@app.get("/api/tokens/status", response_model=StatusResponse)
async def token_status(
    email: EmailStr,
    authorization: str = Header(None)
):
    """
    Check if OAuth tokens exist for a user.
    
    Requires Firebase ID token in Authorization header.
    """
    # Verify Firebase authentication
    decoded_token = await verify_firebase_token(authorization)
    user_email = decoded_token.get("email")
    
    # Verify email matches
    if user_email != email:
        raise HTTPException(
            status_code=403,
            detail="Access denied: You can only check your own token status"
        )
    
    try:
        doc_ref = db.collection("users").document(email)
        doc = doc_ref.get()
        
        if not doc.exists:
            return StatusResponse(
                success=False,
                message="No tokens found",
                data={"has_tokens": False, "email": email}
            )
        
        data = doc.to_dict()
        has_tokens = bool(data.get("access_token") and data.get("refresh_token"))
        
        return StatusResponse(
            success=True,
            message="Token status retrieved",
            data={
                "has_tokens": has_tokens,
                "email": email,
                "last_updated": data.get("last_updated")
            }
        )
    
    except Exception as e:
        print(f"❌ Error checking token status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check token status: {str(e)}")

# Student List Management Endpoints

@app.post("/api/student-lists/create", response_model=StudentListResponse)
async def create_student_list(
    student_list: StudentListCreate,
    authorization: str = Header(None)
):
    """
    Create a new student list.
    
    Requires Firebase ID token in Authorization header.
    Automatically parses emails from the provided text.
    """
    # Verify Firebase authentication
    decoded_token = await verify_firebase_token(authorization)
    user_email = decoded_token.get("email")
    
    if not user_email:
        raise HTTPException(status_code=401, detail="User email not found in token")
    
    try:
        # Parse emails from the provided text
        emails = parse_emails_from_text(student_list.emails_text)
        
        if not emails:
            raise HTTPException(
                status_code=400,
                detail="No valid email addresses found in the provided text"
            )
        
        # Create student list document
        student_list_ref = db.collection("student_lists").document()
        
        current_time = datetime.utcnow().isoformat()
        
        student_list_data = {
            "department_name": student_list.department_name,
            "department_year": student_list.department_year,
            "section": student_list.section,
            "emails": emails,
            "created_by": user_email,
            "created_at": current_time,
            "updated_at": current_time
        }
        
        student_list_ref.set(student_list_data)
        
        print(f"✅ Created student list: {student_list_ref.id} by {user_email}")
        print(f"   Department: {student_list.department_name} - {student_list.department_year} - {student_list.section}")
        print(f"   Students: {len(emails)} emails")
        
        return StudentListResponse(
            id=student_list_ref.id,
            **student_list_data
        )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error creating student list: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create student list: {str(e)}")

@app.get("/api/student-lists", response_model=List[StudentListResponse])
async def get_student_lists(
    authorization: str = Header(None)
):
    """
    Get all student lists created by the authenticated user.
    
    Requires Firebase ID token in Authorization header.
    Returns only lists created by the logged-in user.
    """
    # Verify Firebase authentication
    decoded_token = await verify_firebase_token(authorization)
    user_email = decoded_token.get("email")
    
    if not user_email:
        raise HTTPException(status_code=401, detail="User email not found in token")
    
    try:
        # Query student lists created by this user
        lists_ref = db.collection("student_lists").where("created_by", "==", user_email)
        docs = lists_ref.stream()
        
        student_lists = []
        for doc in docs:
            data = doc.to_dict()
            student_lists.append(StudentListResponse(
                id=doc.id,
                **data
            ))
        
        # Sort by created_at (newest first)
        student_lists.sort(key=lambda x: x.created_at, reverse=True)
        
        print(f"✅ Retrieved {len(student_lists)} student lists for {user_email}")
        
        return student_lists
    
    except Exception as e:
        print(f"❌ Error retrieving student lists: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve student lists: {str(e)}")

@app.get("/api/student-lists/{list_id}", response_model=StudentListResponse)
async def get_student_list(
    list_id: str,
    authorization: str = Header(None)
):
    """
    Get a specific student list by ID.
    
    Requires Firebase ID token in Authorization header.
    Users can only access their own lists.
    """
    # Verify Firebase authentication
    decoded_token = await verify_firebase_token(authorization)
    user_email = decoded_token.get("email")
    
    if not user_email:
        raise HTTPException(status_code=401, detail="User email not found in token")
    
    try:
        # Get the student list document
        doc_ref = db.collection("student_lists").document(list_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Student list not found")
        
        data = doc.to_dict()
        
        # Verify ownership
        if data.get("created_by") != user_email:
            raise HTTPException(
                status_code=403,
                detail="Access denied: You can only access your own student lists"
            )
        
        return StudentListResponse(
            id=doc.id,
            **data
        )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error retrieving student list: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve student list: {str(e)}")

@app.delete("/api/student-lists/{list_id}", response_model=StatusResponse)
async def delete_student_list(
    list_id: str,
    authorization: str = Header(None)
):
    """
    Delete a student list.
    
    Requires Firebase ID token in Authorization header.
    Users can only delete their own lists.
    """
    # Verify Firebase authentication
    decoded_token = await verify_firebase_token(authorization)
    user_email = decoded_token.get("email")
    
    if not user_email:
        raise HTTPException(status_code=401, detail="User email not found in token")
    
    try:
        # Get the student list document
        doc_ref = db.collection("student_lists").document(list_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Student list not found")
        
        data = doc.to_dict()
        
        # Verify ownership
        if data.get("created_by") != user_email:
            raise HTTPException(
                status_code=403,
                detail="Access denied: You can only delete your own student lists"
            )
        
        # Delete the document
        doc_ref.delete()
        
        print(f"✅ Deleted student list: {list_id} by {user_email}")
        
        return StatusResponse(
            success=True,
            message="Student list deleted successfully",
            data={"id": list_id}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error deleting student list: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete student list: {str(e)}")

@app.put("/api/student-lists/{list_id}", response_model=StudentListResponse)
async def update_student_list(
    list_id: str,
    student_list: StudentListCreate,
    authorization: str = Header(None)
):
    """
    Update an existing student list.
    
    Requires Firebase ID token in Authorization header.
    Users can only update their own lists.
    """
    # Verify Firebase authentication
    decoded_token = await verify_firebase_token(authorization)
    user_email = decoded_token.get("email")
    
    if not user_email:
        raise HTTPException(status_code=401, detail="User email not found in token")
    
    try:
        # Get the student list document
        doc_ref = db.collection("student_lists").document(list_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Student list not found")
        
        data = doc.to_dict()
        
        # Verify ownership
        if data.get("created_by") != user_email:
            raise HTTPException(
                status_code=403,
                detail="Access denied: You can only update your own student lists"
            )
        
        # Parse emails from the provided text
        emails = parse_emails_from_text(student_list.emails_text)
        
        if not emails:
            raise HTTPException(
                status_code=400,
                detail="No valid email addresses found in the provided text"
            )
        
        # Update the document
        updated_data = {
            "department_name": student_list.department_name,
            "department_year": student_list.department_year,
            "section": student_list.section,
            "emails": emails,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        doc_ref.update(updated_data)
        
        # Get the updated document
        updated_doc = doc_ref.get()
        updated_data_full = updated_doc.to_dict()
        
        print(f"✅ Updated student list: {list_id} by {user_email}")
        
        return StudentListResponse(
            id=list_id,
            **updated_data_full
        )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error updating student list: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update student list: {str(e)}")

# ============================================================================
# Conversation History Endpoints
# ============================================================================

class Message(BaseModel):
    """Message model for conversation history"""
    role: str  # "user" or "assistant"
    content: str

class ConversationSummary(BaseModel):
    """Conversation summary for list view"""
    id: str
    title: str
    created_at: str
    updated_at: str

class ConversationDetail(BaseModel):
    """Full conversation with messages"""
    id: str
    title: str
    created_at: str
    updated_at: str
    messages: List[dict]

class CreateConversationRequest(BaseModel):
    """Request to create a new conversation"""
    title: Optional[str] = None  # Auto-generated if not provided

class AddMessageRequest(BaseModel):
    """Request to add a message to a conversation"""
    role: str
    content: str

@app.get("/api/conversations", response_model=List[ConversationSummary])
async def list_conversations(
    email: str,
    page: int = 1,
    limit: int = 10
):
    """
    List conversations for the authenticated user with pagination.
    Returns the 10 most recent conversations by default.
    
    Args:
        email: User's Gmail address
        page: Page number (default: 1)
        limit: Number of conversations per page (default: 10)
    
    Returns:
        List of conversation summaries with id, title, created_at, updated_at
    """
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    
    user_email = email
    
    try:
        # Get user document reference
        user_ref = db.collection("users").document(user_email)
        
        # Query conversations subcollection with pagination
        conversations_ref = user_ref.collection("conversations")
        
        # Order by updatedAt descending (most recent first)
        query = conversations_ref.order_by("updatedAt", direction=firestore.Query.DESCENDING)
        
        # Apply pagination
        offset = (page - 1) * limit
        query = query.limit(limit).offset(offset)
        
        # Execute query
        docs = query.stream()
        
        conversations = []
        for doc in docs:
            data = doc.to_dict()
            
            # Convert Firestore timestamps to ISO strings
            created_at = data.get("createdAt", "")
            updated_at = data.get("updatedAt", "")
            
            # Handle both string and timestamp types
            if hasattr(created_at, 'isoformat'):
                created_at = created_at.isoformat()
            elif not isinstance(created_at, str):
                created_at = str(created_at) if created_at else ""
                
            if hasattr(updated_at, 'isoformat'):
                updated_at = updated_at.isoformat()
            elif not isinstance(updated_at, str):
                updated_at = str(updated_at) if updated_at else ""
            
            conversations.append(ConversationSummary(
                id=doc.id,
                title=data.get("title", "Untitled Conversation"),
                created_at=created_at,
                updated_at=updated_at
            ))
        
        print(f"✅ Listed {len(conversations)} conversations for {user_email} (page {page})")
        return conversations
    
    except Exception as e:
        print(f"❌ Error listing conversations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list conversations: {str(e)}")

@app.get("/api/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: str,
    email: str
):
    """
    Get a specific conversation with all its messages.
    
    Args:
        conversation_id: The conversation/session ID
        email: User's Gmail address
    
    Returns:
        Full conversation details with all messages
    """
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    
    user_email = email
    
    try:
        # Get conversation document
        conv_ref = db.collection("users").document(user_email).collection("conversations").document(conversation_id)
        conv_doc = conv_ref.get()
        
        if not conv_doc.exists:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        conv_data = conv_doc.to_dict()
        
        # Convert conversation timestamps
        created_at = conv_data.get("createdAt", "")
        updated_at = conv_data.get("updatedAt", "")
        
        if hasattr(created_at, 'isoformat'):
            created_at = created_at.isoformat()
        elif not isinstance(created_at, str):
            created_at = str(created_at) if created_at else ""
            
        if hasattr(updated_at, 'isoformat'):
            updated_at = updated_at.isoformat()
        elif not isinstance(updated_at, str):
            updated_at = str(updated_at) if updated_at else ""
        
        # Get all messages from the messages subcollection
        messages_ref = conv_ref.collection("messages")
        messages_query = messages_ref.order_by("timestamp", direction=firestore.Query.ASCENDING)
        messages_docs = messages_query.stream()
        
        messages = []
        for msg_doc in messages_docs:
            msg_data = msg_doc.to_dict()
            timestamp = msg_data.get("timestamp", "")
            
            # Convert timestamp to string
            if hasattr(timestamp, 'isoformat'):
                timestamp = timestamp.isoformat()
            elif not isinstance(timestamp, str):
                timestamp = str(timestamp) if timestamp else ""
            
            messages.append({
                "id": msg_doc.id,
                "role": msg_data.get("role", ""),
                "content": msg_data.get("content", ""),
                "timestamp": timestamp
            })
        
        print(f"✅ Retrieved conversation {conversation_id} with {len(messages)} messages for {user_email}")
        
        return ConversationDetail(
            id=conversation_id,
            title=conv_data.get("title", "Untitled Conversation"),
            created_at=created_at,
            updated_at=updated_at,
            messages=messages
        )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error retrieving conversation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve conversation: {str(e)}")

@app.post("/api/conversations", response_model=ConversationSummary)
async def create_conversation(
    request: CreateConversationRequest,
    email: str
):
    """
    Create a new conversation/session.
    
    Args:
        request: Conversation creation request with optional title
        email: User's Gmail address
    
    Returns:
        Created conversation summary
    """
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    
    user_email = email
    
    try:
        # Get user document reference
        user_ref = db.collection("users").document(user_email)
        
        # Create new conversation document
        conversations_ref = user_ref.collection("conversations")
        
        # Generate title if not provided
        title = request.title or "New Conversation"
        
        now = datetime.utcnow().isoformat()
        
        conversation_data = {
            "title": title,
            "createdAt": now,
            "updatedAt": now
        }
        
        # Add the conversation document
        new_conv_ref = conversations_ref.document()  # Auto-generate ID
        new_conv_ref.set(conversation_data)
        
        print(f"✅ Created conversation {new_conv_ref.id} for {user_email}")
        
        return ConversationSummary(
            id=new_conv_ref.id,
            title=title,
            created_at=now,
            updated_at=now
        )
    
    except Exception as e:
        print(f"❌ Error creating conversation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create conversation: {str(e)}")

@app.post("/api/conversations/{conversation_id}/messages")
async def add_message(
    conversation_id: str,
    message: AddMessageRequest,
    email: str
):
    """
    Add a message to an existing conversation.
    
    Args:
        conversation_id: The conversation/session ID
        message: Message to add (role and content)
        email: User's Gmail address
    
    Returns:
        Success message with message ID
    """
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    
    user_email = email
    
    # Validate role
    if message.role not in ["user", "assistant"]:
        raise HTTPException(status_code=400, detail="Role must be 'user' or 'assistant'")
    
    try:
        # Get conversation reference
        conv_ref = db.collection("users").document(user_email).collection("conversations").document(conversation_id)
        
        # Check if conversation exists
        conv_doc = conv_ref.get()
        if not conv_doc.exists:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Add message to messages subcollection
        messages_ref = conv_ref.collection("messages")
        
        now = datetime.utcnow().isoformat()
        
        message_data = {
            "role": message.role,
            "content": message.content,
            "timestamp": now
        }
        
        # Add the message
        new_msg_ref = messages_ref.document()  # Auto-generate ID
        new_msg_ref.set(message_data)
        
        # Update conversation's updatedAt timestamp
        conv_ref.update({"updatedAt": now})
        
        # If this is the first user message and title is "New Conversation", update title
        conv_data = conv_doc.to_dict()
        if conv_data.get("title") == "New Conversation" and message.role == "user":
            # Generate title from first 4-5 words
            words = message.content.split()[:5]
            new_title = " ".join(words)
            if len(message.content.split()) > 5:
                new_title += "..."
            conv_ref.update({"title": new_title})
            print(f"✅ Updated conversation title to: {new_title}")
        
        print(f"✅ Added {message.role} message to conversation {conversation_id} for {user_email}")
        
        return {
            "success": True,
            "message_id": new_msg_ref.id,
            "conversation_id": conversation_id,
            "timestamp": now
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error adding message: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add message: {str(e)}")

@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    email: str
):
    """
    Delete a conversation and all its messages.
    
    Args:
        conversation_id: The conversation/session ID to delete
        email: User's Gmail address
    
    Returns:
        Success message
    """
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    
    user_email = email
    
    try:
        # Get conversation reference
        conv_ref = db.collection("users").document(user_email).collection("conversations").document(conversation_id)
        
        # Check if conversation exists
        conv_doc = conv_ref.get()
        if not conv_doc.exists:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Delete all messages in the subcollection
        messages_ref = conv_ref.collection("messages")
        messages_docs = messages_ref.stream()
        
        message_count = 0
        for msg_doc in messages_docs:
            msg_doc.reference.delete()
            message_count += 1
        
        # Delete the conversation document
        conv_ref.delete()
        
        print(f"✅ Deleted conversation {conversation_id} with {message_count} messages for {user_email}")
        
        return {
            "success": True,
            "conversation_id": conversation_id,
            "messages_deleted": message_count
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error deleting conversation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete conversation: {str(e)}")


# ==================== FORMS HISTORY ENDPOINTS ====================

class FormSummary(BaseModel):
    """Summary of a form for list view"""
    id: str
    title: str
    created_at: str
    updated_at: str
    embed_url: str
    view_url: str
    edit_url: str

class FormDetail(BaseModel):
    """Detailed form information"""
    id: str
    title: str
    form_id: str
    created_at: str
    updated_at: str
    embed_url: str
    view_url: str
    edit_url: str
    chat_messages: List[dict]

class CreateFormRequest(BaseModel):
    """Request to create a new form history entry"""
    title: str
    form_id: str
    embed_url: str
    view_url: str
    edit_url: str

class AddFormMessageRequest(BaseModel):
    """Request to add a message to form chat history"""
    role: str  # 'user' or 'assistant'
    content: str


@app.get("/api/forms", response_model=List[FormSummary])
async def list_forms(
    email: str,
    page: int = 1,
    limit: int = 10
):
    """
    List all forms for a user with pagination.
    Returns forms ordered by most recently updated.
    """
    try:
        user_ref = db.collection("users").document(email)
        forms_ref = user_ref.collection("forms")
        
        # Query forms ordered by updatedAt descending
        query = forms_ref.order_by("updatedAt", direction=firestore.Query.DESCENDING)
        
        # Apply pagination
        offset = (page - 1) * limit
        query = query.limit(limit).offset(offset)
        
        docs = query.stream()
        
        forms = []
        for doc in docs:
            data = doc.to_dict()
            
            # Convert Firestore timestamps to ISO strings
            created_at = data.get("createdAt", "")
            updated_at = data.get("updatedAt", "")
            
            if hasattr(created_at, 'isoformat'):
                created_at = created_at.isoformat()
            elif not isinstance(created_at, str):
                created_at = str(created_at) if created_at else ""
            
            if hasattr(updated_at, 'isoformat'):
                updated_at = updated_at.isoformat()
            elif not isinstance(updated_at, str):
                updated_at = str(updated_at) if updated_at else ""
            
            forms.append(FormSummary(
                id=doc.id,
                title=data.get("title", "Untitled Form"),
                created_at=created_at,
                updated_at=updated_at,
                embed_url=data.get("embedUrl", ""),
                view_url=data.get("viewUrl", ""),
                edit_url=data.get("editUrl", "")
            ))
        
        print(f"✅ Listed {len(forms)} forms for {email} (page {page})")
        return forms
        
    except Exception as e:
        print(f"❌ Error listing forms: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list forms: {str(e)}")


@app.get("/api/forms/{form_history_id}")
async def get_form(
    form_history_id: str,
    email: str
):
    """
    Get a specific form with its complete chat history.
    """
    try:
        user_ref = db.collection("users").document(email)
        form_ref = user_ref.collection("forms").document(form_history_id)
        
        form_doc = form_ref.get()
        
        if not form_doc.exists:
            raise HTTPException(status_code=404, detail="Form not found")
        
        form_data = form_doc.to_dict()
        
        # Convert timestamps
        created_at = form_data.get("createdAt", "")
        updated_at = form_data.get("updatedAt", "")
        
        if hasattr(created_at, 'isoformat'):
            created_at = created_at.isoformat()
        elif not isinstance(created_at, str):
            created_at = str(created_at) if created_at else ""
        
        if hasattr(updated_at, 'isoformat'):
            updated_at = updated_at.isoformat()
        elif not isinstance(updated_at, str):
            updated_at = str(updated_at) if updated_at else ""
        
        # Get chat messages
        messages_ref = form_ref.collection("messages")
        messages_docs = messages_ref.order_by("timestamp").stream()
        
        chat_messages = []
        for msg_doc in messages_docs:
            msg_data = msg_doc.to_dict()
            timestamp = msg_data.get("timestamp", "")
            
            if hasattr(timestamp, 'isoformat'):
                timestamp = timestamp.isoformat()
            elif not isinstance(timestamp, str):
                timestamp = str(timestamp) if timestamp else ""
            
            chat_messages.append({
                "id": msg_doc.id,
                "role": msg_data.get("role", ""),
                "content": msg_data.get("content", ""),
                "timestamp": timestamp
            })
        
        form_detail = FormDetail(
            id=form_doc.id,
            title=form_data.get("title", "Untitled Form"),
            form_id=form_data.get("formId", ""),
            created_at=created_at,
            updated_at=updated_at,
            embed_url=form_data.get("embedUrl", ""),
            view_url=form_data.get("viewUrl", ""),
            edit_url=form_data.get("editUrl", ""),
            chat_messages=chat_messages
        )
        
        print(f"✅ Retrieved form {form_history_id} for {email}")
        return form_detail
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting form: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get form: {str(e)}")


@app.post("/api/forms")
async def create_form(
    request: CreateFormRequest,
    email: str
):
    """
    Create a new form history entry.
    """
    try:
        user_ref = db.collection("users").document(email)
        forms_ref = user_ref.collection("forms")
        
        # Generate new form history ID
        form_history_ref = forms_ref.document()
        
        now = firestore.SERVER_TIMESTAMP
        
        form_data = {
            "title": request.title,
            "formId": request.form_id,
            "embedUrl": request.embed_url,
            "viewUrl": request.view_url,
            "editUrl": request.edit_url,
            "createdAt": now,
            "updatedAt": now
        }
        
        form_history_ref.set(form_data)
        
        print(f"✅ Created form history {form_history_ref.id} for {email}")
        
        return {
            "id": form_history_ref.id,
            "message": "Form history created successfully"
        }
        
    except Exception as e:
        print(f"❌ Error creating form: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create form: {str(e)}")


@app.post("/api/forms/{form_history_id}/messages")
async def add_form_message(
    form_history_id: str,
    request: AddFormMessageRequest,
    email: str
):
    """
    Add a message to a form's chat history.
    """
    try:
        user_ref = db.collection("users").document(email)
        form_ref = user_ref.collection("forms").document(form_history_id)
        
        # Check if form exists
        if not form_ref.get().exists:
            raise HTTPException(status_code=404, detail="Form not found")
        
        # Add message to messages subcollection
        messages_ref = form_ref.collection("messages")
        message_ref = messages_ref.document()
        
        now = firestore.SERVER_TIMESTAMP
        
        message_data = {
            "role": request.role,
            "content": request.content,
            "timestamp": now
        }
        
        message_ref.set(message_data)
        
        # Update form's updatedAt timestamp
        form_ref.update({"updatedAt": now})
        
        print(f"✅ Added message to form {form_history_id} for {email}")
        
        return {
            "id": message_ref.id,
            "message": "Message added successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error adding message: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add message: {str(e)}")


@app.delete("/api/forms/{form_history_id}")
async def delete_form(
    form_history_id: str,
    email: str
):
    """
    Delete a form and all its messages.
    """
    try:
        user_ref = db.collection("users").document(email)
        form_ref = user_ref.collection("forms").document(form_history_id)
        
        # Delete all messages first
        messages_ref = form_ref.collection("messages")
        messages_docs = messages_ref.stream()
        
        for msg_doc in messages_docs:
            msg_doc.reference.delete()
        
        # Delete the form document
        form_ref.delete()
        
        print(f"✅ Deleted form {form_history_id} for {email}")
        
        return {"message": "Form deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error deleting form: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete form: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)


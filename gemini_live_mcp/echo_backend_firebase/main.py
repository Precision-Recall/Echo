"""
FastAPI backend for managing user OAuth tokens in Firebase Firestore.

This service provides REST endpoints to store and retrieve Google OAuth credentials
for users authenticated via Firebase Authentication.
"""

import os
import json
from datetime import datetime
from typing import Optional
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

# Helper functions
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

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)


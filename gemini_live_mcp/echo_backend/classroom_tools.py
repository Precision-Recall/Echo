"""
Google Classroom API Tools with Firestore Authentication

This module provides async functions for interacting with the Google Classroom API.
Uses Firestore for secure, per-user OAuth token storage.

Authentication:
   - Pass `user_email` and `firebase_token` to any tool function
   - Tokens are securely retrieved from Firestore via the token service
   - Each user has their own OAuth tokens
   - Supports multi-user applications

Configuration:
- Set TOKEN_SERVICE_URL environment variable (default: http://localhost:8001)
- Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables
- User must authorize via OAuth and store tokens in Firestore
"""

import os
import json
import logging
import httpx
import asyncio
import smtplib
import io
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List, Dict, Any
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.auth.transport.requests import Request
from google.genai import types

# Paths - Use environment variables or default to current directory
BASE_DIR = os.getenv("CLASSROOM_DATA_DIR", os.path.dirname(__file__))
TOKENS_PATH = os.path.join(BASE_DIR, "tokens.json")
CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials.json")

# Token service configuration
TOKEN_SERVICE_URL = os.getenv("TOKEN_SERVICE_URL", "http://localhost:8001")

async def get_tokens_from_firestore(user_email: str, firebase_id_token: str, max_retries: int = 3) -> dict:
    """
    Retrieve user's OAuth tokens from Firestore via token service with retry mechanism.
    
    Args:
        user_email: User's email address
        firebase_id_token: Firebase ID token for authentication
        max_retries: Maximum number of retry attempts (default: 3)
    
    Returns:
        Dictionary with access_token, refresh_token, and optional fields
    
    Raises:
        Exception: If token retrieval fails after all retries
    """
    last_error = None
    
    for attempt in range(max_retries):
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{TOKEN_SERVICE_URL}/api/tokens/retrieve",
                    params={"email": user_email},
                    headers={"Authorization": f"Bearer {firebase_id_token}"},
                    timeout=15.0  # Increased timeout
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if attempt > 0:
                        print(f"✅ Retrieved tokens from Firestore for {user_email} (attempt {attempt + 1})")
                    else:
                        print(f"✅ Retrieved tokens from Firestore for {user_email}")
                    return {
                        "access_token": data["access_token"],
                        "refresh_token": data["refresh_token"],
                        "expires_in": data.get("expires_in", 3600),
                        "scope": data.get("scope", "")
                    }
                elif response.status_code == 404:
                    raise Exception("No Google Classroom tokens found. Please authorize access first.")
                elif response.status_code == 401:
                    raise Exception("Authentication failed. Please log in again.")
                else:
                    error_data = response.json()
                    raise Exception(error_data.get("detail", "Failed to retrieve tokens"))
            
            except httpx.TimeoutException as e:
                last_error = e
                if attempt < max_retries - 1:
                    print(f"⚠️  Token service timeout (attempt {attempt + 1}/{max_retries}), retrying...")
                    await asyncio.sleep(2)  # Wait 2 seconds before retry
                    continue
                raise Exception("Token service timeout after multiple attempts. Please try again.")
            except httpx.ConnectError as e:
                last_error = e
                raise Exception(f"Cannot connect to token service at {TOKEN_SERVICE_URL}")
            except Exception as e:
                if "No Google Classroom tokens found" in str(e) or "Authentication failed" in str(e):
                    raise
                last_error = e
                if attempt < max_retries - 1:
                    print(f"⚠️  Error retrieving tokens (attempt {attempt + 1}/{max_retries}), retrying...")
                    await asyncio.sleep(2)  # Wait 2 seconds before retry
                    continue
                print(f"❌ Error retrieving tokens from Firestore: {e}")
                raise Exception(f"Failed to retrieve tokens: {str(e)}")

async def update_tokens_in_firestore(user_email: str, firebase_id_token: str, access_token: str, refresh_token: str, expires_in: int = 3600, scope: str = "") -> bool:
    """
    Update user's OAuth tokens in Firestore via token service.
    This is called after refreshing tokens to persist the new access token.
    
    Args:
        user_email: User's email address
        firebase_id_token: Firebase ID token for authentication
        access_token: New access token
        refresh_token: Refresh token
        expires_in: Token expiration time in seconds
        scope: OAuth scopes
    
    Returns:
        True if update successful, False otherwise
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{TOKEN_SERVICE_URL}/api/tokens/store",
                json={
                    "email": user_email,
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "expires_in": expires_in,
                    "scope": scope
                },
                headers={"Authorization": f"Bearer {firebase_id_token}"},
                timeout=10.0
            )
            
            if response.status_code == 200:
                print(f"✅ Updated refreshed tokens in Firestore for {user_email}")
                return True
            else:
                error_data = response.json()
                print(f"⚠️  Failed to update tokens in Firestore: {error_data.get('detail', 'Unknown error')}")
                return False
        
        except Exception as e:
            print(f"⚠️  Error updating tokens in Firestore: {e}")
            return False

async def get_classroom_service(user_email: Optional[str] = None, firebase_id_token: Optional[str] = None):
    """
    Authenticate and return the Google Classroom service.
    
    Args:
        user_email: User's email (for Firestore token retrieval)
        firebase_id_token: Firebase ID token (for Firestore token retrieval)
    
    Returns:
        Google Classroom service object
    
    Raises:
        Exception: If user_email and firebase_id_token are not provided
    """
    # Require Firestore authentication
    if not user_email or not firebase_id_token:
        raise Exception(
            "Authentication required. Please provide user_email and firebase_id_token.\n"
            "User must authorize Google Classroom access through the app."
        )
    
    # Get tokens from Firestore with retry mechanism
    tokens = await get_tokens_from_firestore(user_email, firebase_id_token)
    print(f"📚 Using Firestore tokens for {user_email}")

    # Get Client ID/Secret
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")

    if not client_id or not client_secret:
        if os.path.exists(CREDENTIALS_PATH):
            with open(CREDENTIALS_PATH, "r") as f:
                creds_data = json.load(f)
                web_or_installed = creds_data.get("web") or creds_data.get("installed")
                if web_or_installed:
                    client_id = web_or_installed.get("client_id")
                    client_secret = web_or_installed.get("client_secret")

    if not client_id or not client_secret:
        raise ValueError(
            "Google OAuth credentials not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET "
            "environment variables or provide credentials.json"
        )

    creds = Credentials(
        token=tokens.get("access_token"),
        refresh_token=tokens.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=tokens.get("scope", "").split(" ") if isinstance(tokens.get("scope"), str) else []
    )

    # Refresh if expired
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            print(f"🔄 Refreshed access token")
            
            # Save refreshed token back to Firestore if using Firestore auth
            if user_email and firebase_id_token:
                await update_tokens_in_firestore(
                    user_email=user_email,
                    firebase_id_token=firebase_id_token,
                    access_token=creds.token,
                    refresh_token=creds.refresh_token,
                    expires_in=3600,  # Default expiration
                    scope=" ".join(creds.scopes) if creds.scopes else ""
                )
        except Exception as e:
            logging.error(f"Failed to refresh token: {e}")
            raise Exception("Failed to refresh access token. Please re-authorize Google Classroom.")

    return build("classroom", "v1", credentials=creds)

async def get_docs_service(user_email: Optional[str] = None, firebase_id_token: Optional[str] = None):
    """
    Authenticate and return the Google Docs service.
    Requires Firestore authentication.
    """
    if not user_email or not firebase_id_token:
        raise Exception("Authentication required. Please provide user_email and firebase_id_token.")
    
    # Get tokens from Firestore with retry
    tokens = await get_tokens_from_firestore(user_email, firebase_id_token)
    
    # Get OAuth credentials
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        if os.path.exists(CREDENTIALS_PATH):
            with open(CREDENTIALS_PATH, "r") as f:
                creds_data = json.load(f)
                web_or_installed = creds_data.get("web") or creds_data.get("installed")
                if web_or_installed:
                    client_id = web_or_installed.get("client_id")
                    client_secret = web_or_installed.get("client_secret")
    
    if not client_id or not client_secret:
        raise ValueError("Google OAuth credentials not configured.")
    
    creds = Credentials(
        token=tokens.get("access_token"),
        refresh_token=tokens.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=tokens.get("scope", "").split(" ") if isinstance(tokens.get("scope"), str) else []
    )
    print(f"📄 Using Firestore tokens for Google Docs for {user_email}")
    
    # Refresh if expired
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            print(f"🔄 Refreshed access token for Docs")
            
            # Save refreshed token back to Firestore if using Firestore auth
            if user_email and firebase_id_token:
                await update_tokens_in_firestore(
                    user_email=user_email,
                    firebase_id_token=firebase_id_token,
                    access_token=creds.token,
                    refresh_token=creds.refresh_token,
                    expires_in=3600,
                    scope=" ".join(creds.scopes) if creds.scopes else ""
                )
        except Exception as e:
            logging.error(f"Failed to refresh token: {e}")
            raise
    
    return build("docs", "v1", credentials=creds)

async def get_drive_service(user_email: Optional[str] = None, firebase_id_token: Optional[str] = None):
    """
    Authenticate and return the Google Drive service.
    Uses the same authentication flow as Classroom.
    """
    creds = None
    if user_email and firebase_id_token:
        try:
            tokens = await get_tokens_from_firestore(user_email, firebase_id_token)
            client_id = os.environ.get("GOOGLE_CLIENT_ID")
            client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
            
            if not client_id or not client_secret:
                if os.path.exists(CREDENTIALS_PATH):
                    with open(CREDENTIALS_PATH, "r") as f:
                        creds_data = json.load(f)
                        client_id = creds_data["installed"]["client_id"]
                        client_secret = creds_data["installed"]["client_secret"]
                else:
                    raise Exception("Google OAuth credentials not found")
            
            creds = Credentials(
                token=tokens["access_token"],
                refresh_token=tokens["refresh_token"],
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_id,
                client_secret=client_secret,
                scopes=tokens.get("scope", "").split()
            )
            print(f"📚 Using Firestore tokens for {user_email}")
        except Exception as e:
            logging.error(f"Error getting tokens from Firestore: {e}")
            raise
    else:
        if os.path.exists(TOKENS_PATH):
            creds = Credentials.from_authorized_user_file(TOKENS_PATH)
        else:
            raise Exception("No authentication credentials available")
    
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            if user_email and firebase_id_token:
                await update_tokens_in_firestore(
                    user_email, firebase_id_token,
                    creds.token, creds.refresh_token,
                    3600, " ".join(creds.scopes)
                )
        except Exception as e:
            logging.error(f"Failed to refresh token: {e}")
            raise
    
    return build("drive", "v3", credentials=creds)

async def upload_file_to_drive(file_data: Dict[str, Any], user_email: Optional[str] = None, firebase_token: Optional[str] = None) -> Dict[str, str]:
    """
    Upload a file to Google Drive.
    
    Args:
        file_data: Dictionary containing:
            - name: File name
            - content: Base64-encoded file content
            - mimeType: MIME type of the file
        user_email: User's email (for authentication)
        firebase_token: Firebase ID token (for authentication)
    
    Returns:
        Dictionary with Drive file ID and title
    """
    try:
        drive_service = await get_drive_service(user_email, firebase_token)
        
        # Decode base64 content
        file_content = base64.b64decode(file_data['content'])
        file_stream = io.BytesIO(file_content)
        
        # Create file metadata
        file_metadata = {
            'name': file_data['name'],
            'mimeType': file_data.get('mimeType', 'application/octet-stream')
        }
        
        # Create media upload
        media = MediaIoBaseUpload(
            file_stream,
            mimetype=file_data.get('mimeType', 'application/octet-stream'),
            resumable=True
        )
        
        # Upload file
        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, mimeType, webViewLink'
        ).execute()
        
        file_id = file.get('id')
        file_name = file.get('name')
        
        print(f"📁 Uploaded file to Drive: {file_name} (ID: {file_id})")
        
        # Set file permissions to allow anyone with the link to view
        # This is necessary for Google Classroom to access the file
        try:
            permission = {
                'type': 'anyone',
                'role': 'reader'
            }
            drive_service.permissions().create(
                fileId=file_id,
                body=permission
            ).execute()
            print(f"✅ Set file permissions for: {file_name}")
        except Exception as perm_error:
            print(f"⚠️  Warning: Could not set file permissions: {perm_error}")
        
        return {
            'id': file_id,
            'title': file_name,
            'mimeType': file.get('mimeType'),
            'webViewLink': file.get('webViewLink', '')
        }
        
    except Exception as e:
        print(f"❌ Error uploading file to Drive: {e}")
        raise Exception(f"Failed to upload file: {str(e)}")

async def get_sheets_service(user_email: Optional[str] = None, firebase_id_token: Optional[str] = None):
    """
    Authenticate and return the Google Sheets service.
    Requires Firestore authentication.
    """
    if not user_email or not firebase_id_token:
        raise Exception("Authentication required. Please provide user_email and firebase_id_token.")
    
    # Get tokens from Firestore with retry
    tokens = await get_tokens_from_firestore(user_email, firebase_id_token)
    
    # Get OAuth credentials
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        if os.path.exists(CREDENTIALS_PATH):
            with open(CREDENTIALS_PATH, "r") as f:
                creds_data = json.load(f)
                web_or_installed = creds_data.get("web") or creds_data.get("installed")
                if web_or_installed:
                    client_id = web_or_installed.get("client_id")
                    client_secret = web_or_installed.get("client_secret")
    
    if not client_id or not client_secret:
        raise ValueError("Google OAuth credentials not configured.")
    
    creds = Credentials(
        token=tokens.get("access_token"),
        refresh_token=tokens.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=tokens.get("scope", "").split(" ") if isinstance(tokens.get("scope"), str) else []
    )
    print(f"📊 Using Firestore tokens for Google Sheets for {user_email}")
    
    # Refresh if expired
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            print(f"🔄 Refreshed access token for Sheets")
            
            # Save refreshed token back to Firestore if using Firestore auth
            if user_email and firebase_id_token:
                await update_tokens_in_firestore(
                    user_email=user_email,
                    firebase_id_token=firebase_id_token,
                    access_token=creds.token,
                    refresh_token=creds.refresh_token,
                    expires_in=3600,
                    scope=" ".join(creds.scopes) if creds.scopes else ""
                )
        except Exception as e:
            logging.error(f"Failed to refresh token: {e}")
            raise
    
    return build("sheets", "v4", credentials=creds)

def _load_local_creds_for_docs():
    """Helper to load credentials from local tokens.json for Docs"""
    if not os.path.exists(TOKENS_PATH):
        logging.warning(f"tokens.json not found at {TOKENS_PATH}")
        return None
    
    with open(TOKENS_PATH, "r") as f:
        tokens = json.load(f)
    
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        if os.path.exists(CREDENTIALS_PATH):
            with open(CREDENTIALS_PATH, "r") as f:
                creds_data = json.load(f)
                web_or_installed = creds_data.get("web") or creds_data.get("installed")
                if web_or_installed:
                    client_id = web_or_installed.get("client_id")
                    client_secret = web_or_installed.get("client_secret")
    
    if not client_id or not client_secret:
        return None
    
    return Credentials(
        token=tokens.get("access_token"),
        refresh_token=tokens.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=tokens.get("scope", "").split(" ") if isinstance(tokens.get("scope"), str) else []
    )

def _load_local_creds_for_sheets():
    """Helper to load credentials from local tokens.json for Sheets"""
    # Same as docs
    return _load_local_creds_for_docs()

async def get_forms_service(user_email: Optional[str] = None, firebase_id_token: Optional[str] = None):
    """
    Authenticate and return the Google Forms service.
    Requires Firestore authentication.
    
    Required permission: https://www.googleapis.com/auth/forms.body
    """
    if not user_email or not firebase_id_token:
        raise Exception("Authentication required. Please provide user_email and firebase_id_token.")
    
    # Get tokens from Firestore with retry
    tokens = await get_tokens_from_firestore(user_email, firebase_id_token)
    
    # Get OAuth credentials
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        if os.path.exists(CREDENTIALS_PATH):
            with open(CREDENTIALS_PATH, "r") as f:
                creds_data = json.load(f)
                web_or_installed = creds_data.get("web") or creds_data.get("installed")
                if web_or_installed:
                    client_id = web_or_installed.get("client_id")
                    client_secret = web_or_installed.get("client_secret")
    
    if not client_id or not client_secret:
        raise ValueError("Google OAuth credentials not configured.")
    
    creds = Credentials(
        token=tokens.get("access_token"),
        refresh_token=tokens.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=tokens.get("scope", "").split(" ") if isinstance(tokens.get("scope"), str) else []
    )
    print(f"📋 Using Firestore tokens for Google Forms for {user_email}")
    
    # Refresh if expired
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            print(f"🔄 Refreshed access token for Forms")
            
            # Save refreshed token back to Firestore if using Firestore auth
            if user_email and firebase_id_token:
                await update_tokens_in_firestore(
                    user_email=user_email,
                    firebase_id_token=firebase_id_token,
                    access_token=creds.token,
                    refresh_token=creds.refresh_token,
                    expires_in=3600,
                    scope=" ".join(creds.scopes) if creds.scopes else ""
                )
        except Exception as e:
            logging.error(f"Failed to refresh token: {e}")
            raise
    
    return build("forms", "v1", credentials=creds)

def _load_local_creds_for_forms():
    """Helper to load credentials from local tokens.json for Forms"""
    # Same as docs/sheets
    return _load_local_creds_for_docs()

async def get_slides_service(user_email: Optional[str] = None, firebase_id_token: Optional[str] = None):
    """
    Authenticate and return the Google Slides service.
    Requires Firestore authentication.
    
    Required permission: https://www.googleapis.com/auth/presentations
    """
    if not user_email or not firebase_id_token:
        raise Exception("Authentication required. Please provide user_email and firebase_id_token.")
    
    # Get tokens from Firestore with retry
    tokens = await get_tokens_from_firestore(user_email, firebase_id_token)
    
    # Get OAuth credentials
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        if os.path.exists(CREDENTIALS_PATH):
            with open(CREDENTIALS_PATH, "r") as f:
                creds_data = json.load(f)
                web_or_installed = creds_data.get("web") or creds_data.get("installed")
                if web_or_installed:
                    client_id = web_or_installed.get("client_id")
                    client_secret = web_or_installed.get("client_secret")
    
    if not client_id or not client_secret:
        raise ValueError("Google OAuth credentials not configured.")
    
    creds = Credentials(
        token=tokens.get("access_token"),
        refresh_token=tokens.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=tokens.get("scope", "").split(" ") if isinstance(tokens.get("scope"), str) else []
    )
    print(f"📊 Using Firestore tokens for Google Slides for {user_email}")
    
    # Refresh if expired
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            # Save refreshed token back to Firestore
            await update_tokens_in_firestore(
                user_email=user_email,
                firebase_id_token=firebase_id_token,
                access_token=creds.token,
                refresh_token=creds.refresh_token,
                expires_in=3600,
                scope=" ".join(creds.scopes) if creds.scopes else ""
            )
        except Exception as e:
            logging.error(f"Failed to refresh token: {e}")
            raise
    
    return build("slides", "v1", credentials=creds)

# --- Tool Helper Functions ---

async def list_courses(course_states=None, teacher_id=None, student_id=None, user_email=None, firebase_token=None):
    try:
        service = await get_classroom_service(user_email, firebase_token)
        kwargs = {}
        if course_states: kwargs['courseStates'] = course_states
        if teacher_id: kwargs['teacherId'] = teacher_id
        if student_id: kwargs['studentId'] = student_id
        
        results = service.courses().list(**kwargs).execute()
        return {"courses": results.get("courses", [])}
    except Exception as e:
        print(f"❌ Error in list_courses: {e}")
        return {"error": str(e)}

async def get_course(course_id, user_email=None, firebase_token=None):
    try:
        service = await get_classroom_service(user_email, firebase_token)
        result = service.courses().get(id=course_id).execute()
        return {"course": result}
    except Exception as e:
        print(f"❌ Error in get_course: {e}")
        return {"error": str(e)}

async def show_coursework_form(user_email=None, firebase_token=None):
    """
    Show a form with course dropdown to select which course's coursework to view.
    Internally fetches all available courses.
    """
    try:
        print("📋 Fetching courses for coursework form...")
        courses_result = await list_courses(user_email=user_email, firebase_token=firebase_token)
        
        if "error" in courses_result:
            return courses_result
        
        courses = courses_result.get("courses", [])
        print(f"✅ Displaying coursework form with {len(courses)} courses in dropdown")
        
        return {
            "action": "show_form",
            "form_type": "coursework",
            "courses": courses
        }
    except Exception as e:
        print(f"❌ Error in show_coursework_form: {e}")
        return {"error": str(e)}

async def list_coursework(course_id, course_work_states=None, user_email=None, firebase_token=None):
    try:
        service = await get_classroom_service(user_email, firebase_token)
        kwargs = {'courseId': course_id}
        if course_work_states: kwargs['courseWorkStates'] = course_work_states
        
        results = service.courses().courseWork().list(**kwargs).execute()
        return {"courseWork": results.get("courseWork", [])}
    except Exception as e:
        print(f"❌ Error in list_coursework: {e}")
        return {"error": str(e)}

async def get_coursework(course_id, course_work_id, user_email=None, firebase_token=None):
    try:
        service = await get_classroom_service(user_email, firebase_token)
        result = service.courses().courseWork().get(courseId=course_id, id=course_work_id).execute()
        return {"coursework": result}
    except Exception as e:
        print(f"❌ Error in get_coursework: {e}")
        return {"error": str(e)}

async def show_announcements_form(user_email=None, firebase_token=None):
    """
    Show a form with course dropdown to select which course's announcements to view.
    Internally fetches all available courses.
    """
    try:
        print("📢 Fetching courses for announcements form...")
        courses_result = await list_courses(user_email=user_email, firebase_token=firebase_token)
        
        if "error" in courses_result:
            return courses_result
        
        courses = courses_result.get("courses", [])
        print(f"✅ Displaying announcements form with {len(courses)} courses in dropdown")
        
        return {
            "action": "show_form",
            "form_type": "announcements",
            "courses": courses
        }
    except Exception as e:
        print(f"❌ Error in show_announcements_form: {e}")
        return {"error": str(e)}

async def list_announcements(course_id, announcement_states=None, user_email=None, firebase_token=None):
    try:
        service = await get_classroom_service(user_email, firebase_token)
        kwargs = {'courseId': course_id}
        if announcement_states: kwargs['announcementStates'] = announcement_states
        
        results = service.courses().announcements().list(**kwargs).execute()
        return {"announcements": results.get("announcements", [])}
    except Exception as e:
        print(f"❌ Error in list_announcements: {e}")
        return {"error": str(e)}

async def list_submissions(course_id, course_work_id, user_id=None, user_email=None, firebase_token=None):
    try:
        service = await get_classroom_service(user_email, firebase_token)
        kwargs = {'courseId': course_id, 'courseWorkId': course_work_id}
        if user_id: kwargs['userId'] = user_id
        
        results = service.courses().courseWork().studentSubmissions().list(**kwargs).execute()
        return {"studentSubmissions": results.get("studentSubmissions", [])}
    except Exception as e:
        print(f"❌ Error in list_submissions: {e}")
        return {"error": str(e)}

async def create_coursework(course_id, title, description=None, due_date=None, due_time=None, max_points=None, work_type="ASSIGNMENT", file_ids=None, user_email=None, firebase_token=None):
    """
    Create a new assignment/coursework in Google Classroom.
    
    Args:
        course_id: The ID of the course
        title: Assignment title
        description: Assignment description
        due_date: Due date in YYYY-MM-DD format
        due_time: Due time in HH:MM format
        max_points: Maximum points for the assignment
        work_type: Type of work (ASSIGNMENT, SHORT_ANSWER_QUESTION, etc.)
        file_ids: Comma-separated string of Google Drive file IDs (already uploaded)
        user_email: User's email (for authentication)
        firebase_token: Firebase ID token (for authentication)
    
    Returns:
        Dictionary with coursework details
    """
    try:
        service = await get_classroom_service(user_email, firebase_token)
        body = {
            "title": title,
            "workType": work_type,
            "state": "PUBLISHED",
        }
        if description: body["description"] = description
        if max_points: body["maxPoints"] = max_points
        if due_date:
            y, m, d = map(int, due_date.split("-"))
            body["dueDate"] = {"year": y, "month": m, "day": d}
        if due_time:
            h, m = map(int, due_time.split(":"))
            body["dueTime"] = {"hours": h, "minutes": m}
        
        # Handle file attachments if file IDs are provided
        if file_ids:
            # Parse file IDs (comma-separated string)
            file_id_list = [fid.strip() for fid in file_ids.split(',') if fid.strip()]
            
            if file_id_list:
                print(f"📎 Attaching {len(file_id_list)} file(s) to assignment...")
                materials = []
                
                # Get Drive service to fetch file metadata
                drive_service = await get_drive_service(user_email, firebase_token)
                
                for file_id in file_id_list:
                    try:
                        # Get file metadata from Drive
                        file_metadata = drive_service.files().get(
                            fileId=file_id,
                            fields='id, name, mimeType'
                        ).execute()
                        
                        # Add to materials array
                        materials.append({
                            "driveFile": {
                                "driveFile": {
                                    "id": file_id,
                                    "title": file_metadata.get('name', 'Untitled')
                                }
                            }
                        })
                        print(f"✅ Attached file: {file_metadata.get('name')}")
                    except Exception as file_error:
                        print(f"⚠️  Failed to attach file {file_id}: {file_error}")
                        # Continue with other files even if one fails
                
                if materials:
                    body["materials"] = materials
                    print(f"📎 Added {len(materials)} file(s) as materials to assignment")

        result = service.courses().courseWork().create(courseId=course_id, body=body).execute()
        
        return {"coursework": result}
        
    except Exception as e:
        print(f"❌ Error in create_coursework: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

async def show_assignment_form(course_id=None, user_email=None, firebase_token=None):
    """
    Special tool that signals the UI to show the assignment creation form.
    This tool automatically fetches all available courses and displays them in a dropdown.
    
    Args:
        course_id: Optional course ID to pre-select in the dropdown
        user_email: User's email (for fetching courses from Google Classroom)
        firebase_token: Firebase ID token (for authentication)
    
    Returns:
        Dictionary with form action and courses data for the UI
    """
    print("📋 Fetching courses for assignment form...")
    
    # Automatically fetch courses using the list_courses function
    courses_result = await list_courses(user_email=user_email, firebase_token=firebase_token)
    
    # Extract courses array from result
    courses_data = []
    if isinstance(courses_result, dict):
        if "courses" in courses_result:
            courses_data = courses_result["courses"]
        elif "error" in courses_result:
            print(f"❌ Error fetching courses: {courses_result['error']}")
            courses_data = []
    
    print(f"✅ Displaying assignment form with {len(courses_data)} courses in dropdown")
    if len(courses_data) > 0:
        print(f"  📚 First course: {courses_data[0].get('name', 'Unknown')}")
    
    return {
        "action": "show_form",
        "form_type": "assignment",
        "course_id": course_id or "",
        "courses": courses_data
    }

async def send_course_invitation_email(course_name: str, course_link: str, enrollment_code: str, student_emails: List[str], teacher_name: str = "Your Teacher"):
    """
    Send course invitation email to students using Gmail SMTP.
    
    Args:
        course_name: Name of the course
        course_link: Google Classroom join link
        enrollment_code: Course enrollment code (for manual entry)
        student_emails: List of student email addresses
        teacher_name: Name of the teacher (optional)
    
    Returns:
        Dictionary with success status and message
    """
    try:
        # Get Gmail credentials from environment
        gmail_user = os.getenv("GMAIL_USER")
        gmail_password = os.getenv("GMAIL_APP_PASSWORD")
        
        if not gmail_user or not gmail_password:
            return {
                "success": False,
                "error": "Gmail credentials not configured. Set GMAIL_USER and GMAIL_APP_PASSWORD in environment variables."
            }
        
        # Create email message
        msg = MIMEMultipart('alternative')
        msg['From'] = gmail_user
        msg['To'] = ", ".join(student_emails)
        msg['Subject'] = f"Invitation to Join: {course_name}"
        
        # Email body (HTML)
        html_body = f"""
        <html>
          <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
              <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 10px 10px 0 0; text-align: center;">
                <h1 style="color: white; margin: 0;">You're Invited!</h1>
              </div>
              
              <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
                <p style="font-size: 16px;">Hello,</p>
                
                <p style="font-size: 16px;">
                  {teacher_name} has invited you to join the Google Classroom course:
                </p>
                
                <div style="background: white; padding: 20px; border-left: 4px solid #667eea; margin: 20px 0;">
                  <h2 style="margin: 0; color: #667eea;">{course_name}</h2>
                </div>
                
                <p style="font-size: 16px; margin-bottom: 10px;">
                  <strong>How to join:</strong>
                </p>
                
                <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border: 2px solid #764ba2;">
                  <p style="margin: 0 0 10px 0; font-size: 14px; color: #666;">
                    Use this class code to join:
                  </p>
                  <div style="text-align: center; margin: 10px 0;">
                    <div style="background: #f5f5f5; padding: 15px 25px; border-radius: 5px; display: inline-block;">
                      <span style="font-family: 'Courier New', monospace; font-size: 24px; font-weight: bold; color: #764ba2; letter-spacing: 2px;">
                        {enrollment_code}
                      </span>
                    </div>
                  </div>
                  <p style="margin: 10px 0 0 0; font-size: 12px; color: #999; text-align: center;">
                    Go to <a href="https://classroom.google.com" style="color: #764ba2;">classroom.google.com</a> and enter this code
                  </p>
                </div>
                
                <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
                
                <p style="font-size: 12px; color: #999; text-align: center;">
                  This is an automated message from Google Classroom via Echo AI Assistant.
                </p>
              </div>
            </div>
          </body>
        </html>
        """
        
        # Plain text version
        text_body = f"""
You're Invited to Join a Google Classroom Course!

{teacher_name} has invited you to join: {course_name}

HOW TO JOIN:

Class Code: {enrollment_code}
Go to classroom.google.com and enter this code

---
This is an automated message from Google Classroom via Echo AI Assistant.
        """
        
        # Attach both plain text and HTML versions
        part1 = MIMEText(text_body, 'plain')
        part2 = MIMEText(html_body, 'html')
        msg.attach(part1)
        msg.attach(part2)
        
        # Send email via Gmail SMTP
        print(f"📧 Sending course invitation to {len(student_emails)} students...")
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(gmail_user, gmail_password)
            server.send_message(msg)
        
        print(f"✅ Course invitation sent successfully to {len(student_emails)} students")
        
        return {
            "success": True,
            "message": f"Invitation sent to {len(student_emails)} students",
            "recipients": student_emails
        }
        
    except Exception as e:
        print(f"❌ Error sending course invitation email: {e}")
        return {
            "success": False,
            "error": str(e)
        }

async def create_course(name, section=None, description_heading=None, description=None, room=None, owner_id="me", student_list_id=None, user_email=None, firebase_token=None):
    """
    Create a new course in Google Classroom and optionally send invitations to students.
    
    Required permission: https://www.googleapis.com/auth/classroom.courses
    
    Args:
        name: Course name (required)
        section: Section of the course (e.g., "Period 2", "Section A")
        description_heading: Short description heading
        description: Full course description
        room: Room location
        owner_id: Teacher ID (defaults to "me" for authenticated user)
        student_list_id: Optional ID of student list to send invitations to
        user_email: User's email (for Firestore token retrieval)
        firebase_token: Firebase ID token (for Firestore token retrieval)
    
    Returns:
        Dictionary with course details, enrollment link, and email status
    """
    try:
        service = await get_classroom_service(user_email, firebase_token)
        body = {
            "name": name,
            "ownerId": owner_id,
            # Don't set courseState - let Google Classroom use the default (PROVISIONED)
            # Some accounts can't create courses directly in ACTIVE state
        }
        
        if section: body["section"] = section
        if description_heading: body["descriptionHeading"] = description_heading
        if description: body["description"] = description
        if room: body["room"] = room
        
        result = service.courses().create(body=body).execute()
        
        course_id = result.get('id')
        course_name = result.get('name')
        
        print(f"✅ Course created: {course_name} (ID: {course_id})")
        
        # Get the enrollment code - this is what students use to join
        enrollment_code = result.get('enrollmentCode')
        
        # Construct the enrollment link
        # The correct format is: https://classroom.google.com/c/{enrollmentCode}
        # NOT the course ID - the enrollment code is what allows students to join
        enrollment_link = None
        if enrollment_code:
            enrollment_link = f"https://classroom.google.com/c/{enrollment_code}"
            print(f"📧 Enrollment link: {enrollment_link}")
        else:
            # If no enrollment code (shouldn't happen), log a warning
            print(f"⚠️  No enrollment code found for course {course_id}")
            # Fallback: try to get the course again to fetch enrollment code
            try:
                updated_course = service.courses().get(id=course_id).execute()
                enrollment_code = updated_course.get('enrollmentCode')
                if enrollment_code:
                    enrollment_link = f"https://classroom.google.com/c/{enrollment_code}"
                    print(f"📧 Retrieved enrollment link: {enrollment_link}")
            except Exception as e:
                print(f"⚠️  Could not retrieve enrollment code: {e}")
        
        # Check course state and add appropriate message
        course_state = result.get('courseState', 'PROVISIONED')
        state_message = ""
        if course_state == 'PROVISIONED':
            state_message = "Note: Course created in PROVISIONED state. You may need to manually activate it in Google Classroom before students can join."
        
        response = {
            "course": result,
            "enrollment_link": enrollment_link,
            "enrollment_code": enrollment_code,
            "course_state": course_state,
            "message": state_message
        }
        
        # If student_list_id is provided, fetch the list and send emails
        if student_list_id and user_email and firebase_token:
            print(f"📋 Fetching student list: {student_list_id}")
            
            try:
                # Fetch student list from Firebase
                TOKEN_SERVICE_URL = os.getenv("TOKEN_SERVICE_URL", "http://localhost:8001")
                
                async with httpx.AsyncClient() as client:
                    list_response = await client.get(
                        f"{TOKEN_SERVICE_URL}/api/student-lists/{student_list_id}",
                        headers={"Authorization": f"Bearer {firebase_token}"},
                        timeout=10.0
                    )
                    
                    if list_response.status_code == 200:
                        student_list = list_response.json()
                        student_emails = student_list.get("emails", [])
                        
                        if student_emails and enrollment_link and enrollment_code:
                            # Send invitation emails
                            teacher_name = user_email.split('@')[0].replace('.', ' ').title()
                            email_result = await send_course_invitation_email(
                                course_name=course_name,
                                course_link=enrollment_link,
                                enrollment_code=enrollment_code,
                                student_emails=student_emails,
                                teacher_name=teacher_name
                            )
                            
                            response["email_sent"] = email_result.get("success", False)
                            response["email_message"] = email_result.get("message") or email_result.get("error")
                            response["email_recipients"] = email_result.get("recipients", [])
                        else:
                            response["email_sent"] = False
                            response["email_message"] = "No students in the list or no enrollment link available"
                    else:
                        response["email_sent"] = False
                        response["email_message"] = f"Failed to fetch student list: {list_response.status_code}"
                        
            except Exception as email_error:
                print(f"⚠️  Error sending invitations: {email_error}")
                response["email_sent"] = False
                response["email_message"] = f"Error: {str(email_error)}"
        
        return response
        
    except Exception as e:
        print(f"❌ Error creating course: {e}")
        return {"error": str(e)}

async def show_course_form(user_email=None, firebase_token=None):
    """
    Special tool that signals the UI to show the course creation form.
    Fetches available student lists for the user.
    
    Args:
        user_email: User's email (for fetching student lists)
        firebase_token: Firebase ID token (for fetching student lists)
    """
    print("📋 Displaying course creation form")
    
    student_lists = []
    
    # Fetch student lists if user is authenticated
    if user_email and firebase_token:
        try:
            TOKEN_SERVICE_URL = os.getenv("TOKEN_SERVICE_URL", "http://localhost:8001")
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{TOKEN_SERVICE_URL}/api/student-lists",
                    headers={"Authorization": f"Bearer {firebase_token}"},
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    # The endpoint returns a list directly
                    student_lists = data if isinstance(data, list) else []
                    print(f"✅ Fetched {len(student_lists)} student lists for course form")
                else:
                    print(f"⚠️  Failed to fetch student lists: {response.status_code}")
                    
        except Exception as e:
            print(f"⚠️  Error fetching student lists: {e}")
    
    return {
        "action": "show_form",
        "form_type": "course",
        "student_lists": student_lists
    }

async def create_google_doc(title, content, user_email=None, firebase_token=None):
    """
    Create a new Google Doc with the specified title and properly formatted content.
    
    This function parses the content and applies proper Google Docs formatting:
    - Document title (appears at top)
    - Headings with proper styles (HEADING_1, HEADING_2, HEADING_3)
    - Bold and italic text
    - Proper font sizes and spacing
    - Bulleted and numbered lists
    
    Content should be structured text with markers like:
    - Lines starting with "# " for Heading 1
    - Lines starting with "## " for Heading 2
    - Lines starting with "### " for Heading 3
    - Text with **bold** or *italic* markers
    - Lines starting with "- " or "* " for bullet points
    - Lines starting with "1. " for numbered lists
    
    Required permission: https://www.googleapis.com/auth/documents
    
    Args:
        title: Title of the document (appears at the very top)
        content: Text content with formatting markers
        user_email: User's email (for Firestore token retrieval)
        firebase_token: Firebase ID token (for Firestore token retrieval)
    
    Returns:
        Dictionary with document_id, title, and url
    """
    try:
        docs_service = await get_docs_service(user_email, firebase_token)
        
        # Create a new document with the title
        document = {
            'title': title
        }
        doc = docs_service.documents().create(body=document).execute()
        document_id = doc.get('documentId')
        print(f"📄 Created Google Doc: {title} (ID: {document_id})")
        
        # Format and insert content if provided
        if content:
            requests = _parse_and_format_content(content, title)
            
            if requests:
                docs_service.documents().batchUpdate(
                    documentId=document_id,
                    body={'requests': requests}
                ).execute()
                print(f"✅ Added formatted content to Google Doc: {title}")
        
        doc_url = f"https://docs.google.com/document/d/{document_id}/edit"
        
        return {
            "success": True,
            "document_id": document_id,
            "title": title,
            "url": doc_url,
            "message": f"Successfully created Google Doc: {title}"
        }
        
    except Exception as e:
        print(f"❌ Error creating Google Doc: {e}")
        return {"error": str(e)}

def _parse_and_format_content(content: str, doc_title: str) -> list:
    """
    Parse content and generate Google Docs API formatting requests.
    
    This function converts structured text into properly formatted Google Docs
    with headings, paragraphs, lists, and text styling.
    """
    requests = []
    current_index = 1
    
    # Insert document title at the top with TITLE style
    requests.append({
        'insertText': {
            'location': {'index': 1},
            'text': doc_title + '\n'
        }
    })
    
    # Apply TITLE style to the document title
    title_length = len(doc_title)
    requests.append({
        'updateParagraphStyle': {
            'range': {
                'startIndex': 1,
                'endIndex': title_length + 1
            },
            'paragraphStyle': {
                'namedStyleType': 'TITLE',
                'alignment': 'START',
                'spaceAbove': {'magnitude': 0, 'unit': 'PT'},
                'spaceBelow': {'magnitude': 12, 'unit': 'PT'}
            },
            'fields': 'namedStyleType,alignment,spaceAbove,spaceBelow'
        }
    })
    
    current_index = title_length + 2  # +1 for title, +1 for newline
    
    # Parse content line by line
    lines = content.split('\n')
    
    for line in lines:
        if not line.strip():
            # Empty line - add spacing
            requests.append({
                'insertText': {
                    'location': {'index': current_index},
                    'text': '\n'
                }
            })
            current_index += 1
            continue
        
        # Detect heading levels
        if line.startswith('# '):
            # Heading 1
            text = line[2:].strip() + '\n'
            start_index = current_index
            
            requests.append({
                'insertText': {
                    'location': {'index': current_index},
                    'text': text
                }
            })
            
            requests.append({
                'updateParagraphStyle': {
                    'range': {
                        'startIndex': start_index,
                        'endIndex': start_index + len(text)
                    },
                    'paragraphStyle': {
                        'namedStyleType': 'HEADING_1',
                        'spaceAbove': {'magnitude': 20, 'unit': 'PT'},
                        'spaceBelow': {'magnitude': 6, 'unit': 'PT'}
                    },
                    'fields': 'namedStyleType,spaceAbove,spaceBelow'
                }
            })
            
            current_index += len(text)
            
        elif line.startswith('## '):
            # Heading 2
            text = line[3:].strip() + '\n'
            start_index = current_index
            
            requests.append({
                'insertText': {
                    'location': {'index': current_index},
                    'text': text
                }
            })
            
            requests.append({
                'updateParagraphStyle': {
                    'range': {
                        'startIndex': start_index,
                        'endIndex': start_index + len(text)
                    },
                    'paragraphStyle': {
                        'namedStyleType': 'HEADING_2',
                        'spaceAbove': {'magnitude': 16, 'unit': 'PT'},
                        'spaceBelow': {'magnitude': 4, 'unit': 'PT'}
                    },
                    'fields': 'namedStyleType,spaceAbove,spaceBelow'
                }
            })
            
            current_index += len(text)
            
        elif line.startswith('### '):
            # Heading 3
            text = line[4:].strip() + '\n'
            start_index = current_index
            
            requests.append({
                'insertText': {
                    'location': {'index': current_index},
                    'text': text
                }
            })
            
            requests.append({
                'updateParagraphStyle': {
                    'range': {
                        'startIndex': start_index,
                        'endIndex': start_index + len(text)
                    },
                    'paragraphStyle': {
                        'namedStyleType': 'HEADING_3',
                        'spaceAbove': {'magnitude': 12, 'unit': 'PT'},
                        'spaceBelow': {'magnitude': 4, 'unit': 'PT'}
                    },
                    'fields': 'namedStyleType,spaceAbove,spaceBelow'
                }
            })
            
            current_index += len(text)
            
        elif line.startswith('- ') or line.startswith('* '):
            # Bullet point
            text = line[2:].strip() + '\n'
            start_index = current_index
            
            requests.append({
                'insertText': {
                    'location': {'index': current_index},
                    'text': text
                }
            })
            
            # Apply bullet list style
            requests.append({
                'createParagraphBullets': {
                    'range': {
                        'startIndex': start_index,
                        'endIndex': start_index + len(text)
                    },
                    'bulletPreset': 'BULLET_DISC_CIRCLE_SQUARE'
                }
            })
            
            current_index += len(text)
            
        elif line.strip() and line[0].isdigit() and '. ' in line[:4]:
            # Numbered list (e.g., "1. Item")
            text = line.split('. ', 1)[1].strip() + '\n'
            start_index = current_index
            
            requests.append({
                'insertText': {
                    'location': {'index': current_index},
                    'text': text
                }
            })
            
            # Apply numbered list style
            requests.append({
                'createParagraphBullets': {
                    'range': {
                        'startIndex': start_index,
                        'endIndex': start_index + len(text)
                    },
                    'bulletPreset': 'NUMBERED_DECIMAL_ALPHA_ROMAN'
                }
            })
            
            current_index += len(text)
            
        else:
            # Regular paragraph with potential bold/italic/links
            import re
            
            # Parse the line for formatting
            line_with_newline = line + '\n'
            start_index = current_index
            
            # Find all bold (**text**), italic (*text*), and links
            bold_ranges = []
            italic_ranges = []
            link_ranges = []
            
            # Process bold (**text**)
            bold_pattern = r'\*\*(.+?)\*\*'
            for match in re.finditer(bold_pattern, line):
                bold_ranges.append((match.start(), match.end(), match.group(1)))
            
            # Process italic (*text* but not **)
            italic_pattern = r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)'
            for match in re.finditer(italic_pattern, line):
                # Skip if this is part of a bold section
                is_in_bold = any(match.start() >= b[0] and match.end() <= b[1] for b in bold_ranges)
                if not is_in_bold:
                    italic_ranges.append((match.start(), match.end(), match.group(1)))
            
            # Process links (http:// or https://)
            link_pattern = r'(https?://[^\s\)]+)'
            for match in re.finditer(link_pattern, line):
                link_ranges.append((match.start(), match.end(), match.group(1)))
            
            # Remove all formatting markers to get clean text
            clean_text = line
            clean_text = re.sub(r'\*\*(.+?)\*\*', r'\1', clean_text)  # Remove **
            clean_text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'\1', clean_text)  # Remove *
            clean_text += '\n'
            
            # Insert the clean text
            requests.append({
                'insertText': {
                    'location': {'index': current_index},
                    'text': clean_text
                }
            })
            
            # Apply normal paragraph style
            requests.append({
                'updateParagraphStyle': {
                    'range': {
                        'startIndex': start_index,
                        'endIndex': start_index + len(clean_text)
                    },
                    'paragraphStyle': {
                        'namedStyleType': 'NORMAL_TEXT',
                        'spaceAbove': {'magnitude': 0, 'unit': 'PT'},
                        'spaceBelow': {'magnitude': 8, 'unit': 'PT'},
                        'lineSpacing': 115
                    },
                    'fields': 'namedStyleType,spaceAbove,spaceBelow,lineSpacing'
                }
            })
            
            # Calculate positions in clean text and apply formatting
            # We need to map original positions to clean text positions
            def get_clean_position(original_pos, original_text, clean_text_no_newline):
                """Map position in original text to position in clean text"""
                offset = 0
                for i in range(original_pos):
                    if i < len(original_text):
                        if original_text[i:i+2] == '**':
                            offset += 2
                        elif i > 0 and original_text[i-1:i+1] != '**' and original_text[i] == '*' and (i+1 >= len(original_text) or original_text[i+1] != '*'):
                            offset += 1
                return original_pos - offset
            
            # Apply bold formatting
            for orig_start, orig_end, text_content in bold_ranges:
                clean_start = start_index + get_clean_position(orig_start, line, clean_text[:-1])
                clean_end = clean_start + len(text_content)
                
                requests.append({
                    'updateTextStyle': {
                        'range': {
                            'startIndex': clean_start,
                            'endIndex': clean_end
                        },
                        'textStyle': {
                            'bold': True
                        },
                        'fields': 'bold'
                    }
                })
            
            # Apply italic formatting
            for orig_start, orig_end, text_content in italic_ranges:
                clean_start = start_index + get_clean_position(orig_start, line, clean_text[:-1])
                clean_end = clean_start + len(text_content)
                
                requests.append({
                    'updateTextStyle': {
                        'range': {
                            'startIndex': clean_start,
                            'endIndex': clean_end
                        },
                        'textStyle': {
                            'italic': True
                        },
                        'fields': 'italic'
                    }
                })
            
            # Apply link formatting (make clickable and styled)
            for orig_start, orig_end, url in link_ranges:
                clean_start = start_index + get_clean_position(orig_start, line, clean_text[:-1])
                clean_end = clean_start + len(url)
                
                # Make it a clickable link
                requests.append({
                    'updateTextStyle': {
                        'range': {
                            'startIndex': clean_start,
                            'endIndex': clean_end
                        },
                        'textStyle': {
                            'link': {
                                'url': url
                            },
                            'foregroundColor': {
                                'color': {
                                    'rgbColor': {
                                        'blue': 0.98,
                                        'green': 0.42,
                                        'red': 0.26
                                    }
                                }
                            },
                            'underline': True
                        },
                        'fields': 'link,foregroundColor,underline'
                    }
                })
            
            current_index += len(clean_text)
    
    return requests

async def create_google_sheet(title, headers=None, data=None, user_email=None, firebase_token=None):
    """
    Create a new Google Sheet with the specified title and optional data.
    
    Required permission: https://www.googleapis.com/auth/spreadsheets
    
    Args:
        title: Title of the spreadsheet
        headers: Optional list of column headers (e.g., ["Name", "Email", "Score"])
        data: Optional 2D list of data rows (e.g., [["John", "john@example.com", 95], ...])
        user_email: User's email (for Firestore token retrieval)
        firebase_token: Firebase ID token (for Firestore token retrieval)
    
    Returns:
        Dictionary with spreadsheet_id, title, and url
    """
    try:
        sheets_service = await get_sheets_service(user_email, firebase_token)
        
        # Create a new spreadsheet
        spreadsheet = {
            'properties': {
                'title': title
            }
        }
        spreadsheet_result = sheets_service.spreadsheets().create(
            body=spreadsheet,
            fields='spreadsheetId'
        ).execute()
        
        spreadsheet_id = spreadsheet_result.get('spreadsheetId')
        print(f"📊 Created Google Sheet: {title} (ID: {spreadsheet_id})")
        
        # Add data if provided
        if headers or data:
            values = []
            if headers:
                values.append(headers)
            if data:
                values.extend(data)
            
            # Log the data being added
            num_rows = len(data) if data else 0
            num_cols = len(headers) if headers else (len(data[0]) if data and len(data) > 0 else 0)
            print(f"📝 Adding {num_rows} data rows with {num_cols} columns")
            
            body = {
                'values': values
            }
            
            sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range='A1',  # Start from A1
                valueInputOption='RAW',
                body=body
            ).execute()
            print(f"✅ Added {num_rows} rows to Google Sheet: {title}")
        
        sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
        
        # Build success message with row count
        num_data_rows = len(data) if data else 0
        if num_data_rows > 0:
            message = f"Successfully created Google Sheet: {title} with {num_data_rows} rows of data"
        else:
            message = f"Successfully created Google Sheet: {title} (empty, ready for data)"
        
        return {
            "success": True,
            "spreadsheet_id": spreadsheet_id,
            "title": title,
            "url": sheet_url,
            "rows_created": num_data_rows,
            "message": message
        }
        
    except Exception as e:
        print(f"❌ Error creating Google Sheet: {e}")
        return {"error": str(e)}

async def create_google_form(title, description=None, questions=None, user_email=None, firebase_token=None):
    """
    Create a new Google Form with the specified title, description, and questions.
    
    Required permissions: 
    - https://www.googleapis.com/auth/forms.body
    - https://www.googleapis.com/auth/drive
    
    Args:
        title: Title of the form (e.g., "Customer Feedback Survey")
        description: Optional description for the form (e.g., "Please provide your feedback")
        questions: List of question dictionaries. Each question should have:
            - "question_text": The question text (required)
            - "question_type": Type of question - "TEXT", "PARAGRAPH_TEXT", "MULTIPLE_CHOICE", 
                              "CHECKBOXES", "DROPDOWN", "LINEAR_SCALE", "DATE", "TIME" (required)
            - "required": Boolean, whether the question is required (default: False)
            - "options": List of option strings (required for MULTIPLE_CHOICE, CHECKBOXES, DROPDOWN)
            - "scale_low": Integer for linear scale low value (default: 1, for LINEAR_SCALE)
            - "scale_high": Integer for linear scale high value (default: 5, for LINEAR_SCALE)
            - "scale_low_label": Optional label for low end of scale
            - "scale_high_label": Optional label for high end of scale
        user_email: User's email (for Firestore token retrieval)
        firebase_token: Firebase ID token (for Firestore token retrieval)
    
    Example questions:
        [
            {
                "question_text": "What is your name?",
                "question_type": "TEXT",
                "required": True
            },
            {
                "question_text": "How satisfied are you with our service?",
                "question_type": "MULTIPLE_CHOICE",
                "options": ["Very Satisfied", "Satisfied", "Neutral", "Dissatisfied", "Very Dissatisfied"],
                "required": True
            },
            {
                "question_text": "Rate our service from 1 to 10",
                "question_type": "LINEAR_SCALE",
                "scale_low": 1,
                "scale_high": 10,
                "scale_low_label": "Poor",
                "scale_high_label": "Excellent",
                "required": True
            },
            {
                "question_text": "Additional comments",
                "question_type": "PARAGRAPH_TEXT",
                "required": False
            }
        ]
    
    Returns:
        Dictionary with form_id, title, url, and responder_uri
    """
    try:
        forms_service = await get_forms_service(user_email, firebase_token)
        
        # Create the form with basic info
        form_body = {
            "info": {
                "title": title,
            }
        }
        
        if description:
            form_body["info"]["documentTitle"] = title
            
        # Create the form
        form = forms_service.forms().create(body=form_body).execute()
        form_id = form.get("formId")
        form_url = form.get("responderUri")
        
        print(f"📋 Created Google Form: {title} (ID: {form_id})")
        
        # Add description and questions if provided
        if description or (questions and len(questions) > 0):
            requests = []
            
            # Add description as first item if provided
            if description:
                requests.append({
                    "createItem": {
                        "item": {
                            "title": description,
                            "description": "",
                            "textItem": {}
                        },
                        "location": {"index": 0}
                    }
                })
            
            # Add questions
            if questions:
                for idx, q in enumerate(questions):
                    question_text = q.get("question_text", "")
                    question_type = q.get("question_type", "TEXT").upper()
                    required = q.get("required", False)
                    
                    # Build the question item
                    item = {
                        "title": question_text,
                        "questionItem": {
                            "question": {
                                "required": required
                            }
                        }
                    }
                    
                    # Add question-type-specific configuration
                    if question_type == "TEXT":
                        item["questionItem"]["question"]["textQuestion"] = {}
                    
                    elif question_type == "PARAGRAPH_TEXT":
                        item["questionItem"]["question"]["textQuestion"] = {
                            "paragraph": True
                        }
                    
                    elif question_type in ["MULTIPLE_CHOICE", "CHECKBOXES", "DROPDOWN"]:
                        options = q.get("options", [])
                        if not options:
                            print(f"⚠️ Warning: {question_type} question requires options, skipping question: {question_text}")
                            continue
                        
                        # Map user-friendly names to Google Forms API values
                        api_type_map = {
                            "MULTIPLE_CHOICE": "RADIO",      # Single selection
                            "CHECKBOXES": "CHECKBOX",         # Multiple selections
                            "DROPDOWN": "DROP_DOWN"           # Dropdown list
                        }
                        
                        choice_question = {
                            "type": api_type_map[question_type],
                            "options": [{"value": opt} for opt in options]
                        }
                        
                        item["questionItem"]["question"]["choiceQuestion"] = choice_question
                    
                    elif question_type == "LINEAR_SCALE":
                        scale_low = q.get("scale_low", 1)
                        scale_high = q.get("scale_high", 5)
                        scale_low_label = q.get("scale_low_label", "")
                        scale_high_label = q.get("scale_high_label", "")
                        
                        item["questionItem"]["question"]["scaleQuestion"] = {
                            "low": scale_low,
                            "high": scale_high,
                            "lowLabel": scale_low_label,
                            "highLabel": scale_high_label
                        }
                    
                    elif question_type == "DATE":
                        item["questionItem"]["question"]["dateQuestion"] = {}
                    
                    elif question_type == "TIME":
                        item["questionItem"]["question"]["timeQuestion"] = {}
                    
                    else:
                        print(f"⚠️ Warning: Unknown question type '{question_type}', defaulting to TEXT")
                        item["questionItem"]["question"]["textQuestion"] = {}
                    
                    # Calculate the position (after description if it exists)
                    position = (idx + 1) if description else idx
                    
                    requests.append({
                        "createItem": {
                            "item": item,
                            "location": {"index": position}
                        }
                    })
                
                # Execute batch update to add all questions
                if requests:
                    update_body = {"requests": requests}
                    forms_service.forms().batchUpdate(
                        formId=form_id,
                        body=update_body
                    ).execute()
                    
                    num_questions = len([r for r in requests if "questionItem" in r.get("createItem", {}).get("item", {})])
                    print(f"✅ Added {num_questions} questions to form: {title}")
        
        edit_url = f"https://docs.google.com/forms/d/{form_id}/edit"
        
        # Build success message with properly formatted links
        num_questions = len(questions) if questions else 0
        
        message = f"""✅ Successfully created Google Form: **{title}**

📊 **Form Details:**
- Questions added: {num_questions}
- Form ID: `{form_id}`

🔗 **Links:**
- **Edit Form (Teacher):** {edit_url}
- **View/Share Form (Students):** {form_url}

You can now edit the form or share the view link with students!"""
        
        return {
            "success": True,
            "form_id": form_id,
            "title": title,
            "url": form_url,  # Public responder URL
            "edit_url": edit_url,  # Edit URL for form creator
            "questions_added": num_questions,
            "message": message
        }
        
    except Exception as e:
        print(f"❌ Error creating Google Form: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

# --- Map function names to callables ---
TOOL_FUNCTIONS = {
    "list_courses": list_courses,
    "get_course": get_course,
    "show_coursework_form": show_coursework_form,
    "list_coursework": list_coursework,
    "get_coursework": get_coursework,
    "show_announcements_form": show_announcements_form,
    "list_announcements": list_announcements,
    "list_submissions": list_submissions,
    "create_coursework": create_coursework,
    "show_assignment_form": show_assignment_form,
    "create_course": create_course,
    "show_course_form": show_course_form,
    "create_google_doc": create_google_doc,
    "create_google_sheet": create_google_sheet,
    "create_google_form": create_google_form,
}

# --- Gemini Tool Definition ---
CLASSROOM_TOOLS_DEF = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="list_courses",
            description="List all Google Classroom courses. Can filter by state (ACTIVE, ARCHIVED, etc), teacher, or student.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "course_states": types.Schema(type="ARRAY", items=types.Schema(type="STRING"), description="Filter by course states"),
                    "teacher_id": types.Schema(type="STRING", description="Filter by teacher ID"),
                    "student_id": types.Schema(type="STRING", description="Filter by student ID"),
                }
            )
        ),
        types.FunctionDeclaration(
            name="get_course",
            description="Get detailed information about a specific course.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "course_id": types.Schema(type="STRING", description="The ID of the course"),
                },
                required=["course_id"]
            )
        ),
        types.FunctionDeclaration(
            name="show_coursework_form",
            description="Show a form to select which course's assignments/coursework to view. This tool fetches all available courses and displays them in a dropdown. Use this when user wants to view or list coursework/assignments.",
            parameters=types.Schema(
                type="OBJECT",
                properties={},
                required=[]
            )
        ),
        types.FunctionDeclaration(
            name="list_coursework",
            description="List assignments and coursework for a specific course. This is called internally after user selects a course from the form. Do not call this directly - use show_coursework_form instead.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "course_id": types.Schema(type="STRING", description="The ID of the course"),
                    "course_work_states": types.Schema(type="ARRAY", items=types.Schema(type="STRING"), description="Filter by state (PUBLISHED, DRAFT)"),
                },
                required=["course_id"]
            )
        ),
        types.FunctionDeclaration(
            name="get_coursework",
            description="Get details of a specific assignment.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "course_id": types.Schema(type="STRING", description="The ID of the course"),
                    "course_work_id": types.Schema(type="STRING", description="The ID of the coursework"),
                },
                required=["course_id", "course_work_id"]
            )
        ),
         types.FunctionDeclaration(
            name="show_announcements_form",
            description="Show a form to select which course's announcements to view. This tool fetches all available courses and displays them in a dropdown. Use this when user wants to view or list announcements.",
            parameters=types.Schema(
                type="OBJECT",
                properties={},
                required=[]
            )
        ),
        types.FunctionDeclaration(
            name="list_announcements",
            description="List announcements for a specific course. This is called internally after user selects a course from the form. Do not call this directly - use show_announcements_form instead.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "course_id": types.Schema(type="STRING", description="The ID of the course"),
                    "announcement_states": types.Schema(type="ARRAY", items=types.Schema(type="STRING")),
                },
                required=["course_id"]
            )
        ),
        types.FunctionDeclaration(
            name="list_submissions",
            description="List student submissions for an assignment.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "course_id": types.Schema(type="STRING", description="The ID of the course"),
                    "course_work_id": types.Schema(type="STRING", description="The ID of the coursework"),
                    "user_id": types.Schema(type="STRING", description="Filter by student ID"),
                },
                required=["course_id", "course_work_id"]
            )
        ),
        types.FunctionDeclaration(
            name="show_assignment_form",
            description="Show the assignment creation form to the user. This tool automatically fetches all available courses and displays them in a dropdown for the user to select from. Call this tool directly when user wants to create an assignment.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "course_id": types.Schema(type="STRING", description="Optional course ID to pre-select in dropdown if user mentioned a specific course."),
                },
                required=[]
            )
        ),
        types.FunctionDeclaration(
            name="create_coursework",
            description="Create a new assignment with all details provided, including optional file attachments. If the user message contains 'File IDs:', extract the comma-separated Drive file IDs and pass as file_ids parameter. Use this ONLY when you have all the assignment details from the form submission, NOT for initial user requests.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "course_id": types.Schema(type="STRING", description="The ID of the course"),
                    "title": types.Schema(type="STRING", description="Title of the assignment"),
                    "description": types.Schema(type="STRING", description="Description"),
                    "due_date": types.Schema(type="STRING", description="YYYY-MM-DD"),
                    "due_time": types.Schema(type="STRING", description="HH:MM"),
                    "max_points": types.Schema(type="NUMBER", description="Max points"),
                    "work_type": types.Schema(type="STRING", description="ASSIGNMENT, SHORT_ANSWER_QUESTION, etc"),
                    "file_ids": types.Schema(type="STRING", description="Optional comma-separated Google Drive file IDs to attach as materials. Extract from 'File IDs:' in the user message."),
                },
                required=["course_id", "title"]
            )
        ),
        types.FunctionDeclaration(
            name="show_course_form",
            description="Show the course creation form to the user. Use this when the user wants to create a new course or class. This will display an interactive form for them to fill in the course details.",
            parameters=types.Schema(
                type="OBJECT",
                properties={},
                required=[]
            )
        ),
        types.FunctionDeclaration(
            name="create_course",
            description="Create a new course in Google Classroom and optionally send invitation emails to students. Use this ONLY when you have all the course details from the form submission, NOT for initial user requests. If a student_list_id is provided, the system will automatically send invitation emails with the course join link to all students in that list.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "name": types.Schema(type="STRING", description="Course name (required)"),
                    "section": types.Schema(type="STRING", description="Section of the course (e.g., 'Period 2', 'Section A')"),
                    "description_heading": types.Schema(type="STRING", description="Short description heading"),
                    "description": types.Schema(type="STRING", description="Full course description"),
                    "room": types.Schema(type="STRING", description="Room location"),
                    "owner_id": types.Schema(type="STRING", description="Teacher ID (defaults to 'me')"),
                    "student_list_id": types.Schema(type="STRING", description="Optional: ID of the student list to send course invitations to. If provided, all students in the list will receive an email with the course join link."),
                },
                required=["name"]
            )
        ),
        types.FunctionDeclaration(
            name="create_google_doc",
            description="Create a new Google Document with properly formatted title and content. Use this when the user asks you to create a document, write a report, draft text, etc. YOU must generate well-structured content with proper formatting markers. The content will be rendered with Google Docs native formatting (NOT markdown). Use these formatting markers: '# ' for Heading 1, '## ' for Heading 2, '### ' for Heading 3, '**text**' for bold, '*text*' for italic, '- ' for bullet points, '1. ' for numbered lists. Example structure: '# Introduction\\n\\nMachine learning is...\\n\\n## Key Concepts\\n\\n- Supervised learning\\n- Unsupervised learning\\n\\n## Applications\\n\\n1. Image recognition\\n2. Natural language processing'",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "title": types.Schema(type="STRING", description="Title of the document (e.g., 'Introduction to Machine Learning'). This will appear at the top in TITLE style."),
                    "content": types.Schema(type="STRING", description="Full text content with formatting markers. Structure it with: '# ' for main headings, '## ' for subheadings, '### ' for sub-subheadings, '**bold**' for emphasis, '*italic*' for subtle emphasis, '- ' for bullet lists, '1. ' for numbered lists. Use proper paragraph breaks (\\n\\n) between sections. Generate comprehensive, well-organized content based on the user's request."),
                },
                required=["title", "content"]
            )
        ),
        types.FunctionDeclaration(
            name="create_google_sheet",
            description="Create a new Google Spreadsheet with optional headers and data. Use this when the user asks to create a spreadsheet, table, dataset, etc. YOU should generate the structure and data based on the user's request. IMPORTANT: If the user specifies a number of rows (e.g., '10 rows', '20 entries', '50 students'), you MUST generate EXACTLY that many data rows. For example, if user asks 'create a spreadsheet with 20 rows for tracking expenses', generate 20 rows of sample data. If user asks 'create a spreadsheet to track student grades', determine appropriate headers (Name, Assignment 1, Assignment 2, Final Score) and provide reasonable sample data.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "title": types.Schema(type="STRING", description="Title of the spreadsheet (e.g., 'Student Grades Tracker')"),
                    "headers": types.Schema(
                        type="ARRAY", 
                        items=types.Schema(type="STRING"),
                        description="Optional: Array of column headers (e.g., ['Name', 'Email', 'Score']). Generate appropriate headers based on the user's request."
                    ),
                    "data": types.Schema(
                        type="ARRAY",
                        items=types.Schema(
                            type="ARRAY",
                            items=types.Schema(type="STRING")
                        ),
                        description="Optional: 2D array of data rows. Each row is an array matching the headers. Example: [['John Doe', 'john@example.com', '95'], ['Jane Smith', 'jane@example.com', '87']]. CRITICAL: If user specifies a row count (e.g., '10 rows', '25 entries'), you MUST generate EXACTLY that number of rows. If user says 'create 50 rows', generate 50 rows of realistic sample data. If no count specified, provide 5-10 sample rows or leave empty for user to fill."
                    ),
                },
                required=["title"]
            )
        ),
        types.FunctionDeclaration(
            name="create_google_form",
            description="Create a new Google Form with questions. Use this when the user asks to create a form, survey, questionnaire, quiz, or feedback form. YOU should generate appropriate questions based on the user's request. If user specifies questions directly, use them. If user asks for a form for a specific purpose (e.g., 'customer feedback form', 'event registration', 'quiz on Python'), YOU determine appropriate questions. Support multiple question types: TEXT (short answer), PARAGRAPH_TEXT (long answer), MULTIPLE_CHOICE, CHECKBOXES, DROPDOWN, LINEAR_SCALE (rating), DATE, TIME. IMPORTANT: Always generate at least 3-5 relevant questions unless user specifies otherwise. Example: User says 'create a customer satisfaction survey' -> Generate questions like 'What is your name?', 'How satisfied are you with our product?' (MULTIPLE_CHOICE with options), 'Rate our service 1-10' (LINEAR_SCALE), 'Additional comments' (PARAGRAPH_TEXT).",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "title": types.Schema(type="STRING", description="Title of the form (e.g., 'Customer Satisfaction Survey', 'Event Registration Form')"),
                    "description": types.Schema(type="STRING", description="Optional: Brief description or instructions for the form (e.g., 'Please take a moment to share your feedback')"),
                    "questions": types.Schema(
                        type="ARRAY",
                        items=types.Schema(
                            type="OBJECT",
                            properties={
                                "question_text": types.Schema(type="STRING", description="The question text (e.g., 'What is your email address?')"),
                                "question_type": types.Schema(
                                    type="STRING", 
                                    description="Type of question: TEXT (short answer), PARAGRAPH_TEXT (long answer), MULTIPLE_CHOICE, CHECKBOXES, DROPDOWN, LINEAR_SCALE (1-5 or 1-10 rating), DATE, TIME. Choose the most appropriate type for each question."
                                ),
                                "required": types.Schema(type="BOOLEAN", description="Whether this question is required (true/false). Important questions should be required."),
                                "options": types.Schema(
                                    type="ARRAY",
                                    items=types.Schema(type="STRING"),
                                    description="List of options (REQUIRED for MULTIPLE_CHOICE, CHECKBOXES, DROPDOWN). Example: ['Very Satisfied', 'Satisfied', 'Neutral', 'Dissatisfied', 'Very Dissatisfied']"
                                ),
                                "scale_low": types.Schema(type="INTEGER", description="For LINEAR_SCALE: lowest value (default: 1)"),
                                "scale_high": types.Schema(type="INTEGER", description="For LINEAR_SCALE: highest value (default: 5, can be 10 for broader scales)"),
                                "scale_low_label": types.Schema(type="STRING", description="For LINEAR_SCALE: optional label for low end (e.g., 'Poor', 'Strongly Disagree')"),
                                "scale_high_label": types.Schema(type="STRING", description="For LINEAR_SCALE: optional label for high end (e.g., 'Excellent', 'Strongly Agree')"),
                            },
                            required=["question_text", "question_type"]
                        ),
                        description="Array of question objects. YOU MUST generate appropriate questions based on the user's request. If user says 'create a feedback form', generate relevant feedback questions. If user provides questions directly (e.g., 'ask their name, email, and satisfaction'), convert them to proper question objects. CRITICAL: Generate at least 3-5 questions for a meaningful form unless user specifies a different number."
                    ),
                },
                required=["title", "questions"]
            )
        ),
    ]
)


"""
Google Classroom API Tools with Dual Authentication Support

This module provides async functions for interacting with the Google Classroom API.
It supports two authentication methods:

1. **Firestore Token Storage (Recommended)**:
   - Pass `user_email` and `firebase_token` to any tool function
   - Tokens are securely retrieved from Firestore via the token service
   - Each user has their own OAuth tokens
   - Supports multi-user applications

2. **Legacy tokens.json File**:
   - Falls back to local tokens.json if Firestore credentials not provided
   - Useful for development and testing
   - Single-user authentication

Configuration:
- Set TOKEN_SERVICE_URL environment variable (default: http://localhost:8001)
- Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables
- For Firestore: User must authorize via OAuth and store tokens
- For legacy: Place tokens.json and credentials.json in CLASSROOM_DATA_DIR
"""

import os
import json
import logging
import httpx
from typing import Optional
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.genai import types

# Paths - Use environment variables or default to current directory
BASE_DIR = os.getenv("CLASSROOM_DATA_DIR", os.path.dirname(__file__))
TOKENS_PATH = os.path.join(BASE_DIR, "tokens.json")
CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials.json")

# Token service configuration
TOKEN_SERVICE_URL = os.getenv("TOKEN_SERVICE_URL", "http://localhost:8001")

async def get_tokens_from_firestore(user_email: str, firebase_id_token: str) -> dict:
    """
    Retrieve user's OAuth tokens from Firestore via token service.
    
    Args:
        user_email: User's email address
        firebase_id_token: Firebase ID token for authentication
    
    Returns:
        Dictionary with access_token, refresh_token, and optional fields
    
    Raises:
        Exception: If token retrieval fails
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{TOKEN_SERVICE_URL}/api/tokens/retrieve",
                params={"email": user_email},
                headers={"Authorization": f"Bearer {firebase_id_token}"},
                timeout=10.0
            )
            
            if response.status_code == 200:
                data = response.json()
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
        
        except httpx.TimeoutException:
            raise Exception("Token service timeout. Please try again.")
        except httpx.ConnectError:
            raise Exception(f"Cannot connect to token service at {TOKEN_SERVICE_URL}")
        except Exception as e:
            if "No Google Classroom tokens found" in str(e) or "Authentication failed" in str(e):
                raise
            print(f"❌ Error retrieving tokens from Firestore: {e}")
            raise Exception(f"Failed to retrieve tokens: {str(e)}")

async def get_classroom_service(user_email: Optional[str] = None, firebase_id_token: Optional[str] = None):
    """
    Authenticate and return the Google Classroom service.
    
    Args:
        user_email: User's email (for Firestore token retrieval)
        firebase_id_token: Firebase ID token (for Firestore token retrieval)
    
    Returns:
        Google Classroom service object
    
    Note:
        If user_email and firebase_id_token are provided, retrieves tokens from Firestore.
        Otherwise, falls back to legacy tokens.json file.
    """
    tokens = None
    
    # Try to get tokens from Firestore if user credentials provided
    if user_email and firebase_id_token:
        try:
            tokens = await get_tokens_from_firestore(user_email, firebase_id_token)
            print(f"📚 Using Firestore tokens for {user_email}")
        except Exception as e:
            print(f"⚠️  Failed to get Firestore tokens: {e}")
            print(f"   Falling back to tokens.json if available")
            tokens = None
    
    # Fall back to tokens.json if Firestore tokens not available
    if tokens is None:
        if not os.path.exists(TOKENS_PATH):
            raise FileNotFoundError(
                        f"No authentication available. Either:\n"
                        f"1. Provide user_email and firebase_id_token to use Firestore tokens, or\n"
                        f"2. Place tokens.json at {TOKENS_PATH}"
            )

        with open(TOKENS_PATH, "r") as f:
            tokens = json.load(f)
        print(f"📚 Using legacy tokens.json")

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
        except Exception as e:
            logging.error(f"Failed to refresh token: {e}")
            raise Exception("Failed to refresh access token. Please re-authorize Google Classroom.")

    return build("classroom", "v1", credentials=creds)

async def get_docs_service(user_email: Optional[str] = None, firebase_id_token: Optional[str] = None):
    """
    Authenticate and return the Google Docs service.
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
                        web_or_installed = creds_data.get("web") or creds_data.get("installed")
                        if web_or_installed:
                            client_id = web_or_installed.get("client_id")
                            client_secret = web_or_installed.get("client_secret")
            
            creds = Credentials(
                token=tokens.get("access_token"),
                refresh_token=tokens.get("refresh_token"),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_id,
                client_secret=client_secret,
                scopes=tokens.get("scope", "").split(" ") if isinstance(tokens.get("scope"), str) else []
            )
            print(f"📄 Using Firestore tokens for Google Docs for {user_email}")
        except Exception as e:
            logging.error(f"Failed to retrieve Firestore tokens for {user_email}: {e}")
            creds = _load_local_creds_for_docs()
    else:
        creds = _load_local_creds_for_docs()
    
    if not creds:
        raise ValueError("No valid credentials found for Google Docs service.")
    
    # Refresh if expired
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as e:
            logging.error(f"Failed to refresh token: {e}")
            raise
    
    return build("docs", "v1", credentials=creds)

async def get_sheets_service(user_email: Optional[str] = None, firebase_id_token: Optional[str] = None):
    """
    Authenticate and return the Google Sheets service.
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
                        web_or_installed = creds_data.get("web") or creds_data.get("installed")
                        if web_or_installed:
                            client_id = web_or_installed.get("client_id")
                            client_secret = web_or_installed.get("client_secret")
            
            creds = Credentials(
                token=tokens.get("access_token"),
                refresh_token=tokens.get("refresh_token"),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_id,
                client_secret=client_secret,
                scopes=tokens.get("scope", "").split(" ") if isinstance(tokens.get("scope"), str) else []
            )
            print(f"📊 Using Firestore tokens for Google Sheets for {user_email}")
        except Exception as e:
            logging.error(f"Failed to retrieve Firestore tokens for {user_email}: {e}")
            creds = _load_local_creds_for_sheets()
    else:
        creds = _load_local_creds_for_sheets()
    
    if not creds:
        raise ValueError("No valid credentials found for Google Sheets service.")
    
    # Refresh if expired
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
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
    Uses the same authentication flow as Classroom.
    
    Required permission: https://www.googleapis.com/auth/forms.body
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
                        web_or_installed = creds_data.get("web") or creds_data.get("installed")
                        if web_or_installed:
                            client_id = web_or_installed.get("client_id")
                            client_secret = web_or_installed.get("client_secret")
            
            creds = Credentials(
                token=tokens.get("access_token"),
                refresh_token=tokens.get("refresh_token"),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_id,
                client_secret=client_secret,
                scopes=tokens.get("scope", "").split(" ") if isinstance(tokens.get("scope"), str) else []
            )
            print(f"📋 Using Firestore tokens for Google Forms for {user_email}")
        except Exception as e:
            logging.error(f"Failed to retrieve Firestore tokens for {user_email}: {e}")
            creds = _load_local_creds_for_forms()
    else:
        creds = _load_local_creds_for_forms()
    
    if not creds:
        raise ValueError("No valid credentials found for Google Forms service.")
    
    # Refresh if expired
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as e:
            logging.error(f"Failed to refresh token: {e}")
            raise
    
    return build("forms", "v1", credentials=creds)

def _load_local_creds_for_forms():
    """Helper to load credentials from local tokens.json for Forms"""
    # Same as docs/sheets
    return _load_local_creds_for_docs()

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

async def list_students(course_id, user_email=None, firebase_token=None):
    try:
        service = await get_classroom_service(user_email, firebase_token)
        results = service.courses().students().list(courseId=course_id).execute()
        return {"students": results.get("students", [])}
    except Exception as e:
        print(f"❌ Error in list_students: {e}")
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

async def create_coursework(course_id, title, description=None, due_date=None, due_time=None, max_points=None, work_type="ASSIGNMENT", user_email=None, firebase_token=None):
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

        result = service.courses().courseWork().create(courseId=course_id, body=body).execute()
        return {"coursework": result}
    except Exception as e:
        print(f"❌ Error in create_coursework: {e}")
        return {"error": str(e)}

async def show_assignment_form(courses_data=None, course_id=None, user_email=None, firebase_token=None):
    """
    Special tool that signals the UI to show the assignment creation form.
    This is not a real API call - it's a UI control tool.
    
    IMPORTANT: You must call list_courses() FIRST to get the courses data,
    then pass that data to this function.
    
    Args:
        courses_data: The courses array from list_courses() response
        course_id: Optional course ID to pre-select
        user_email: User's email (not used, but accepted for consistency)
        firebase_token: Firebase ID token (not used, but accepted for consistency)
    """
    # Handle case where courses_data might be None or not provided
    if courses_data is None:
        print("⚠️  WARNING: show_assignment_form called without courses_data!")
        courses_data = []
    
    # Handle if the entire result object was passed instead of just the courses array
    if isinstance(courses_data, dict) and "courses" in courses_data:
        courses_data = courses_data["courses"]
    
    print(f"📋 Displaying assignment form with {len(courses_data)} courses in dropdown")
    if len(courses_data) > 0:
        print(f"  ✅ First course: {courses_data[0].get('name', 'Unknown')}")
    
    return {
        "action": "show_form",
        "form_type": "assignment",
        "course_id": course_id or "",
        "courses": courses_data
    }

async def create_course(name, section=None, description_heading=None, description=None, room=None, owner_id="me", user_email=None, firebase_token=None):
    """
    Create a new course in Google Classroom.
    
    Required permission: https://www.googleapis.com/auth/classroom.courses
    
    Args:
        name: Course name (required)
        section: Section of the course (e.g., "Period 2", "Section A")
        description_heading: Short description heading
        description: Full course description
        room: Room location
        owner_id: Teacher ID (defaults to "me" for authenticated user)
        user_email: User's email (for Firestore token retrieval)
        firebase_token: Firebase ID token (for Firestore token retrieval)
    """
    try:
        service = await get_classroom_service(user_email, firebase_token)
        body = {
            "name": name,
            "ownerId": owner_id,
            "courseState": "PROVISIONED"  # Can be ACTIVE, ARCHIVED, PROVISIONED, or DECLINED
        }
        
        if section: body["section"] = section
        if description_heading: body["descriptionHeading"] = description_heading
        if description: body["description"] = description
        if room: body["room"] = room
        
        result = service.courses().create(body=body).execute()
        print(f"✅ Course created: {result.get('name')} (ID: {result.get('id')})")
        return {"course": result}
    except Exception as e:
        print(f"❌ Error creating course: {e}")
        return {"error": str(e)}

async def show_course_form(user_email=None, firebase_token=None):
    """
    Special tool that signals the UI to show the course creation form.
    This is not a real API call - it's a UI control tool.
    
    Args:
        user_email: User's email (not used, but accepted for consistency)
        firebase_token: Firebase ID token (not used, but accepted for consistency)
    """
    print("📋 Displaying course creation form")
    
    return {
        "action": "show_form",
        "form_type": "course"
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
        
        # Build success message
        num_questions = len(questions) if questions else 0
        if num_questions > 0:
            message = f"Successfully created Google Form: {title} with {num_questions} questions"
        else:
            message = f"Successfully created Google Form: {title} (empty, ready for questions)"
        
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
    "list_coursework": list_coursework,
    "get_coursework": get_coursework,
    "list_announcements": list_announcements,
    "list_students": list_students,
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
            name="list_coursework",
            description="List assignments and coursework for a course.",
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
            name="list_announcements",
            description="List announcements for a course.",
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
            name="list_students",
            description="List students in a course.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "course_id": types.Schema(type="STRING", description="The ID of the course"),
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
            description="Show the assignment creation form to the user with a dropdown of courses. REQUIRED WORKFLOW: 1) First call list_courses() to get courses. 2) Take the 'courses' array from the list_courses response. 3) Pass that entire courses array as courses_data parameter to this tool. Example: If list_courses returns {'courses': [...]}, pass courses_data=[...] to this tool.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "courses_data": types.Schema(
                        type="ARRAY",
                        items=types.Schema(type="OBJECT"),
                        description="REQUIRED: The courses array from list_courses() response. This is the 'courses' field from the list_courses result, NOT the entire result object."
                    ),
                    "course_id": types.Schema(type="STRING", description="Optional course ID to pre-select in dropdown if user mentioned a specific course."),
                },
                required=["courses_data"]
            )
        ),
        types.FunctionDeclaration(
            name="create_coursework",
            description="Create a new assignment with all details provided. Use this ONLY when you have all the assignment details from the form submission, NOT for initial user requests.",
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
            description="Create a new course in Google Classroom. Use this ONLY when you have all the course details from the form submission, NOT for initial user requests.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "name": types.Schema(type="STRING", description="Course name (required)"),
                    "section": types.Schema(type="STRING", description="Section of the course (e.g., 'Period 2', 'Section A')"),
                    "description_heading": types.Schema(type="STRING", description="Short description heading"),
                    "description": types.Schema(type="STRING", description="Full course description"),
                    "room": types.Schema(type="STRING", description="Room location"),
                    "owner_id": types.Schema(type="STRING", description="Teacher ID (defaults to 'me')"),
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


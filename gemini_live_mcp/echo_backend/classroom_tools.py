import os
import json
import logging
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.genai import types

# Paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../classroom_mcp-main"))
TOKENS_PATH = os.path.join(BASE_DIR, "tokens.json")
CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials.json")

def get_classroom_service():
    """Authenticate and return the Google Classroom service."""
    if not os.path.exists(TOKENS_PATH):
        raise FileNotFoundError(f"tokens.json not found at {TOKENS_PATH}")

    with open(TOKENS_PATH, "r") as f:
        tokens = json.load(f)

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

    creds = Credentials(
        token=tokens.get("access_token"),
        refresh_token=tokens.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=tokens.get("scope", "").split(" ")
    )

    # Refresh if expired
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as e:
            logging.error(f"Failed to refresh token: {e}")

    return build("classroom", "v1", credentials=creds)

# --- Tool Helper Functions ---

async def list_courses(course_states=None, teacher_id=None, student_id=None):
    try:
        service = get_classroom_service()
        kwargs = {}
        if course_states: kwargs['courseStates'] = course_states
        if teacher_id: kwargs['teacherId'] = teacher_id
        if student_id: kwargs['studentId'] = student_id
        
        results = service.courses().list(**kwargs).execute()
        return {"courses": results.get("courses", [])}
    except Exception as e:
        return {"error": str(e)}

async def get_course(course_id):
    try:
        service = get_classroom_service()
        result = service.courses().get(id=course_id).execute()
        return result
    except Exception as e:
        return {"error": str(e)}

async def list_coursework(course_id, course_work_states=None):
    try:
        service = get_classroom_service()
        kwargs = {'courseId': course_id}
        if course_work_states: kwargs['courseWorkStates'] = course_work_states
        
        results = service.courses().courseWork().list(**kwargs).execute()
        return {"courseWork": results.get("courseWork", [])}
    except Exception as e:
        return {"error": str(e)}

async def get_coursework(course_id, course_work_id):
    try:
        service = get_classroom_service()
        result = service.courses().courseWork().get(courseId=course_id, id=course_work_id).execute()
        return result
    except Exception as e:
        return {"error": str(e)}

async def list_announcements(course_id, announcement_states=None):
    try:
        service = get_classroom_service()
        kwargs = {'courseId': course_id}
        if announcement_states: kwargs['announcementStates'] = announcement_states
        
        results = service.courses().announcements().list(**kwargs).execute()
        return {"announcements": results.get("announcements", [])}
    except Exception as e:
        return {"error": str(e)}

async def list_students(course_id):
    try:
        service = get_classroom_service()
        results = service.courses().students().list(courseId=course_id).execute()
        return {"students": results.get("students", [])}
    except Exception as e:
        return {"error": str(e)}

async def list_submissions(course_id, course_work_id, user_id=None):
    try:
        service = get_classroom_service()
        kwargs = {'courseId': course_id, 'courseWorkId': course_work_id}
        if user_id: kwargs['userId'] = user_id
        
        results = service.courses().courseWork().studentSubmissions().list(**kwargs).execute()
        return {"studentSubmissions": results.get("studentSubmissions", [])}
    except Exception as e:
        return {"error": str(e)}

async def create_coursework(course_id, title, description=None, due_date=None, due_time=None, max_points=None, work_type="ASSIGNMENT"):
    try:
        service = get_classroom_service()
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
        return result
    except Exception as e:
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
            name="create_coursework",
            description="Create a new assignment.",
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
    ]
)


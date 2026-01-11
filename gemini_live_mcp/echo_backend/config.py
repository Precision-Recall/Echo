"""
Configuration module for API key management
Supports both free API key and paid Vertex AI credentials
"""

import os
import json
from typing import Optional, Literal
from dotenv import load_dotenv

load_dotenv()

# API Type Configuration
API_KEY_TYPE = os.getenv("API_KEY_TYPE", "free").lower()  # "free" or "paid"

# Free API Key (Google AI Studio)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Vertex AI Configuration (Paid)
GOOGLE_APPLICATION_CREDENTIALS_JSON = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
GEMINI_LOCATION = os.getenv("GEMINI_LOCATION", "us-central1")
VERTEX_PROJECT_ID = None

def get_api_type() -> Literal["free", "paid"]:
    """Get the configured API type"""
    return "paid" if API_KEY_TYPE == "paid" else "free"

def get_vertex_credentials() -> Optional[dict]:
    """
    Parse and return Vertex AI credentials from environment variable
    Returns None if not configured
    """
    if not GOOGLE_APPLICATION_CREDENTIALS_JSON:
        return None
    
    try:
        credentials = json.loads(GOOGLE_APPLICATION_CREDENTIALS_JSON)
        global VERTEX_PROJECT_ID
        VERTEX_PROJECT_ID = credentials.get("project_id")
        return credentials
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing GOOGLE_APPLICATION_CREDENTIALS_JSON: {e}")
        return None

def get_project_id() -> Optional[str]:
    """Get the Vertex AI project ID"""
    if VERTEX_PROJECT_ID:
        return VERTEX_PROJECT_ID
    
    # Try to extract from credentials
    creds = get_vertex_credentials()
    if creds:
        return creds.get("project_id")
    
    return None

def validate_configuration() -> tuple[bool, str]:
    """
    Validate that the required configuration is present
    Returns (is_valid, error_message)
    """
    api_type = get_api_type()
    
    if api_type == "free":
        if not GEMINI_API_KEY:
            return False, "API_KEY_TYPE is 'free' but GEMINI_API_KEY is not set"
        return True, f"Using free API key (Google AI Studio)"
    
    elif api_type == "paid":
        if not GOOGLE_APPLICATION_CREDENTIALS_JSON:
            return False, "API_KEY_TYPE is 'paid' but GOOGLE_APPLICATION_CREDENTIALS_JSON is not set"
        
        creds = get_vertex_credentials()
        if not creds:
            return False, "Failed to parse GOOGLE_APPLICATION_CREDENTIALS_JSON"
        
        project_id = get_project_id()
        if not project_id:
            return False, "Could not extract project_id from Vertex AI credentials"
        
        return True, f"Using paid Vertex AI (Project: {project_id}, Location: {GEMINI_LOCATION})"
    
    else:
        return False, f"Invalid API_KEY_TYPE: {API_KEY_TYPE}. Must be 'free' or 'paid'"

def get_client_config() -> dict:
    """
    Get the configuration dictionary for initializing Gemini clients
    """
    api_type = get_api_type()
    
    if api_type == "free":
        return {
            "api_type": "free",
            "api_key": GEMINI_API_KEY,
            "http_options": {'api_version': 'v1beta'}
        }
    else:  # paid
        return {
            "api_type": "paid",
            "project_id": get_project_id(),
            "location": GEMINI_LOCATION,
            "credentials_json": GOOGLE_APPLICATION_CREDENTIALS_JSON
        }

# Validate on import
is_valid, message = validate_configuration()
if is_valid:
    print(f"✅ API Configuration: {message}")
else:
    print(f"⚠️  API Configuration Warning: {message}")


"""
Backend endpoints for Google Forms creation and AI-powered editing
"""
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from classroom_tools import create_google_form, get_forms_service
import json
import os
import config
from google.oauth2 import service_account
from vertexai.generative_models import GenerativeModel
import vertexai

router = APIRouter()

# Initialize Vertex AI
client_config = config.get_client_config()
if client_config["api_type"] == "paid":
    credentials_dict = json.loads(client_config["credentials_json"])
    credentials = service_account.Credentials.from_service_account_info(
        credentials_dict,
        scopes=[
            "https://www.googleapis.com/auth/generative-language",
            "https://www.googleapis.com/auth/cloud-platform"
        ]
    )
    vertexai.init(
        project=client_config["project_id"],
        location=client_config["location"],
        credentials=credentials
    )
    print(f"✅ Forms endpoints using Vertex AI (Project: {client_config['project_id']})")
else:
    print(f"⚠️ Forms endpoints using free API key (may have quota limits)")

class CreateFormRequest(BaseModel):
    topic: str
    num_questions: int
    question_type: str  # MIXED, MULTIPLE_CHOICE, TEXT, PARAGRAPH_TEXT

class EditFormRequest(BaseModel):
    form_id: str
    instruction: str
    form_history_id: Optional[str] = None  # Optional: for saving to history

@router.post("/api/forms/create")
async def create_form_endpoint(
    request: CreateFormRequest,
    authorization: str = Header(None),
    x_user_email: str = Header(None, alias="X-User-Email")
):
    """
    Create a Google Form based on user's topic and requirements
    """
    if not authorization or not x_user_email:
        raise HTTPException(status_code=401, detail="Missing authorization or user email")
    
    # Extract Firebase token
    firebase_token = authorization.replace("Bearer ", "")
    
    try:
        # Generate questions using Gemini (Vertex AI)
        model = GenerativeModel('gemini-2.0-flash-exp')
        
        # Force all questions to be multiple choice
        question_type_instruction = "MULTIPLE_CHOICE" if request.question_type == "MIXED" else request.question_type
        
        prompt = f"""Generate {request.num_questions} educational multiple-choice questions about: {request.topic}

Requirements:
1. Generate EXACTLY {request.num_questions} questions
2. ALL questions MUST be MULTIPLE_CHOICE type
3. Each question must have 4-5 answer options
4. Each question must be educational and relevant to the topic
5. Return ONLY a JSON array, no other text, no markdown

Format for each question:
{{
  "question_text": "The actual question?",
  "question_type": "MULTIPLE_CHOICE",
  "required": true,
  "options": ["Option A", "Option B", "Option C", "Option D"]
}}

Example:
[
  {{
    "question_text": "What is supervised learning?",
    "question_type": "MULTIPLE_CHOICE",
    "required": true,
    "options": ["Learning with labeled data", "Learning without labels", "Reinforcement learning", "Unsupervised clustering"]
  }},
  {{
    "question_text": "Which algorithm is used for classification?",
    "question_type": "MULTIPLE_CHOICE",
    "required": true,
    "options": ["Linear Regression", "Logistic Regression", "K-Means", "PCA"]
  }}
]

Generate {request.num_questions} multiple-choice questions now:"""

        response = model.generate_content(prompt)
        questions_text = response.text.strip()
        
        # Extract JSON from response (remove markdown code blocks if present)
        if "```json" in questions_text:
            questions_text = questions_text.split("```json")[1].split("```")[0].strip()
        elif "```" in questions_text:
            questions_text = questions_text.split("```")[1].split("```")[0].strip()
        
        questions = json.loads(questions_text)
        
        # Create the form
        result = await create_google_form(
            title=f"{request.topic}",
            description=f"A quiz/survey about {request.topic}",
            questions=questions,
            user_email=x_user_email,
            firebase_token=firebase_token
        )
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        # Get the responder URL and construct embeddable URL
        form_id = result["form_id"]
        responder_url = result["url"]  # This is the responderUri from API
        
        # The responder URL already has the correct format for embedding
        # Just add the embedded=true parameter
        embed_url = f"{responder_url}?embedded=true" if "?" not in responder_url else f"{responder_url}&embedded=true"
        
        # Save form to Firebase history
        form_history_id = None
        try:
            import httpx
            TOKEN_SERVICE_URL = os.getenv("TOKEN_SERVICE_URL", "http://localhost:8001")
            
            print(f"📝 Attempting to save form to history at {TOKEN_SERVICE_URL}")
            print(f"   Form: {request.topic} (ID: {form_id})")
            print(f"   User: {x_user_email}")
            
            async with httpx.AsyncClient() as client:
                history_response = await client.post(
                    f"{TOKEN_SERVICE_URL}/api/forms?email={x_user_email}",
                    json={
                        "title": request.topic,
                        "form_id": form_id,
                        "embed_url": embed_url,
                        "view_url": responder_url,
                        "edit_url": result["edit_url"]
                    },
                    timeout=10.0
                )
                
                if history_response.status_code == 200:
                    history_data = history_response.json()
                    form_history_id = history_data.get("id")
                    print(f"✅ Saved form to history: {form_history_id}")
                else:
                    print(f"⚠️ Failed to save form to history: {history_response.status_code}")
                    print(f"   Response: {history_response.text}")
        except Exception as e:
            print(f"⚠️ Error saving form to history: {e}")
            import traceback
            traceback.print_exc()
            # Don't fail the request if history save fails
        
        return {
            "success": True,
            "form_id": form_id,
            "form_history_id": form_history_id,
            "edit_url": result["edit_url"],
            "view_url": responder_url,
            "embed_url": embed_url,
            "message": f"Created form with {len(questions)} questions"
        }
        
    except Exception as e:
        print(f"❌ Error in create_form_endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/forms/edit")
async def edit_form_endpoint(
    request: EditFormRequest,
    authorization: str = Header(None),
    x_user_email: str = Header(None, alias="X-User-Email")
):
    """
    Edit a Google Form using AI-powered natural language instructions
    """
    if not authorization or not x_user_email:
        raise HTTPException(status_code=401, detail="Missing authorization or user email")
    
    # Extract Firebase token
    firebase_token = authorization.replace("Bearer ", "")
    
    try:
        # Get the form service
        forms_service = await get_forms_service(x_user_email, firebase_token)
        
        # Get current form structure
        form = forms_service.forms().get(formId=request.form_id).execute()
        
        # Use Gemini to understand the instruction and generate batch update requests (Vertex AI)
        model = GenerativeModel('gemini-2.0-flash-exp')
        
        current_questions = []
        for idx, item in enumerate(form.get('items', [])):
            if 'questionItem' in item:
                current_questions.append({
                    'index': idx,
                    'title': item.get('title', ''),
                    'itemId': item.get('itemId', ''),
                })
        
        num_questions = len(current_questions)
        max_index = num_questions - 1
        
        prompt = f"""You are a Google Forms API expert. Generate batch update requests for Google Forms API.

Current form has {num_questions} questions (indices 0-{max_index}):
{json.dumps(current_questions, indent=2)}

User instruction: "{request.instruction}"

LOCATION RULES:
- When ADDING new items, use index {num_questions} to append at the end
- When DELETING, use the exact index from the list above (0-{max_index})
- When UPDATING, include the itemId from the current questions list

CRITICAL RULES:
1. The "question" object CANNOT have a "type" field
2. Question types are defined by which field you include: textQuestion, choiceQuestion, scaleQuestion, etc.
3. For multiple choice, use "choiceQuestion" with "type": "RADIO" and "options" array

VALID EXAMPLES:

ADD TEXT QUESTION:
{{
  "createItem": {{
    "item": {{
      "title": "What is your name?",
      "questionItem": {{
        "question": {{
          "required": true,
          "textQuestion": {{}}
        }}
      }}
    }},
    "location": {{"index": 0}}
  }}
}}

ADD MULTIPLE CHOICE QUESTION:
{{
  "createItem": {{
    "item": {{
      "title": "What is your favorite color?",
      "questionItem": {{
        "question": {{
          "required": true,
          "choiceQuestion": {{
            "type": "RADIO",
            "options": [
              {{"value": "Red"}},
              {{"value": "Blue"}},
              {{"value": "Green"}},
              {{"value": "Yellow"}}
            ]
          }}
        }}
      }}
    }},
    "location": {{"index": 0}}
  }}
}}

ADD SCALE QUESTION (1-5 rating):
{{
  "createItem": {{
    "item": {{
      "title": "Rate your experience",
      "questionItem": {{
        "question": {{
          "required": true,
          "scaleQuestion": {{
            "low": 1,
            "high": 5,
            "lowLabel": "Poor",
            "highLabel": "Excellent"
          }}
        }}
      }}
    }},
    "location": {{"index": 0}}
  }}
}}

CRITICAL: For scale questions, use "low", "high", "lowLabel", "highLabel" - NOT "lowerBound", "upperBound", etc.

DELETE QUESTION:
{{
  "deleteItem": {{
    "location": {{"index": 0}}
  }}
}}

UPDATE QUESTION TITLE:
{{
  "updateItem": {{
    "item": {{
      "itemId": "ITEM_ID_FROM_CURRENT_QUESTIONS",
      "title": "Updated question text?"
    }},
    "updateMask": "title",
    "location": {{"index": 0}}
  }}
}}

UPDATE FORM TITLE (if user asks to change the form name):
{{
  "updateFormInfo": {{
    "info": {{
      "title": "New Form Title"
    }},
    "updateMask": "title"
  }}
}}

CRITICAL RULES:
- DO NOT use "updateSettings" for title changes
- Use "updateFormInfo" to change the form title
- Use "updateItem" to change a question title
- Always include "updateMask" to specify what fields are being updated

Return ONLY a JSON object with "requests" array. No markdown, no explanation.
Format: {{"requests": [...]}}

Generate now:"""

        response = model.generate_content(prompt)
        update_text = response.text.strip()
        
        # Extract JSON
        if "```json" in update_text:
            update_text = update_text.split("```json")[1].split("```")[0].strip()
        elif "```" in update_text:
            update_text = update_text.split("```")[1].split("```")[0].strip()
        
        # Parse and validate JSON
        try:
            update_body = json.loads(update_text)
            
            # Validate that requests array exists
            if "requests" not in update_body or not isinstance(update_body["requests"], list):
                raise ValueError("Invalid response format: missing 'requests' array")
            
            if len(update_body["requests"]) == 0:
                raise ValueError("No update requests generated")
                
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse Gemini response as JSON: {update_text}")
            raise HTTPException(
                status_code=500, 
                detail="AI generated invalid response format. Please try rephrasing your instruction."
            )
        except ValueError as e:
            print(f"❌ Validation error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        
        # Validate and fix item indices
        for req in update_body.get("requests", []):
            if "createItem" in req:
                location = req["createItem"].get("location", {})
                index = location.get("index", num_questions)
                
                # Ensure index is valid (can be at most num_questions for appending)
                if index > num_questions:
                    print(f"⚠️ Adjusting createItem index from {index} to {num_questions}")
                    location["index"] = num_questions
            
            elif "deleteItem" in req:
                location = req["deleteItem"].get("location", {})
                index = location.get("index", 0)
                
                # Ensure index is within bounds
                if index > max_index or index < 0:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid item index: {index}. Form has {num_questions} items (indices 0-{max_index})."
                    )
        
        # Execute the batch update
        result = forms_service.forms().batchUpdate(
            formId=request.form_id,
            body=update_body
        ).execute()
        
        # Verify the update
        updated_form = forms_service.forms().get(formId=request.form_id).execute()
        updated_items_count = len(updated_form.get('items', []))
        
        print(f"✅ Form updated successfully. Items: {num_questions} → {updated_items_count}")
        
        return {
            "success": True,
            "message": f"✅ Form updated successfully! Now has {updated_items_count} questions. Refresh to see changes.",
            "updated_items_count": updated_items_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in edit_form_endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


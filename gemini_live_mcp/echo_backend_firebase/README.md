# Echo Firebase Token Service

FastAPI backend service for managing Google OAuth tokens in Firebase Firestore.

## Features

- Store OAuth tokens (access token, refresh token) in Firestore
- Retrieve tokens for authenticated users
- Delete tokens when user logs out
- Check token status
- Firebase Authentication verification
- User can only access their own tokens

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Get Firebase Admin SDK Credentials

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project
3. Go to **Project Settings** (gear icon)
4. Go to **Service Accounts** tab
5. Click **Generate New Private Key**
6. Save the downloaded JSON file as `firebase-credentials.json` in this directory

### 3. Configure Environment

Create a `.env` file:

```bash
# Firebase Configuration
FIREBASE_CREDENTIALS_PATH=firebase-credentials.json

# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret

# Server Configuration
PORT=8001
ALLOWED_ORIGINS=http://localhost:3000
```

Get your Google OAuth credentials:
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project
3. Go to **APIs & Services** > **Credentials**
4. Create **OAuth 2.0 Client ID** (or use existing)
5. Add authorized JavaScript origins: `http://localhost:3000`
6. Add authorized redirect URIs: `http://localhost:3000`
7. Copy Client ID and Client Secret to `.env`

### 4. Run the Server

```bash
python main.py
```

Or with uvicorn:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

The server will start at: http://localhost:8001

## API Endpoints

### Health Check

```http
GET /
```

Response:
```json
{
  "service": "Echo OAuth Token Service",
  "status": "running",
  "version": "1.0.0"
}
```

### Store Tokens

```http
POST /api/tokens/store
Authorization: Bearer <firebase-id-token>
Content-Type: application/json

{
  "email": "user@example.com",
  "access_token": "ya29.a0...",
  "refresh_token": "1//0g...",
  "expires_in": 3599,
  "scope": "https://www.googleapis.com/auth/classroom.courses ..."
}
```

Response:
```json
{
  "success": true,
  "message": "Tokens stored successfully",
  "data": {
    "email": "user@example.com"
  }
}
```

### Retrieve Tokens

```http
GET /api/tokens/retrieve?email=user@example.com
Authorization: Bearer <firebase-id-token>
```

Response:
```json
{
  "email": "user@example.com",
  "access_token": "ya29.a0...",
  "refresh_token": "1//0g...",
  "last_updated": "2024-01-15T10:30:00",
  "expires_in": 3599,
  "scope": "https://www.googleapis.com/auth/classroom.courses ..."
}
```

### Check Token Status

```http
GET /api/tokens/status?email=user@example.com
Authorization: Bearer <firebase-id-token>
```

Response:
```json
{
  "success": true,
  "message": "Token status retrieved",
  "data": {
    "has_tokens": true,
    "email": "user@example.com",
    "last_updated": "2024-01-15T10:30:00"
  }
}
```

### Delete Tokens

```http
DELETE /api/tokens/delete?email=user@example.com
Authorization: Bearer <firebase-id-token>
```

Response:
```json
{
  "success": true,
  "message": "Tokens deleted successfully",
  "data": {
    "email": "user@example.com"
  }
}
```

## Security

- All endpoints require Firebase ID token in Authorization header
- Users can only access their own tokens
- Email from Firebase token must match requested email
- Tokens are stored in Firestore with document ID = user email

## Firestore Structure

```
users/
  {email}/
    access_token: string
    refresh_token: string
    last_updated: string (ISO 8601)
    expires_in: number (optional)
    scope: string (optional)
```

## Error Handling

All errors return appropriate HTTP status codes:

- `401 Unauthorized`: Missing or invalid Firebase token
- `403 Forbidden`: Attempting to access another user's tokens
- `404 Not Found`: No tokens found for user
- `500 Internal Server Error`: Database or server errors

## Testing

Test the API using curl:

```bash
# Get Firebase ID token from your frontend
TOKEN="your-firebase-id-token"
EMAIL="user@example.com"

# Store tokens
curl -X POST http://localhost:8001/api/tokens/store \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "'$EMAIL'",
    "access_token": "test-access-token",
    "refresh_token": "test-refresh-token"
  }'

# Retrieve tokens
curl -X GET "http://localhost:8001/api/tokens/retrieve?email=$EMAIL" \
  -H "Authorization: Bearer $TOKEN"

# Check status
curl -X GET "http://localhost:8001/api/tokens/status?email=$EMAIL" \
  -H "Authorization: Bearer $TOKEN"

# Delete tokens
curl -X DELETE "http://localhost:8001/api/tokens/delete?email=$EMAIL" \
  -H "Authorization: Bearer $TOKEN"
```

## Integration with Main Backend

The main Echo backend (`echo_backend`) can use this service to retrieve user tokens when calling Google Classroom APIs.

Example:
```python
import requests

async def get_user_tokens(user_email: str, firebase_token: str):
    response = requests.get(
        f"http://localhost:8001/api/tokens/retrieve?email={user_email}",
        headers={"Authorization": f"Bearer {firebase_token}"}
    )
    return response.json()
```


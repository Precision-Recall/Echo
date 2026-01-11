"""
Test script for Conversation History API
Run this after starting the backend_firebase service
"""
import asyncio
import httpx

BASE_URL = "http://localhost:8001"
# Replace with your actual Firebase ID token
FIREBASE_TOKEN = "your-firebase-token-here"

async def test_conversation_api():
    """Test all conversation endpoints"""
    
    headers = {"Authorization": f"Bearer {FIREBASE_TOKEN}"}
    
    async with httpx.AsyncClient() as client:
        print("🧪 Testing Conversation History API\n")
        
        # 1. Create a new conversation
        print("1️⃣ Creating new conversation...")
        response = await client.post(
            f"{BASE_URL}/api/conversations",
            headers=headers,
            json={"title": "Test Conversation"}
        )
        print(f"   Status: {response.status_code}")
        conv_data = response.json()
        print(f"   Created: {conv_data}")
        conversation_id = conv_data["id"]
        print()
        
        # 2. Add user message
        print("2️⃣ Adding user message...")
        response = await client.post(
            f"{BASE_URL}/api/conversations/{conversation_id}/messages",
            headers=headers,
            json={
                "role": "user",
                "content": "Hello! Can you help me create an assignment?"
            }
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        print()
        
        # 3. Add assistant message
        print("3️⃣ Adding assistant message...")
        response = await client.post(
            f"{BASE_URL}/api/conversations/{conversation_id}/messages",
            headers=headers,
            json={
                "role": "assistant",
                "content": "Of course! I'd be happy to help you create an assignment. Which course is this for?"
            }
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        print()
        
        # 4. Add another user message
        print("4️⃣ Adding another user message...")
        response = await client.post(
            f"{BASE_URL}/api/conversations/{conversation_id}/messages",
            headers=headers,
            json={
                "role": "user",
                "content": "Math 101"
            }
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        print()
        
        # 5. Get full conversation
        print("5️⃣ Retrieving full conversation...")
        response = await client.get(
            f"{BASE_URL}/api/conversations/{conversation_id}",
            headers=headers
        )
        print(f"   Status: {response.status_code}")
        full_conv = response.json()
        print(f"   Title: {full_conv['title']}")
        print(f"   Messages: {len(full_conv['messages'])}")
        for i, msg in enumerate(full_conv['messages'], 1):
            print(f"     {i}. [{msg['role']}]: {msg['content'][:50]}...")
        print()
        
        # 6. List all conversations
        print("6️⃣ Listing all conversations...")
        response = await client.get(
            f"{BASE_URL}/api/conversations?page=1&limit=10",
            headers=headers
        )
        print(f"   Status: {response.status_code}")
        conversations = response.json()
        print(f"   Total conversations: {len(conversations)}")
        for conv in conversations[:3]:  # Show first 3
            print(f"     - {conv['title']} (ID: {conv['id'][:10]}...)")
        print()
        
        # 7. Delete conversation
        print("7️⃣ Deleting test conversation...")
        response = await client.delete(
            f"{BASE_URL}/api/conversations/{conversation_id}",
            headers=headers
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        print()
        
        print("✅ All tests completed!")

if __name__ == "__main__":
    print("⚠️  Make sure to:")
    print("   1. Start the backend_firebase service (python main.py)")
    print("   2. Replace FIREBASE_TOKEN with your actual token")
    print("   3. Have Firebase credentials configured\n")
    
    asyncio.run(test_conversation_api())


"""
Quick test script for VoiceFlow Desktop backend
Tests MCP connection and basic agent functionality
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.automation import MCPClient, DesktopTools
from src.agent import DesktopAgent, ThinkingLogger


async def test_mcp_connection():
    """Test MCP client connection"""
    print("\n🧪 Test 1: MCP Client Connection")
    print("="*60)
    
    try:
        client = MCPClient()
        print("  ✓ MCPClient initialized")
        
        await client.connect()
        print("  ✓ Connected to Windows-MCP")
        
        # Test get_state
        state = await client.get_state()
        print(f"  ✓ Got desktop state: {len(str(state))} bytes")
        
        await client.disconnect()
        print("  ✓ Disconnected from Windows-MCP")
        
        print("\n✅ Test 1 PASSED\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Test 1 FAILED: {e}\n")
        return False


async def test_desktop_tools():
    """Test desktop tools wrapper"""
    print("\n🧪 Test 2: Desktop Tools")
    print("="*60)
    
    try:
        client = MCPClient()
        await client.connect()
        
        tools = DesktopTools(client)
        print("  ✓ DesktopTools initialized")
        
        # Get tool definitions
        tool_defs = tools.get_tool_definitions()
        print(f"  ✓ Got {len(tool_defs)} tool definitions")
        
        for tool in tool_defs[:3]:  # Show first 3
            print(f"    - {tool['name']}: {tool['description'][:50]}...")
        
        await client.disconnect()
        
        print("\n✅ Test 2 PASSED\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Test 2 FAILED: {e}\n")
        return False


async def test_thinking_logger():
    """Test thinking logger"""
    print("\n🧪 Test 3: Thinking Logger")
    print("="*60)
    
    try:
        logger = ThinkingLogger()
        print("  ✓ ThinkingLogger initialized")
        
        logger.log_thought("Testing thought logging")
        logger.log_action("test_tool", {"param": "value"})
        logger.log_observation({"success": True, "message": "Test observation"})
        logger.log_result("Test completed")
        
        trace = logger.get_full_trace()
        print(f"  ✓ Logged {len(trace)} events")
        
        print("\n✅ Test 3 PASSED\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Test 3 FAILED: {e}\n")
        return False


async def test_agent_basic():
    """Test basic agent functionality"""
    print("\n🧪 Test 4: Basic Agent (if API key is set)")
    print("="*60)
    
    load_dotenv()
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("  ⚠️  GEMINI_API_KEY not set, skipping agent test")
        print("  → Add your API key to .env to test the agent\n")
        return True
    
    try:
        client = MCPClient()
        await client.connect()
        
        tools = DesktopTools(client)
        logger = ThinkingLogger()
        
        agent = DesktopAgent(
            gemini_api_key=api_key,
            desktop_tools=tools,
            thinking_logger=logger
        )
        print("  ✓ Agent initialized")
        
        # Note: Not executing a real task to avoid unwanted actions
        print("  ✓ Agent ready (task execution skipped in test)")
        
        await client.disconnect()
        
        print("\n✅ Test 4 PASSED\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Test 4 FAILED: {e}\n")
        return False


async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("  VoiceFlow Desktop - Backend Tests")
    print("="*60)
    
    results = []
    
    # Run tests
    results.append(await test_mcp_connection())
    results.append(await test_desktop_tools())
    results.append(await test_thinking_logger())
    results.append(await test_agent_basic())
    
    # Summary
    print("\n" + "="*60)
    print("  Test Summary")
    print("="*60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"  Passed: {passed}/{total}")
    
    if passed == total:
        print("\n  🎉 All tests passed!\n")
        print("  Next steps:")
        print("  1. Add your GEMINI_API_KEY to .env")
        print("  2. Test the agent: uv run python main.py test --command \"Open Notepad\"")
        print("  3. Build the Electron UI (coming next)")
    else:
        print(f"\n  ⚠️  {total - passed} test(s) failed\n")
    
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

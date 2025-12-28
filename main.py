"""
VoiceFlow Desktop - Voice-controlled Windows desktop automation
"""

import os
import sys
import asyncio
import argparse
from dotenv import load_dotenv


from src.agent import DesktopAgent, ThinkingLogger


async def test_agent(command: str):
    """
    Test the agent directly from CLI (without Electron UI)
    
    Args:
        command: Command to execute
    """
    load_dotenv()
    
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        print("❌ Error: GEMINI_API_KEY not set in environment")
        print("   Please create a .env file with your Gemini API key")
        sys.exit(1)
    
    # Initialize components with LangChain + Windows-MCP
    print("🤖 Initializing VoiceFlow Desktop agent...")
    print("   (Make sure Windows-MCP server is running on http://localhost:8000)")
    
    thinking_logger = ThinkingLogger()
    
    agent = DesktopAgent(
        gemini_api_key=gemini_api_key,
        thinking_logger=thinking_logger,
        # Default to FAST mode for CLI testing
        # To use Voice mode later: mode=AgentMode.VOICE
    )
    
    # Initialize agent (connect to MCP, load tools)
    try:
        await agent.initialize()
    except Exception as e:
        print(f"\n❌ Failed to initialize agent: {e}")
        print("\n💡 Make sure Windows-MCP server is running:")
        print("   uvx windows-mcp --transport streamable-http --port 8000")
        sys.exit(1)
    
    print(f"\n🎯 Executing: {command}\n")
    print("="*60)
    
    # Execute task
    result = await agent.execute_task(command)
    
    print("="*60)
    print("\n📊 FINAL RESULT:")
    print(f"   Success: {result.get('success')}")
    print(f"   Message: {result.get('result', result.get('error'))}")
    
    if result.get('trace'):
        print(f"\n📋 Saved trace to: agent_trace.json")
        thinking_logger.save_to_file("agent_trace.json")
    
    # Cleanup
    await agent.cleanup()




def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="VoiceFlow Desktop - Voice-controlled Windows automation"
    )
    
    parser.add_argument(
        "--command",
        "-c",
        type=str,
        help="Command to execute",
        required=True
    )
    
    args = parser.parse_args()
    
    # Run test agent directly
    asyncio.run(test_agent(args.command))


if __name__ == "__main__":
    main()


"""
VoiceFlow Desktop - Voice-controlled Windows desktop automation
"""

import os
import sys
import asyncio
import argparse
from dotenv import load_dotenv


from src.agent import DesktopAgent, ThinkingLogger, AgentMode


async def test_agent(command: str, mode: AgentMode = AgentMode.FAST):
    """
    Test the agent directly from CLI (without Electron UI)
    
    Args:
        command: Command to execute
        mode: Execution AgentMode (FAST or VOICE)
    """
    load_dotenv()
    
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        print("❌ Error: GEMINI_API_KEY not set in environment")
        print("   Please create a .env file with your Gemini API key")
        sys.exit(1)
    
    # Initialize components with LangChain + Windows-MCP
    print("🤖 Initializing Echo...")
    print("   (Make sure Windows-MCP server is running on http://localhost:8000)")
    
    thinking_logger = ThinkingLogger()
    
    agent = DesktopAgent(
        gemini_api_key=gemini_api_key,
        thinking_logger=thinking_logger,
        mode=mode
    )
    
    # Initialize agent (connect to MCP, load tools)
    try:
        await agent.initialize()
    except Exception as e:
        print(f"\n❌ Failed to initialize agent: {e}")
        print("\n💡 Make sure Windows-MCP server is running:")
        print("   uvx windows-mcp --transport streamable-http --port 8000")
        sys.exit(1)
        
    try:
        if mode == AgentMode.VOICE:
            print("\n🎙️ Starting Voice Mode (Gemini Live)...")
            print("   Using Model: " + agent.config.model_name)
            print("   Speak into your microphone. Press Ctrl+C to stop.")
            await agent.run_voice_session()
        else:
            if not command:
                print("❌ Error: --command is required for fast mode")
                print("   Use --mode voice for voice interaction")
                return

            print(f"\n🎯 Executing: {command}\n")
            print("="*60)
            
            # Execute task
            result = await agent.execute_task(command)
            
            print("="*60)
            print("\n📊 FINAL RESULT:")
            print(f"   Success: {result.get('success')}")
            print(f"   Message: {result.get('message', result.get('error'))}")
            
    except KeyboardInterrupt:
        print("\n👋 Stopped by user")
    except Exception as e:
        print(f"\n❌ Error during execution: {e}")
    finally:
        await agent.cleanup()
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
        help="Command to execute (required for 'fast' mode, ignored for 'voice')",
        default=None
    )
    
    parser.add_argument(
        "--mode",
        "-m",
        type=str,
        choices=["fast", "voice"],
        default="fast",
        help="Execution mode: 'fast' (text command) or 'voice' (interactive audio)"
    )
    
    args = parser.parse_args()
    
    # Map CLI mode string to Enum
    mode_map = {
        "fast": AgentMode.FAST,
        "voice": AgentMode.VOICE
    }
    selected_mode = mode_map[args.mode]
    
    # Run test agent
    asyncio.run(test_agent(args.command, mode=selected_mode))


if __name__ == "__main__":
    main()


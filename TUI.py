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
    # Try loading .env from multiple locations with fallback
    project_root = os.path.dirname(os.path.abspath(__file__))
    env_locations = [
        os.path.join(project_root, '.env'),
        os.path.join(os.getcwd(), '.env'),
        os.path.join(os.path.expanduser('~'), '.env'),
        os.path.join(os.path.expanduser('~'), '.gemini', '.env'),
    ]
    
    for env_path in env_locations:
        if os.path.exists(env_path):
            load_dotenv(env_path)
            if os.getenv("GEMINI_API_KEY"):
                break
    
    # Try multiple key names (including numbered backups)
    gemini_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    
    # Fallback to numbered backup keys
    if not gemini_api_key:
        for i in range(1, 5):
            gemini_api_key = os.getenv(f"GEMINI_API_KEY_{i}")
            if gemini_api_key:
                break
    
    if not gemini_api_key:
        print("[x] Error: GEMINI_API_KEY not found")
        print("   Searched: .env (project, cwd, home, ~/.gemini)")
        print("   Also checked: GOOGLE_API_KEY environment variable")
        sys.exit(1)
    
    # Initialize components with LangChain + Windows-MCP
    from src.utils.ui import print_header, console, custom_theme
    from src.utils.mcp_config import MCPConfigManager
    
    # Load MCP configuration (same as Electron app)
    mcp_manager = MCPConfigManager()
    mcp_config = mcp_manager.load_config()
    
    # Show which servers are enabled
    enabled_servers = [name for name, details in mcp_config.get("mcp_servers", {}).items() 
                       if details.get("enabled", True)]
    
    print_header("Initializing Echo...", "Starting MCP & Gemini Connection")
    
    if enabled_servers:
        console.print(f"[dim]   MCP Servers: {', '.join(enabled_servers)}[/dim]")
    else:
        console.print("[dim]   (Make sure MCP servers are running - check mcp_config.json)[/dim]")
    
    thinking_logger = ThinkingLogger()
    
    agent = DesktopAgent(
        gemini_api_key=gemini_api_key,
        thinking_logger=thinking_logger,
        mode=mode,
        mcp_config=mcp_config
    )
    
    import traceback
    
    # Initialize agent (connect to MCP, load tools)
    try:
        with console.status("[bold #D946EF]Connecting to Desktop...[/]", spinner="dots"):
            await agent.initialize()
        console.print("[success][+] Agent initialized successfully[/success]")
    except Exception as e:
        error_msg = str(e)
        if "TaskGroup" in error_msg or "ConnectError" in error_msg:
            # Check for connection error details
            console.print("\n[error][x] Connection Failed[/error]")
            console.print("[dim]   Could not connect to Windows-MCP server at http://localhost:8000[/dim]")
            
            from rich.panel import Panel
            console.print(Panel(
                "[bold yellow]1. Check Server:[/bold yellow] Is the terminal window open?\n"
                "[bold yellow]2. Restart:[/bold yellow] Stop (Ctrl+C) and run:\n"
                "   [bold white]uvx windows-mcp --transport streamable-http --port 8000[/bold white]",
                title="[bold red]Server Not Reachable[/bold red]",
                border_style="red"
            ))
        else:
            console.print(f"\n[error][x] Failed to initialize: {e}[/error]")
            console.print("[dim]Traceback available in logs[/dim]")
            
        sys.exit(1)
    
    result = {} # Initialize to avoid unbound error in finally
    try:
        if mode == AgentMode.VOICE:
            # Use Advanced TUI for Voice
            from src.utils.tui import EchoTUI
            tui = EchoTUI()
            
            # Callback to update TUI from Logger
            def log_callback(type_: str, message: str):
                if type_ == "thought":
                    tui.add_thought(message)
                else:
                    style = "white"
                    if type_ == "error": style = "red"
                    if type_ == "result": style = "green"
                    tui.add_log(message, style)
            
            # Update the existing logger instead of creating new agent
            thinking_logger.ui_callback = log_callback
            
            # Re-init agent connection is NOT needed - we already initialized above!
            # Just start the TUI with existing agent
            
            try:
                tui.set_listening(True) # Assume listening start
                
                async with asyncio.TaskGroup() as tg:
                    tg.create_task(tui.start())
                    
                    # Agent Task
                    async def run_agent():
                        try:
                            tui.add_log("[+] Agent Connected", "green")
                            tui.add_thought("Starting Voice Session...")
                            await agent.run_voice_session()
                        except asyncio.CancelledError:
                            pass
                        except Exception as e:
                            tui.add_log(f"Error: {e}", "red")
                            import traceback
                            traceback.print_exc()
                            tui.stop_event.set()
                        finally:
                            tui.stop_event.set()
                            
                    tg.create_task(run_agent())
                    
            except KeyboardInterrupt:
                pass
            except Exception as e:
                print(f"Error: {e}")
                import traceback
                traceback.print_exc()
                
        else:
            if not command:
                console.print("[error][x] Error: --command is required for fast mode[/error]")
                console.print("   Use [bold]--mode voice[/bold] for voice interaction")
                return

            print_header("Executing Command", command)
            
            # Execute task
            with console.status("[bold #8B5CF6]Thinking...[/]", spinner="dots"):
                result = await agent.execute_task(command)
            
            from rich.panel import Panel
            
            success = result.get('success', False)
            message = result.get('message', result.get('error', 'Unknown result'))
            
            style = "success" if success else "error"
            title = "Task Completed" if success else "Task Failed"
            
            console.print(Panel(
                message,
                title=f"[bold {style}]{title}[/]",
                border_style="#D946EF"
            ))
            
    except KeyboardInterrupt:
        console.print("\n[dim]-- Stopped by user[/dim]")
    except Exception as e:
        console.print(f"\n[error][x] Error during execution: {e}[/error]")
    finally:
        await agent.cleanup()
        # FIX: Check for 'events' attribute, not 'logs'
        if thinking_logger.events:
            console.print(f"\n[dim][>] Saved trace to: agent_trace.json[/dim]")
            thinking_logger.save_to_file("agent_trace.json")




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
import asyncio
from datetime import datetime
from typing import List, Optional

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich import box
from rich.align import Align

# Shared Console
console = Console()

class EchoTUI:
    """
    Advanced TUI for Echo with split layout and live updates.
    Inspired by Claude Code.
    """
    
    def __init__(self):
        self.layout = Layout()
        self.ThinkingLog: List[Text] = []
        self.MainLog: List[Text] = []
        self.is_listening = False
        self.wave_frame = 0
        self.stop_event = asyncio.Event()
        
        self._setup_layout()
        
    def _setup_layout(self):
        """Define the main layout structure"""
        self.layout.split(
            Layout(name="header", size=5),
            Layout(name="body", ratio=1),
            Layout(name="footer", size=3)
        )
        
        self.layout["body"].split_row(
            Layout(name="main", ratio=2),
            Layout(name="sidebar", ratio=1)
        )
        
        # Initial Content
        self.update_header()
        self.update_footer()
        self.update_sidebar()
        self.update_main()

    def update_header(self):
        """Render Header"""
        banner_text = """█▀▀ █▀▀ █ █ █▀█
██▄ █▄▄ █▀█ █▄█"""
        
        grid = Table.grid(expand=True)
        grid.add_column(justify="center", ratio=1)
        
        title = Text(banner_text, style="bold white")
        subtitle = Text("Voice & Desktop Agent • Gemini Live", style="dim white")
        
        grid.add_row(title)
        grid.add_row(subtitle)
        
        self.layout["header"].update(
            Panel(
                grid, 
                style="on #2E1065", 
                box=box.HEAVY_EDGE,
                padding=(0, 0)
            )
        )

    def update_footer(self):
        """Render Footer"""
        text = Text(" ⬤  Stop: Ctrl+C ", style="bold red")
        self.layout["footer"].update(Panel(Align.center(text), style="on #2E1065", box=box.HEAVY_EDGE))

    def update_sidebar(self):
        """Render Thinking Trace (Right)"""
        content = Text("\n".join([str(t) for t in self.ThinkingLog[-20:]])) # Show last 20 lines
        
        self.layout["sidebar"].update(
            Panel(
                content,
                title="[bold #D946EF]🧠 Thinking Process[/]",
                border_style="#D946EF",
                box=box.ROUNDED
            )
        )

    def get_wave_animation(self) -> str:
        """Generate a simple wave animation frame"""
        if not self.is_listening:
            return "💤 Idle"
            
        waves = [
            "  ▂ ▃ ▄ ▅ ▆ ▇ █ ▇ ▆ ▅ ▄ ▃ ▂  ",
            " ▂ ▃ ▄ ▅ ▆ ▇ █ ▇ ▆ ▅ ▄ ▃ ▂   ",
            "▂ ▃ ▄ ▅ ▆ ▇ █ ▇ ▆ ▅ ▄ ▃ ▂    ",
            "▃ ▄ ▅ ▆ ▇ █ ▇ ▆ ▅ ▄ ▃ ▂      "
        ]
        self.wave_frame = (self.wave_frame + 1) % len(waves)
        return f"[bold cyan]🎙️ Listening...[/] {waves[self.wave_frame]}"

    def update_main(self):
        """Render Main Content (Left)"""
        # Status / Wave
        status_text = self.get_wave_animation()
        
        # Main Activity Log
        log_content = Text("\n").join(self.MainLog[-15:])
        
        main_grid = Layout()
        main_grid.split(
            Layout(Panel(Align.center(status_text), border_style="cyan", box=box.ROUNDED, title="Status"), size=5),
            Layout(Panel(log_content, title="Action Log", border_style="white", box=box.ROUNDED), ratio=1)
        )
        
        self.layout["main"].update(main_grid)

    def add_thought(self, message: str):
        """Add a thought to the sidebar"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.ThinkingLog.append(Text(f"[{timestamp}] {message}", style="dim #D946EF"))
        self.update_sidebar()

    def add_log(self, message: str, style="white"):
        """Add a log to the main window"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.MainLog.append(Text(f"[{timestamp}] {message}", style=style))
        self.update_main()

    def set_listening(self, active: bool):
        self.is_listening = active
        self.update_main()

    async def start(self):
        """Start the Live Loop"""
        with Live(self.layout, refresh_per_second=10, screen=True) as live:
            while not self.stop_event.is_set():
                self.update_main() # Update animations
                live.refresh()
                await asyncio.sleep(0.1)

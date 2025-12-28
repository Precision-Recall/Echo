from rich.console import Console
from rich.theme import Theme
from rich.style import Style

# Claude Code-inspired Theme (Purple/Pink)
custom_theme = Theme({
    "info": "dim cyan",
    "warning": "magenta",
    "error": "bold red",
    "success": "bold green",
    "thought": "bold #D946EF",     # Pink/Fuchsia
    "action": "bold #8B5CF6",      # Violet/Purple
    "observation": "dim #A78BFA",  # Light Purple
    "header": "bold white on #8B5CF6",
    "panel.border": "#D946EF",
})

console = Console(theme=custom_theme)

def print_header(title: str, subtitle: str = ""):
    from rich.panel import Panel
    from rich.text import Text
    
    grid = Text.assemble(
        (title, "bold white"),
        "\n",
        (subtitle, "dim white")
    )
    
    console.print(Panel(
        grid,
        style="panel.border",
        padding=(1, 2),
        title="[bold white]Echo[/bold white]",
        subtitle="[dim white]Voice & Desktop Agent[/dim white]"
    ))

def print_thought(message: str):
    console.print(f"[thought]💭 {message}[/thought]")

def print_action(tool: str, params: str):
    console.print(f"[action]🔧 {tool}[/action] [dim]{params}[/dim]")

def print_result(message: str):
    console.print(f"[success]✅ Result:[/success] {message}")

def print_observation(message: str, success: bool = True):
    symbol = "✓" if success else "✗"
    color = "success" if success else "error"
    console.print(f"[{color}]👁️ {symbol} {message}[/{color}]")

def print_error(message: str):
    console.print(f"[error]❌ {message}[/error]")

"""CLI display module — all Rich-based output functions for Finance Agent terminal interface.

Handles all visual output — typing effects, status messages, success/error/warning display.
Used only by agent/core.py and main.py — never imported by tools or bridge.

Functions:
    type_out        — print text with typewriter effect
    type_list       — print list items with staggered typing effect
    agent_thinking  — animated spinner context manager while LLM or operation runs
    agent_status    — real-time status message for ongoing operations
    agent_success   — green success message with optional typing effect
    agent_warning   — yellow warning message with optional typing effect
    agent_error     — red error message with optional typing effect
    agent_info      — cyan info message with optional typing effect
"""
import time
import random
from rich.console import Console
from rich.status import Status
from contextlib import contextmanager


console = Console()


def type_out(text: str, delay: float = 0.018, color: str = "green", prefix: str = ""):
    """
    Enhanced typing effect — feels like a real AI agent is responding.
    - Natural random speed variation (human-like)
    - Optional prefix (e.g., "→ " or "💰 ")
    - Rich colors for premium feel
    """
    if prefix:
        console.print(prefix, end="", style=color)

    for char in text:
        console.print(char, end="", style=color)
        # Natural typing speed (slightly random)
        time.sleep(delay + random.uniform(-0.004, 0.009))
    
    console.print()  # New line


def type_list(items: list, delay: float = 0.05, numbered: bool = True):
    """
    Print list items with typing effect — perfect for welcome/capabilities.
    """
    for i, item in enumerate(items, start=1):
        if numbered:
            console.print(f"  [bold cyan]{i}.[/bold cyan] ", end="")
        else:
            console.print("  • ", end="", style="cyan")
        
        type_out(item, delay=0.016, color="white")
        
        if delay > 0:
            time.sleep(delay)


@contextmanager
def agent_thinking(message: str = "Thinking"):
    """
    Shows animated "thinking..." while LLM or operation is in progress.
    Uses Rich spinner — user feels something is happening in real-time.

    Wraps LLM call in core.py. Do not call console.print() 
    inside this context — it conflicts with the spinner display.
    """
    with console.status(f"[bold yellow]🤔 {message}...[/bold yellow]", spinner="dots12"):
        yield


def agent_status(operation: str, detail: str = "", style: str = "yellow"):
    """
    Real-time status messages (exactly what you asked for).
    Examples:
        agent_status("Adding new transaction")
        agent_status("Filtering expenses", "by category & date")
        agent_status("Generating PDF report", style="blue")
    """
    status_text = f"[bold {style}]→ {operation}[/bold {style}]"
    if detail:
        status_text += f" [dim]{detail}[/dim]"
    
    console.print(status_text)
    time.sleep(0.2)  # Short pause so user notices the action


def agent_success(message: str, typing: bool = True):
    """✅ Success message with AI personality"""
    if typing:
        console.print("[bold green]✅ [/bold green] ", end="")
        type_out(message, delay=0.018, color="green")
    else:
        console.print(f"[bold green]✅ [/bold green] {message}")


def agent_warning(message: str, typing: bool = True):
    """⚠️  Warning message """
    if typing:
        console.print("[bold yellow]⚠️  [/bold yellow] ", end="")
        type_out(message, delay=0.018, color="yellow")
    else:
        console.print(f"[bold yellow]⚠️  [/bold yellow] {message}")


def agent_error(message: str, typing: bool = True):
    """❌ Error message """
    if typing:
        console.print("[bold red]❌ [/bold red] ", end="")
        type_out(message, delay=0.018, color="red")
    else:
        console.print(f"[bold red]❌ [/bold red] {message}")


def agent_info(message: str, typing: bool = True):
    """ℹ️  Info / neutral message (bonus — very useful for agent responses) """
    if typing:
        console.print("[bold cyan]  [/bold cyan] ", end="")
        type_out(message, delay=0.018, color="cyan")
    else:
        console.print(f"[bold cyan]  [/bold cyan] {message}")


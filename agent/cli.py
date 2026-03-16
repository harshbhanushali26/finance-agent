"""CLI display module — all Rich-based output functions for Finance Agent terminal interface.

Handles all visual output — typing effects, status messages, success/error/warning display,
and all dashboard/budget/insights/categories panels.
Used only by main.py — never imported by tools or bridge.

Functions:
    type_out        — print text with typewriter effect
    type_list       — print list items with staggered typing effect
    agent_thinking  — animated spinner context manager while LLM or operation runs
    agent_status    — real-time status message for ongoing operations
    agent_success   — green success message with optional typing effect
    agent_warning   — yellow warning message with optional typing effect
    agent_error     — red error message with optional typing effect
    agent_info      — cyan info message with optional typing effect
    show_dashboard  — today + monthly summary panels
    show_budget     — budget status with per-category burn rate
    show_categories — income and expense category list
    show_insights   — pattern detection results panel
    print_welcome   — welcome screen with capabilities list
    print_help      — commands and example queries table
"""

import time
import random
from datetime import datetime, timedelta

from rich import box
from rich.panel import Panel
from rich.table import Table
from rich.console import Console
from contextlib import contextmanager




console = Console()


COMMANDS = {
    "help":       "Show available commands and example queries",
    "clear":      "Clear conversation history — start fresh context",
    "history":    "Show current conversation history",
    "dashboard":  "Quick summary — today + this month",
    "budget":     "Quick budget status for current month",
    "categories": "Show all your income and expense categories",
    "exit":       "Exit Finance Agent",
}


EXAMPLES = [
    "add 250 for food",
    "add 50000 salary income for today",
    "how much did I spend this month?",
    "show my top 5 expense categories",
    "what did I spend on food last month?",
    "set food budget to 5000",
    "show budget status",
    "show all expenses this week",
    "delete transaction <id>",
    "update transaction <id> amount to 300",
    "set my monthly income to 50000",
]


# ── Helper Functions ───────────────────────────────────────────────────────────────────────


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



# ── APP CLI Functions ───────────────────────────────────────────────────────────────────────


def print_welcome():
    """Print welcome screen with capabilities list."""
    console.print()
    console.print(Panel.fit(
        "[bold cyan]💰 Finance Agent[/bold cyan]  [dim]v1.0[/dim]\n"
        "[dim]Your personal AI finance assistant[/dim]",
        border_style="blue"
    ))
    console.print()
    console.print("[dim]What I can help with:[/dim]")
    console.print()
    type_list([
        "Track income and expenses",
        "Daily, monthly and custom reports",
        "Spending pattern analysis",
        "Budget tracking and alerts",
        "Smart balance and top categories",
    ], delay=0.05)
    console.print()
    console.print("[dim]Type [bold white]help[/bold white] for commands · [bold white]exit[/bold white] to quit[/dim]")
    console.print()


def print_help():
    """Print available commands and example queries."""
    console.print()

    cmd_table = Table(
        title="⚡ Commands",
        box=box.SIMPLE_HEAVY,
        show_header=True,
        header_style="bold cyan"
    )
    cmd_table.add_column("Command", style="bold yellow", min_width=14)
    cmd_table.add_column("Description", style="white")

    for cmd, desc in COMMANDS.items():
        cmd_table.add_row(cmd, desc)

    console.print(cmd_table)
    console.print()

    ex_table = Table(
        title="💬 Example Queries",
        box=box.SIMPLE_HEAVY,
        show_header=False,
    )
    ex_table.add_column("", style="cyan")

    for example in EXAMPLES:
        ex_table.add_row(f'"{example}"')

    console.print(ex_table)
    console.print()


def show_dashboard(data):
    """Display dashboard directly from bridge — no LLM involved."""
    if data is None:
        agent_error("Could not load dashboard data")
        return

    daily = data["daily"]
    monthly = data["monthly"]

    today_label = datetime.now().strftime("%d %b %Y")
    month_label = datetime.now().strftime("%B %Y")

    # ── Today ──────────────────────────────────────────────
    today_lines = (
        f"[dim]Income[/dim]    [bold green]₹{daily['income']:,.0f}[/bold green]\n"
        f"[dim]Expense[/dim]   [bold red]₹{daily['expense']:,.0f}[/bold red]\n"
        f"[dim]Balance[/dim]   [bold cyan]₹{daily['balance']:,.0f}[/bold cyan]\n"
        f"[dim]Carry Fwd[/dim] [dim]₹{daily['carry_forward']:,.0f}[/dim]\n"
        f"[dim]Txns[/dim]      [dim]{daily['num_income']} income · {daily['num_expense']} expense[/dim]"
    )

    # ── This Month ─────────────────────────────────────────
    breakdown = monthly.get("breakdown", {})
    top_categories = sorted(breakdown.items(), key=lambda x: x[1], reverse=True)[:3]
    top_str = "  ".join(f"[dim]{cat}[/dim] [yellow]₹{amt:,.0f}[/yellow]" for cat, amt in top_categories)

    month_lines = (
        f"[dim]Income[/dim]    [bold green]₹{monthly['income']:,.0f}[/bold green]\n"
        f"[dim]Expense[/dim]   [bold red]₹{monthly['expense']:,.0f}[/bold red]\n"
        f"[dim]Balance[/dim]   [bold cyan]₹{monthly['balance']:,.0f}[/bold cyan]\n"
        f"[dim]Carry Fwd[/dim] [dim]₹{monthly['carry_forward']:,.0f}[/dim]\n"
        f"[dim]Txns[/dim]      [dim]{monthly['num_income']} income · {monthly['num_expense']} expense[/dim]\n"
        + (f"[dim]Top[/dim]       {top_str}" if top_categories else "")
    )

    console.print()
    console.print(Panel.fit(
        today_lines,
        title=f"[bold cyan]📅 Today — {today_label}[/bold cyan]",
        border_style="blue",
        padding=(0, 2)
    ))
    console.print(Panel.fit(
        month_lines,
        title=f"[bold cyan]📊 {month_label}[/bold cyan]",
        border_style="blue",
        padding=(0, 2)
    ))
    console.print()


def show_categories(data):
    """Display income and expense categories in a Rich panel.
    
    Args:
        data: Dict with 'income' and 'expense' keys — list of category name strings each.
    """
    income_cats = data.get("income", [])
    expense_cats = data.get("expense", [])

    income_str = "  ".join(f"[green]{cat}[/green]" for cat in income_cats) or "[dim]none[/dim]"
    expense_str = "  ".join(f"[yellow]{cat}[/yellow]" for cat in expense_cats) or "[dim]none[/dim]"

    console.print()
    console.print(Panel.fit(
        f"[dim]Income[/dim]   {income_str}\n\n"
        f"[dim]Expense[/dim]  {expense_str}",
        title="[bold cyan]📂 Your Categories[/bold cyan]",
        border_style="blue",
        padding=(0, 2)
    ))
    console.print()


def show_insights(insights):
    """Display all pattern detection insights for current month. 0 LLM calls."""
    
    month_label = datetime.now().strftime("%B %Y")

    console.print()
    if not insights:
        console.print(Panel.fit(
            "[dim]No significant patterns detected this month yet.\n"
            "Add more transactions to get insights.[/dim]",
            title=f"[bold cyan]💡 Insights — {month_label}[/bold cyan]",
            border_style="blue",
            padding=(0, 2)
        ))
    else:
        lines = [f"[white]{insight}[/white]" for insight in insights]
        console.print(Panel.fit(
            "\n".join(lines),
            title=f"[bold cyan]💡 Insights — {month_label}[/bold cyan]",
            border_style="blue",
            padding=(0, 2)
        ))
    console.print()


def show_budget(data):
    """Display budget status — pure display, no bridge calls."""
    if data is None:
        agent_error("Could not load budget data.")
        return

    month_label = data["month_label"]

    if data.get("empty"):
        agent_info(f"No budgets set for {month_label}. Try: set food budget to 5000")
        return

    
    budgets        = data["budgets"]
    breakdown      = data["breakdown"]
    carried        = data["carried"]
    unbudgeted     = data["unbudgeted"]
    days_passed    = data["days_passed"]
    days_in_month  = data["days_in_month"]
    days_remaining = data["days_remaining"]
    today          = data["today"]


    # carry-forward notice
    if carried:
        console.print(f"[cyan]↩ Carried forward from last month: {', '.join(carried)}[/cyan]")
        console.print()

    # unbudgeted reminder
    if unbudgeted:
        console.print(f"[yellow]⚠ No budget set for: {', '.join(unbudgeted)}[/yellow]")
        console.print(f"[dim]  Try: set {unbudgeted[0].split(' ')[0].lower()} budget to 5000[/dim]")
        console.print()

    lines = []
    for category, limit in budgets.items():
        spent = breakdown.get(category, 0)
        percent = (spent / limit * 100) if limit > 0 else 0
        remaining = limit - spent
        filled = round(percent / 10)
        bar = "█" * filled + "░" * (10 - filled)

        if spent > limit:
            status = "[bold red]OVER[/bold red]"
            color = "red"
        elif percent >= 80:
            status = "[bold yellow]NEAR[/bold yellow]"
            color = "yellow"
        else:
            status = "[bold green]OK[/bold green]"
            color = "green"

        lines.append(
            f"[bold]{category:<12}[/bold] [{color}]{bar}[/{color}] "
            f"₹{spent:,.0f} / ₹{limit:,.0f}  {status}  "
            f"[dim]₹{remaining:,.0f} left[/dim]"
        )

        # ── Overspend trend ──
        if days_passed > 0 and spent < limit:
            cat_daily = spent / days_passed
            cat_daily_allowed = limit / days_in_month
            if cat_daily > cat_daily_allowed:
                days_to_exceed = (limit - spent) / cat_daily
                exceed_date = (today + timedelta(days=days_to_exceed)).strftime("%d %b")
                lines.append(f"  [dim]↑ At this rate, {category} exceeded by {exceed_date}[/dim]")

        lines.append("")


    # ── Per-category Burn Rate ─────────────────────────────────
    lines.append("[dim]── Burn Rate ─────────────────────────────────────────[/dim]")

    for category, limit in budgets.items():
        spent = breakdown.get(category, 0)
        daily_actual  = spent / days_passed if days_passed > 0 else 0
        daily_allowed = limit / days_in_month

        if daily_actual > daily_allowed:
            rate_color = "red"
        elif daily_actual > daily_allowed * 0.8:
            rate_color = "yellow"
        else:
            rate_color = "green"

        lines.append(
            f"  [bold]{category:<12}[/bold] "
            f"[{rate_color}]₹{daily_actual:,.0f}/day[/{rate_color}] actual  "
            f"[dim]vs  ₹{daily_allowed:,.0f}/day allowed[/dim]"
        )

    # ── Overall total line ─────────────────────────────────────
    total_spent_all  = sum(breakdown.values())   # all expense categories
    total_budget_all = sum(budgets.values())
    daily_actual_total  = total_spent_all / days_passed if days_passed > 0 else 0
    daily_allowed_total = total_budget_all / days_in_month

    lines.append("")
    lines.append(
        f"  [bold]{'Total':<12}[/bold] "
        f"[yellow]₹{daily_actual_total:,.0f}/day[/yellow] actual  "
        f"[dim]vs  ₹{daily_allowed_total:,.0f}/day allowed  · {days_remaining} days left[/dim]"
    )

    console.print()
    console.print(Panel.fit(
        "\n".join(lines),
        title=f"[bold cyan]💰 Budget Status — {month_label}[/bold cyan]",
        border_style="blue",
        padding=(0, 2)
    ))
    console.print()




"""main.py — CLI entry point for Finance Agent.

Handles welcome screen, login, session creation, and main chat loop.
Supports special commands for quick actions and navigation.
"""

import sys
from rich.prompt import Prompt
from rich.panel import Panel
from rich.table import Table
from rich import box

from bridge.expense_bridge import ExpenseBridge
from bridge.auth_helper import login
from agent.session import Session
from agent import core
from agent.cli import (
    agent_success, agent_info,
    agent_error, agent_status, agent_thinking,
    type_list, type_out, console
)

MAX_LOGIN_RETRIES = 3

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


# ── Welcome ────────────────────────────────────────────────────────────────────

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


# ── Dashboard ────────────────────────────────────────────────────────────────────

def show_dashboard(session: Session):
    """Fetch and display dashboard directly from bridge — no LLM involved."""
    from datetime import datetime

    today = datetime.now().strftime("%Y-%m-%d")
    month = datetime.now().strftime("%Y-%m")
    today_label = datetime.now().strftime("%d %b %Y")
    month_label = datetime.now().strftime("%B %Y")

    try:
        daily = session.bridge.get_daily_summary(today)
        monthly = session.bridge.get_monthly_summary(month)

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

    except Exception as e:
        agent_error(f"Could not load dashboard: {str(e)}")


def show_budget(session: Session):
    """Display budget status directly from bridge."""
    from datetime import datetime
    import json
    from pathlib import Path

    month = datetime.now().strftime("%Y-%m")
    month_label = datetime.now().strftime("%B %Y")

    try:
        budget_file = Path(__file__).parent / "data" / f"budgets_{session.user_id}.json"
        if not budget_file.exists() or month not in json.loads(budget_file.read_text()):
            agent_info(f"No budgets set for {month_label}. Try: set food budget to 5000")
            return

        budgets = json.loads(budget_file.read_text()).get(month, {})
        monthly = session.bridge.get_monthly_summary(month)
        breakdown = monthly.get("breakdown", {})

        lines = []
        for category, limit in budgets.items():
            spent = breakdown.get(category, 0)
            percent = (spent / limit * 100) if limit > 0 else 0
            remaining = limit - spent
            bar = "█" * int(percent / 10) + "░" * (10 - int(percent / 10))

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

        console.print()
        console.print(Panel.fit(
            "\n".join(lines),
            title=f"[bold cyan]💰 Budget Status — {month_label}[/bold cyan]",
            border_style="blue",
            padding=(0, 2)
        ))
        console.print()

    except Exception as e:
        agent_error(f"Could not load budget: {str(e)}")


def show_categories(session: Session):
    """Display all categories directly from bridge."""
    try:
        categories = session.bridge.get_categories()
        income_cats = categories.get("income", [])
        expense_cats = categories.get("expense", [])

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

    except Exception as e:
        agent_error(f"Could not load categories: {str(e)}")


# ── Help ───────────────────────────────────────────────────────────────────────

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


# ── Login ──────────────────────────────────────────────────────────────────────

def handle_login() -> tuple[str, str]:
    """Handle login flow with max retry limit.

    Returns:
        Tuple of (username, user_id)
    """
    console.print("\n[bold cyan]🔑 Login to Finance Agent[/bold cyan]\n")

    for attempt in range(1, MAX_LOGIN_RETRIES + 1):
        console.print(f"[dim]Attempt {attempt}/{MAX_LOGIN_RETRIES}[/dim]")

        username = Prompt.ask("👤 Username").strip()
        password = Prompt.ask("🔒 Password", password=True).strip()

        if not username or not password:
            agent_error("Username and password cannot be empty.")
            continue

        agent_status("Verifying credentials")
        user_id = login(username, password)

        if user_id:
            agent_success(f"Welcome back, {username}!")
            return username, user_id
        else:
            agent_error("Invalid credentials. Please try again.")

    agent_error("Too many failed attempts. Exiting.")
    sys.exit()


# ── Commands ───────────────────────────────────────────────────────────────────

def handle_command(command: str, session: Session) -> bool:
    """Handle special commands.

    Args:
        command: Lowercased user input
        session: Current Session instance

    Returns:
        True if command was handled, False if should be sent to LLM
    """
    if command in ("exit", "quit", "bye"):
        agent_info(f"Goodbye, {session.username}! See you soon. 👋")
        sys.exit()

    if command == "help":
        print_help()
        return True

    if command == "clear":
        session.clear_history()
        agent_info("Conversation history cleared. Starting fresh.")
        return True

    if command == "history":
        if session.message_count <= 1:
            agent_info("No conversation history yet.")
        else:
            console.print()
            for msg in session.get_history():
                # skip system, tool messages — show only user and assistant
                if msg["role"] in ("system", "tool"):
                    continue
                role = msg["role"].upper()
                content = msg.get("content") or ""
                # skip assistant messages that only contain tool_calls
                if not isinstance(content, str) or not content.strip():
                    continue
                color = "cyan" if role == "USER" else "green"
                console.print(f"[bold {color}]{role}:[/bold {color}] {content[:300]}")
            console.print()
        return True

    if command == "dashboard":
        show_dashboard(session)
        return True

    if command == "budget":
        show_budget(session)
        return True

    if command == "categories":
        show_categories(session)
        return True

    return False


# ── Chat Loop ──────────────────────────────────────────────────────────────────

def _execute_pending(session: Session):
    action = session.state.confirm()
    if not action:
        return

    try:
        if action["action_type"] == "delete":
            result = session.bridge.delete_txn(action["txn_id"])
            msg = (
                f"Deleted — {action['description']}."
                if result["success"]
                else f"Failed — {result.get('error', 'transaction not found')}"
            )

        elif action["action_type"] == "update":
            result = session.bridge.update_txn(action["txn_id"], action["fields"])
            changes = ", ".join(f"{k} → {v}" for k, v in action["fields"].items())
            msg = (
                f"Updated — {action['description']}. Changed {changes}."
                if result["success"]
                else f"Failed — {result.get('error', 'transaction not found')}"
            )

        console.print()
        console.print("[bold green]Agent:[/bold green] ", end="")
        type_out(msg, color="white")
        console.print()

    except Exception as e:
        agent_error(f"Action failed: {str(e)}")



def chat_loop(session: Session):
    """Main conversation loop.

    Args:
        session: Current Session instance
    """
    console.print()
    console.print(Panel.fit(
        f"[bold green]Session started[/bold green] — logged in as "
        f"[bold cyan]{session.username}[/bold cyan]\n"
        "[dim]Type [bold]help[/bold] for commands or just start talking naturally[/dim]",
        box=box.ROUNDED,
        border_style="dim"
    ))
    console.print()

    while True:
        try:
            user_input = Prompt.ask("[bold cyan]You[/bold cyan]").strip()
            console.print()

            if not user_input:
                continue

            # ── AWAIT_SELECT — user picking number ────────────────
            if session.state.mode == "await_select":
                if user_input.strip().isdigit():
                    number = int(user_input.strip())
                    pending = session.state.select(number)
                    if pending:
                        console.print()
                        console.print("[bold green]Agent:[/bold green] ", end="")
                        if pending["action_type"] == "delete":
                            type_out(f"Delete {pending['description']}? Say yes to confirm.", color="white")
                        elif pending["action_type"] == "update":
                            changes = ", ".join(f"{k} → {v}" for k, v in pending["fields"].items())
                            type_out(f"Update {pending['description']} — change {changes}? Say yes to confirm.", color="white")
                        console.print()
                    else:
                        agent_error("Invalid number — pick from the list above.")
                elif handle_command(user_input.lower(), session):
                        pass
                else:
                    # user said something else — cancel state, send to LLM
                    session.state.reset()
                    with agent_thinking("Processing your request"):
                        response = core.run(user_input, session)
                    console.print()
                    console.print("[bold green]Agent:[/bold green] ", end="")
                    type_out(response, color="white")
                    console.print()
                continue

            # ── AWAIT_CONFIRM — user saying yes/no ────────────────
            if session.state.mode == "await_confirm":
                if user_input.lower() in ("yes", "y", "confirm", "ok", "sure", "do it"):
                    _execute_pending(session)
                elif user_input.lower() in ("no", "n", "cancel", "stop", "nope"):
                    session.state.cancel()
                    console.print()
                    console.print("[bold green]Agent:[/bold green] ", end="")
                    type_out("Cancelled — nothing changed.", color="white")
                    console.print()
                elif handle_command(user_input.lower(), session):
                        pass
                else:
                    console.print()
                    console.print("[bold green]Agent:[/bold green] ", end="")
                    type_out("Reply yes to confirm or no to cancel.", color="white")
                    console.print()
                continue

            # ── IDLE ──────────────────────────────────────────────
            if handle_command(user_input.lower(), session):
                continue

            # send to LLM
            with agent_thinking("Processing your request"):
                response = core.run(user_input, session)

            console.print()
            console.print("[bold green]Agent:[/bold green] ", end="")
            type_out(response, color="white")
            console.print()
            console.print()

        except KeyboardInterrupt:
            console.print()
            agent_info(f"Goodbye, {session.username}! 👋")
            sys.exit()


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    """Entry point — welcome, login, session setup, chat loop."""
    print_welcome()

    username, user_id = handle_login()

    bridge = ExpenseBridge(user_id)
    session = Session(user_id, username, bridge)
    session.add_system_prompt()

    chat_loop(session)


if __name__ == "__main__":
    main()
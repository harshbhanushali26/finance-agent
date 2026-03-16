"""main.py — CLI entry point for Finance Agent.

Handles welcome screen, login, session creation, and main chat loop.
Supports special commands for quick actions and navigation.
"""

import sys
from rich import box
from rich.panel import Panel
from rich.prompt import Prompt
from datetime import datetime

from agent import core
from agent.session import Session
from bridge.auth_helper import login
from bridge.expense_bridge import ExpenseBridge
from config import MAX_LOGIN_RETRIES, DEBUG
from agent.pattern_matcher import match as pm_match
from agent.cli import (
    agent_success, agent_info,
    agent_error, agent_status, agent_thinking, type_out, console
)

from agent.insights import run_all
from agent.utils import get_dashboard_data, get_categories_data, get_budget_data
from agent.cli import print_help, show_dashboard, show_categories, show_insights, print_welcome, show_budget



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
        console.print()

        if user_id:
            agent_success(f"Welcome back, {username}!")
            return username, user_id
        else:
            agent_error("Invalid credentials. Please try again.")

    agent_error("Too many failed attempts. Exiting.")
    sys.exit()


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
        data = get_dashboard_data(session)
        show_dashboard(data)
        return True

    if command == "budget":
        data = get_budget_data(session)
        show_budget(data)
        return True

    if command == "categories":
        data = get_categories_data(session)
        show_categories(data)
        return True

    if command == "insights":
        month = datetime.now().strftime("%Y-%m")
        insights = run_all(session.bridge, month)
        show_insights(insights)
        return True

    return False


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

    # insights alert
    from agent.insights import run_all
    month = datetime.now().strftime("%Y-%m")
    insights = run_all(session.bridge, month)
    if insights:
        console.print(
            f"[dim cyan]💡 {len(insights)} insight(s) this month — "
            f"type [bold]insights[/bold] to view[/dim cyan]"
        )
        console.print()


    if DEBUG: print(f"[STATE] mode: {session.state.mode}")
    while True:
        try:
            user_input = Prompt.ask("[bold cyan]You[/bold cyan]").strip()
            if DEBUG: print(f"[STATE] mode={session.state.mode} input={user_input!r}")
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
                    # if state is still idle after LLM — previous delete flow was cancelled
                    if session.state.mode == "idle":
                        console.print()
                        console.print("[dim]Previous selection cancelled. Start a new request.[/dim]")
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

            # Pattern matcher — try before LLM
            result = pm_match(user_input, session)
            if result["matched"]:
                console.print()
                console.print("[bold green]Agent:[/bold green] ", end="")
                type_out(result["response"], color="white")
                console.print()
                console.print()
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
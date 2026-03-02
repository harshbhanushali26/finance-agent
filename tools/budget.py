"""Budget tools — handler functions for setting and checking budgets.

Reads and writes data/budgets_u001.json directly — no ExpenseManager involved.
"""

import json
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent.parent / "data"


def _get_budget_filepath(user_id: str) -> Path:
    return DATA_DIR / f"budgets_{user_id}.json"


def _load_budgets(user_id: str) -> dict:
    filepath = _get_budget_filepath(user_id)
    if not filepath.exists():
        return {}
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}


def _save_budgets(user_id: str, budgets: dict):
    filepath = _get_budget_filepath(user_id)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(budgets, f, indent=4)


def set_budget(args: dict, session) -> str:
    """Handle set_budget tool call."""
    try:
        month = args.get("month") or datetime.now().strftime("%Y-%m")
        budgets = _load_budgets(session.user_id)

        if month not in budgets:
            budgets[month] = {}

        budgets[month][args["category"]] = float(args["limit"])
        _save_budgets(session.user_id, budgets)

        return f"Budget set — {args['category']} limit for {month}: ₹{args['limit']}"

    except Exception as e:
        return f"Error setting budget: {str(e)}"


def get_budget_status(args: dict, session) -> str:
    """Handle get_budget_status tool call."""
    try:
        month = args.get("month") or datetime.now().strftime("%Y-%m")
        budgets = _load_budgets(session.user_id)

        if month not in budgets or not budgets[month]:
            return f"No budgets set for {month}"

        summary = session.bridge.get_monthly_summary(month)
        breakdown = summary.get("breakdown", {})

        lines = []
        for category, limit in budgets[month].items():
            spent = breakdown.get(category, 0)
            remaining = limit - spent
            percent = (spent / limit * 100) if limit > 0 else 0
            status = "⚠️ Over budget" if spent > limit else f"{percent:.0f}% used"
            lines.append(f"{category}: spent ₹{spent} of ₹{limit} — {status}, remaining ₹{remaining}")

        return f"Budget status for {month} — " + " | ".join(lines)

    except Exception as e:
        return f"Error getting budget status: {str(e)}"


def check_overspend(args: dict, session) -> str:
    """Handle check_overspend tool call."""
    try:
        month = args.get("month") or datetime.now().strftime("%Y-%m")
        budgets = _load_budgets(session.user_id)

        if month not in budgets or not budgets[month]:
            return f"No budgets set for {month}"

        summary = session.bridge.get_monthly_summary(month)
        breakdown = summary.get("breakdown", {})

        over = []
        warning = []

        for category, limit in budgets[month].items():
            spent = breakdown.get(category, 0)
            percent = (spent / limit * 100) if limit > 0 else 0

            if spent > limit:
                over.append(f"{category}: ₹{spent} spent, ₹{limit} limit (over by ₹{spent - limit})")
            elif percent >= 80:
                warning.append(f"{category}: {percent:.0f}% used (₹{spent} of ₹{limit})")

        if not over and not warning:
            return f"All categories within budget for {month} ✅"

        result = []
        if over:
            result.append(f"Over budget — {', '.join(over)}")
        if warning:
            result.append(f"Near limit — {', '.join(warning)}")

        return " | ".join(result)

    except Exception as e:
        return f"Error checking overspend: {str(e)}"
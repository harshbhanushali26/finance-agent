"""Budget tools — LLM-callable handler functions for setting and checking budgets.

Reads and writes budget data via agent.utils helpers (_load_budgets, _save_budgets).
No ExpenseManager involved — budget data lives in data/budgets_{user_id}.json separately.

Functions:
    set_budget        — set monthly category budget limit
    get_budget_status — current usage vs limit per category
    check_overspend   — flag categories over or near limit
    suggest_budget    — recommend limits based on 3-month average
    _get_avg_spend    — internal helper for average category spend
"""

from datetime import datetime
from agent.utils import get_last_n_months, _save_budgets, _load_budgets, _get_budget_filepath



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


def _get_avg_spend(session, category: str, months: int = 3) -> float:
    """Get average monthly spend for a category over last N months."""
    past_months = get_last_n_months(months)
    totals = []
    for month in past_months:
        breakdown = session.bridge.get_category_breakdown("expense", month)
        amount = breakdown.get(category, 0)
        if amount > 0:
            totals.append(amount)
    return sum(totals) / len(totals) if totals else 0


def suggest_budget(args: dict, session) -> str:
    """Suggest budget amounts based on last 3 months average spend per category."""
    try:
        month = datetime.now().strftime("%Y-%m")
        categories = session.bridge.get_categories()
        expense_cats = categories.get("expense", [])

        suggestions = []
        for category in expense_cats:
            avg = _get_avg_spend(session, category)
            if avg > 0:
                # suggest 10% buffer over average
                suggested = round(avg * 1.1 / 100) * 100  # round to nearest 100
                suggestions.append(f"{category}: ₹{suggested:,.0f} (avg ₹{avg:,.0f}/month)")

        if not suggestions:
            return "Not enough history to suggest budgets — need at least 1 month of data"

        return "Suggested budgets based on last 3 months — " + " | ".join(suggestions)

    except Exception as e:
        return f"Error getting budget suggestions: {str(e)}"


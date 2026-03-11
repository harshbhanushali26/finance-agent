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


def _get_last_n_months(n: int = 3) -> list[str]:
    """Return last N month strings in YYYY-MM format."""
    from datetime import datetime
    today = datetime.now()
    months = []
    for i in range(1, n + 1):
        month_num = today.month - i
        year = today.year
        while month_num <= 0:
            month_num += 12
            year -= 1
        months.append(f"{year}-{month_num:02d}")
    return months


def _get_avg_spend(session, category: str, months: int = 3) -> float:
    """Get average monthly spend for a category over last N months."""
    past_months = _get_last_n_months(months)
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


def _carry_forward_budgets(user_id: str, session) -> list[str]:
    """On 1st of month, carry forward unused budget from previous month."""
    from datetime import datetime
    
    today = datetime.now()
    if today.day != 1:
        return []
    
    current_month = today.strftime("%Y-%m")
    # previous month
    prev_month_num = today.month - 1
    prev_year = today.year
    if prev_month_num == 0:
        prev_month_num = 12
        prev_year -= 1
    prev_month = f"{prev_year}-{prev_month_num:02d}"
    
    budgets = _load_budgets(user_id)
    
    # check if carry-forward already done this month
    carried_key = f"_carried_{current_month}"
    if budgets.get(carried_key):
        return []
    
    if prev_month not in budgets:
        return []
    
    prev_budgets = budgets[prev_month]
    prev_summary = session.bridge.get_monthly_summary(prev_month)
    prev_breakdown = prev_summary.get("breakdown", {})
    
    if current_month not in budgets:
        budgets[current_month] = {}
    
    carried = []
    for category, limit in prev_budgets.items():
        spent = prev_breakdown.get(category, 0)
        remaining = limit - spent
        if remaining > 0:
            current_limit = budgets[current_month].get(category, 0)
            budgets[current_month][category] = current_limit + remaining
            carried.append(f"{category}: +₹{remaining:,.0f}")
    
    if carried:
        budgets[carried_key] = True
        _save_budgets(user_id, budgets)
    
    return carried
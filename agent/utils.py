"""Shared utility functions for Finance Agent.

Data fetching, file I/O, and helper functions used across agent, cli, and tools layers.
No LLM calls, no Rich output — pure data operations only.

Functions:
    get_dashboard_data      — fetch daily + monthly summary for dashboard display
    get_budget_data         — fetch all budget data needed for budget display
    get_categories_data     — fetch income and expense categories
    get_budget_file_path    — return Path to budget file if month data exists
    get_last_n_months       — return last N month strings in YYYY-MM format
    _get_budget_filepath    — return Path to budget file for a user
    _load_budgets           — load budget JSON file for a user
    _save_budgets           — write budget JSON file for a user
    _carry_forward_budgets  — carry unused budget from previous month on 1st
"""
import json
from pathlib import Path
from calendar import monthrange
from datetime import date, datetime, timedelta

DATA_DIR = Path(__file__).parent.parent / "data"


def _get_budget_filepath(user_id: str) -> Path:
    """Return Path to budget JSON file for given user. File may not exist yet."""
    return DATA_DIR / f"budgets_{user_id}.json"


def _load_budgets(user_id: str) -> dict:
    """Load budget data from JSON file. Returns empty dict if file missing or corrupt."""
    filepath = _get_budget_filepath(user_id)
    if not filepath.exists():
        return {}
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}


def _save_budgets(user_id: str, budgets: dict):
    """Write budget data to JSON file. Creates parent directory if needed."""
    filepath = _get_budget_filepath(user_id)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(budgets, f, indent=4)


def get_dashboard_data(session):
    """Fetches data for dashboard"""
    today = datetime.now().strftime("%Y-%m-%d")
    month = datetime.now().strftime("%Y-%m")

    try:
        daily = session.bridge.get_daily_summary(today)
        monthly = session.bridge.get_monthly_summary(month)
        data = {
            "daily": daily,
            "monthly": monthly
        }

        return data

    except Exception:
        return None


def get_categories_data(session):
    """Fetches data for Categories"""
    try:
        categories = session.bridge.get_categories()
        return categories

    except Exception:
        return None


def get_budget_file_path(user_id, month) -> Path | None:
    """Returns Path to budget file if it exists and has data for given month, else None."""
    try:
        budget_file = Path(__file__).parent.parent / "data" / f"budgets_{user_id}.json"
        if not budget_file.exists():
            return None
        if month not in json.loads(budget_file.read_text()):
            return None
        return budget_file
    except Exception:
        return None


def get_budget_data(session) -> dict | None:
    """Fetch all data needed for budget display. Returns None on failure."""
    month      = datetime.now().strftime("%Y-%m")
    month_label = datetime.now().strftime("%B %Y")
    try:
        budget_file = get_budget_file_path(session.user_id, month)
        if not budget_file:
            return {"empty": True, "month_label": month_label}

        budgets = json.loads(budget_file.read_text()).get(month, {})
        monthly = session.bridge.get_monthly_summary(month)
        breakdown = monthly.get("breakdown", {})    

        # carry forward — reload budgets if anything was carried
        carried = _carry_forward_budgets(session.user_id, session)
        if carried:
            budgets = json.loads(budget_file.read_text()).get(month, {})

        # unbudgeted category reminder
        all_budgets = set(budgets.keys())
        unbudgeted = []
        for cat, amount in breakdown.items():
            if cat not in all_budgets and amount > 0:
                # count transactions for this category this month
                txns = session.bridge.filter_txn(type="expense", category=cat, month=month)
                if len(txns) >= 3:
                    unbudgeted.append(f"{cat} (₹{amount:,.0f} spent, {len(txns)} transactions)")

        # ── Date calculations ──────────────────────────────────────────────
        today = datetime.now()
        days_passed = today.day     # Date only i.e, 11 <- (2026-03-11)
        days_in_month = monthrange(today.year, today.month)[1]  # No of days in current month
        days_remaining = days_in_month - days_passed

        return {
            "empty":          False,
            "budgets":        budgets,
            "breakdown":      breakdown,
            "carried":        carried,        # list of strings — cli prints if non-empty
            "unbudgeted":     unbudgeted,  # list of strings — cli prints if non-empty
            "days_passed":    days_passed,
            "days_in_month":  days_in_month,
            "days_remaining": days_remaining,
            "month_label":    month_label,
            "today":          today,
        }

    except Exception:
        return None


# Doesn't return current month
def get_last_n_months(n: int = 3) -> list[str]:
    """Return last N month strings in YYYY-MM format, most recent first. Does not include current month."""
    months = []
    first_of_current = date.today().replace(day=1)
    for i in range(1, n + 1):
        # subtract i months by going back i times via first-of-month
        d = first_of_current
        for _ in range(i):
            d = (d - timedelta(days=1)).replace(day=1)
        months.append(d.strftime("%Y-%m"))
    return months


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
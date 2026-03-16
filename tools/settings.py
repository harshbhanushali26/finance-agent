"""Config tools — handler functions for user preferences and settings.

Reads and writes data/config_u001.json directly.
"""

import json
from pathlib import Path

from config import DEFAULT_CURRENCY, DEFAULT_BUDGET_WARNING_PERCENT, DEFAULT_LOW_BALANCE_ALERT

DATA_DIR = Path(__file__).parent.parent / "data"

def _get_config_filepath(user_id: str) -> Path:
    return DATA_DIR / f"config_{user_id}.json"


def _load_config(user_id: str) -> dict:
    filepath = _get_config_filepath(user_id)
    if not filepath.exists():
        return {
            "user_id": user_id,
            "monthly_income": 0,
            "currency": DEFAULT_CURRENCY,
            "monthly_budget": {"total": 0, "categories": {}},
            "alerts": {"budget_warning_percent": DEFAULT_BUDGET_WARNING_PERCENT, "low_balance_alert": DEFAULT_LOW_BALANCE_ALERT},
            "preferences": {"date_format": "DD-MM-YYYY"}
        }
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}


def _save_config(user_id: str, config: dict):
    filepath = _get_config_filepath(user_id)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(config, f, indent=4)


def get_config(args: dict, session) -> str:
    """Handle get_config tool call."""
    try:
        config = _load_config(session.user_id)

        return (
            f"Config for {session.username} — "
            f"Monthly income: ₹{config['monthly_income']}, "
            f"Currency: {config['currency']}, "
            f"Budget warning at: {config['alerts']['budget_warning_percent']}%, "
            f"Low balance alert: ₹{config['alerts']['low_balance_alert']}, "
            f"Date format: {config['preferences']['date_format']}"
        )

    except Exception as e:
        return f"Error getting config: {str(e)}"


def set_monthly_income(args: dict, session) -> str:
    """Handle set_monthly_income tool call."""
    try:
        config = _load_config(session.user_id)
        config["monthly_income"] = args["amount"]
        _save_config(session.user_id, config)

        return f"Monthly income updated to ₹{args['amount']}"

    except Exception as e:
        return f"Error setting monthly income: {str(e)}"


def set_preference(args: dict, session) -> str:
    """Handle set_preference tool call."""
    try:
        config = _load_config(session.user_id)
        config["preferences"][args["key"]] = args["value"]
        _save_config(session.user_id, config)

        return f"Preference updated — {args['key']}: {args['value']}"

    except Exception as e:
        return f"Error setting preference: {str(e)}"
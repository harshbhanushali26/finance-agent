"""App-wide configuration constants for Finance Agent.

All hardcoded values live here — import from this module instead of hardcoding
in core.py, session.py, or main.py.

Usage:
    from config import MODEL, DEBUG, MAX_TOOL_CALLS

Values can be overridden via .env for environment-specific behaviour.
"""
# ── App Config ──
MODEL = "openai/gpt-oss-20b"    # fallback: openai/gpt-oss-120b
DEBUG = False
MAX_TOOL_CALLS = 5
MAX_LOGIN_RETRIES = 3

# ── Session / Memory Config ──
MAX_HISTORY_MESSAGES = 20          # auto-clear threshold
TOOL_RESULTS_TO_KEEP = 4          # full tool results retained
TOOL_RESULT_TRIM_LENGTH = 60      # chars kept from old results

# ── User Defaults ──
DEFAULT_CURRENCY = "INR"
DEFAULT_BUDGET_WARNING_PERCENT = 80
DEFAULT_LOW_BALANCE_ALERT = 5000

"""
Pattern Matcher — Phase A
Intercepts simple user messages before they reach the LLM.

Match families:
    1. Add     — "add 250 food", "spent 2.5k on transport", "got 50000 salary"
    2. View    — "show this month", "transactions today", "list january"
    3. Balance — "balance", "my balance", "how much left"

Returns:
    {"matched": True,  "response": "<formatted string>"}
    {"matched": False}

If anything is ambiguous, returns {"matched": False} — LLM handles it.
"""

import re
import json
from datetime import date, timedelta
from calendar import month_name
from pathlib import Path


# ── Constants ──────────────────────────────────────────────────────────────────

INCOME_TRIGGERS  = {"got", "received", "income", "earned", "credited"}
EXPENSE_TRIGGERS = {"spent", "spend", "paid", "pay", "bought", "buy", "added", "add", "expense"}
ALL_TRIGGERS     = INCOME_TRIGGERS | EXPENSE_TRIGGERS

VIEW_TRIGGERS = {"show", "view", "list", "display", "see"}
VIEW_PHRASES  = {"what did i spend", "show me", "show my", "list my", "my transactions"}

BALANCE_PHRASES = {
    "balance", "my balance", "overview", "dashboard",
    "how much do i have", "how much left", "how much do i have left",
    "what's my balance", "whats my balance"
}

# Words that can never be a category
STOP_WORDS = {"a", "an", "the", "my", "me", "i", "it", "this", "that", "and", "in", "to"}

DATE_WORDS = {
    "today", "yesterday",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december"
}

ANALYTICS_KEYWORDS = {"top", "breakdown", "pattern", "analysis", "compare", "trend"}

REJECTED_CATEGORY_WORDS = STOP_WORDS | DATE_WORDS | ALL_TRIGGERS

# month name → zero-padded number
MONTH_MAP = {name.lower(): f"{i:02d}" for i, name in enumerate(month_name) if name}

DEBUG = False  # set False in production

# ── Public entry point ─────────────────────────────────────────────────────────

def match(user_message: str, session) -> dict:
    """
    Try to match user_message against known patterns.
    Returns {"matched": True, "response": str} or {"matched": False}.
    """
    original   = user_message.strip()
    normalized = original.lower()

    # Bail on question marks — likely a conversational query
    if "?" in original:
        if DEBUG: print("[PM] ✗ bail — question mark")
        return {"matched": False}

    # Bail on multi-clause messages
    if _has_multiple_clauses(normalized):
        if DEBUG: print("[PM] ✗ bail — multiple clauses")
        return {"matched": False}

    # Priority: balance → view → add
    if _is_balance_query(normalized):
        if DEBUG: print("[PM] ✓ matched — balance")
        return _handle_balance(session)

    if _is_view_query(normalized):
        if DEBUG: print("[PM] ✓ matched — view")
        return _handle_view(normalized, session)

    if _is_add_query(normalized):
        if DEBUG: print("[PM] ✓ matched — add")
        return _handle_add(original, normalized, session)

    if DEBUG: print("[PM] ✗ no match — falling to LLM")
    return {"matched": False}


# ── Guard helpers ──────────────────────────────────────────────────────────────

def _has_multiple_clauses(normalized: str) -> bool:
    clause_words = r"\b(but|although|however|also|and then|then delete|then update|except)\b"
    return bool(re.search(clause_words, normalized))


# ── Balance ────────────────────────────────────────────────────────────────────

def _is_balance_query(normalized: str) -> bool:
    return normalized in BALANCE_PHRASES


def _handle_balance(session) -> dict:
    try:
        today      = date.today()
        month_str  = today.strftime("%Y-%m")
        summary    = session.bridge.get_monthly_summary(month_str)
        currency   = _get_currency(session)

        income     = summary.get("income", 0)
        expenses   = summary.get("expense", 0)
        balance    = income - expenses
        month_label = today.strftime("%B %Y")

        response = (
            f"{month_label} — "
            f"Income: {currency}{income:,.0f}  |  "
            f"Expenses: {currency}{expenses:,.0f}  |  "
            f"Balance: {currency}{balance:,.0f}"
        )
        return {"matched": True, "response": response}
    except Exception:
        return {"matched": False}


# ── View ───────────────────────────────────────────────────────────────────────


def _is_view_query(normalized: str) -> bool:
    if any(word in normalized.split() for word in ANALYTICS_KEYWORDS):
        return False
    if any(normalized.startswith(t) for t in VIEW_TRIGGERS):
        return True
    if any(phrase in normalized for phrase in VIEW_PHRASES):
        return True
    if normalized in {"transactions", "my transactions", "this month", "last month"}:
        return True
    return False


def _handle_view(normalized: str, session) -> dict:
    try:
        period = _extract_period(normalized)
        if period is None:
            return {"matched": False}

        currency = _get_currency(session)

        if period["type"] == "day":
            day_str   = period["value"]
            summary   = session.bridge.get_daily_summary(day_str)
            label     = "Today" if day_str == str(date.today()) else "Yesterday"

            income    = summary.get("income", 0)
            expenses  = summary.get("expense", 0)
            txn_count = summary.get("num_income", 0) + summary.get("num_expense", 0)

            response = (
                f"{label} ({day_str}) — "
                f"Income: {currency}{income:,.0f}  |  "
                f"Expenses: {currency}{expenses:,.0f}  |  "
                f"{txn_count} transaction(s)"
            )
            return {"matched": True, "response": response}

        elif period["type"] == "month":
            month_str = period["value"]
            summary   = session.bridge.get_monthly_summary(month_str)
            year, mon = month_str.split("-")
            label     = f"{month_name[int(mon)]} {year}"

            income    = summary.get("income", 0)
            expenses  = summary.get("expense", 0)
            balance   = income - expenses
            txn_count = summary.get("num_income", 0) + summary.get("num_expense", 0)

            response = (
                f"{label} — "
                f"Income: {currency}{income:,.0f}  |  "
                f"Expenses: {currency}{expenses:,.0f}  |  "
                f"Balance: {currency}{balance:,.0f}  |  "
                f"{txn_count} transaction(s)"
            )
            return {"matched": True, "response": response}

    except Exception:
        return {"matched": False}

    return {"matched": False}


def _extract_period(normalized: str) -> dict | None:
    today = date.today()

    if "today" in normalized:
        return {"type": "day", "value": str(today)}

    if "yesterday" in normalized:
        return {"type": "day", "value": str(today - timedelta(days=1))}

    if "this month" in normalized or normalized in {"transactions", "my transactions"}:
        return {"type": "month", "value": today.strftime("%Y-%m")}

    if "last month" in normalized:
        first_of_this = today.replace(day=1)
        last_month    = first_of_this - timedelta(days=1)
        return {"type": "month", "value": last_month.strftime("%Y-%m")}

    # Month name — "january", "show february", "list march 2025"
    for mon_name, mon_num in MONTH_MAP.items():
        if mon_name in normalized:
            year_match = re.search(r"\b(20\d{2})\b", normalized)
            year       = year_match.group(1) if year_match else str(today.year)
            return {"type": "month", "value": f"{year}-{mon_num}"}

    # Reject anything with ambiguous time references
    ambiguous = r"\b(week|ago|recent|latest|past|monday|tuesday|wednesday|thursday|friday|saturday|sunday|last)\b"
    if re.search(ambiguous, normalized):
        return None

    # No date reference — default to this month
    return {"type": "month", "value": today.strftime("%Y-%m")}


# ── Add ────────────────────────────────────────────────────────────────────────

def _is_add_query(normalized: str) -> bool:
    first_word = normalized.split()[0] if normalized.split() else ""
    return first_word in ALL_TRIGGERS


def _handle_add(original: str, normalized: str, session) -> dict:
    try:
        # 1. Type — from normalized (trigger word is always lowercase)
        type_ = _extract_type(normalized)
        if type_ is None:
            if DEBUG: print("[PM] ✗ add — could not extract type")
            return {"matched": False}

        # 2. Amount — from normalized (digits are case-insensitive)
        amount = _extract_amount(normalized)
        if amount is None:
            if DEBUG: print("[PM] ✗ add — could not extract amount")
            return {"matched": False}

        # 3. Category — from original to preserve casing
        category = _extract_category(original)
        if category is None:
            if DEBUG: print("[PM] ✗ add — could not extract category")
            return {"matched": False}
        if DEBUG: print(f"[PM DEBUG] extracted category: '{category}'")

        # 4. Date — from normalized
        txn_date = _extract_date(normalized)
        if txn_date is None:
            if DEBUG: print("[PM] ✗ add — could not extract date (ambiguous)")
            return {"matched": False}

        # 5. Call bridge
        result = session.bridge.add_txn(
            type_=type_,
            amount=amount,
            category=category,
            date=txn_date,
        )

        if not result.get("success"):
            if DEBUG: print(f"[PM] ✗ add — bridge error: {result.get('error')}")
            return {"matched": False}

        if result.get("warning") and "Created new category" in result.get("warning", ""):
            if DEBUG: print(f"[PM] ✗ add — bridge created new category, falling to LLM")
            return {"matched": False}

        if not result:
            return {"matched": False}

        # 6. Format response
        currency      = _get_currency(session)
        month_str     = txn_date[:7]
        cat_breakdown = session.bridge.get_category_breakdown(type_, month=month_str)
        # category stored as title case by bridge (.strip().title())
        cat_total     = cat_breakdown.get(category.title(), 0)

        date_obj   = date.fromisoformat(txn_date)
        date_label = (
            "today"     if date_obj == date.today()
            else "yesterday" if date_obj == date.today() - timedelta(days=1)
            else date_obj.strftime("%b %d")
        )

        type_label = "income" if type_ == "income" else "expense"
        response   = (
            f"Added {currency}{amount:,.0f} for {category.title()} {date_label}. "
            f"{category.title()} {type_label} this month: {currency}{cat_total:,.0f}."
        )
        return {"matched": True, "response": response}

    except Exception as e:
        if DEBUG: print(f"[PM] ✗ exception in _handle_add: {e}")
        return {"matched": False}


def _extract_type(normalized: str) -> str | None:
    """
    Type is determined solely by the first word (the trigger).
    No secondary regex block — avoids priority conflicts.
    """
    first_word = normalized.split()[0] if normalized.split() else ""
    if first_word in INCOME_TRIGGERS:
        return "income"
    if first_word in EXPENSE_TRIGGERS:
        return "expense"
    return None


def _extract_amount(normalized: str) -> float | None:
    """
    Handles: 250, 2500, 2.5k, 2,500, 10k
    Does NOT handle word numbers — returns None → falls to LLM.
    """
    m = re.search(r"\b(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)([kK])?\b", normalized)
    if not m:
        return None

    raw    = m.group(1).replace(",", "")
    suffix = m.group(2)

    try:
        value = float(raw)
    except ValueError:
        return None

    if suffix and suffix.lower() == "k":
        value *= 1000

    return value if value > 0 else None


def _extract_category(original: str) -> str | None:
    """
    Extracts category from the ORIGINAL (casing-preserved) message.
    Strategy priority:
        1. After "for"  — "add 250 for Food"
        2. After "on"   — "spent 500 on Transport"
        3. After "from" — "got 50000 from Salary"
        4. After "as"   — "received 5000 as Bonus"
        5. Word immediately after the amount token

    Rejects: stop words, date words, trigger words.
    """
    # Work on lowercased copy only for matching positions,
    # but extract the word from original to preserve casing.
    normalized = original.lower()

    def is_valid(word: str) -> bool:
        return word.lower() not in REJECTED_CATEGORY_WORDS and word.isalpha()

    def has_next_content_word(text: str, match_end: int) -> bool:
        """Returns True if the word after match_end is a valid content word."""
        rest = text[match_end:].strip()
        next_m = re.match(r"([A-Za-z]+)", rest)
        return bool(next_m and is_valid(next_m.group(1)))

    # Strategies 1–4: preposition + next word
    for prep in ("for", "on", "from", "as"):
        pattern = rf"\b{prep}\s+([A-Za-z]+)\b"
        m = re.search(pattern, original, re.IGNORECASE)
        if m:
            word = m.group(1)
            if is_valid(word):
                if has_next_content_word(original, m.end()):
                    if DEBUG: print("[PM] ✗ add — multi-word category, falling to LLM")
                    return None
                return word

    # Strategy 5: word immediately after the amount token (in original)
    amount_pattern = r"\b\d[\d,\.]*[kK]?\b"
    m = re.search(rf"(?:{amount_pattern})\s+([A-Za-z]+)\b", original)
    if m:
        word = m.group(1)
        if is_valid(word):
            if has_next_content_word(original, m.end()):
                if DEBUG: print("[PM] ✗ add — multi-word category, falling to LLM")
                return None
            return word

    return None


def _extract_date(normalized: str) -> str | None:
    """
    Returns "YYYY-MM-DD". Defaults to today.
    Ambiguous references → None → fall to LLM.
    """
    today = date.today()

    if "yesterday" in normalized:
        return str(today - timedelta(days=1))

    # Explicit ISO date in message
    iso = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", normalized)
    if iso:
        return iso.group(1)

    # Reject ambiguous date references
    ambiguous = r"\b(last|next|previous|monday|tuesday|wednesday|thursday|friday|saturday|sunday|week|ago)\b"
    if re.search(ambiguous, normalized):
        return None

    return str(today)


# ── Config / Currency ──────────────────────────────────────────────────────────

def _get_currency(session) -> str:
    """
    Reads currency code from data/config_{user_id}.json directly.
    Falls back to ₹ if file missing or unreadable.
    """
    try:
        config_path = Path(f"data/config_{session.user_id}.json")
        if not config_path.exists():
            return "₹"
        with open(config_path) as f:
            config = json.load(f)
        symbol_map = {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥"}
        code = config.get("currency", "INR")
        return symbol_map.get(code, code + " ")
    except Exception:
        return "₹"
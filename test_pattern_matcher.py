"""
test_pattern_matcher.py — standalone tests for Phase A pattern matcher.
Run: python test_pattern_matcher.py

No pytest. No real data touched — bridge calls are mocked.
"""

import sys
from pathlib import Path
from datetime import date, timedelta

# ── Path setup ─────────────────────────────────────────────────────────────────
sys.path.append(str(Path(__file__).parent))

from agent.pattern_matcher import match


# ── Mock objects ───────────────────────────────────────────────────────────────

class MockBridge:
    """Minimal bridge mock — returns realistic responses without touching files."""

    def add_txn(self, type_, amount, category, date, description=None):
        return {"success": True, "warning": None}

    def get_monthly_summary(self, month):
        return {"income": 50000, "expense": 4000, "balance": 46000,
                "num_income": 1, "num_expense": 15, "carry_forward": 0}

    def get_daily_summary(self, date):
        return {"income": 0, "expense": 500, "balance": -500,
                "num_income": 0, "num_expense": 2, "carry_forward": 0}

    def get_category_breakdown(self, type_, month=None):
        return {"Food": 1200, "Transport": 500, "Salary": 50000}


class MockSession:
    user_id = "u001"
    bridge  = MockBridge()


session = MockSession()

# ── Test runner ────────────────────────────────────────────────────────────────

passed = 0
failed = 0

def run(label: str, message: str, expect_matched: bool, expect_in: str = None):
    """
    Run a single test case.
    label:          Short description
    message:        User input to test
    expect_matched: True if PM should handle it, False if should fall to LLM
    expect_in:      Optional string that must appear in response when matched
    """
    global passed, failed

    result = match(message, session)
    matched = result.get("matched", False)

    if matched != expect_matched:
        print(f"  FAIL  {label}")
        print(f"        input:    '{message}'")
        print(f"        expected: matched={expect_matched}")
        print(f"        got:      matched={matched}")
        failed += 1
        return

    if expect_matched and expect_in:
        response = result.get("response", "")
        if expect_in.lower() not in response.lower():
            print(f"  FAIL  {label}")
            print(f"        input:     '{message}'")
            print(f"        expect_in: '{expect_in}'")
            print(f"        response:  '{response}'")
            failed += 1
            return

    print(f"  PASS  {label}")
    passed += 1


# ── Test cases ─────────────────────────────────────────────────────────────────

def test_add_expense():
    print("\n── Add — expense triggers ────────────────────────────")
    run("add + amount + category",          "add 250 food",              True,  "Food")
    run("spent + on + category",            "spent 500 on transport",    True,  "Transport")
    run("paid + category",                  "paid 1200 rent",            True,  "Rent")
    run("bought + category",                "bought 150 groceries",      True,  "Groceries")
    run("add + 2.5k amount",               "add 2.5k electricity",      True,  "Electricity")
    run("add + comma amount",              "add 2,500 medicine",        True,  "Medicine")


def test_add_income():
    print("\n── Add — income triggers ─────────────────────────────")
    run("got + category",                   "got 50000 salary",          True,  "Salary")
    run("received + category",              "received 5000 bonus",       True,  "Bonus")
    run("earned + category",                "earned 2000 freelance",     True,  "Freelance")
    run("income keyword",                   "income 10000 consulting",   True,  "Consulting")


def test_add_with_date():
    print("\n── Add — with date ───────────────────────────────────")
    yesterday = str(date.today() - timedelta(days=1))
    run("expense yesterday",                "add 300 food yesterday",    True,  "Food")
    run("income yesterday",                 "got 1000 freelance yesterday", True, "Freelance")


def test_add_prepositions():
    print("\n── Add — preposition category extraction ─────────────")
    run("for + category",                   "add 300 for groceries",     True,  "Groceries")
    run("on + category",                    "spent 1000 on entertainment", True, "Entertainment")
    run("from + category (income)",         "got 50000 from salary",     True,  "Salary")
    run("as + category (income)",           "received 5000 as bonus",    True,  "Bonus")


def test_add_fallthrough():
    print("\n── Add — must fall to LLM ────────────────────────────")
    run("question mark",                    "add 250 food?",             False)
    run("multi-clause but",                 "add 250 food but update last one too", False)
    run("ambiguous date — last tuesday",    "add 250 food last tuesday", False)
    run("ambiguous date — last week",       "add 500 transport last week", False)
    run("no amount",                        "add food",                  False)
    run("word number",                      "add two fifty food",        False)
    run("multi-word category",              "add 739 electricity bill",  False)
    run("multi-word after for",             "add 500 for electricity bill", False)


def test_view():
    print("\n── View ──────────────────────────────────────────────")
    run("show this month",                  "show this month",           True)
    run("list this month",                  "list this month",           True)
    run("transactions keyword",             "transactions",              True)
    run("my transactions",                  "my transactions",           True)
    run("show today",                       "show today",                True,  "Today")
    run("show yesterday",                   "show yesterday",            True,  "Yesterday")
    run("month name — january",             "show january",              True,  "January")
    run("month name — february",            "list february",             True,  "February")
    run("month + year",                     "show march 2025",           True,  "2025")
    run("last month",                       "last month",                True)


def test_view_fallthrough():
    print("\n── View — must fall to LLM ───────────────────────────")
    run("last tuesday",                     "show last tuesday",         False)
    run("this week",                        "show this week",            False)
    run("last 7 days",                      "show last 7 days",          False)
    run("recent",                           "show recent transactions",  False)


def test_balance():
    print("\n── Balance ───────────────────────────────────────────")
    run("balance",                          "balance",                   True)
    run("my balance",                       "my balance",                True)
    run("how much left",                    "how much left",             True)
    run("how much do i have",               "how much do i have",        True)
    run("overview",                         "overview",                  True)


def test_llm_only():
    print("\n── Always LLM — conversational queries ───────────────")
    run("question about spending",          "how much did I spend on food?",     False)
    run("delete request",                   "delete last transaction",           False)
    run("update request",                   "update the rent entry",             False)
    run("top categories",                   "show my top categories",            False)
    run("pattern question",                 "what's my spending pattern?",       False)
    run("afford question",                  "can I afford a 5000 purchase?",     False)


# ── Run all ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 56)
    print("  Pattern Matcher — Phase A Tests")
    print("=" * 56)

    test_add_expense()
    test_add_income()
    test_add_with_date()
    test_add_prepositions()
    test_add_fallthrough()
    test_view()
    test_view_fallthrough()
    test_balance()
    test_llm_only()

    print()
    print("=" * 56)
    print(f"  Results: {passed} passed  |  {failed} failed  |  {passed + failed} total")
    print("=" * 56)
    print()

    sys.exit(0 if failed == 0 else 1)
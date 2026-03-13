"""
test_classifier.py — standalone tests for Phase B intent classifier.
Run: python test_classifier.py

No pytest. No real data.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from agent.classifier import classify_intent


# ── Test runner ────────────────────────────────────────────────────────────────

passed = 0
failed = 0


def run(label: str, message: str, expected: str):
    global passed, failed
    result = classify_intent(message)
    if result == expected:
        print(f"  PASS  {label}")
        passed += 1
    else:
        print(f"  FAIL  {label}")
        print(f"        input:    '{message}'")
        print(f"        expected: {expected}")
        print(f"        got:      {result}")
        failed += 1


# ── Test cases ─────────────────────────────────────────────────────────────────

def test_delete():
    print("\n── Delete ────────────────────────────────────────────")
    run("delete last transaction",        "delete last transaction",              "delete")
    run("remove food entry",              "remove my food entry",                 "delete")
    run("cancel last expense",            "cancel last expense",                  "delete")
    run("delete utilities expense",       "delete my last utilities expense",     "delete")
    run("delete specific date",           "delete the rent on march 1",           "delete")


def test_update():
    print("\n── Update ────────────────────────────────────────────")
    run("update rent amount",             "update my rent to 13000",              "update")
    run("change food entry",              "change the food entry to 500",         "update")
    run("edit last transaction",          "edit last transaction",                "update")
    run("fix the amount",                 "fix the amount for yesterday",         "update")
    run("correct salary entry",           "correct my salary entry",              "update")


def test_add():
    print("\n── Add ───────────────────────────────────────────────")
    run("add expense",                    "add 250 food",                         "add")
    run("spent on transport",             "spent 500 on transport",               "add")
    run("paid rent",                      "paid 12000 rent",                      "add")
    run("got salary",                     "got 50000 salary",                     "add")
    run("received bonus",                 "received 5000 bonus",                  "add")
    run("bought groceries",               "bought groceries for 300",             "add")
    run("earned freelance",               "earned 2000 from freelance",           "add")


def test_budget():
    print("\n── Budget ────────────────────────────────────────────")
    run("budget status",                  "show budget status",                   "budget")
    run("set budget",                     "set food budget to 5000",              "budget")
    run("am i over budget",               "am I over budget?",                    "budget")
    run("afford purchase",                "can I afford a 5000 purchase?",        "budget")
    run("overspending on food",           "am I overspending on food?",           "budget")


def test_settings():
    print("\n── Settings ──────────────────────────────────────────")
    run("set monthly income",             "set my monthly income to 50000",       "settings")
    run("change currency",                "change currency to USD",               "settings")
    run("update preference",              "update my preference",                 "settings")
    run("get config",                     "show my config",                       "settings")
    run("monthly income query",           "what is my monthly income",            "settings")


def test_analytics():
    print("\n── Analytics ─────────────────────────────────────────")
    run("top categories",                 "show my top 5 categories",             "analytics")
    run("category breakdown",             "show category breakdown",              "analytics")
    run("compare months",                 "compare this month and last month",    "analytics")
    run("spending pattern",               "what is my spending pattern?",         "analytics")
    run("spending trend",                 "show my spending trend",               "analytics")
    run("highest category",               "which category has highest spend?",    "analytics")


def test_view():
    print("\n── View ──────────────────────────────────────────────")
    run("show this month",                "show this month",                      "view")
    run("list transactions",              "list all transactions",                "view")
    run("show food expenses",             "show all food expenses",               "view")
    run("view last month",                "view last month transactions",         "view")
    run("how much spent on food",         "how much did I spend on food?",        "view")


def test_unknown():
    print("\n── Unknown ───────────────────────────────────────────")
    run("greeting",                       "hello",                                "unknown")
    run("general question",               "who are you?",                         "unknown")
    run("gibberish",                      "asdf qwer",                            "unknown")
    run("no match",                       "tell me something interesting",        "unknown")


def test_priority():
    print("\n── Priority — specific beats generic ─────────────────")
    run("delete beats view",              "show me what to delete",               "delete")
    run("update beats view",              "show transactions to update",          "update")
    run("budget beats view",              "show my budget",                       "budget")
    run("add beats analytics",            "got 50000 — what is the top category", "add")
    run("show expense — not add",         "show expense this month",              "view")
    run("show income — not add",          "show income this month",               "view")


# ── Run all ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 56)
    print("  Classifier — Phase B Tests")
    print("=" * 56)

    test_delete()
    test_update()
    test_add()
    test_budget()
    test_settings()
    test_analytics()
    test_view()
    test_unknown()
    test_priority()

    print()
    print("=" * 56)
    print(f"  Results: {passed} passed  |  {failed} failed  |  {passed + failed} total")
    print("=" * 56)
    print()

    sys.exit(0 if failed == 0 else 1)
"""
test_insights.py — standalone tests for v1.4 pattern detectors.
Run: python tests/test_insights.py
No pytest. MockBridge returns controlled data.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from agent.insights import (
    detect_spending_spikes,
    detect_subscriptions,
    detect_weekend_vs_weekday,
    detect_time_of_month,
    detect_lifestyle_inflation,
    detect_new_categories,
    run_all,
)

passed = 0
failed = 0

def check(label: str, result: list, expect_match: bool, expect_in: str = None):
    global passed, failed
    has_results = len(result) > 0

    if has_results != expect_match:
        print(f"  FAIL  {label}")
        print(f"        expected insights: {expect_match}")
        print(f"        got:               {result}")
        failed += 1
        return

    if expect_match and expect_in:
        combined = " ".join(result).lower()
        if expect_in.lower() not in combined:
            print(f"  FAIL  {label}")
            print(f"        expect_in: '{expect_in}'")
            print(f"        got:       {result}")
            failed += 1
            return

    print(f"  PASS  {label}")
    passed += 1


# ── Mock Bridge ────────────────────────────────────────────────────────────────

class SpikeMockBridge:
    def get_category_breakdown(self, type_, month=None):
        if month == "2026-03":
            return {"Food": 3000, "Transport": 500}
        return {"Food": 1000, "Transport": 500}  # past months

    def filter_txn(self, **kwargs): return {}
    def get_monthly_summary(self, month): return {"expense": 0}


class SubscriptionMockBridge:
    def get_category_breakdown(self, type_, month=None): return {}
    def filter_txn(self, **kwargs):
        # same amount ₹370 Entertainment in all 3 months
        class T:
            def __init__(self, cat, amt, d):
                self.category = cat; self.amount = amt; self.date = d; self.type = "expense"
        return {
            "1": T("Entertainment", 370, "2026-01-10"),
            "2": T("Entertainment", 370, "2026-02-10"),
            "3": T("Entertainment", 370, "2026-03-10"),
        }
    def get_monthly_summary(self, month): return {"expense": 0}


class WeekendMockBridge:
    def get_category_breakdown(self, type_, month=None): return {}
    def get_monthly_summary(self, month): return {"expense": 0}
    def filter_txn(self, **kwargs):
        class T:
            def __init__(self, amt, d):
                self.amount = amt; self.date = d; self.type = "expense"; self.category = "Food"
        return {
            "1": T(500, "2026-03-07"),  # Saturday
            "2": T(500, "2026-03-08"),  # Sunday
            "3": T(100, "2026-03-09"),  # Monday
            "4": T(100, "2026-03-10"),  # Tuesday
            "5": T(100, "2026-03-11"),  # Wednesday
        }


class TimeOfMonthMockBridge:
    def get_category_breakdown(self, type_, month=None): return {}
    def get_monthly_summary(self, month): return {"expense": 0}
    def filter_txn(self, **kwargs):
        class T:
            def __init__(self, amt, d):
                self.amount = amt; self.date = d; self.type = "expense"; self.category = "Food"
        return {
            "1": T(100, "2026-03-05"),
            "2": T(100, "2026-03-08"),
            "3": T(2000, "2026-03-25"),
            "4": T(2000, "2026-03-28"),
        }


class InflationMockBridge:
    def get_category_breakdown(self, type_, month=None): return {}
    def filter_txn(self, **kwargs): return {}
    def get_monthly_summary(self, month):
        data = {
            "2025-12": {"expense": 3000},
            "2026-01": {"expense": 3500},
            "2026-02": {"expense": 4000},
            "2026-03": {"expense": 5000},
        }
        return data.get(month, {"expense": 0})


class NewCatMockBridge:
    def get_category_breakdown(self, type_, month=None):
        if month == "2026-03":
            return {"Food": 500, "Health": 200, "Travel": 100}
        return {"Food": 500}
    def filter_txn(self, **kwargs): return {}
    def get_monthly_summary(self, month): return {"expense": 0}


class EmptyMockBridge:
    def get_category_breakdown(self, type_, month=None): return {}
    def filter_txn(self, **kwargs): return {}
    def get_monthly_summary(self, month): return {"expense": 0}


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_spending_spikes():
    print("\n── Spending Spike ────────────────────────────────────")
    check("food 3x spike detected",
          detect_spending_spikes(SpikeMockBridge(), "2026-03"),
          True, "food")
    check("no spike — empty data",
          detect_spending_spikes(EmptyMockBridge(), "2026-03"),
          False)


def test_subscriptions():
    print("\n── Subscription Creep ────────────────────────────────")
    check("entertainment recurring 3 months",
          detect_subscriptions(SubscriptionMockBridge(), "2026-03"),
          True, "entertainment")
    check("no subscription — empty data",
          detect_subscriptions(EmptyMockBridge(), "2026-03"),
          False)


def test_weekend_vs_weekday():
    print("\n── Weekend vs Weekday ────────────────────────────────")
    check("weekend spend higher",
          detect_weekend_vs_weekday(WeekendMockBridge(), "2026-03"),
          True, "weekend")
    check("no data — empty",
          detect_weekend_vs_weekday(EmptyMockBridge(), "2026-03"),
          False)


def test_time_of_month():
    print("\n── Time of Month ─────────────────────────────────────")
    check("most spend in last 10 days",
          detect_time_of_month(TimeOfMonthMockBridge(), "2026-03"),
          True, "last")
    check("no data — empty",
          detect_time_of_month(EmptyMockBridge(), "2026-03"),
          False)


def test_lifestyle_inflation():
    print("\n── Lifestyle Inflation ───────────────────────────────")
    check("expenses grew 66% over 3 months",
          detect_lifestyle_inflation(InflationMockBridge(), "2026-03"),
          True, "grew")
    check("no data — empty",
          detect_lifestyle_inflation(EmptyMockBridge(), "2026-03"),
          False)


def test_new_categories():
    print("\n── New Categories ────────────────────────────────────")
    check("health and travel are new",
          detect_new_categories(NewCatMockBridge(), "2026-03"),
          True, "first time")
    check("no new categories — empty",
          detect_new_categories(EmptyMockBridge(), "2026-03"),
          False)


def test_run_all():
    print("\n── run_all ───────────────────────────────────────────")
    check("run_all returns insights",
          run_all(SpikeMockBridge(), "2026-03"),
          True)
    check("run_all empty — no data",
          run_all(EmptyMockBridge(), "2026-03"),
          False)


# ── Run ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 56)
    print("  Insights — v1.4 Pattern Detection Tests")
    print("=" * 56)

    test_spending_spikes()
    test_subscriptions()
    test_weekend_vs_weekday()
    test_time_of_month()
    test_lifestyle_inflation()
    test_new_categories()
    test_run_all()

    print()
    print("=" * 56)
    print(f"  Results: {passed} passed  |  {failed} failed  |  {passed + failed} total")
    print("=" * 56)
    print()

    sys.exit(0 if failed == 0 else 1)
from datetime import date, datetime, timedelta

from agent.utils import get_last_n_months

# Detector 1 — spending spikes
def detect_spending_spikes(bridge, month: str) -> list[str]:
    """Detect categories where current month spend is 2x higher than 3-month average."""
    try:
        past_months = get_last_n_months(3)

        # collect breakdown for each past month
        past_breakdowns = []
        for m in past_months:
            breakdown = bridge.get_category_breakdown("expense", month=m)
            past_breakdowns.append(breakdown)

        # need at least 2 months of history
        months_with_data = [b for b in past_breakdowns if b]
        if len(months_with_data) < 2:
            return []

        current_breakdown = bridge.get_category_breakdown("expense", month=month)
        if not current_breakdown:
            return []

        insights = []
        for category, current_amt in current_breakdown.items():
            # get amount for this category across past months
            past_amounts = [b.get(category, 0) for b in past_breakdowns]
            past_avg = sum(past_amounts) / len(past_breakdowns)

            # skip if no historical spend in this category
            if past_avg == 0:
                continue

            ratio = current_amt / past_avg
            if ratio >= 2.0:
                insights.append(
                    f"⚠ {category} spend (₹{current_amt:,.0f}) is "
                    f"{ratio:.1f}x your 3-month average (₹{past_avg:,.0f})"
                )

        return insights

    except Exception:
        return []


# Detector 2 — subscription creep
def detect_subscriptions(bridge, month: str) -> list[str]:
    """Detect recurring transactions — same category + similar amount for 3 months."""
    try:
        past_months = get_last_n_months(3)
        if len(past_months) < 3:
            return []

        # fetch raw transactions for each of last 3 months
        monthly_txns = []
        for m in past_months:
            txns = bridge.filter_txn(type="expense", month=m)
            monthly_txns.append(txns)

        # need data in all 3 months
        if any(len(t) == 0 for t in monthly_txns):
            return []

        # group by category → list of amounts per month
        # {category: [amt_month1, amt_month2, amt_month3]}
        cat_amounts = {}
        for month_data in monthly_txns:
            seen_cats = {}
            for txn in month_data.values():
                cat = txn.category
                # sum per category per month
                seen_cats[cat] = seen_cats.get(cat, 0) + txn.amount
            for cat, amt in seen_cats.items():
                if cat not in cat_amounts:
                    cat_amounts[cat] = []
                cat_amounts[cat].append(amt)

        insights = []
        for category, amounts in cat_amounts.items():
            # must appear in all 3 months
            if len(amounts) < 3:
                continue

            # check if amounts are within 5% of each other
            min_amt = min(amounts)
            max_amt = max(amounts)
            if min_amt == 0:
                continue

            variation = (max_amt - min_amt) / min_amt
            if variation <= 0.05:
                avg_amt = sum(amounts) / len(amounts)
                insights.append(
                    f"↻ Possible subscription: ₹{avg_amt:,.0f} {category} "
                    f"— recurring for 3 months"
                )

        return insights

    except Exception:
        return []


# Detector 3 — weekend vs weekday
def detect_weekend_vs_weekday(bridge, month: str) -> list[str]:
    """Compare average daily spend on weekends vs weekdays."""
    try:
        from calendar import monthrange
        from datetime import datetime

        txns = bridge.filter_txn(type="expense", month=month)
        if not txns:
            return []

        weekend_total  = 0.0
        weekday_total  = 0.0

        for txn in txns.values():
            day = datetime.strptime(txn.date, "%Y-%m-%d").weekday()
            if day >= 5:  # 5=Saturday, 6=Sunday
                weekend_total += txn.amount
            else:
                weekday_total += txn.amount

        # count actual weekend days and weekday days in month
        year, mon = int(month[:4]), int(month[5:])
        total_days = monthrange(year, mon)[1]

        weekend_days = sum(
            1 for d in range(1, total_days + 1)
            if datetime(year, mon, d).weekday() >= 5
        )
        weekday_days = total_days - weekend_days

        if weekend_days == 0 or weekday_days == 0:
            return []

        daily_weekend = weekend_total / weekend_days
        daily_weekday = weekday_total / weekday_days

        if daily_weekday == 0:
            return []

        ratio = daily_weekend / daily_weekday
        if ratio >= 1.5:
            return [
                f"📅 You spend {ratio:.1f}x more on weekends "
                f"(₹{daily_weekend:,.0f}/day vs ₹{daily_weekday:,.0f}/day weekdays)"
            ]

        return []

    except Exception:
        return []


# Detector 4 — time of month
def detect_time_of_month(bridge, month: str) -> list[str]:
    """Detect which third of the month has highest spending."""
    try:
        from calendar import monthrange

        txns = bridge.filter_txn(type="expense", month=month)
        if not txns:
            return []

        year, mon  = int(month[:4]), int(month[5:])
        total_days = monthrange(year, mon)[1]
        last_day   = total_days

        part1 = 0.0  # days 1–10
        part2 = 0.0  # days 11–20
        part3 = 0.0  # days 21–end

        for txn in txns.values():
            day = int(txn.date[8:10])
            if day <= 10:
                part1 += txn.amount
            elif day <= 20:
                part2 += txn.amount
            else:
                part3 += txn.amount

        total = part1 + part2 + part3
        if total == 0:
            return []

        parts = {
            "first 10 days":  part1,
            "middle 10 days": part2,
            f"last {last_day - 20} days": part3,
        }

        max_part  = max(parts, key=parts.get)
        max_amt   = parts[max_part]
        pct       = (max_amt / total) * 100

        if pct >= 50:
            return [
                f"📆 {pct:.0f}% of your spending happens in the {max_part} of the month"
            ]

        return []

    except Exception:
        return []


# Detector 5 — lifestyle inflation
def detect_lifestyle_inflation(bridge, month: str) -> list[str]:
    """Detect month-over-month expense growth trend."""
    try:
        past_months = get_last_n_months(3)
        if len(past_months) < 2:
            return []

        # collect expenses oldest → newest
        # past_months is most-recent-first, so reverse
        months_ordered = list(reversed(past_months)) + [month]

        expenses = []
        for m in months_ordered:
            summary = bridge.get_monthly_summary(m)
            expenses.append(summary.get("expense", 0))

        # need at least 2 months with actual data
        months_with_data = [e for e in expenses if e > 0]
        if len(months_with_data) < 2:
            return []

        oldest = expenses[0]
        newest = expenses[-1]

        if oldest == 0:
            return []

        overall_growth = (newest - oldest) / oldest * 100

        if overall_growth >= 10:
            # build trend string
            month_labels = [m for m in months_ordered]
            trend_parts  = [f"₹{e:,.0f}" for e in expenses if e > 0]
            trend_str    = " → ".join(trend_parts)
            return [
                f"📈 Monthly expenses grew {overall_growth:.0f}% over last 3 months "
                f"({trend_str})"
            ]

        return []

    except Exception:
        return []


# Detector 6 — new categories
def detect_new_categories(bridge, month: str) -> list[str]:
    """Detect expense categories that appear this month but not last month."""
    try:
        past_months   = get_last_n_months(1)
        last_month    = past_months[0]

        this_cats = set(bridge.get_category_breakdown("expense", month=month).keys())
        last_cats = set(bridge.get_category_breakdown("expense", month=last_month).keys())

        new_cats = this_cats - last_cats
        if not new_cats:
            return []

        cats_str = ", ".join(sorted(new_cats))
        count    = len(new_cats)
        label    = "category" if count == 1 else "categories"
        return [
            f"🆕 First time spending this month on: {cats_str}"
        ]

    except Exception:
        return []


def run_all(bridge, month: str) -> list[str]:
    """Run all detectors and return combined insights."""
    detectors = [
        detect_spending_spikes,
        detect_subscriptions,
        detect_weekend_vs_weekday,
        detect_time_of_month,
        detect_lifestyle_inflation,
        detect_new_categories,
    ]

    insights = []
    for detector in detectors:
        try:
            results = detector(bridge, month)
            insights.extend(results)
        except Exception:
            continue

    return insights



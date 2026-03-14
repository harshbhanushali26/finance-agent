from datetime import date, timedelta


# Doesn't return current month
def get_last_n_months(n: int = 3) -> list[str]:
    """Return last N month strings in YYYY-MM format, most recent first."""
    months = []
    first_of_current = date.today().replace(day=1)
    for i in range(1, n + 1):
        # subtract i months by going back i times via first-of-month
        d = first_of_current
        for _ in range(i):
            d = (d - timedelta(days=1)).replace(day=1)
        months.append(d.strftime("%Y-%m"))
    return months
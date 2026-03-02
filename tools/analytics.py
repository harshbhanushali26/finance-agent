"""Analytics tools — handler functions for summaries and category breakdowns.

All operations go through session.bridge — never call ExpenseManager directly.
"""

from datetime import datetime


def get_daily_summary(args: dict, session) -> str:
    """Handle get_daily_summary tool call."""
    try:
        summary = session.bridge.get_daily_summary(args["date"])

        return (
            f"Daily summary for {args['date']} — "
            f"Income: ₹{summary['income']}, "
            f"Expense: ₹{summary['expense']}, "
            f"Balance: ₹{summary['balance']}, "
            f"Carry Forward: ₹{summary['carry_forward']}, "
            f"Transactions: {summary['num_income']} income, {summary['num_expense']} expense, "
            f"Breakdown: {summary['breakdown']}"
        )

    except Exception as e:
        return f"Error getting daily summary: {str(e)}"


def get_monthly_summary(args: dict, session) -> str:
    """Handle get_monthly_summary tool call."""
    try:
        summary = session.bridge.get_monthly_summary(args["month"])

        return (
            f"Monthly summary for {args['month']} — "
            f"Income: ₹{summary['income']}, "
            f"Expense: ₹{summary['expense']}, "
            f"Balance: ₹{summary['balance']}, "
            f"Carry Forward: ₹{summary['carry_forward']}, "
            f"Transactions: {summary['num_income']} income, {summary['num_expense']} expense, "
            f"Category breakdown: {summary['breakdown']}"
        )

    except Exception as e:
        return f"Error getting monthly summary: {str(e)}"


def get_category_breakdown(args: dict, session) -> str:
    """Handle get_category_breakdown tool call."""
    try:
        breakdown = session.bridge.get_category_breakdown(args["type_"])

        if not breakdown:
            return f"No {args['type_']} transactions found"

        lines = [f"{category}: ₹{amount}" for category, amount in breakdown.items()]
        return f"{args['type_'].capitalize()} breakdown — " + ", ".join(lines)

    except Exception as e:
        return f"Error getting category breakdown: {str(e)}"


def get_top_categories(args: dict, session) -> str:
    """Handle get_top_categories tool call."""
    try:
        top_n = args.get("top_n", 5)
        categories = session.bridge.get_top_categories(args["month"], top_n)

        if not categories:
            return f"No expense data found for {args['month']}"

        lines = [f"{i+1}. {cat}: ₹{amount}" for i, (cat, amount) in enumerate(categories)]
        return f"Top {top_n} expense categories for {args['month']} — " + ", ".join(lines)

    except Exception as e:
        return f"Error getting top categories: {str(e)}"


def get_categories(args: dict, session) -> str:
    """Handle get_categories tool call — returns all category names."""
    try:
        categories = session.bridge.get_categories()
        income = ", ".join(categories.get("income", []))
        expense = ", ".join(categories.get("expense", []))
        return f"Income categories: {income} | Expense categories: {expense}"
    except Exception as e:
        return f"Error getting categories: {str(e)}"
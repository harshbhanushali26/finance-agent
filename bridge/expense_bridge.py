"""ExpenseBridge — single connection point between finance-agent and expense-tracker.

All tools must call bridge methods only. Never import from expense-tracker directly
outside this file.
"""

import sys
from pathlib import Path

# To get path of expense-tracker folder (root)
EXPENSE_TRACKER_PATH = Path(__file__).parent.parent.parent / "expense-tracker"
sys.path.append(str(EXPENSE_TRACKER_PATH))

# Override hardcoded paths BEFORE importing any expense-tracker modules
import utils.json_io as json_io       # type: ignore
import utils.auth as auth_module      # type: ignore

# data path of expense-tracker for getting user/txn files
DATA_PATH = EXPENSE_TRACKER_PATH / "data"

# for load and save
json_io.DATA_DIR = DATA_PATH
json_io.USERS_FILE = DATA_PATH / "users.json"  

# for auth -> login 
auth_module.USERS_FILE = DATA_PATH / "users.json"

# all required imports from expense-tracker
from core.manager import ExpenseManager          # type: ignore
from core.transaction import Transaction         # type: ignore
from core.category import CategoryManager        # type: ignore
from utils.filtering import filter_by_criteria   # type: ignore



class ExpenseBridge:
    """Bridge between finance-agent tools and expense-tracker core logic.
    
    Creates and holds ExpenseManager and CategoryManager instances for a
    single user. All CRUD and analytics operations go through this class.
    """


    def __init__(self, user_id: str):
        """Initialize bridge with user-specific manager instances.
        
        Args:
            user_id: Unique user identifier e.g. 'u001'
        """
        file_path = DATA_PATH / f"transactions_{user_id}.json"
        self.manager = ExpenseManager(file_path)
        self.category_manager = CategoryManager(user_id)
        self.user_id = user_id


    # ── CRUD Operations ────────────────────────────────────────────────────────

    def add_txn(self, type_: str, amount: float, category: str, date: str, description: str = None) -> bool:
        """Add a new transaction. Auto-creates category if it doesn't exist.
        
        Args:
            type_:       'income' or 'expense'
            amount:      Transaction amount
            category:    Category name
            date:        Date string in YYYY-MM-DD format
            description: Optional description
            
        Returns:
            True if added successfully, False otherwise
        """

        category = category.strip().title()
        valid_categories = (
            self.category_manager.get_income_categories()
            if type_ == "income"
            else self.category_manager.get_expense_categories()
        )

        if category not in valid_categories:
            self.category_manager.add_category(type_, category)

        txn = Transaction(type_, amount, category, date, description=description)
        return self.manager.add_transaction(txn)


    def update_txn(self, txn_id: str, fields: dict) -> bool:
        """Update specific fields of an existing transaction.
        
        Args:
            txn_id: Transaction UUID
            fields: Dict of only the fields to change e.g. {"amount": 300}
            
        Returns:
            True if updated, False if txn_id not found
        """
        return self.manager.update_transaction(txn_id, fields)


    def delete_txn(self, txn_id: str) -> bool:
        """Delete a transaction by ID.
        
        Args:
            txn_id: Transaction UUID
            
        Returns:
            True if deleted, False if txn_id not found
        """
        return self.manager.delete_transaction(txn_id)


    def filter_txn(self, **kwargs) -> dict:
        """Filter transactions by any combination of criteria.
        
        Kwargs:
            type:      'income' or 'expense'
            category:  Category name
            date:      Exact date YYYY-MM-DD
            from_date: Start of date range YYYY-MM-DD
            to_date:   End of date range YYYY-MM-DD
            month:     Month string YYYY-MM
            
        Returns:
            Dict of {txn_id: Transaction} matching criteria
        """
        return filter_by_criteria(self.manager.transactions, **kwargs)


    # ── Category Operations ────────────────────────────────────────────────────

    def get_categories(self) -> dict:
        """Return all categories for this user.
        
        Returns:
            Dict with 'income' and 'expense' lists
        """
        return self.category_manager.view_categories()


    def add_category(self, type_: str, name: str) -> bool:
        """Add a new custom category.
        
        Args:
            type_: 'income' or 'expense'
            name:  Category name
            
        Returns:
            True if added, False if already exists
        """
        return self.category_manager.add_category(type_, name)


    # ── Analytics ─────────────────────────────────────────────────────────────

    def get_monthly_summary(self, month: str) -> dict:
        """Get income, expense, balance summary for a month.
        
        Args:
            month: Month string e.g. '2026-02'
            
        Returns:
            Dict with income, expense, balance, carry_forward, breakdown
        """
        return self.manager.get_monthly_summary(month)


    def get_daily_summary(self, date: str) -> dict:
        """Get income, expense, balance summary for a single day.
        
        Args:
            date: Date string e.g. '2026-02-27'
            
        Returns:
            Dict with income, expense, balance, carry_forward, breakdown
        """
        return self.manager.get_daily_summary(date)


    def get_category_breakdown(self, type_: str) -> dict:
        """Get total amount spent per category for a transaction type.
        
        Args:
            type_: 'income' or 'expense'
            
        Returns:
            Dict of {category: total_amount}
        """
        return self.manager.get_category_breakdown(type_)


    def get_top_categories(self, month: str, top_n: int = 5) -> list:
        """Get top N expense categories for a month by total amount.
        
        Args:
            month: Month string e.g. '2026-02'
            top_n: Number of top categories to return (default 5)
            
        Returns:
            List of (category, total) tuples sorted descending
        """
        return self.manager.get_top_categories(month, top_n)


    def get_monthly_transactions(self, month: str) -> list:
        """Get all transactions for a given month.
        
        Args:
            month: Month string e.g. '2026-02'
            
        Returns:
            List of Transaction objects
        """
        return self.manager.get_monthly_transactions(month)




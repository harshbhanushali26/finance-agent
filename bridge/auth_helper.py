"""auth_helper.py — wraps login and signup from expense-tracker utils/auth.py"""

from utils.auth import login as _login, signup as _signup   # type: ignore


def login(username: str, password: str) -> str | None:
    """Verify credentials and return user_id if valid.
    
    Args:
        username: Plain text username
        password: Plain text password
        
    Returns:
        user_id string e.g. 'u001' if valid, None if invalid
    """
    try:
        return _login(username, password)
    except Exception:
        return None


def signup(username: str, password: str) -> str | None:
    """Create new user account and return user_id.
    
    Args:
        username: Plain text username
        password: Plain text password
        
    Returns:
        user_id string if created, None if username already exists
    """
    try:
        return _signup(username, password)
    except Exception:
        return None
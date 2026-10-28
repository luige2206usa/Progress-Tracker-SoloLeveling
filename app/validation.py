from datetime import datetime


def is_valid_date(text):
    """Return True if text looks like YYYY-MM-DD and is a real date."""
    try:
        datetime.strptime(text, "%Y-%m-%d")
        return True
    except ValueError:
        return False
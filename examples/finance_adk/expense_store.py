"""
Finance Agent Demo - Local Expense Store

Stores expense records in a local JSON file. No external database needed.
Each record: {id, date, amount, category, note, created_at}
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import config


def _load() -> list[dict]:
    """Load all expenses from JSON file."""
    if not config.EXPENSES_FILE.exists():
        return []
    try:
        with open(config.EXPENSES_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def _save(expenses: list[dict]):
    """Save expenses to JSON file."""
    with open(config.EXPENSES_FILE, "w", encoding="utf-8") as f:
        json.dump(expenses, f, ensure_ascii=False, indent=2)


def add_expense(amount: float, category: str, note: str = "",
                date: Optional[str] = None) -> dict:
    """Add a single expense record."""
    record = {
        "id": str(uuid.uuid4())[:8],
        "date": date or datetime.now().strftime("%Y-%m-%d"),
        "amount": round(amount, 2),
        "category": category,
        "note": note,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    expenses = _load()
    expenses.append(record)
    _save(expenses)
    return record


def query(start_date: Optional[str] = None,
          end_date: Optional[str] = None,
          category: Optional[str] = None) -> list[dict]:
    """Query expenses by date range and/or category."""
    expenses = _load()
    result = expenses
    if start_date:
        result = [e for e in result if e["date"] >= start_date]
    if end_date:
        result = [e for e in result if e["date"] <= end_date]
    if category:
        result = [e for e in result if e["category"] == category]
    return result


def get_period_data(period: str = "this_month") -> list[dict]:
    """Get expenses for a named period (this_month, last_month, all)."""
    now = datetime.now()
    if period == "this_month":
        start = now.strftime("%Y-%m-01")
        return query(start_date=start)
    elif period == "last_month":
        # Previous calendar month
        from datetime import timedelta
        last_month_start = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
        return query(
            start_date=last_month_start.strftime("%Y-%m-%d"),
            end_date=(now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m-%d"),
        )
    else:  # "all"
        return _load()
    
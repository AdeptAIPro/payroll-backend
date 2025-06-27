from typing import Dict, Any, Optional, List
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta
import uuid
import hashlib
import secrets

def generate_employee_id() -> str:
    """Generate unique employee ID"""
    timestamp = int(datetime.now().timestamp())
    return f"EMP{timestamp % 1000000:06d}"

def generate_secure_token() -> str:
    """Generate secure random token"""
    return secrets.token_urlsafe(32)

def hash_sensitive_data(data: str) -> str:
    """Hash sensitive data"""
    return hashlib.sha256(data.encode()).hexdigest()

def round_currency(amount: Decimal) -> Decimal:
    """Round currency to 2 decimal places"""
    return amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

def calculate_percentage(amount: Decimal, percentage: Decimal) -> Decimal:
    """Calculate percentage of amount"""
    return round_currency(amount * percentage)

def get_week_dates(date: datetime) -> tuple[datetime, datetime]:
    """Get start and end dates of the week"""
    start_of_week = date - timedelta(days=date.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    return start_of_week, end_of_week

def format_currency(amount: Decimal) -> str:
    """Format currency for display"""
    return f"${amount:,.2f}"

def parse_currency(currency_str: str) -> Decimal:
    """Parse currency string to Decimal"""
    cleaned = currency_str.replace('$', '').replace(',', '')
    return Decimal(cleaned)

def calculate_age(birth_date: datetime) -> int:
    """Calculate age from birth date"""
    today = datetime.now()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

def mask_sensitive_info(info: str, visible_chars: int = 4) -> str:
    """Mask sensitive information"""
    if len(info) <= visible_chars:
        return '*' * len(info)
    return '*' * (len(info) - visible_chars) + info[-visible_chars:]

def paginate_query(query, page: int, per_page: int):
    """Add pagination to query"""
    offset = (page - 1) * per_page
    return query.offset(offset).limit(per_page)

def build_filter_conditions(filters: Dict[str, Any]) -> List[Any]:
    """Build filter conditions from dictionary"""
    conditions = []
    for key, value in filters.items():
        if value is not None:
            conditions.append(f"{key} = {value}")
    return conditions

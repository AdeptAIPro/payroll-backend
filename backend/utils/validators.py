from typing import Optional
import re
from decimal import Decimal
from datetime import datetime

def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone: str) -> bool:
    """Validate phone number format"""
    pattern = r'^\+?1?[-.\s]?$$?[0-9]{3}$$?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}$'
    return re.match(pattern, phone) is not None

def validate_employee_id(employee_id: str) -> bool:
    """Validate employee ID format"""
    pattern = r'^EMP\d{3,6}$'
    return re.match(pattern, employee_id) is not None

def validate_salary(salary: Decimal) -> bool:
    """Validate salary amount"""
    return salary > 0 and salary <= Decimal('1000000.00')

def validate_hours(hours: Decimal) -> bool:
    """Validate hours worked"""
    return Decimal('0') <= hours <= Decimal('24')

def validate_tax_rate(rate: Decimal) -> bool:
    """Validate tax rate (0-100%)"""
    return Decimal('0') <= rate <= Decimal('1')

def validate_date_range(start_date: datetime, end_date: datetime) -> bool:
    """Validate date range"""
    return start_date <= end_date

def sanitize_string(value: str, max_length: int = 255) -> str:
    """Sanitize string input"""
    if not value:
        return ""
    return value.strip()[:max_length]

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Enum, DECIMAL, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import Base
import enum
from datetime import datetime
from sqlalchemy_utils import EncryptedType
from cryptography.fernet import Fernet
import os
from dotenv import load_dotenv
from backend.models.contractor import Contractor

load_dotenv()  # Load variables from .env

key_str = os.getenv("ENCRYPTION_KEY")
if not key_str:
    raise ValueError("ENCRYPTION_KEY not set in environment variables")

try:
    key = key_str.encode()  # Fernet key must be base64-encoded bytes
    Fernet(key)  # Validate the key
except Exception:
    raise ValueError("ENCRYPTION_KEY is not a valid 32-byte url-safe base64 string")

def get_fernet():
    return Fernet(key)

class OnboardingStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETE = "complete"

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    EMPLOYEE = "employee"

class SalaryType(str, enum.Enum):
    HOURLY = "hourly"
    FIXED = "fixed"

class TimesheetStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class PayrollStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Organization(Base):
    __tablename__ = "organizations"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    address = Column(Text)
    phone = Column(String(20))
    email = Column(String(255))
    tax_id = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    employees = relationship("Employee", back_populates="organization")
    tax_configs = relationship("TaxConfiguration", back_populates="organization")
    contractors = relationship("Contractor", back_populates="organization")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Employee(Base):
    __tablename__ = "employees"
    
    id = Column(Integer, primary_key=True, index=True)
    cognito_sub = Column(String(255), unique=True, nullable=False, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    employee_id = Column(String(50), unique=True, nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(20))
    role = Column(Enum(UserRole), nullable=False, default=UserRole.EMPLOYEE)
    department = Column(String(100))
    position = Column(String(100))
    salary_type = Column(Enum(SalaryType), nullable=False)
    base_salary = Column(DECIMAL(10, 2), nullable=False)
    hourly_rate = Column(DECIMAL(8, 2))
    tax_status = Column(String(20), default="single")
    bank_account_id = Column(String(255))  # Plaid account ID
    is_active = Column(Boolean, default=True)
    hire_date = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    organization = relationship("Organization", back_populates="employees")
    timesheets = relationship("Timesheet", back_populates="employee", foreign_keys="Timesheet.employee_id")
    payslips = relationship("Payslip", back_populates="employee", foreign_keys="Payslip.employee_id")
    
    # Onboarding fields and status
    ssn = Column(String(255), nullable=True)
    address = Column(String(255))
    city = Column(String(100))
    state = Column(String(50))
    zip_code = Column(String(20))
    birth_date = Column(DateTime(timezone=True))
    onboarding_status = Column(Enum(OnboardingStatus), default=OnboardingStatus.PENDING)
    emergency_contacts = relationship("EmergencyContact", backref="employee")
    compensation = relationship("Compensation", uselist=False, backref="employee")
    tax_info = relationship("TaxInfo", uselist=False, backref="employee")

class Timesheet(Base):
    __tablename__ = "timesheets"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    week_start_date = Column(DateTime(timezone=True), nullable=False)
    week_end_date = Column(DateTime(timezone=True), nullable=False)
    monday_hours = Column(DECIMAL(4, 2), default=0)
    tuesday_hours = Column(DECIMAL(4, 2), default=0)
    wednesday_hours = Column(DECIMAL(4, 2), default=0)
    thursday_hours = Column(DECIMAL(4, 2), default=0)
    friday_hours = Column(DECIMAL(4, 2), default=0)
    saturday_hours = Column(DECIMAL(4, 2), default=0)
    sunday_hours = Column(DECIMAL(4, 2), default=0)
    total_hours = Column(DECIMAL(5, 2), nullable=False)
    overtime_hours = Column(DECIMAL(5, 2), default=0)
    status = Column(Enum(TimesheetStatus), default=TimesheetStatus.PENDING)
    approved_by = Column(Integer, ForeignKey("employees.id"))
    approved_at = Column(DateTime(timezone=True))
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    employee = relationship("Employee", back_populates="timesheets", foreign_keys=[employee_id])
    approver = relationship("Employee", foreign_keys=[approved_by])

class TaxConfiguration(Base):
    __tablename__ = "tax_configurations"
    
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    federal_tax_rate = Column(DECIMAL(5, 4), nullable=False)  # e.g., 0.2200 for 22%
    state_tax_rate = Column(DECIMAL(5, 4), nullable=False)
    social_security_rate = Column(DECIMAL(5, 4), default=0.0620)  # 6.2%
    medicare_rate = Column(DECIMAL(5, 4), default=0.0145)  # 1.45%
    unemployment_rate = Column(DECIMAL(5, 4), default=0.0060)  # 0.6%
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    organization = relationship("Organization", back_populates="tax_configs")

class PayrollRun(Base):
    __tablename__ = "payroll_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    pay_period_start = Column(DateTime(timezone=True), nullable=False)
    pay_period_end = Column(DateTime(timezone=True), nullable=False)
    pay_date = Column(DateTime(timezone=True), nullable=False)
    status = Column(Enum(PayrollStatus), default=PayrollStatus.PENDING)
    total_gross_pay = Column(DECIMAL(12, 2), default=0)
    total_net_pay = Column(DECIMAL(12, 2), default=0)
    total_taxes = Column(DECIMAL(12, 2), default=0)
    processed_by = Column(Integer, ForeignKey("employees.id"))
    processed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    payslips = relationship("Payslip", back_populates="payroll_run")
    processor = relationship("Employee", foreign_keys=[processed_by])

class Payslip(Base):
    __tablename__ = "payslips"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    payroll_run_id = Column(Integer, ForeignKey("payroll_runs.id"), nullable=False)
    pay_period_start = Column(DateTime(timezone=True), nullable=False)
    pay_period_end = Column(DateTime(timezone=True), nullable=False)
    pay_date = Column(DateTime(timezone=True), nullable=False)
    
    # Earnings
    regular_hours = Column(DECIMAL(5, 2), default=0)
    overtime_hours = Column(DECIMAL(5, 2), default=0)
    regular_pay = Column(DECIMAL(10, 2), default=0)
    overtime_pay = Column(DECIMAL(10, 2), default=0)
    gross_pay = Column(DECIMAL(10, 2), nullable=False)
    
    # Deductions
    federal_tax = Column(DECIMAL(8, 2), default=0)
    state_tax = Column(DECIMAL(8, 2), default=0)
    social_security = Column(DECIMAL(8, 2), default=0)
    medicare = Column(DECIMAL(8, 2), default=0)
    total_deductions = Column(DECIMAL(10, 2), default=0)
    
    # Net pay
    net_pay = Column(DECIMAL(10, 2), nullable=False)
    
    # Payment
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    payment_method = Column(String(50))  # stripe, dwolla
    payment_reference = Column(String(255))
    
    # PDF
    pdf_url = Column(String(500))
    pdf_generated_at = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    employee = relationship("Employee", back_populates="payslips")
    payroll_run = relationship("PayrollRun", back_populates="payslips")

class BankAccount(Base):
    __tablename__ = "bank_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    plaid_account_id = Column(String(255), nullable=False)
    plaid_access_token = Column(String(255), nullable=False)
    account_name = Column(String(255))
    account_type = Column(String(50))
    account_subtype = Column(String(50))
    mask = Column(String(10))
    is_primary = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    
    # Extend BankAccount for encrypted account number
    account_number = Column(EncryptedType(String, key, get_fernet), nullable=True)
    routing_number = Column(EncryptedType(String, key, get_fernet), nullable=True)

class EmergencyContact(Base):
    __tablename__ = "emergency_contacts"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    name = Column(String(100), nullable=False)
    relationship = Column(String(50))
    phone = Column(String(20))
    email = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Compensation(Base):
    __tablename__ = "compensations"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    compensation_type = Column(String(20))  # hourly/salary
    amount = Column(DECIMAL(10, 2), nullable=False)
    start_date = Column(DateTime(timezone=True))
    review_date = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class TaxInfo(Base):
    __tablename__ = "tax_infos"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    w4_status = Column(String(50))
    state = Column(String(50))
    exemptions = Column(Integer, default=0)
    i9_verified = Column(Boolean, default=False)
    i9_document_url = Column(String(500))
    w4_document_url = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class EmployeeOnboardingDraft(Base):
    __tablename__ = "employee_onboarding_draft"
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    data = Column(JSON, nullable=False)
    status = Column(String(20), default="draft")  # draft or complete
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    organization = relationship("Organization") 
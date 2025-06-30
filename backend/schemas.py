from __future__ import annotations
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field, constr, condecimal, validator, field_serializer
from enum import Enum
from datetime import datetime, date
from decimal import Decimal
from backend.orm_models import UserRole, SalaryType, TimesheetStatus, PayrollStatus, PaymentStatus, OnboardingStatus

# Base schemas
class OrganizationBase(BaseModel):
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    tax_id: Optional[str] = None

class OrganizationCreate(OrganizationBase):
    pass

class Organization(OrganizationBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = {"from_attributes": True}

# Employee schemas
class EmployeeBase(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    role: UserRole = UserRole.EMPLOYEE
    department: Optional[str] = None
    position: Optional[str] = None
    salary_type: SalaryType
    base_salary: Decimal
    hourly_rate: Optional[Decimal] = None
    tax_status: str = "single"
    hire_date: Optional[datetime] = None
    ssn: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    birth_date: Optional[date] = None
    onboarding_status: Optional[OnboardingStatus] = None
    # emergency_contacts: Optional[List["EmergencyContact"]] = None
    # compensation: Optional["Compensation"] = None
    # tax_info: Optional["TaxInfo"] = None

    @field_serializer('birth_date')
    def serialize_birth_date(self, value):
        if value is None:
            return None
        return value.isoformat()

class EmployeeCreate(EmployeeBase):
    org_id: int
    cognito_sub: Optional[str] = None
    employee_id: str

class EmployeeUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    role: Optional[UserRole] = None
    department: Optional[str] = None
    position: Optional[str] = None
    salary_type: Optional[SalaryType] = None
    base_salary: Optional[Decimal] = None
    hourly_rate: Optional[Decimal] = None
    tax_status: Optional[str] = None
    is_active: Optional[bool] = None

class Employee(EmployeeBase):
    id: int
    org_id: int
    cognito_sub: str
    employee_id: str
    bank_account_id: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    @field_serializer('created_at', 'updated_at', 'hire_date')
    def serialize_datetimes(self, value):
        if value is None:
            return None
        return value.isoformat()

    model_config = {"from_attributes": True}

# Timesheet schemas
class TimesheetBase(BaseModel):
    week_start_date: datetime
    week_end_date: datetime
    monday_hours: Decimal = Field(default=0, ge=0, le=24)
    tuesday_hours: Decimal = Field(default=0, ge=0, le=24)
    wednesday_hours: Decimal = Field(default=0, ge=0, le=24)
    thursday_hours: Decimal = Field(default=0, ge=0, le=24)
    friday_hours: Decimal = Field(default=0, ge=0, le=24)
    saturday_hours: Decimal = Field(default=0, ge=0, le=24)
    sunday_hours: Decimal = Field(default=0, ge=0, le=24)
    notes: Optional[str] = None

class TimesheetCreate(TimesheetBase):
    employee_id: int

class TimesheetUpdate(BaseModel):
    monday_hours: Optional[Decimal] = None
    tuesday_hours: Optional[Decimal] = None
    wednesday_hours: Optional[Decimal] = None
    thursday_hours: Optional[Decimal] = None
    friday_hours: Optional[Decimal] = None
    saturday_hours: Optional[Decimal] = None
    sunday_hours: Optional[Decimal] = None
    notes: Optional[str] = None

class TimesheetApproval(BaseModel):
    status: TimesheetStatus
    notes: Optional[str] = None

class Timesheet(TimesheetBase):
    id: int
    employee_id: int
    total_hours: Decimal
    overtime_hours: Decimal
    status: TimesheetStatus
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = {"from_attributes": True}

# Tax Configuration schemas
class TaxConfigurationBase(BaseModel):
    federal_tax_rate: Decimal = Field(ge=0, le=1)
    state_tax_rate: Decimal = Field(ge=0, le=1)
    social_security_rate: Decimal = Field(default=0.062, ge=0, le=1)
    medicare_rate: Decimal = Field(default=0.0145, ge=0, le=1)
    unemployment_rate: Decimal = Field(default=0.006, ge=0, le=1)

class TaxConfigurationCreate(TaxConfigurationBase):
    org_id: int

class TaxConfiguration(TaxConfigurationBase):
    id: int
    org_id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = {"from_attributes": True}

# Payroll schemas
class PayrollRunBase(BaseModel):
    pay_period_start: datetime
    pay_period_end: datetime
    pay_date: datetime

class PayrollRunCreate(PayrollRunBase):
    org_id: int

class PayrollRun(PayrollRunBase):
    id: int
    org_id: int
    status: PayrollStatus
    total_gross_pay: Decimal
    total_net_pay: Decimal
    total_taxes: Decimal
    processed_by: Optional[int] = None
    processed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = {"from_attributes": True}

# Payslip schemas
class PayslipBase(BaseModel):
    pay_period_start: datetime
    pay_period_end: datetime
    pay_date: datetime
    regular_hours: Decimal
    overtime_hours: Decimal
    regular_pay: Decimal
    overtime_pay: Decimal
    gross_pay: Decimal
    federal_tax: Decimal
    state_tax: Decimal
    social_security: Decimal
    medicare: Decimal
    total_deductions: Decimal
    net_pay: Decimal

class Payslip(PayslipBase):
    id: int
    employee_id: int
    payroll_run_id: int
    payment_status: PaymentStatus
    payment_method: Optional[str] = None
    payment_reference: Optional[str] = None
    pdf_url: Optional[str] = None
    pdf_generated_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = {"from_attributes": True}

# Bank Account schemas
class BankAccountBase(BaseModel):
    account_name: Optional[str] = None
    account_type: Optional[str] = None
    account_subtype: Optional[str] = None
    mask: Optional[str] = None
    is_primary: bool = True

class BankAccountCreate(BankAccountBase):
    employee_id: int
    plaid_account_id: str
    plaid_access_token: str

class BankAccount(BankAccountBase):
    id: int
    employee_id: int
    plaid_account_id: str
    is_verified: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = {"from_attributes": True}

# Auth schemas
class UserInfo(BaseModel):
    sub: str
    email: str
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    groups: List[str] = []
    org_id: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_info: UserInfo

class OnboardingStatus(str, Enum):
    pending = "pending"
    complete = "complete"

class EmergencyContactBase(BaseModel):
    name: str
    relationship: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None

class EmergencyContactCreate(EmergencyContactBase):
    pass

class EmergencyContact(EmergencyContactBase):
    id: int
    model_config = {"from_attributes": True}

class CompensationBase(BaseModel):
    compensation_type: str
    amount: float
    start_date: Optional[str] = None
    review_date: Optional[str] = None

class CompensationCreate(CompensationBase):
    pass

class Compensation(CompensationBase):
    id: int
    model_config = {"from_attributes": True}

class TaxInfoBase(BaseModel):
    w4_status: Optional[str] = None
    state: Optional[str] = None
    exemptions: Optional[int] = None
    i9_verified: Optional[bool] = None
    i9_document_url: Optional[str] = None
    w4_document_url: Optional[str] = None

class TaxInfoCreate(TaxInfoBase):
    pass

class TaxInfo(TaxInfoBase):
    id: int
    model_config = {"from_attributes": True}

class ContractorBase(BaseModel):
    org_id: int
    contractor_type: str
    name: str
    email: EmailStr
    phone: Optional[str] = None
    tax_id: Optional[str] = None

class ContractorCreate(ContractorBase):
    pass

class Contractor(ContractorBase):
    id: int
    onboarding_status: OnboardingStatus
    model_config = {"from_attributes": True}

class W2EmployeeOnboardingDraft(BaseModel):
    id: int
    org_id: int
    user_id: int | None = None
    data: Dict
    status: str
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        orm_mode = True

class CompensationRate(BaseModel):
    amount: condecimal(gt=0)
    pay_type: str  # Hourly / Salary / Commission / Other
    description: Optional[str]
    standard_pay_period: Optional[float]
    standard_overtime: Optional[float]
    is_default: bool = False

class EmergencyContact(BaseModel):
    name: str
    relationship: str
    phone: str
    email: Optional[EmailStr]

class DirectDepositAccount(BaseModel):
    bank_name: str
    account_number: str
    routing_number: str
    account_type: str  # Checking/Savings
    is_primary: bool = False

class EarningDeduction(BaseModel):
    type: str  # Earning/Deduction
    name: str
    amount: condecimal(gt=0)
    description: Optional[str]

class W2EmployeeOnboarding(BaseModel):
    # Step 1: Personal
    legal_first_name: constr(strip_whitespace=True, min_length=1)
    legal_middle_name: Optional[str]
    legal_last_name: constr(strip_whitespace=True, min_length=1)
    go_by_first_name: Optional[str]
    go_by_last_name: Optional[str]
    prefix: Optional[str]
    suffix: Optional[str]
    ssn: constr(pattern=r"^\d{3}-\d{2}-\d{4}$")
    # Step 2: Birth & ID
    birth_date: date
    sex: Optional[str]
    pronouns: Optional[str]
    employee_id: constr(strip_whitespace=True, min_length=1)
    clock_id: Optional[str]
    # Step 3: Delivery Address
    address_type: str
    address_line1: str
    address_line2: Optional[str]
    city: str
    state: str
    zip_code: constr(pattern=r"^\d{5}(-\d{4})?$")
    # Step 4: Employment Details
    hire_date: date
    seniority_date: Optional[date]
    employment_type: str
    statutory_employee: bool = False
    retirement_plan_eligible: bool = False
    location: str
    position: str
    supervisor: Optional[str]
    officer_type: Optional[str]
    # Step 5: Work & Coverage
    works_from_home: bool = False
    workers_comp_state: str
    class_code: Optional[str]
    sui_state: str
    # Step 6: Compensation
    compensation_rates: List[CompensationRate]
    # Step 7: Pay Details
    pay_frequency: str
    overtime_exempt: bool = False
    overtime_factor: Optional[float]
    # Step 8: Raise & Review
    projected_change_date: Optional[date]
    next_review_date: Optional[date]
    # Step 9: I-9 Verification
    i9_completer: str
    i9_remote_type: Optional[str]
    # Step 10: Tax Lookup
    # (No fields, just a lookup action)
    # Step 11: Federal & State Tax Setup
    w4_form_type: str
    taxable: bool = True
    taxes_withheld: bool = True
    residency: str
    filing_status: str
    multiple_jobs: bool = False
    dependents: Optional[float]
    other_income: Optional[float]
    deductions: Optional[float]
    extra_amount: Optional[float]
    additional_percentage: Optional[float]
    state_taxes: Optional[List[dict]]
    # Step 12: Social & UI Reporting
    override_amount: Optional[float]
    override_percentage: Optional[float]
    social_security_taxable: bool = True
    medicare_taxable: bool = True
    federal_unemployment_taxable: bool = True
    # Step 13: EEO & Demographics
    apply_edits_date: Optional[date]
    eeo1_reporting_eligible: bool = False
    ca_pay_data_eligible: bool = False
    job_category: Optional[str]
    sex_for_reporting: Optional[str]
    race_ethnicity: Optional[str]
    identification_by: Optional[str]
    # Step 14: Direct Deposit
    direct_deposit_accounts: Optional[List[DirectDepositAccount]]
    # Step 15: Earnings & Deductions
    earnings_deductions: Optional[List[EarningDeduction]]
    # Step 16: Time Off & Emergency Contacts
    time_off_policies: Optional[List[str]]
    emergency_contacts: Optional[List[EmergencyContact]]
    # Step 17: (Finish)

    @validator('compensation_rates')
    def at_least_one_rate(cls, v):
        if not v or len(v) == 0:
            raise ValueError('At least one compensation rate is required')
        return v

    class Config:
        orm_mode = True

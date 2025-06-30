from pydantic import BaseModel, constr, conlist, validator
from typing import List, Optional
from datetime import date
from backend.database import get_db
from backend.models import Contractor, ContractorCompensation, ContractorTaxInfo, ContractorDirectDeposit, ContractorEarningsDeductions, ContractorEmergencyContact, ContractorOnboardingDraft
from sqlalchemy.orm import Session

class RateBlock(BaseModel):
    amount: float
    pay_type: constr(pattern="^(Hourly|Flat Fee|Commission|Other)$")
    description: Optional[str]
    standard_pay_period: Optional[float]
    standard_overtime: Optional[float]
    default_rate: bool

class BankAccount(BaseModel):
    account_type: constr(pattern="^(Checking|Savings)$")
    routing_number: constr(pattern="^\\d{9}$")
    account_number: constr(min_length=4, max_length=17)
    reenter_account_number: constr(min_length=4, max_length=17)
    calculation: constr(pattern="^(Remainder|Flat Amount)$")
    amount: Optional[float]

    @validator('reenter_account_number')
    def account_numbers_match(cls, v, values):
        if 'account_number' in values and v != values['account_number']:
            raise ValueError('Account numbers do not match')
        return v

class Contractor1099Onboarding(BaseModel):
    send_account_invite: bool
    legal_first_name: constr(min_length=1)
    legal_middle_name: Optional[str]
    legal_last_name: constr(min_length=1)
    go_by_first_name: Optional[str]
    go_by_last_name: Optional[str]
    ssn: Optional[constr(pattern="^\\d{3}-\\d{2}-\\d{4}$")]
    birth_date: Optional[date]
    sex: Optional[constr(pattern="^(Not specified|Male|Female|Other)$")]
    pronouns: Optional[str]
    contractor_id: constr(min_length=1)
    clock_id: Optional[str]
    address_type: constr(pattern="^(Home|Mailing|Other)$")
    address_line1: constr(min_length=1)
    address_line2: Optional[str]
    city: constr(min_length=1)
    state: constr(min_length=2, max_length=2)
    zip_code: constr(pattern="^\\d{5}(-\\d{4})?$")
    begin_contract_date: date
    seniority_date: Optional[date]
    contract_type: constr(pattern="^(One-time|Hourly|Project|Retainer|Other)$")
    statutory_employee: bool
    retirement_plan_eligible: bool
    org_id: int
    location: constr(min_length=1)
    position: constr(min_length=1)
    supervisor: Optional[str]
    work_state: constr(min_length=2, max_length=2)
    class_code: Optional[str]
    sui_state: Optional[constr(min_length=2, max_length=2)]
    rates: conlist(RateBlock, min_items=1)
    pay_frequency: constr(pattern="^(Weekly|Biweekly|Semimonthly|Monthly)$")
    overtime_exempt: bool
    overtime_factor: Optional[float]
    projected_change_date: Optional[date]
    next_review_date: Optional[date]
    # Tax & Withholding, Demographics, etc. omitted for brevity
    bank_accounts: List[BankAccount]
    # ... other fields ...

# Service functions for draft save, final submit, and mapping to DB

def save_contractor_draft(db: Session, draft_id: str, data: dict, user_id: int):
    # Upsert logic for draft
    pass

async def submit_contractor_onboarding(db: AsyncSession, onboarding_data: Contractor1099Onboarding, user_id: int):
    async with db.begin():
        # Create Contractor
        contractor_data = onboarding_data.dict(exclude={'rates', 'bank_accounts', 'emergency_contacts', 'draft_id', 'send_account_invite', 'org_id'})
        contractor_data['org_id'] = onboarding_data.org_id
        db_contractor = Contractor(**contractor_data, user_id=user_id)
        db.add(db_contractor)
        await db.flush()
        # Validate, map, and create all records in a transaction
        pass 
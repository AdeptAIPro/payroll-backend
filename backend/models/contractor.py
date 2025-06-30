from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON, ForeignKey, Date
from sqlalchemy.orm import relationship
from backend.database import Base
from datetime import datetime

class Contractor(Base):
    __tablename__ = 'contractors'
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey('organizations.id'), nullable=False)
    legal_first_name = Column(String(255), nullable=False)
    legal_middle_name = Column(String(255))
    legal_last_name = Column(String(255), nullable=False)
    go_by_first_name = Column(String(255))
    go_by_last_name = Column(String(255))
    ssn = Column(String(11), unique=True, index=True)
    birth_date = Column(Date)
    sex = Column(String(20))
    pronouns = Column(String(50))
    contractor_id = Column(String(50), unique=True, nullable=False)
    clock_id = Column(String(50))
    address_type = Column(String(20), nullable=False)
    address_line1 = Column(String(255), nullable=False)
    address_line2 = Column(String(255))
    city = Column(String(100), nullable=False)
    state = Column(String(2), nullable=False)
    zip_code = Column(String(10), nullable=False)
    begin_contract_date = Column(Date, nullable=False)
    seniority_date = Column(Date)
    contract_type = Column(String(50), nullable=False)
    statutory_employee = Column(Boolean, default=False)
    retirement_plan_eligible = Column(Boolean, default=False)
    location = Column(String(255), nullable=False)
    position = Column(String(255), nullable=False)
    supervisor = Column(String(255))
    work_state = Column(String(2), nullable=False)
    class_code = Column(String(50))
    sui_state = Column(String(2))
    pay_frequency = Column(String(50), nullable=False)
    overtime_exempt = Column(Boolean, default=False)
    overtime_factor = Column(Float)
    projected_change_date = Column(Date)
    next_review_date = Column(Date)
    eeo1_eligible = Column(Boolean)
    ca_paydata_eligible = Column(Boolean)
    job_category = Column(String(100))
    sex_reporting = Column(String(20))
    race_ethnicity = Column(String(100))
    identification_by = Column(String(50))
    paperless_payroll = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship('Organization', back_populates='contractors')
    compensations = relationship("ContractorCompensation", back_populates="contractor")
    direct_deposits = relationship("ContractorDirectDeposit", back_populates="contractor")
    emergency_contacts = relationship("ContractorEmergencyContact", back_populates="contractor")

class ContractorCompensation(Base):
    __tablename__ = 'contractor_compensations'
    id = Column(Integer, primary_key=True, index=True)
    contractor_id = Column(Integer, ForeignKey('contractors.id'), nullable=False)
    amount = Column(Float, nullable=False)
    pay_type = Column(String(50), nullable=False)
    description = Column(String(255))
    standard_pay_period = Column(Float)
    standard_overtime = Column(Float)
    default_rate = Column(Boolean, default=False)
    contractor = relationship("Contractor", back_populates="compensations")

class ContractorDirectDeposit(Base):
    __tablename__ = 'contractor_direct_deposits'
    id = Column(Integer, primary_key=True, index=True)
    contractor_id = Column(Integer, ForeignKey('contractors.id'), nullable=False)
    account_type = Column(String(20), nullable=False)
    routing_number = Column(String(9), nullable=False)
    account_number = Column(String(20), nullable=False)
    calculation = Column(String(20), nullable=False)
    amount = Column(Float)
    contractor = relationship("Contractor", back_populates="direct_deposits")

class ContractorEmergencyContact(Base):
    __tablename__ = 'contractor_emergency_contacts'
    id = Column(Integer, primary_key=True, index=True)
    contractor_id = Column(Integer, ForeignKey('contractors.id'), nullable=False)
    name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)
    contractor = relationship("Contractor", back_populates="emergency_contacts")

class ContractorOnboardingDraft(Base):
    __tablename__ = 'contractor_onboarding_drafts'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False) # Assuming user_id is provided
    data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) 
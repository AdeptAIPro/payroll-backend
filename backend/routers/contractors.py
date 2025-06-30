from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.services.auth_service import get_current_user
from backend.models import Contractor
from backend.orm_models import EmergencyContact, OnboardingStatus, User
from backend.schemas import ContractorCreate, Contractor as ContractorSchema, EmergencyContactCreate, EmergencyContact as EmergencyContactSchema, Contractor1099Onboarding
from backend.database import get_db
from typing import List
from sqlalchemy.orm import Session
from backend.services.contractor_service import save_contractor_draft, submit_contractor_onboarding

router = APIRouter(prefix="/api/contractors", tags=["Contractors"])

@router.post("/onboarding", response_model=ContractorSchema)
async def create_contractor_onboarding_draft(
    payload: Contractor1099Onboarding,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    draft = await save_contractor_draft(db, payload, current_user.id)
    return draft

@router.patch("/onboarding/{draft_id}", response_model=ContractorSchema)
async def update_contractor_onboarding_draft(
    draft_id: int,
    payload: Contractor1099Onboarding,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    draft = await save_contractor_draft(db, payload, current_user.id, draft_id)
    return draft

@router.post("/onboarding/submit", response_model=ContractorSchema)
async def submit_contractor_onboarding_final(
    payload: Contractor1099Onboarding,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    contractor = await submit_contractor_onboarding(db, payload, current_user.id)
    return contractor
    
@router.put("/{contractor_id}/onboarding-status")
async def update_contractor_onboarding_status(
    contractor_id: int,
    status: OnboardingStatus,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if "admin" not in current_user.roles:
        raise HTTPException(status_code=403, detail="Not authorized")
    contractor = await db.get(Contractor, contractor_id)
    if not contractor:
        raise HTTPException(status_code=404, detail="Contractor not found")
    contractor.onboarding_status = status.value
    await db.commit()
    return {"status": status.value}

@router.post("/{contractor_id}/emergency-contacts", response_model=EmergencyContactSchema)
async def add_contractor_emergency_contact(
    contractor_id: int,
    contact: EmergencyContactCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if "admin" not in current_user.roles:
        raise HTTPException(status_code=403, detail="Not authorized")
    db_contact = EmergencyContact(contractor_id=contractor_id, **contact.dict())
    db.add(db_contact)
    await db.commit()
    await db.refresh(db_contact)
    return db_contact

@router.get("/{contractor_id}/emergency-contacts", response_model=List[EmergencyContactSchema])
async def list_contractor_emergency_contacts(
    contractor_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # This should be part of a service, but for now, we'll leave it here.
    # Also, need to ensure user has rights to view this.
    contacts = await db.execute(
        select(EmergencyContact).where(EmergencyContact.contractor_id == contractor_id)
    )
    return contacts.scalars().all()

@router.delete("/{contractor_id}/emergency-contacts/{contact_id}")
async def delete_contractor_emergency_contact(
    contractor_id: int,
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if "admin" not in current_user.roles:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    contact = await db.get(EmergencyContact, contact_id)
    if not contact or contact.contractor_id != contractor_id:
        raise HTTPException(status_code=404, detail="Contact not found")

    await db.delete(contact)
    await db.commit()
    return {"detail": "Deleted"} 
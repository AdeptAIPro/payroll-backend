from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from services.auth_service import get_current_user
from models import Contractor, EmergencyContact, OnboardingStatus
from schemas import ContractorCreate, Contractor, EmergencyContactCreate, EmergencyContact
from database import get_db
from typing import List

router = APIRouter()

@router.post("/onboard", response_model=Contractor)
async def onboard_contractor(
    contractor: ContractorCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if "admin" not in current_user.get("groups", []):
        raise HTTPException(status_code=403, detail="Not authorized")
    db_contractor = Contractor(**contractor.dict())
    db.add(db_contractor)
    await db.commit()
    await db.refresh(db_contractor)
    return db_contractor

@router.put("/{contractor_id}/onboarding-status")
async def update_contractor_onboarding_status(
    contractor_id: int,
    status: OnboardingStatus,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if "admin" not in current_user.get("groups", []):
        raise HTTPException(status_code=403, detail="Not authorized")
    contractor = await db.get(Contractor, contractor_id)
    if not contractor:
        raise HTTPException(status_code=404, detail="Contractor not found")
    contractor.onboarding_status = status
    await db.commit()
    return {"status": status}

@router.post("/{contractor_id}/emergency-contacts", response_model=EmergencyContact)
async def add_contractor_emergency_contact(
    contractor_id: int,
    contact: EmergencyContactCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if "admin" not in current_user.get("groups", []):
        raise HTTPException(status_code=403, detail="Not authorized")
    db_contact = EmergencyContact(employee_id=contractor_id, **contact.dict())
    db.add(db_contact)
    await db.commit()
    await db.refresh(db_contact)
    return db_contact

@router.get("/{contractor_id}/emergency-contacts", response_model=List[EmergencyContact])
async def list_contractor_emergency_contacts(
    contractor_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    contacts = await db.execute(
        select(EmergencyContact).where(EmergencyContact.employee_id == contractor_id)
    )
    return contacts.scalars().all()

@router.delete("/{contractor_id}/emergency-contacts/{contact_id}")
async def delete_contractor_emergency_contact(
    contractor_id: int,
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    contact = await db.get(EmergencyContact, contact_id)
    if not contact or contact.employee_id != contractor_id:
        raise HTTPException(status_code=404, detail="Contact not found")
    if "admin" not in current_user.get("groups", []):
        raise HTTPException(status_code=403, detail="Not authorized")
    await db.delete(contact)
    await db.commit()
    return {"detail": "Deleted"} 
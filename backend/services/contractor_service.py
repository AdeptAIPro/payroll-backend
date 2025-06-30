import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models.contractor import Contractor, ContractorCompensation, ContractorDirectDeposit, ContractorEmergencyContact, ContractorOnboardingDraft
from schemas.contractor_onboarding import Contractor1099Onboarding

async def save_contractor_draft(db: AsyncSession, payload: Contractor1099Onboarding, user_id: int, draft_id: int = None):
    if draft_id:
        # Update existing draft
        result = await db.execute(select(ContractorOnboardingDraft).where(ContractorOnboardingDraft.id == draft_id, ContractorOnboardingDraft.user_id == user_id))
        db_draft = result.scalars().first()
        if not db_draft:
            raise ValueError("Draft not found or not owned by user")
        
        existing_data = json.loads(db_draft.data)
        existing_data.update(payload.dict(exclude_unset=True, exclude={'organization'}))
        db_draft.data = json.dumps(existing_data)
    else:
        # Create new draft
        db_draft = ContractorOnboardingDraft(user_id=user_id, data=json.dumps(payload.dict(exclude={'organization'})))
        db.add(db_draft)
    
    await db.commit()
    await db.refresh(db_draft)
    return db_draft

async def submit_contractor_onboarding(db: AsyncSession, onboarding_data: Contractor1099Onboarding, user_id: int):
    async with db.begin():
        # Create Contractor
        contractor_data = onboarding_data.dict(exclude={'rates', 'bank_accounts', 'emergency_contacts', 'draft_id', 'send_account_invite', 'organization'})
        contractor_data['org_id'] = onboarding_data.org_id
        db_contractor = Contractor(**contractor_data, user_id=user_id)
        db.add(db_contractor)
        await db.flush()

        # Create Compensations
        if onboarding_data.rates:
            for rate_block in onboarding_data.rates:
                db_comp = ContractorCompensation(contractor_id=db_contractor.id, **rate_block.dict())
                db.add(db_comp)

        # Create Direct Deposits
        if onboarding_data.bank_accounts:
            for account in onboarding_data.bank_accounts:
                db_deposit = ContractorDirectDeposit(contractor_id=db_contractor.id, **account.dict(exclude={'reenter_account_number'}))
                db.add(db_deposit)
            
        # Create Emergency Contacts
        if onboarding_data.emergency_contacts:
            for contact in onboarding_data.emergency_contacts:
                db_contact = ContractorEmergencyContact(contractor_id=db_contractor.id, **contact.dict())
                db.add(db_contact)
        
        # If there was a draft, delete it
        if onboarding_data.draft_id:
            await db.execute(
                select(ContractorOnboardingDraft)
                .where(ContractorOnboardingDraft.id == onboarding_data.draft_id, ContractorOnboardingDraft.user_id == user_id)
                .delete()
            )

    await db.refresh(db_contractor)

    # Placeholder for sending an invite - should be a separate, non-blocking task
    if onboarding_data.send_account_invite:
        print(f"Initiating account invite for {db_contractor.legal_first_name}")

    return db_contractor 
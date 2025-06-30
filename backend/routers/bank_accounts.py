from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List
from backend.database import get_db
from backend.orm_models import BankAccount, Employee, UserRole
from backend.schemas import BankAccount as BankAccountSchema, BankAccountCreate, UserInfo
from backend.services.auth_service import get_current_user
from backend.services.plaid_service import plaid_service
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

router = APIRouter()
security = HTTPBearer()

async def get_current_user_info(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserInfo:
    """Get current user info from token"""
    token = credentials.credentials
    user_info = await get_current_user(token)
    return UserInfo(**user_info)

class LinkTokenRequest(BaseModel):
    client_name: str = "Payroll System"

class PublicTokenRequest(BaseModel):
    public_token: str
    account_id: str

@router.post("/link-token")
async def create_link_token(
    request: LinkTokenRequest,
    current_user: UserInfo = Depends(get_current_user_info),
    db: AsyncSession = Depends(get_db)
):
    """Create a Plaid link token for bank account connection"""
    try:
        # Get employee record
        employee_result = await db.execute(
            select(Employee).where(Employee.cognito_sub == current_user.sub)
        )
        employee = employee_result.scalar_one_or_none()
        
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee record not found"
            )
        
        # Create link token
        link_token = await plaid_service.create_link_token(
            user_id=str(employee.id),
            client_name=request.client_name
        )
        
        return {"link_token": link_token}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating link token: {str(e)}"
        )

@router.post("/connect")
async def connect_bank_account(
    request: PublicTokenRequest,
    current_user: UserInfo = Depends(get_current_user_info),
    db: AsyncSession = Depends(get_db)
):
    """Connect a bank account using Plaid"""
    try:
        # Get employee record
        employee_result = await db.execute(
            select(Employee).where(Employee.cognito_sub == current_user.sub)
        )
        employee = employee_result.scalar_one_or_none()
        
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee record not found"
            )
        
        # Exchange public token for access token
        token_data = await plaid_service.exchange_public_token(request.public_token)
        
        # Get account details
        accounts = await plaid_service.get_accounts(token_data['access_token'])
        account = next((acc for acc in accounts if acc['account_id'] == request.account_id), None)
        
        if not account:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account not found"
            )
        
        # Verify account is a depository account
        if account['type'] != 'depository':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only depository accounts are supported for payroll"
            )
        
        # Check if bank account already exists
        existing_result = await db.execute(
            select(BankAccount).where(
                and_(
                    BankAccount.employee_id == employee.id,
                    BankAccount.plaid_account_id == request.account_id
                )
            )
        )
        existing_account = existing_result.scalar_one_or_none()
        
        if existing_account:
            # Update existing account
            existing_account.plaid_access_token = token_data['access_token']
            existing_account.account_name = account['name']
            existing_account.account_type = account['type']
            existing_account.account_subtype = account['subtype']
            existing_account.mask = account['mask']
            existing_account.is_verified = True
            
            await db.commit()
            await db.refresh(existing_account)
            
            return existing_account
        else:
            # Create new bank account
            bank_account = BankAccount(
                employee_id=employee.id,
                plaid_account_id=request.account_id,
                plaid_access_token=token_data['access_token'],
                account_name=account['name'],
                account_type=account['type'],
                account_subtype=account['subtype'],
                mask=account['mask'],
                is_verified=True,
                is_primary=True
            )
            
            db.add(bank_account)
            await db.commit()
            await db.refresh(bank_account)
            
            return bank_account
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error connecting bank account: {str(e)}"
        )

@router.get("/", response_model=List[BankAccountSchema])
async def get_bank_accounts(
    current_user: UserInfo = Depends(get_current_user_info),
    db: AsyncSession = Depends(get_db)
):
    """Get bank accounts for the current user"""
    try:
        # Get employee record
        employee_result = await db.execute(
            select(Employee).where(Employee.cognito_sub == current_user.sub)
        )
        employee = employee_result.scalar_one_or_none()
        
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee record not found"
            )
        
        # Get bank accounts
        accounts_result = await db.execute(
            select(BankAccount).where(BankAccount.employee_id == employee.id)
        )
        accounts = accounts_result.scalars().all()
        
        return accounts
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting bank accounts: {str(e)}"
        )

@router.get("/{account_id}", response_model=BankAccountSchema)
async def get_bank_account(
    account_id: int,
    current_user: UserInfo = Depends(get_current_user_info),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific bank account"""
    try:
        # Get employee record
        employee_result = await db.execute(
            select(Employee).where(Employee.cognito_sub == current_user.sub)
        )
        employee = employee_result.scalar_one_or_none()
        
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee record not found"
            )
        
        # Get bank account
        account_result = await db.execute(
            select(BankAccount).where(
                and_(
                    BankAccount.id == account_id,
                    BankAccount.employee_id == employee.id
                )
            )
        )
        account = account_result.scalar_one_or_none()
        
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bank account not found"
            )
        
        return account
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting bank account: {str(e)}"
        )

@router.delete("/{account_id}")
async def delete_bank_account(
    account_id: int,
    current_user: UserInfo = Depends(get_current_user_info),
    db: AsyncSession = Depends(get_db)
):
    """Delete a bank account"""
    try:
        # Get employee record
        employee_result = await db.execute(
            select(Employee).where(Employee.cognito_sub == current_user.sub)
        )
        employee = employee_result.scalar_one_or_none()
        
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee record not found"
            )
        
        # Get bank account
        account_result = await db.execute(
            select(BankAccount).where(
                and_(
                    BankAccount.id == account_id,
                    BankAccount.employee_id == employee.id
                )
            )
        )
        account = account_result.scalar_one_or_none()
        
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bank account not found"
            )
        
        # Delete account
        await db.delete(account)
        await db.commit()
        
        return {"message": "Bank account deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting bank account: {str(e)}"
        )

@router.post("/{account_id}/verify")
async def verify_bank_account(
    account_id: int,
    current_user: UserInfo = Depends(get_current_user_info),
    db: AsyncSession = Depends(get_db)
):
    """Verify a bank account"""
    try:
        # Get employee record
        employee_result = await db.execute(
            select(Employee).where(Employee.cognito_sub == current_user.sub)
        )
        employee = employee_result.scalar_one_or_none()
        
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee record not found"
            )
        
        # Get bank account
        account_result = await db.execute(
            select(BankAccount).where(
                and_(
                    BankAccount.id == account_id,
                    BankAccount.employee_id == employee.id
                )
            )
        )
        account = account_result.scalar_one_or_none()
        
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bank account not found"
            )
        
        # Verify account with Plaid
        verification_result = await plaid_service.verify_bank_account(
            account.plaid_access_token,
            account.plaid_account_id
        )
        
        # Update account verification status
        account.is_verified = verification_result['verified']
        account.account_name = verification_result['account_name']
        account.account_type = verification_result['account_type']
        account.account_subtype = verification_result['account_subtype']
        account.mask = verification_result['mask']
        
        await db.commit()
        await db.refresh(account)
        
        return {
            "verified": account.is_verified,
            "account": account
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error verifying bank account: {str(e)}"
        ) 
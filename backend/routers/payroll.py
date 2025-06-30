from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from datetime import datetime
from backend.database import get_db
from backend.orm_models import PayrollRun, Employee, UserRole, PayrollStatus
from backend.schemas import PayrollRun as PayrollRunSchema, PayrollRunCreate, UserInfo
from backend.services.payroll_service import PayrollService

router = APIRouter()
payroll_service = PayrollService()

async def get_current_user_info(request: Request) -> UserInfo:
    """Get current user info from request state"""
    try:
        user_info = request.state.user
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated"
            )
        return UserInfo(**user_info)
    except AttributeError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )

@router.post("/", response_model=PayrollRunSchema)
async def create_payroll_run(
    payroll_run: PayrollRunCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user_info)
):
    """Create a new payroll run (Admin only)"""
    if UserRole.ADMIN.value not in current_user.groups:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create payroll runs"
        )
    
    # Check if payroll run already exists for this period
    result = await db.execute(
        select(PayrollRun).where(
            and_(
                PayrollRun.org_id == payroll_run.org_id,
                PayrollRun.pay_period_start == payroll_run.pay_period_start,
                PayrollRun.pay_period_end == payroll_run.pay_period_end
            )
        )
    )
    existing_run = result.scalar_one_or_none()
    
    if existing_run:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payroll run already exists for this period"
        )
    
    db_payroll_run = PayrollRun(**payroll_run.dict())
    db.add(db_payroll_run)
    await db.commit()
    await db.refresh(db_payroll_run)
    
    return db_payroll_run

@router.get("/", response_model=List[PayrollRunSchema])
async def get_payroll_runs(
    org_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user_info)
):
    """Get payroll runs list"""
    # Build query conditions
    conditions = []
    
    # Organization filter
    if org_id:
        conditions.append(PayrollRun.org_id == org_id)
    elif current_user.org_id:
        conditions.append(PayrollRun.org_id == int(current_user.org_id))
    
    # Role-based access control
    if UserRole.EMPLOYEE.value in current_user.groups and UserRole.ADMIN.value not in current_user.groups:
        # Employees can only see payroll runs for their organization
        if current_user.org_id:
            conditions.append(PayrollRun.org_id == int(current_user.org_id))
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to view payroll runs"
            )
    
    query = select(PayrollRun)
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    payroll_runs = result.scalars().all()
    
    return payroll_runs

@router.get("/{payroll_run_id}", response_model=PayrollRunSchema)
async def get_payroll_run(
    payroll_run_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user_info)
):
    """Get payroll run by ID"""
    result = await db.execute(select(PayrollRun).where(PayrollRun.id == payroll_run_id))
    payroll_run = result.scalar_one_or_none()
    
    if not payroll_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll run not found"
        )
    
    # Check permissions
    if UserRole.EMPLOYEE.value in current_user.groups and UserRole.ADMIN.value not in current_user.groups:
        if current_user.org_id and payroll_run.org_id != int(current_user.org_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view payroll runs for your organization"
            )
    
    return payroll_run

@router.post("/{payroll_run_id}/process")
async def process_payroll_run(
    payroll_run_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user_info)
):
    """Process payroll run (Admin only)"""
    if UserRole.ADMIN.value not in current_user.groups:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can process payroll"
        )
    
    try:
        result = await payroll_service.process_payroll(db, payroll_run_id)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing payroll: {str(e)}"
        ) 
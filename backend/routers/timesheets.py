from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from typing import List, Optional
from datetime import datetime, timedelta
from backend.database import get_db
from backend.orm_models import Timesheet, Employee, UserRole, TimesheetStatus, TaxConfiguration
from backend.schemas import (
    Timesheet as TimesheetSchema, 
    TimesheetCreate, 
    TimesheetUpdate, 
    TimesheetApproval,
    UserInfo
)
from backend.services.email_service import EmailService
from backend.services.auth_service import get_current_user
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.services.tax_service import TaxService
from backend.services.payment_service import PaymentService

router = APIRouter()
email_service = EmailService()
security = HTTPBearer()

async def get_current_user_info(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserInfo:
    """Get current user info from token"""
    token = credentials.credentials
    user_info = await get_current_user(token)
    return UserInfo(**user_info)

@router.post("/", response_model=TimesheetSchema)
async def create_timesheet(
    timesheet: TimesheetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user_info)
):
    """Create a new timesheet"""
    # Determine employee_id based on role
    employee_id = None
    if UserRole.ADMIN.value in current_user.groups or UserRole.MANAGER.value in current_user.groups:
        # Admin/Manager can submit for any employee
        employee_id = timesheet.employee_id
        # Validate employee exists
        employee_result = await db.execute(select(Employee).where(Employee.id == employee_id))
        employee = employee_result.scalar_one_or_none()
        if not employee:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee record not found")
    else:
        # Regular employee can only submit for themselves
        employee_result = await db.execute(select(Employee).where(Employee.cognito_sub == current_user.sub))
        employee = employee_result.scalar_one_or_none()
        if not employee:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee record not found")
        if timesheet.employee_id != employee.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only submit timesheets for yourself")
        employee_id = employee.id

    # Check if timesheet already exists for this period
    result = await db.execute(
        select(Timesheet).where(
            and_(
                Timesheet.employee_id == employee_id,
                Timesheet.week_start_date == timesheet.week_start_date
            )
        )
    )
    existing_timesheet = result.scalar_one_or_none()
    if existing_timesheet:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Timesheet already exists for this week"
        )

    # Create timesheet
    timesheet_data = timesheet.dict()
    timesheet_data['employee_id'] = employee_id
    # Calculate total_hours and overtime_hours
    total_hours = (
        timesheet_data['monday_hours'] +
        timesheet_data['tuesday_hours'] +
        timesheet_data['wednesday_hours'] +
        timesheet_data['thursday_hours'] +
        timesheet_data['friday_hours'] +
        timesheet_data['saturday_hours'] +
        timesheet_data['sunday_hours']
    )
    overtime_hours = max(0, total_hours - 40)
    timesheet_data['total_hours'] = total_hours
    timesheet_data['overtime_hours'] = overtime_hours
    db_timesheet = Timesheet(**timesheet_data)
    db.add(db_timesheet)
    await db.commit()
    await db.refresh(db_timesheet)
    return db_timesheet

@router.get("/", response_model=List[TimesheetSchema])
async def get_timesheets(
    employee_id: Optional[int] = None,
    week_start: Optional[str] = None,
    status: Optional[TimesheetStatus] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user_info)
):
    """Get timesheets list"""
    # Build query conditions
    conditions = []
    
    # Employee filter
    if employee_id:
        conditions.append(Timesheet.employee_id == employee_id)
    else:
        # If no specific employee requested, filter by current user's organization
        if current_user.org_id:
            conditions.append(Employee.org_id == int(current_user.org_id))
    
    # Week start filter
    if week_start:
        conditions.append(Timesheet.week_start_date == week_start)
    
    # Status filter
    if status:
        conditions.append(Timesheet.status == status)
    
    # Role-based access control
    if UserRole.EMPLOYEE.value in current_user.groups and UserRole.ADMIN.value not in current_user.groups:
        # Employees can only see their own timesheets
        employee_result = await db.execute(
            select(Employee).where(Employee.cognito_sub == current_user.sub)
        )
        employee = employee_result.scalar_one_or_none()
        if employee:
            conditions.append(Timesheet.employee_id == employee.id)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee record not found"
            )
    
    # Build query with joins if needed
    if any(cond.left.table.name == 'employee' for cond in conditions if hasattr(cond.left, 'table')):
        query = select(Timesheet).join(Employee, Timesheet.employee_id == Employee.id)
    else:
        query = select(Timesheet)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    timesheets = result.scalars().all()
    
    return timesheets

@router.get("/{timesheet_id}", response_model=TimesheetSchema)
async def get_timesheet(
    timesheet_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user_info)
):
    """Get timesheet by ID"""
    result = await db.execute(select(Timesheet).where(Timesheet.id == timesheet_id))
    timesheet = result.scalar_one_or_none()
    
    if not timesheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timesheet not found"
        )
    
    # Check permissions
    if UserRole.EMPLOYEE.value in current_user.groups and UserRole.ADMIN.value not in current_user.groups:
        employee_result = await db.execute(
            select(Employee).where(Employee.cognito_sub == current_user.sub)
        )
        employee = employee_result.scalar_one_or_none()
        if not employee or timesheet.employee_id != employee.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own timesheets"
            )
    
    return timesheet

@router.put("/{timesheet_id}", response_model=TimesheetSchema)
async def update_timesheet(
    timesheet_id: int,
    timesheet_update: TimesheetUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user_info)
):
    """Update timesheet"""
    result = await db.execute(select(Timesheet).where(Timesheet.id == timesheet_id))
    timesheet = result.scalar_one_or_none()
    
    if not timesheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timesheet not found"
        )
    
    # Check permissions
    if UserRole.EMPLOYEE.value in current_user.groups and UserRole.ADMIN.value not in current_user.groups:
        employee_result = await db.execute(
            select(Employee).where(Employee.cognito_sub == current_user.sub)
        )
        employee = employee_result.scalar_one_or_none()
        if not employee or timesheet.employee_id != employee.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own timesheets"
            )
        
        # Employees can only update timesheets that are not yet submitted
        if timesheet.status != TimesheetStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot update timesheet that is not in draft status"
            )
    
    # Update fields
    update_data = timesheet_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(timesheet, field, value)
    
    await db.commit()
    await db.refresh(timesheet)
    
    return timesheet

@router.post("/{timesheet_id}/approve", response_model=TimesheetSchema)
async def approve_timesheet(
    timesheet_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user_info)
):
    """Approve timesheet (Admin/Manager only)"""
    if UserRole.ADMIN.value not in current_user.groups:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can approve timesheets"
        )
    
    result = await db.execute(select(Timesheet).where(Timesheet.id == timesheet_id))
    timesheet = result.scalar_one_or_none()
    
    if not timesheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timesheet not found"
        )
    
    if timesheet.status != TimesheetStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only approve pending timesheets"
        )
    
    timesheet.status = TimesheetStatus.APPROVED
    await db.commit()
    await db.refresh(timesheet)
    
    return timesheet

@router.delete("/{timesheet_id}")
async def delete_timesheet(
    timesheet_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user_info)
):
    """Delete timesheet"""
    result = await db.execute(select(Timesheet).where(Timesheet.id == timesheet_id))
    timesheet = result.scalar_one_or_none()
    
    if not timesheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timesheet not found"
        )
    
    # Check if timesheet can be deleted
    if timesheet.status == TimesheetStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete approved timesheet"
        )
    
    # Check permissions
    if UserRole.EMPLOYEE.value in current_user.groups and UserRole.ADMIN.value not in current_user.groups:
        employee_result = await db.execute(
            select(Employee).where(Employee.id == timesheet.employee_id)
        )
        employee = employee_result.scalar_one_or_none()
        
        if not employee or employee.cognito_sub != current_user.sub:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own timesheets"
            )
    
    await db.delete(timesheet)
    await db.commit()
    
    return {"message": "Timesheet deleted successfully"}

@router.post("/{timesheet_id}/calculate-taxes")
async def calculate_taxes_for_timesheet(
    timesheet_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user_info)
):
    result = await db.execute(select(Timesheet).where(Timesheet.id == timesheet_id))
    timesheet = result.scalar_one_or_none()
    if not timesheet:
        raise HTTPException(status_code=404, detail="Timesheet not found")
    employee_result = await db.execute(select(Employee).where(Employee.id == timesheet.employee_id))
    employee = employee_result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    tax_config_result = await db.execute(select(TaxConfiguration).where(TaxConfiguration.org_id == employee.org_id, TaxConfiguration.is_active == True))
    tax_config = tax_config_result.scalar_one_or_none()
    if not tax_config:
        raise HTTPException(status_code=404, detail="Tax configuration not found")
    # Calculate gross pay
    if hasattr(employee, 'hourly_rate') and employee.hourly_rate:
        gross_pay = timesheet.total_hours * employee.hourly_rate
    elif hasattr(employee, 'base_salary') and employee.base_salary:
        # Assume weekly salary for the period
        gross_pay = employee.base_salary / 52
    else:
        raise HTTPException(status_code=400, detail="Employee pay rate not set")
    tax_service = TaxService()
    taxes = tax_service.calculate_taxes(gross_pay, tax_config, employee)
    return taxes

@router.post("/{timesheet_id}/pay")
async def pay_timesheet(
    timesheet_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user_info)
):
    # Only admin/manager can pay
    if UserRole.ADMIN.value not in current_user.groups and UserRole.MANAGER.value not in current_user.groups:
        raise HTTPException(status_code=403, detail="Only admin/manager can pay timesheets")
    result = await db.execute(select(Timesheet).where(Timesheet.id == timesheet_id))
    timesheet = result.scalar_one_or_none()
    if not timesheet:
        raise HTTPException(status_code=404, detail="Timesheet not found")
    employee_result = await db.execute(select(Employee).where(Employee.id == timesheet.employee_id))
    employee = employee_result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    tax_config_result = await db.execute(select(TaxConfiguration).where(TaxConfiguration.org_id == employee.org_id, TaxConfiguration.is_active == True))
    tax_config = tax_config_result.scalar_one_or_none()
    if not tax_config:
        raise HTTPException(status_code=404, detail="Tax configuration not found")
    # Calculate gross pay
    if hasattr(employee, 'hourly_rate') and employee.hourly_rate:
        gross_pay = timesheet.total_hours * employee.hourly_rate
    elif hasattr(employee, 'base_salary') and employee.base_salary:
        gross_pay = employee.base_salary / 52
    else:
        raise HTTPException(status_code=400, detail="Employee pay rate not set")
    tax_service = TaxService()
    taxes = tax_service.calculate_taxes(gross_pay, tax_config, employee)
    net_pay = taxes['net_pay']
    payment_service = PaymentService()
    payment_result = await payment_service.send_payment_via_plaid(net_pay, employee.id, f"Timesheet {timesheet_id} payment", db)
    return payment_result 
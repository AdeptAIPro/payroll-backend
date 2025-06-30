from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from datetime import datetime
from backend.database import get_db
from backend.orm_models import Payslip, Employee, UserRole
from backend.schemas import Payslip as PayslipSchema, UserInfo
import boto3
from backend.config import settings
from backend.services.pdf_service import generate_payslip_pdf
from backend.services.auth_service import get_current_user

router = APIRouter()

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

@router.get("/", response_model=List[PayslipSchema])
async def get_payslips(
    employee_id: Optional[int] = None,
    payroll_run_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user_info)
):
    """Get payslips list"""
    # Build query conditions
    conditions = []
    
    # Employee filter
    if employee_id:
        conditions.append(Payslip.employee_id == employee_id)
    
    # Payroll run filter
    if payroll_run_id:
        conditions.append(Payslip.payroll_run_id == payroll_run_id)
    
    # Role-based access control
    if UserRole.EMPLOYEE.value in current_user.groups and UserRole.ADMIN.value not in current_user.groups:
        # Employees can only see their own payslips
        employee_result = await db.execute(
            select(Employee).where(Employee.cognito_sub == current_user.sub)
        )
        employee = employee_result.scalar_one_or_none()
        if employee:
            conditions.append(Payslip.employee_id == employee.id)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee record not found"
            )
    
    query = select(Payslip)
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    payslips = result.scalars().all()
    
    return payslips

@router.get("/{payslip_id}", response_model=PayslipSchema)
async def get_payslip(
    payslip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user_info)
):
    """Get payslip by ID"""
    result = await db.execute(select(Payslip).where(Payslip.id == payslip_id))
    payslip = result.scalar_one_or_none()
    
    if not payslip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payslip not found"
        )
    
    # Check permissions
    if UserRole.EMPLOYEE.value in current_user.groups and UserRole.ADMIN.value not in current_user.groups:
        employee_result = await db.execute(
            select(Employee).where(Employee.cognito_sub == current_user.sub)
        )
        employee = employee_result.scalar_one_or_none()
        if not employee or payslip.employee_id != employee.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own payslips"
            )
    
    return payslip

@router.get("/{payslip_id}/download")
async def download_payslip(
    payslip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user_info)
):
    """Get payslip PDF download URL"""
    result = await db.execute(select(Payslip).where(Payslip.id == payslip_id))
    payslip = result.scalar_one_or_none()
    if not payslip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payslip not found"
        )
    # Check permissions
    if UserRole.EMPLOYEE.value in current_user.groups and UserRole.ADMIN.value not in current_user.groups:
        employee_result = await db.execute(
            select(Employee).where(Employee.id == payslip.employee_id)
        )
        employee = employee_result.scalar_one_or_none()
        if not employee or employee.cognito_sub != current_user.sub:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    if not payslip.pdf_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payslip PDF not available"
        )
    # Generate fresh presigned URL
    s3 = boto3.client(
        "s3",
        region_name=settings.S3_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )
    # Extract bucket and key from the stored URL or config
    bucket = settings.S3_BUCKET_NAME
    # Assume pdf_url is the S3 key (path in bucket)
    key = payslip.pdf_url if not payslip.pdf_url.startswith("https://") else payslip.pdf_url.split(f"/{bucket}/", 1)[-1]
    presigned_url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=60000000  # 10 minutes
    )
    return {"download_url": presigned_url} 
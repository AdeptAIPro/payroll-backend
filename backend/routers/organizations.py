from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from backend.database import get_db
from backend.orm_models import Organization, TaxConfiguration, UserRole
from backend.schemas import (
    Organization as OrganizationSchema, 
    OrganizationCreate,
    TaxConfiguration as TaxConfigurationSchema,
    TaxConfigurationCreate,
    UserInfo
)
from backend.services.auth_service import get_current_user
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter()
security = HTTPBearer()

async def get_current_user_info(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserInfo:
    """Get current user info from token"""
    token = credentials.credentials
    user_info = await get_current_user(token)
    return UserInfo(**user_info)

@router.post("/", response_model=OrganizationSchema)
async def create_organization(
    organization: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user_info)
):
    """Create a new organization (Admin only)"""
    if UserRole.ADMIN.value not in current_user.groups:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create organizations"
        )
    
    # Check if organization already exists
    result = await db.execute(
        select(Organization).where(Organization.name == organization.name)
    )
    existing_org = result.scalar_one_or_none()
    
    if existing_org:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization with this name already exists"
        )
    
    db_organization = Organization(**organization.dict())
    db.add(db_organization)
    await db.commit()
    await db.refresh(db_organization)
    
    return db_organization

@router.get("/public", response_model=List[OrganizationSchema])
async def get_public_organizations(
    db: AsyncSession = Depends(get_db)
):
    """Get public organizations (no auth required)"""
    result = await db.execute(select(Organization))
    organizations = result.scalars().all()
    return organizations

@router.get("/", response_model=List[OrganizationSchema])
async def get_organizations(
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user_info)
):
    """Get organizations list"""
    # For now, return all organizations
    # In a real app, you might want to filter based on user permissions
    result = await db.execute(select(Organization))
    organizations = result.scalars().all()
    return organizations

@router.get("/{org_id}", response_model=OrganizationSchema)
async def get_organization(
    org_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user_info)
):
    """Get organization by ID"""
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    organization = result.scalar_one_or_none()
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    return organization

@router.post("/{org_id}/tax-config", response_model=TaxConfigurationSchema)
async def create_tax_configuration(
    org_id: int,
    tax_config: TaxConfigurationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user_info)
):
    """Create tax configuration for organization (Admin only)"""
    if UserRole.ADMIN.value not in current_user.groups:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create tax configurations"
        )
    
    # Check if organization exists
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    organization = result.scalar_one_or_none()
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Check if tax config already exists
    existing_result = await db.execute(
        select(TaxConfiguration).where(TaxConfiguration.org_id == org_id)
    )
    existing_config = existing_result.scalar_one_or_none()
    
    if existing_config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tax configuration already exists for this organization"
        )
    
    # Create tax configuration
    tax_config_data = tax_config.dict()
    tax_config_data['org_id'] = org_id
    db_tax_config = TaxConfiguration(**tax_config_data)
    db.add(db_tax_config)
    await db.commit()
    await db.refresh(db_tax_config)
    
    return db_tax_config

@router.get("/{org_id}/tax-config", response_model=TaxConfigurationSchema)
async def get_tax_configuration(
    org_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user_info)
):
    """Get tax configuration for organization"""
    result = await db.execute(
        select(TaxConfiguration).where(TaxConfiguration.org_id == org_id)
    )
    tax_config = result.scalar_one_or_none()
    
    if not tax_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tax configuration not found"
        )
    
    return tax_config

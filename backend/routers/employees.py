from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from typing import List, Optional
from backend.database import get_db
from backend.orm_models import Employee, UserRole, SalaryType, Payslip, BankAccount, EmergencyContact, Compensation, TaxInfo, OnboardingStatus, EmployeeOnboardingDraft, Compensation as CompensationModel, EmergencyContact as EmergencyContactModel, BankAccount as BankAccountModel
from backend.schemas import Employee as EmployeeSchema, EmployeeCreate, EmployeeUpdate, UserInfo, Payslip as PayslipSchema, BankAccount as BankAccountSchema, EmergencyContactCreate, EmergencyContact, CompensationCreate, Compensation, W2EmployeeOnboardingDraft, W2EmployeeOnboarding
from backend.services.auth_service import get_current_user, cognito_service
from backend.services.email_service import EmailService
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import boto3
import hmac
import hashlib
import base64
from backend.config import settings
import shutil
import os
from sqlalchemy.future import select
from sqlalchemy.exc import NoResultFound, IntegrityError
from datetime import datetime
import logging

router = APIRouter()
security = HTTPBearer()
email_service = EmailService()

def calculate_secret_hash(username: str) -> str:
    """Calculate SECRET_HASH for Cognito requests"""
    key = settings.COGNITO_CLIENT_SECRET.encode()
    msg = (username + settings.COGNITO_CLIENT_ID).encode()
    dig = hmac.new(key, msg, hashlib.sha256).digest()
    return base64.b64encode(dig).decode()

async def get_current_user_info(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserInfo:
    """Get current user info from token"""
    token = credentials.credentials
    user_info = await get_current_user(token)
    return UserInfo(**user_info)

@router.post("/", response_model=EmployeeSchema)
async def create_employee(
    employee: EmployeeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user_info)
):
    """Create a new employee (Admin only)"""
    if "admin" not in current_user.get("groups", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create employees"
        )
    
    # Initialize Cognito client
    client = boto3.client(
        "cognito-idp",
        region_name=settings.COGNITO_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )
    
    cognito_sub = None
    
    # If cognito_sub is provided, use it; otherwise create new Cognito user
    if employee.cognito_sub and not employee.cognito_sub.startswith('temp_'):
        cognito_sub = employee.cognito_sub
        # Verify the user exists in Cognito
        try:
            client.admin_get_user(
                UserPoolId=settings.COGNITO_USER_POOL_ID,
                Username=employee.email
            )
        except client.exceptions.UserNotFoundException:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cognito user not found. Please create the user in Cognito first or leave cognito_sub empty to auto-create."
            )
    else:
        # Auto-create Cognito user
        try:
            # Generate a temporary password
            temp_password = f"Temp{employee.first_name}{employee.last_name}123!"
            
            # Create user in Cognito
            cognito_response = client.admin_create_user(
                UserPoolId=settings.COGNITO_USER_POOL_ID,
                Username=employee.email,
                UserAttributes=[
                    {"Name": "email", "Value": employee.email},
                    {"Name": "given_name", "Value": employee.first_name},
                    {"Name": "family_name", "Value": employee.last_name},
                    {"Name": "name", "Value": f"{employee.first_name} {employee.last_name}"},
                    {"Name": "email_verified", "Value": "true"},
                ],
                TemporaryPassword=temp_password,
                MessageAction="SUPPRESS"  # Don't send welcome email
            )
            
            cognito_sub = cognito_response['User']['Username']
            
            # Add user to appropriate group based on role
            try:
                client.admin_add_user_to_group(
                    UserPoolId=settings.COGNITO_USER_POOL_ID,
                    Username=employee.email,
                    GroupName=employee.role
                )
                print(f"Added user to {employee.role} group")
            except Exception as e:
                print(f"Error adding user to group: {e}")
            
            print(f"Created Cognito user with sub: {cognito_sub}")
            
            # Send welcome email with temporary password
            try:
                await email_service.send_welcome_email(
                    to_email=employee.email,
                    employee_name=f"{employee.first_name} {employee.last_name}",
                    temp_password=temp_password
                )
            except Exception as e:
                print(f"Error sending welcome email: {e}")
                # Don't fail the employee creation if email fails
            
        except client.exceptions.UsernameExistsException:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already exists in Cognito. Please provide the existing cognito_sub."
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating Cognito user: {str(e)}"
            )
    
    # Check if employee already exists
    result = await db.execute(
        select(Employee).where(
            (Employee.email == employee.email) | 
            (Employee.cognito_sub == cognito_sub)
        )
    )
    existing_employee = result.scalar_one_or_none()
    
    if existing_employee:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee with this email or Cognito sub already exists"
        )
    
    # Create employee record with the cognito_sub
    employee_data = employee.dict()
    employee_data['cognito_sub'] = cognito_sub
    db_employee = Employee(**employee_data)
    db.add(db_employee)
    await db.commit()
    await db.refresh(db_employee)

    # If we auto-created a Cognito user, print the temp password
    if not employee.cognito_sub or employee.cognito_sub.startswith('temp_'):
        temp_password = f"Temp{employee.first_name}{employee.last_name}123!"
        print(f"Cognito user created with temporary password: {temp_password}")

    return db_employee

@router.get("/", response_model=List[EmployeeSchema])
async def get_employees(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    department: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user_info)
):
    """Get employees list"""
    # Build query conditions
    conditions = []
    
    # Organization filter
    if current_user.org_id:
        conditions.append(Employee.org_id == int(current_user.org_id))
    
    # Department filter
    if department:
        conditions.append(Employee.department == department)
    
    # Active status filter
    if is_active is not None:
        conditions.append(Employee.is_active == is_active)
    
    # Role-based access control
    if UserRole.EMPLOYEE.value in current_user.groups and UserRole.ADMIN.value not in current_user.groups:
        # Employees can only see themselves
        conditions.append(Employee.cognito_sub == current_user.sub)
    
    query = select(Employee)
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    employees = result.scalars().all()
    
    return employees

@router.get("/{employee_id}", response_model=EmployeeSchema)
async def get_employee(
    employee_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user_info)
):
    """Get employee by ID, including compensation, emergency_contacts, and bank_accounts"""
    result = await db.execute(select(Employee).where(Employee.id == employee_id))
    employee = result.scalar_one_or_none()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    # Permissions
    if UserRole.EMPLOYEE.value in current_user.groups and UserRole.ADMIN.value not in current_user.groups:
        if employee.cognito_sub != current_user.sub:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own profile"
            )
    # Fetch related data
    comp_result = await db.execute(select(CompensationModel).where(CompensationModel.employee_id == employee_id))
    compensation = comp_result.scalar_one_or_none()
    contacts_result = await db.execute(select(EmergencyContactModel).where(EmergencyContactModel.employee_id == employee_id))
    emergency_contacts = contacts_result.scalars().all()
    bank_result = await db.execute(select(BankAccountModel).where(BankAccountModel.employee_id == employee_id))
    bank_accounts = bank_result.scalars().all()
    # Serialize
    emp_dict = EmployeeSchema.model_validate(employee, from_attributes=True).dict()
    emp_dict["compensation"] = compensation.dict() if compensation else None
    emp_dict["emergency_contacts"] = [c.dict() for c in emergency_contacts]
    emp_dict["bank_accounts"] = [b.dict() for b in bank_accounts]
    return emp_dict

@router.put("/{employee_id}", response_model=EmployeeSchema)
async def update_employee(
    employee_id: int,
    employee_update: EmployeeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user_info)
):
    """Update employee (Admin only)"""
    result = await db.execute(select(Employee).where(Employee.id == employee_id))
    employee = result.scalar_one_or_none()
    
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    # Check permissions
    if "admin" not in current_user.get("groups", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update employees"
        )
    
    # Update fields
    update_data = employee_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(employee, field, value)
    
    await db.commit()
    await db.refresh(employee)
    
    return employee

@router.delete("/{employee_id}")
async def delete_employee(
    employee_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user_info)
):
    """Delete employee (Admin only)"""
    if "admin" not in current_user.get("groups", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete employees"
        )
    
    result = await db.execute(select(Employee).where(Employee.id == employee_id))
    employee = result.scalar_one_or_none()
    
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    # Soft delete by setting is_active to False
    employee.is_active = False
    await db.commit()
    
    return {"message": "Employee deleted successfully"}

@router.get("/me/profile", response_model=EmployeeSchema)
async def get_my_profile(
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user_info)
):
    """Get current user's employee profile"""
    result = await db.execute(
        select(Employee).where(Employee.cognito_sub == current_user.sub)
    )
    employee = result.scalar_one_or_none()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found"
        )
    return employee

@router.get("/me/salary")
async def get_my_salary(
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user_info)
):
    """Get current user's most recent payslip (salary info)"""
    result = await db.execute(
        select(Payslip)
        .join(Employee, Payslip.employee_id == Employee.id)
        .where(Employee.cognito_sub == current_user.sub)
        .order_by(desc(Payslip.pay_date))
        .limit(1)
    )
    payslip = result.scalar_one_or_none()
    return payslip

@router.get("/me/bank-account")
async def get_my_bank_account(
    db: AsyncSession = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user_info)
):
    """Get current user's bank account info"""
    result = await db.execute(
        select(Employee).where(Employee.cognito_sub == current_user.sub)
    )
    employee = result.scalar_one_or_none()
    if not employee or not employee.bank_account_id:
        return None
    result = await db.execute(
        select(BankAccount).where(BankAccount.id == employee.bank_account_id)
    )
    bank_account = result.scalar_one_or_none()
    return bank_account

@router.post("/onboard", response_model=EmployeeSchema)
async def onboard_employee(
    employee: EmployeeCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    # Only admin can onboard
    if "admin" not in current_user.get("groups", []):
        raise HTTPException(status_code=403, detail="Not authorized")
    # Create user in Cognito
    sub, temp_password = cognito_service.create_user(
        email=employee.email,
        first_name=employee.first_name,
        last_name=employee.last_name
    )
    # Create employee in DB with cognito_sub
    employee_data = employee.dict()
    employee_data["cognito_sub"] = sub
    db_employee = Employee(**employee_data)
    db.add(db_employee)
    await db.commit()
    await db.refresh(db_employee)
    # Send welcome email with temp password
    await email_service.send_welcome_email(
        to_email=employee.email,
        employee_name=f"{employee.first_name} {employee.last_name}",
        temp_password=temp_password
    )
    return db_employee

@router.post("/{employee_id}/emergency-contacts", response_model=EmergencyContact)
async def add_emergency_contact(
    employee_id: int,
    contact: EmergencyContactCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    # Only admin or self
    if "admin" not in current_user.get("groups", []) and current_user['id'] != employee_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    db_contact = EmergencyContact(employee_id=employee_id, **contact.dict())
    db.add(db_contact)
    await db.commit()
    await db.refresh(db_contact)
    return db_contact

@router.get("/{employee_id}/emergency-contacts", response_model=List[EmergencyContact])
async def list_emergency_contacts(
    employee_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    contacts = await db.execute(
        select(EmergencyContact).where(EmergencyContact.employee_id == employee_id)
    )
    return contacts.scalars().all()

@router.delete("/{employee_id}/emergency-contacts/{contact_id}")
async def delete_emergency_contact(
    employee_id: int,
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    contact = await db.get(EmergencyContact, contact_id)
    if not contact or contact.employee_id != employee_id:
        raise HTTPException(status_code=404, detail="Contact not found")
    if "admin" not in current_user.get("groups", []) and current_user['id'] != employee_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    await db.delete(contact)
    await db.commit()
    return {"detail": "Deleted"}

@router.post("/{employee_id}/upload-document")
async def upload_document(
    employee_id: int,
    doc_type: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    # Only admin or self
    if "admin" not in current_user.get("groups", []) and current_user['id'] != employee_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    # Save file to S3 or local (mock here)
    file_location = f"uploads/{employee_id}_{doc_type}_{file.filename}"
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    # Update TaxInfo
    tax_info = await db.execute(select(TaxInfo).where(TaxInfo.employee_id == employee_id))
    tax_info = tax_info.scalar_one_or_none()
    if not tax_info:
        tax_info = TaxInfo(employee_id=employee_id)
        db.add(tax_info)
    if doc_type == "i9":
        tax_info.i9_document_url = file_location
    elif doc_type == "w4":
        tax_info.w4_document_url = file_location
    await db.commit()
    return {"url": file_location}

@router.put("/{employee_id}/onboarding-status")
async def update_onboarding_status(
    employee_id: int,
    status: OnboardingStatus,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    # Only admin
    if "admin" not in current_user.get("groups", []):
        raise HTTPException(status_code=403, detail="Not authorized")
    employee = await db.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    employee.onboarding_status = status
    await db.commit()
    return {"status": status}

@router.patch("/api/employees/{draft_id}", response_model=W2EmployeeOnboardingDraft)
async def save_employee_draft(draft_id: int, data: dict = Body(...), db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    # Only admin or self
    draft = await db.get(EmployeeOnboardingDraft, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    # Merge data
    draft.data.update(data)
    draft.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(draft)
    return draft

@router.post("/api/employees/w2", response_model=EmployeeSchema)
async def finalize_employee_onboarding(payload: W2EmployeeOnboarding, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    # Only admin
    if "admin" not in current_user.get("groups", []):
        raise HTTPException(status_code=403, detail="Not authorized")
    data = payload.dict()
    try:
        # 1. Cognito user creation
        client = boto3.client(
            "cognito-idp",
            region_name=settings.COGNITO_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        cognito_sub = None
        email = data.get("email")
        first_name = data["legal_first_name"]
        last_name = data["legal_last_name"]
        try:
            # Try to get user
            user = client.admin_get_user(
                UserPoolId=settings.COGNITO_USER_POOL_ID,
                Username=email
            )
            cognito_sub = user["Username"]
        except client.exceptions.UserNotFoundException:
            # Create user
            temp_password = f"Temp{first_name}{last_name}123!"
            resp = client.admin_create_user(
                UserPoolId=settings.COGNITO_USER_POOL_ID,
                Username=email,
                UserAttributes=[
                    {"Name": "email", "Value": email},
                    {"Name": "given_name", "Value": first_name},
                    {"Name": "family_name", "Value": last_name},
                    {"Name": "name", "Value": f"{first_name} {last_name}"},
                    {"Name": "email_verified", "Value": "true"},
                ],
                TemporaryPassword=temp_password,
                MessageAction="SUPPRESS"
            )
            cognito_sub = resp["User"]["Username"]
            # Add to group
            try:
                client.admin_add_user_to_group(
                    UserPoolId=settings.COGNITO_USER_POOL_ID,
                    Username=email,
                    GroupName="employee"
                )
            except Exception as e:
                logging.error(f"Error adding user to group: {e}")
            # Send welcome email
            try:
                await email_service.send_welcome_email(
                    to_email=email,
                    employee_name=f"{first_name} {last_name}",
                    temp_password=temp_password
                )
            except Exception as e:
                logging.error(f"Error sending welcome email: {e}")
        # 2. Create Employee
        employee = Employee(
            cognito_sub=cognito_sub,
            org_id=data["organization"],
            employee_id=data["employee_id"],
            first_name=first_name,
            last_name=last_name,
            email=email,
            role=UserRole.EMPLOYEE,
            department=data.get("department"),
            position=data.get("position"),
            salary_type=SalaryType.FIXED if any(r["pay_type"].lower() == "salary" for r in data["compensation_rates"]) else SalaryType.HOURLY,
            base_salary=float(data["compensation_rates"][0]["amount"]),
            hire_date=data["hire_date"],
            ssn=data["ssn"],
            address=data["address_line1"],
            city=data["city"],
            state=data["state"],
            zip_code=data["zip_code"],
            birth_date=data["birth_date"],
            onboarding_status=OnboardingStatus.COMPLETE,
            is_active=True
        )
        db.add(employee)
        await db.flush()  # Get employee.id
        # 3. Compensation
        for rate in data["compensation_rates"]:
            comp = Compensation(
                employee_id=employee.id,
                compensation_type=rate["pay_type"],
                amount=rate["amount"],
                start_date=data["hire_date"]
            )
            db.add(comp)
        # 4. Tax Info
        tax = TaxInfo(
            employee_id=employee.id,
            w4_status=data["filing_status"],
            state=data["state"],
            exemptions=int(data.get("dependents", 0)),
            i9_verified=True if data.get("i9_completer") else False
        )
        db.add(tax)
        # 5. Emergency Contacts
        for contact in data.get("emergency_contacts", []):
            ec = EmergencyContact(
                employee_id=employee.id,
                name=contact["name"],
                relationship=contact["relationship"],
                phone=contact["phone"],
                email=contact.get("email")
            )
            db.add(ec)
        # 6. Bank Accounts (Direct Deposit)
        for acct in data.get("direct_deposit_accounts", []):
            ba = BankAccount(
                employee_id=employee.id,
                account_name=acct["bank_name"],
                account_type=acct["account_type"],
                account_number=acct["account_number"],
                routing_number=acct["routing_number"],
                is_primary=acct.get("is_primary", False)
            )
            db.add(ba)
        # TODO: Add earnings/deductions, EEO, time off, etc.
        await db.commit()
        # 7. Mark draft as complete if draft_id present
        draft_id = data.get("draft_id")
        if draft_id:
            draft = await db.get(EmployeeOnboardingDraft, draft_id)
            if draft:
                draft.status = "complete"
                await db.commit()
        await db.refresh(employee)
        return employee
    except IntegrityError as e:
        await db.rollback()
        logging.error(f"DB Integrity error: {e}")
        raise HTTPException(status_code=400, detail="Duplicate or invalid data")
    except Exception as e:
        await db.rollback()
        logging.error(f"Onboarding error: {e}")
        raise HTTPException(status_code=500, detail=f"Onboarding failed: {str(e)}")

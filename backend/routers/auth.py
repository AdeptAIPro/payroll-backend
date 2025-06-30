from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.services.auth_service import cognito_service, get_current_user
from backend.schemas import UserInfo, Token
from backend.config import settings
from backend.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.orm_models import Employee, UserRole, SalaryType, Organization
from decimal import Decimal
import boto3
import hmac
import hashlib
import base64
from typing import Optional
from pydantic import BaseModel

router = APIRouter()
security = HTTPBearer()

class SignupRequest(BaseModel):
    email: str
    password: str
    given_name: str
    family_name: str
    org_id: str
    role: str

class ConfirmRequest(BaseModel):
    email: str
    confirmation_code: str

class LoginRequest(BaseModel):
    email: str
    password: str

def calculate_secret_hash(username: str) -> str:
    """Calculate SECRET_HASH for Cognito requests"""
    key = settings.COGNITO_CLIENT_SECRET.encode()
    msg = (username + settings.COGNITO_CLIENT_ID).encode()
    dig = hmac.new(key, msg, hashlib.sha256).digest()
    return base64.b64encode(dig).decode()

@router.post("/signup")
async def signup(
    request: SignupRequest,
    db: AsyncSession = Depends(get_db),
):
    """Sign up a new user with Cognito"""
    # No org_id validation, allow any string
    client = boto3.client(
        "cognito-idp",
        region_name=settings.COGNITO_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )
    
    try:
        attributes = [
            {"Name": "email", "Value": request.email},
            {"Name": "given_name", "Value": request.given_name},
            {"Name": "family_name", "Value": request.family_name},
            {"Name": "name", "Value": f"{request.given_name} {request.family_name}"},
            {"Name": "custom:organizationId", "Value": request.org_id},
            {"Name": "custom:role", "Value": request.role},
        ]
        print("Cognito signup attributes:", attributes)
        response = client.sign_up(
            ClientId=settings.COGNITO_CLIENT_ID,
            SecretHash=calculate_secret_hash(request.email),
            Username=request.email,
            Password=request.password,
            UserAttributes=attributes,
        )
        
        # Auto-confirm the user
        try:
            client.admin_confirm_sign_up(
                UserPoolId=settings.COGNITO_USER_POOL_ID,
                Username=request.email
            )
        except client.exceptions.NotAuthorizedException as e:
            if "Current status is CONFIRMED" not in str(e):
                raise
        
        # Add user to appropriate group based on role
        role = request.role.lower()
        if role in ["admin", "manager", "employee"]:
            try:
                client.admin_add_user_to_group(
                    UserPoolId=settings.COGNITO_USER_POOL_ID,
                    Username=request.email,
                    GroupName=role
                )
                print(f"Added user to {role} group")
            except Exception as e:
                print(f"Error adding user to group: {e}")
                # Don't fail the signup if group assignment fails
        
        # Create employee record in database
        try:
            # Generate employee ID (you might want to implement a more sophisticated ID generation)
            employee_id = f"EMP{response.get('UserSub', '')[-8:].upper()}"
            
            # Create employee record
            employee = Employee(
                cognito_sub=response.get("UserSub"),
                org_id=request.org_id,  # Store as string
                employee_id=employee_id,
                first_name=request.given_name,
                last_name=request.family_name,
                email=request.email,
                role=UserRole(role),
                salary_type=SalaryType.FIXED,  # Default to fixed salary
                base_salary=Decimal('50000.00'),  # Default salary
                is_active=True
            )
            
            db.add(employee)
            await db.commit()
            await db.refresh(employee)
            
            print(f"Created employee record: {employee.id}")
            
        except Exception as e:
            print(f"Error creating employee record: {e}")
            # Don't fail the signup if employee creation fails
            # The user can still sign up and an admin can create their employee record later
        
        return {
            "message": "Sign up successful. You can now log in.",
            "user_sub": response.get("UserSub"),
            "user_confirmed": True
        }
        
    except client.exceptions.UsernameExistsException:
        raise HTTPException(status_code=400, detail="User already exists")
    except client.exceptions.InvalidPasswordException as e:
        raise HTTPException(status_code=400, detail="Password does not meet requirements")
    except client.exceptions.InvalidParameterException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sign up failed: {str(e)}")

@router.post("/confirm")
async def confirm_signup(
    request: ConfirmRequest,
):
    """Confirm user signup with verification code"""
    client = boto3.client(
        "cognito-idp",
        region_name=settings.COGNITO_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )
    
    try:
        response = client.confirm_sign_up(
            ClientId=settings.COGNITO_CLIENT_ID,
            SecretHash=calculate_secret_hash(request.email),
            Username=request.email,
            ConfirmationCode=request.confirmation_code,
        )
        
        return {"message": "Email confirmed successfully"}
        
    except client.exceptions.CodeMismatchException:
        raise HTTPException(status_code=400, detail="Invalid confirmation code")
    except client.exceptions.NotAuthorizedException:
        raise HTTPException(status_code=400, detail="User is already confirmed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Confirmation failed: {str(e)}")

@router.post("/login")
async def login(
    request: LoginRequest,
):
    """Login user with Cognito"""
    client = boto3.client(
        "cognito-idp",
        region_name=settings.COGNITO_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )
    
    try:
        response = client.admin_initiate_auth(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            ClientId=settings.COGNITO_CLIENT_ID,
            AuthFlow="ADMIN_NO_SRP_AUTH",
            AuthParameters={
                "USERNAME": request.email,
                "PASSWORD": request.password,
                "SECRET_HASH": calculate_secret_hash(request.email),
            },
        )
        
        # Get user info including groups
        user_info = await get_user_info_from_cognito(request.email)
        
        return {
            "message": "Login successful",
            "access_token": response["AuthenticationResult"]["AccessToken"],
            "id_token": response["AuthenticationResult"]["IdToken"],
            "refresh_token": response["AuthenticationResult"]["RefreshToken"],
            "user": user_info
        }
        
    except client.exceptions.NotAuthorizedException:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    except client.exceptions.UserNotConfirmedException:
        raise HTTPException(status_code=400, detail="User not confirmed. Please check your email.")
    except client.exceptions.UserNotFoundException:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")

async def get_user_info_from_cognito(username: str) -> dict:
    """Get user information from Cognito"""
    client = boto3.client(
        "cognito-idp",
        region_name=settings.COGNITO_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )
    
    try:
        # Get user attributes
        response = client.admin_get_user(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            Username=username
        )
        
        user_info = {
            'sub': response['Username'],
            'email': '',
            'given_name': '',
            'family_name': '',
            'groups': [],
            'org_id': None
        }
        
        for attr in response.get('UserAttributes', []):
            name = attr['Name']
            value = attr['Value']
            
            if name == 'email':
                user_info['email'] = value
            elif name == 'given_name':
                user_info['given_name'] = value
            elif name == 'family_name':
                user_info['family_name'] = value
            elif name == 'custom:organizationId':
                user_info['org_id'] = value
        
        # Get user groups
        try:
            groups_response = client.admin_list_groups_for_user(
                UserPoolId=settings.COGNITO_USER_POOL_ID,
                Username=username
            )
            user_info['groups'] = [group['GroupName'].lower() for group in groups_response.get('Groups', [])]
            print(f"User groups: {user_info['groups']}")
        except Exception as e:
            print(f"Error getting user groups: {e}")
            user_info['groups'] = []
        
        return user_info
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting user info: {str(e)}")

@router.post("/verify", response_model=UserInfo)
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token and return user info"""
    token = credentials.credentials
    user_info = await get_current_user(token)
    return UserInfo(**user_info)

@router.get("/me", response_model=UserInfo)
async def get_me(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user information"""
    token = credentials.credentials
    user_info = await get_current_user(token)
    return UserInfo(**user_info)

import boto3
import jwt
import requests
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from backend.config import settings
import json

class CognitoService:
    def __init__(self):
        self.region = settings.COGNITO_REGION
        self.user_pool_id = settings.COGNITO_USER_POOL_ID
        self.client_id = settings.COGNITO_CLIENT_ID
        self.client_secret = settings.COGNITO_CLIENT_SECRET
        
        # Initialize Cognito client
        self.cognito_client = boto3.client(
            'cognito-idp',
            region_name=self.region,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        
        # Get JWKs for token verification
        self.jwks_url = f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}/.well-known/jwks.json"
        self.jwks = self._get_jwks()
    
    def _get_jwks(self) -> Dict[str, Any]:
        """Get JSON Web Key Set from Cognito"""
        try:
            response = requests.get(self.jwks_url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching JWKS: {e}")
            return {"keys": []}
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token and return claims"""
        try:
            # Decode header to get kid
            header = jwt.get_unverified_header(token)
            kid = header.get('kid')
            
            # Find the correct key
            key = None
            for jwk in self.jwks.get('keys', []):
                if jwk.get('kid') == kid:
                    key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))
                    break
            
            if not key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: Key not found"
                )
            
            # Verify and decode token
            payload = jwt.decode(
                token,
                key,
                algorithms=['RS256'],
                audience=self.client_id,
                issuer=f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}",
                options={"verify_aud": False}  # Disable audience check for development
            )
            # Ensure all required fields for UserInfo are present
            user_info = {
                'sub': payload.get('sub'),
                'email': payload.get('email', ''),
                'given_name': payload.get('given_name', ''),
                'family_name': payload.get('family_name', ''),
                'groups': payload.get('groups', []),
                'org_id': payload.get('org_id', None)
            }
            return user_info
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )
    
    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from Cognito"""
        try:
            response = self.cognito_client.get_user(AccessToken=access_token)
            
            # Parse user attributes
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
                elif name == 'custom:org_id':
                    user_info['org_id'] = value
            
            # Get user groups
            try:
                groups_response = self.cognito_client.admin_list_groups_for_user(
                    UserPoolId=self.user_pool_id,
                    Username=response['Username']
                )
                user_info['groups'] = [group['GroupName'].lower() for group in groups_response.get('Groups', [])]
            except Exception as e:
                print(f"Error getting user groups: {e}")
            
            return user_info
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Error getting user info: {str(e)}"
            )

    def create_user(self, email: str, first_name: str, last_name: str, temp_password: str = None) -> str:
        """Create a new user in AWS Cognito and return the sub."""
        try:
            if not temp_password:
                import random, string
                temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12)) + '1!Aa'
            response = self.cognito_client.admin_create_user(
                UserPoolId=self.user_pool_id,
                Username=email,
                UserAttributes=[
                    {'Name': 'email', 'Value': email},
                    {'Name': 'email_verified', 'Value': 'true'},
                    {'Name': 'given_name', 'Value': first_name},
                    {'Name': 'family_name', 'Value': last_name},
                ],
                TemporaryPassword=temp_password,
                MessageAction='SUPPRESS',  # Don't send email automatically
                DesiredDeliveryMediums=['EMAIL'],
            )
            # Get sub from attributes
            sub = None
            for attr in response['User']['Attributes']:
                if attr['Name'] == 'sub':
                    sub = attr['Value']
                    break
            if not sub:
                # fallback: get user by username
                user = self.cognito_client.admin_get_user(UserPoolId=self.user_pool_id, Username=email)
                for attr in user['UserAttributes']:
                    if attr['Name'] == 'sub':
                        sub = attr['Value']
                        break
            return sub, temp_password
        except self.cognito_client.exceptions.UsernameExistsException:
            raise HTTPException(status_code=400, detail='User already exists in Cognito')
        except Exception as e:
            raise HTTPException(status_code=500, detail=f'Error creating Cognito user: {e}')

# Global instance
cognito_service = CognitoService()

async def verify_token(token: str) -> Dict[str, Any]:
    """Verify token and return user info"""
    return cognito_service.verify_token(token)

async def get_current_user(token: str) -> Dict[str, Any]:
    """Get current user information"""
    return cognito_service.get_user_info(token)

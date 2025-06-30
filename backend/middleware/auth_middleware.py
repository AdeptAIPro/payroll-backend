from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.services.auth_service import verify_token
from backend.utils.logger import api_logger
from backend.config import settings

security = HTTPBearer()

async def verify_auth_token(credentials: HTTPAuthorizationCredentials = None):
    """Verify authentication token"""
    if not credentials:
        api_logger.error("No authentication credentials provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No authentication credentials provided"
        )
    
    try:
        user_info = await verify_token(credentials.credentials)
        api_logger.info(f"Authentication successful for user: {user_info.get('sub')} with groups: {user_info.get('groups', [])}")
        return user_info
    except Exception as e:
        api_logger.error(f"Authentication failed: {str(e)}")
        
        # For development/testing, use test user if enabled
        if settings.ENABLE_TEST_USER:
            api_logger.warning("Using test user due to auth failure")
            return {
                "sub": "test_user_123",
                "email": "test@example.com",
                "given_name": "Test",
                "family_name": "User",
                "groups": ["admin"],
                "org_id": "1"
            }
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

async def auth_middleware(request: Request, call_next):
    """Authentication middleware"""
    try:
        # Skip auth for OPTIONS requests and debug endpoints
        if request.method == "OPTIONS":
            return await call_next(request)
            
        # List of public endpoints that don't require authentication
        public_paths = [
            "/health",
            "/api/auth/login",
            "/api/auth/register",
            "/api/auth/reset-password",
            "/docs",
            "/openapi.json"
        ]
        
        # Skip auth for public endpoints
        if any(request.url.path.startswith(path) for path in public_paths):
            return await call_next(request)
            
        # Get token from header
        auth_header = request.headers.get("Authorization")
        
        # For development/testing, use test user if enabled
        if settings.ENABLE_TEST_USER:
            request.state.user = {
                "sub": "test_user_123",
                "email": "test@example.com",
                "given_name": "Test",
                "family_name": "User",
                "groups": ["admin"],
                "org_id": "1"
            }
            return await call_next(request)
        
        # If no auth header and test user is disabled, return error
        if not auth_header:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No Authorization header"
            )
            
        # Parse token
        try:
            scheme, token = auth_header.split()
            if scheme.lower() != "bearer":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication scheme"
                )
                
            # Verify token and set user info in request state
            user_info = await verify_token(token)
            request.state.user = user_info
            
            return await call_next(request)
            
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Authorization header format"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        # In development mode, fall back to test user
        if settings.ENABLE_TEST_USER:
            request.state.user = {
                "sub": "test_user_123",
                "email": "test@example.com",
                "given_name": "Test",
                "family_name": "User",
                "groups": ["admin"],
                "org_id": "1"
            }
            return await call_next(request)
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed"
            )

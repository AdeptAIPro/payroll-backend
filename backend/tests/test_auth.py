import pytest
from httpx import AsyncClient
from unittest.mock import patch, MagicMock

@pytest.mark.asyncio
async def test_verify_token_success(client: AsyncClient):
    """Test successful token verification."""
    mock_user_info = {
        "sub": "test_user_123",
        "email": "test@example.com",
        "given_name": "Test",
        "family_name": "User",
        "groups": ["employee"],
        "org_id": "1"
    }
    
    with patch('services.auth_service.get_current_user', return_value=mock_user_info):
        response = await client.post(
            "/api/auth/verify",
            headers={"Authorization": "Bearer valid_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["sub"] == "test_user_123"

@pytest.mark.asyncio
async def test_verify_token_invalid(client: AsyncClient):
    """Test invalid token verification."""
    with patch('services.auth_service.get_current_user', side_effect=Exception("Invalid token")):
        response = await client.post(
            "/api/auth/verify",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401

@pytest.mark.asyncio
async def test_get_me_success(client: AsyncClient):
    """Test getting current user info."""
    mock_user_info = {
        "sub": "test_user_123",
        "email": "test@example.com",
        "given_name": "Test",
        "family_name": "User",
        "groups": ["employee"],
        "org_id": "1"
    }
    
    with patch('services.auth_service.get_current_user', return_value=mock_user_info):
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer valid_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"

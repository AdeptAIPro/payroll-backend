import pytest
import pytest
from httpx import AsyncClient
from models import Employee

@pytest.mark.asyncio
async def test_create_employee(client: AsyncClient, sample_organization):
    """Test creating a new employee."""
    employee_data = {
        "org_id": sample_organization.id,
        "cognito_sub": "new_user_456",
        "employee_id": "EMP002",
        "first_name": "Jane",
        "last_name": "Smith",
        "email": "jane.smith@testcorp.com",
        "role": "employee",
        "department": "Marketing",
        "position": "Manager",
        "salary_type": "fixed",
        "base_salary": 60000.00,
        "tax_status": "married"
    }
    
    response = await client.post("/api/employees/", json=employee_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["first_name"] == "Jane"
    assert data["last_name"] == "Smith"
    assert data["email"] == "jane.smith@testcorp.com"

@pytest.mark.asyncio
async def test_get_employees(client: AsyncClient, sample_employee):
    """Test getting list of employees."""
    response = await client.get("/api/employees/")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) >= 1
    assert any(emp["id"] == sample_employee.id for emp in data)

@pytest.mark.asyncio
async def test_get_employee_by_id(client: AsyncClient, sample_employee):
    """Test getting a specific employee."""
    response = await client.get(f"/api/employees/{sample_employee.id}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] == sample_employee.id
    assert data["first_name"] == sample_employee.first_name

@pytest.mark.asyncio
async def test_update_employee(client: AsyncClient, sample_employee):
    """Test updating an employee."""
    update_data = {
        "first_name": "Johnny",
        "department": "Senior Engineering"
    }
    
    response = await client.put(f"/api/employees/{sample_employee.id}", json=update_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["first_name"] == "Johnny"
    assert data["department"] == "Senior Engineering"

@pytest.mark.asyncio
async def test_delete_employee(client: AsyncClient, sample_employee):
    """Test deleting an employee."""
    response = await client.delete(f"/api/employees/{sample_employee.id}")
    assert response.status_code == 200
    
    # Verify employee is soft deleted
    get_response = await client.get(f"/api/employees/{sample_employee.id}")
    data = get_response.json()
    assert data["is_active"] == False

import pytest
from httpx import AsyncClient
from models import Timesheet, TimesheetStatus
from datetime import datetime, timedelta
from decimal import Decimal

@pytest.mark.asyncio
async def test_create_timesheet(client: AsyncClient, sample_employee):
    """Test creating a new timesheet."""
    timesheet_data = {
        "employee_id": sample_employee.id,
        "week_start_date": datetime.now().isoformat(),
        "week_end_date": (datetime.now() + timedelta(days=6)).isoformat(),
        "monday_hours": 8.0,
        "tuesday_hours": 8.0,
        "wednesday_hours": 8.0,
        "thursday_hours": 8.0,
        "friday_hours": 8.0,
        "saturday_hours": 0.0,
        "sunday_hours": 0.0,
        "notes": "Regular work week"
    }
    
    response = await client.post("/api/timesheets/", json=timesheet_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["total_hours"] == 40.0
    assert data["overtime_hours"] == 0.0
    assert data["status"] == "pending"

@pytest.mark.asyncio
async def test_approve_timesheet(client: AsyncClient, sample_employee, db_session):
    """Test approving a timesheet."""
    # Create a timesheet first
    timesheet = Timesheet(
        employee_id=sample_employee.id,
        week_start_date=datetime.now(),
        week_end_date=datetime.now() + timedelta(days=6),
        monday_hours=Decimal('8.0'),
        tuesday_hours=Decimal('8.0'),
        wednesday_hours=Decimal('8.0'),
        thursday_hours=Decimal('8.0'),
        friday_hours=Decimal('8.0'),
        saturday_hours=Decimal('0.0'),
        sunday_hours=Decimal('0.0'),
        total_hours=Decimal('40.0'),
        overtime_hours=Decimal('0.0'),
        status=TimesheetStatus.PENDING
    )
    db_session.add(timesheet)
    await db_session.commit()
    await db_session.refresh(timesheet)
    
    approval_data = {
        "status": "approved",
        "notes": "Looks good"
    }
    
    response = await client.post(f"/api/timesheets/{timesheet.id}/approve", json=approval_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "approved"

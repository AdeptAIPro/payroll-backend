import pytest
from httpx import AsyncClient
from models import PayrollRun, PayrollStatus
from datetime import datetime, timedelta

@pytest.mark.asyncio
async def test_create_payroll_run(client: AsyncClient, sample_organization):
    """Test creating a new payroll run."""
    payroll_data = {
        "org_id": sample_organization.id,
        "pay_period_start": datetime.now().isoformat(),
        "pay_period_end": (datetime.now() + timedelta(days=13)).isoformat(),
        "pay_date": (datetime.now() + timedelta(days=16)).isoformat()
    }
    
    response = await client.post("/api/payroll/", json=payroll_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["org_id"] == sample_organization.id
    assert data["status"] == "pending"

@pytest.mark.asyncio
async def test_get_payroll_runs(client: AsyncClient, sample_organization, db_session):
    """Test getting payroll runs."""
    # Create a payroll run first
    payroll_run = PayrollRun(
        org_id=sample_organization.id,
        pay_period_start=datetime.now(),
        pay_period_end=datetime.now() + timedelta(days=13),
        pay_date=datetime.now() + timedelta(days=16),
        status=PayrollStatus.PENDING
    )
    db_session.add(payroll_run)
    await db_session.commit()
    
    response = await client.get("/api/payroll/")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) >= 1
    assert any(pr["id"] == payroll_run.id for pr in data)

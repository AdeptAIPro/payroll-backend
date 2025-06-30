import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from backend.database import Base, get_db
from main import app
from backend.orm_models import Organization, Employee, UserRole, SalaryType
from datetime import datetime
from decimal import Decimal

# Test database URL
TEST_DATABASE_URL = "mysql+aiomysql://root:testpassword@localhost:3306/payroll_test"

# Create test engine
test_engine = create_async_engine(TEST_DATABASE_URL, echo=True)
TestSessionLocal = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def setup_database():
    """Set up test database."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def db_session(setup_database):
    """Create a test database session."""
    async with TestSessionLocal() as session:
        yield session

@pytest.fixture
async def override_get_db(db_session):
    """Override the get_db dependency."""
    async def _override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()

@pytest.fixture
async def client(override_get_db):
    """Create test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def sample_organization(db_session):
    """Create a sample organization."""
    org = Organization(
        name="Test Corp",
        address="123 Test St",
        phone="555-0123",
        email="test@testcorp.com",
        tax_id="12-3456789"
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org

@pytest.fixture
async def sample_employee(db_session, sample_organization):
    """Create a sample employee."""
    employee = Employee(
        org_id=sample_organization.id,
        cognito_sub="test_user_123",
        employee_id="EMP001",
        first_name="John",
        last_name="Doe",
        email="john.doe@testcorp.com",
        role=UserRole.EMPLOYEE,
        department="Engineering",
        position="Developer",
        salary_type=SalaryType.HOURLY,
        base_salary=Decimal('50000.00'),
        hourly_rate=Decimal('25.00'),
        tax_status="single",
        hire_date=datetime.now()
    )
    db_session.add(employee)
    await db_session.commit()
    await db_session.refresh(employee)
    return employee

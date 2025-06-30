"""
Seed script to populate the database with sample data for testing
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import AsyncSessionLocal, engine, Base
from backend.orm_models import (
    Organization, Employee, TaxConfiguration, Timesheet, 
    UserRole, SalaryType, TimesheetStatus, Contractor, EmergencyContact, Compensation, TaxInfo, OnboardingStatus
)

async def create_sample_data():
    """Create sample data for testing"""
    async with AsyncSessionLocal() as session:
        try:
            # Clear existing employees to avoid duplicate key errors
            await session.execute("DELETE FROM employees")
            await session.commit()
            
            # Create organization
            org = Organization(
                name="Acme Corporation",
                address="123 Business St, City, State 12345",
                phone="(555) 123-4567",
                email="hr@acmecorp.com",
                tax_id="12-3456789"
            )
            session.add(org)
            await session.flush()  # Get the ID
            
            # Create tax configuration
            tax_config = TaxConfiguration(
                org_id=org.id,
                federal_tax_rate=Decimal('0.22'),  # 22%
                state_tax_rate=Decimal('0.05'),   # 5%
                social_security_rate=Decimal('0.062'),  # 6.2%
                medicare_rate=Decimal('0.0145')  # 1.45%
            )
            session.add(tax_config)
            
            # Create sample employees
            employees_data = [
                {
                    "cognito_sub": "admin_user_123",
                    "employee_id": "EMP0011",
                    "first_name": "John",
                    "last_name": "Admin",
                    "email": "john@acmecorp.com",
                    "phone": "(555) 123-0001",
                    "role": UserRole.ADMIN,
                    "department": "Administration",
                    "position": "System Administrator",
                    "salary_type": SalaryType.FIXED,
                    "base_salary": Decimal('75000.00'),
                    "tax_status": "single",
                    "hire_date": datetime.now() - timedelta(days=365),
                    "ssn": "123-45-6789",
                    "address": "100 Main St",
                    "city": "New York",
                    "state": "NY",
                    "zip_code": "10001",
                    "birth_date": datetime(1985, 4, 12),
                    "onboarding_status": OnboardingStatus.COMPLETE
                },
                {
                    "cognito_sub": "manager_user_456",
                    "employee_id": "EMP002",
                    "first_name": "Sarah",
                    "last_name": "Manager",
                    "email": "sarah.manager@acmecorp.com",
                    "phone": "(555) 123-0002",
                    "role": UserRole.MANAGER,
                    "department": "Human Resources",
                    "position": "HR Manager",
                    "salary_type": SalaryType.FIXED,
                    "base_salary": Decimal('65000.00'),
                    "tax_status": "married",
                    "hire_date": datetime.now() - timedelta(days=300),
                    "ssn": "234-56-7890",
                    "address": "200 Park Ave",
                    "city": "Boston",
                    "state": "MA",
                    "zip_code": "02110",
                    "birth_date": datetime(1988, 7, 23),
                    "onboarding_status": OnboardingStatus.COMPLETE
                },
                {
                    "cognito_sub": "employee_user_789",
                    "employee_id": "EMP003",
                    "first_name": "Mike",
                    "last_name": "Developer",
                    "email": "mike.developer@acmecorp.com",
                    "phone": "(555) 123-0003",
                    "role": UserRole.EMPLOYEE,
                    "department": "Engineering",
                    "position": "Software Developer",
                    "salary_type": SalaryType.HOURLY,
                    "base_salary": Decimal('50000.00'),
                    "hourly_rate": Decimal('35.00'),
                    "tax_status": "single",
                    "hire_date": datetime.now() - timedelta(days=180),
                    "ssn": "345-67-8901",
                    "address": "300 Tech Rd",
                    "city": "San Francisco",
                    "state": "CA",
                    "zip_code": "94105",
                    "birth_date": datetime(1992, 2, 15),
                    "onboarding_status": OnboardingStatus.PENDING
                },
                {
                    "cognito_sub": "employee_user_101",
                    "employee_id": "EMP004",
                    "first_name": "Lisa",
                    "last_name": "Designer",
                    "email": "lisa.designer@acmecorp.com",
                    "phone": "(555) 123-0004",
                    "role": UserRole.EMPLOYEE,
                    "department": "Design",
                    "position": "UI/UX Designer",
                    "salary_type": SalaryType.HOURLY,
                    "base_salary": Decimal('45000.00'),
                    "hourly_rate": Decimal('30.00'),
                    "tax_status": "single",
                    "hire_date": datetime.now() - timedelta(days=90),
                    "ssn": "456-78-9012",
                    "address": "400 Art Blvd",
                    "city": "Chicago",
                    "state": "IL",
                    "zip_code": "60601",
                    "birth_date": datetime(1990, 11, 5),
                    "onboarding_status": OnboardingStatus.PENDING
                },
                {
                    "cognito_sub": "employee_user_202",
                    "employee_id": "EMP005",
                    "first_name": "David",
                    "last_name": "Sales",
                    "email": "david.sales@acmecorp.com",
                    "phone": "(555) 123-0005",
                    "role": UserRole.EMPLOYEE,
                    "department": "Sales",
                    "position": "Sales Representative",
                    "salary_type": SalaryType.FIXED,
                    "base_salary": Decimal('55000.00'),
                    "tax_status": "married",
                    "hire_date": datetime.now() - timedelta(days=120),
                    "ssn": "567-89-0123",
                    "address": "500 Commerce St",
                    "city": "Dallas",
                    "state": "TX",
                    "zip_code": "75201",
                    "birth_date": datetime(1987, 9, 30),
                    "onboarding_status": OnboardingStatus.COMPLETE
                },
                {
                    "cognito_sub": "employee_user_303",
                    "employee_id": "EMP006",
                    "first_name": "Priya",
                    "last_name": "Patel",
                    "email": "priya.patel@acmecorp.com",
                    "phone": "(555) 123-0006",
                    "role": UserRole.EMPLOYEE,
                    "department": "Finance",
                    "position": "Accountant",
                    "salary_type": SalaryType.FIXED,
                    "base_salary": Decimal('70000.00'),
                    "tax_status": "single",
                    "hire_date": datetime.now() - timedelta(days=210),
                    "ssn": "678-90-1234",
                    "address": "600 Finance Ave",
                    "city": "Atlanta",
                    "state": "GA",
                    "zip_code": "30303",
                    "birth_date": datetime(1991, 6, 18),
                    "onboarding_status": OnboardingStatus.COMPLETE
                },
                {
                    "cognito_sub": "employee_user_404",
                    "employee_id": "EMP007",
                    "first_name": "Chen",
                    "last_name": "Wang",
                    "email": "chen.wang@acmecorp.com",
                    "phone": "(555) 123-0007",
                    "role": UserRole.EMPLOYEE,
                    "department": "IT",
                    "position": "Network Engineer",
                    "salary_type": SalaryType.FIXED,
                    "base_salary": Decimal('80000.00'),
                    "tax_status": "married",
                    "hire_date": datetime.now() - timedelta(days=400),
                    "ssn": "789-01-2345",
                    "address": "700 Network Dr",
                    "city": "Seattle",
                    "state": "WA",
                    "zip_code": "98101",
                    "birth_date": datetime(1989, 3, 22),
                    "onboarding_status": OnboardingStatus.COMPLETE
                },
                {
                    "cognito_sub": "employee_user_505",
                    "employee_id": "EMP008",
                    "first_name": "Maria",
                    "last_name": "Gonzalez",
                    "email": "maria.gonzalez@acmecorp.com",
                    "phone": "(555) 123-0008",
                    "role": UserRole.EMPLOYEE,
                    "department": "Marketing",
                    "position": "Marketing Specialist",
                    "salary_type": SalaryType.FIXED,
                    "base_salary": Decimal('60000.00'),
                    "tax_status": "single",
                    "hire_date": datetime.now() - timedelta(days=150),
                    "ssn": "890-12-3456",
                    "address": "800 Market St",
                    "city": "Miami",
                    "state": "FL",
                    "zip_code": "33101",
                    "birth_date": datetime(1993, 12, 10),
                    "onboarding_status": OnboardingStatus.PENDING
                },
                {
                    "cognito_sub": "employee_user_606",
                    "employee_id": "EMP009",
                    "first_name": "Ahmed",
                    "last_name": "Khan",
                    "email": "ahmed.khan@acmecorp.com",
                    "phone": "(555) 123-0009",
                    "role": UserRole.EMPLOYEE,
                    "department": "Support",
                    "position": "Customer Support",
                    "salary_type": SalaryType.HOURLY,
                    "base_salary": Decimal('40000.00'),
                    "hourly_rate": Decimal('20.00'),
                    "tax_status": "single",
                    "hire_date": datetime.now() - timedelta(days=60),
                    "ssn": "901-23-4567",
                    "address": "900 Help Rd",
                    "city": "Houston",
                    "state": "TX",
                    "zip_code": "77001",
                    "birth_date": datetime(1994, 8, 2),
                    "onboarding_status": OnboardingStatus.PENDING
                },
                {
                    "cognito_sub": "employee_user_707",
                    "employee_id": "EMP010",
                    "first_name": "Emily",
                    "last_name": "Clark",
                    "email": "emily.clark@acmecorp.com",
                    "phone": "(555) 123-0010",
                    "role": UserRole.EMPLOYEE,
                    "department": "Legal",
                    "position": "Legal Advisor",
                    "salary_type": SalaryType.FIXED,
                    "base_salary": Decimal('90000.00'),
                    "tax_status": "married",
                    "hire_date": datetime.now() - timedelta(days=500),
                    "ssn": "012-34-5678",
                    "address": "1000 Law St",
                    "city": "Los Angeles",
                    "state": "CA",
                    "zip_code": "90001",
                    "birth_date": datetime(1986, 1, 17),
                    "onboarding_status": OnboardingStatus.COMPLETE
                }
            ]
            
            employees = []
            for emp_data in employees_data:
                employee = Employee(org_id=org.id, **emp_data)
                session.add(employee)
                employees.append(employee)
            
            await session.flush()  # Get employee IDs
            
            # Create sample timesheets for the last 4 weeks
            for week in range(4):
                week_start = datetime.now() - timedelta(days=datetime.now().weekday() + (week * 7))
                week_end = week_start + timedelta(days=6)
                
                for employee in employees:
                    if employee.salary_type == SalaryType.HOURLY:
                        # Create varying hours for hourly employees
                        timesheet = Timesheet(
                            employee_id=employee.id,
                            week_start_date=week_start,
                            week_end_date=week_end,
                            monday_hours=Decimal('8.0'),
                            tuesday_hours=Decimal('8.0'),
                            wednesday_hours=Decimal('8.0'),
                            thursday_hours=Decimal('8.0'),
                            friday_hours=Decimal('8.0'),
                            saturday_hours=Decimal('0.0'),
                            sunday_hours=Decimal('0.0'),
                            total_hours=Decimal('40.0'),
                            overtime_hours=Decimal('0.0'),
                            status=TimesheetStatus.APPROVED if week > 0 else TimesheetStatus.PENDING,
                            approved_by=employees[0].id if week > 0 else None,  # Admin approves
                            approved_at=datetime.now() - timedelta(days=week*7-1) if week > 0 else None,
                            notes=f"Week {week+1} timesheet"
                        )
                        session.add(timesheet)
            
            await session.commit()
            print("✅ Sample data created successfully!")
            print(f"📊 Created:")
            print(f"   - 1 Organization: {org.name}")
            print(f"   - 1 Tax Configuration")
            print(f"   - {len(employees)} Employees")
            print(f"   - Multiple Timesheets for testing")
            print("\n🔑 Test Accounts:")
            print("   Admin: admin@acmecorp.com")
            print("   Manager: sarah.manager@acmecorp.com") 
            print("   Employee: mike.developer@acmecorp.com")
            print("   Employee: lisa.designer@acmecorp.com")
            print("   Employee: david.sales@acmecorp.com")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Error creating sample data: {e}")
            raise

async def seed():
    async with AsyncSessionLocal() as db:
        # Sample employee
        emp = Employee(
            cognito_sub="sample-sub-1",
            org_id=1,
            employee_id="EMP001",
            first_name="Alice",
            last_name="Smith",
            email="alice.smith@example.com",
            role="employee",
            salary_type="salary",
            base_salary=80000,
            is_active=True,
            onboarding_status=OnboardingStatus.COMPLETE,
            address="123 Main St",
            city="Metropolis",
            state="NY",
            zip_code="10001",
            birth_date=datetime(1990, 5, 1)
        )
        db.add(emp)
        await db.commit()
        await db.refresh(emp)
        # Compensation
        comp = Compensation(
            employee_id=emp.id,
            compensation_type="salary",
            amount=80000,
            start_date=datetime(2024, 1, 1),
            review_date=datetime(2024, 12, 31)
        )
        db.add(comp)
        # Tax Info
        tax = TaxInfo(
            employee_id=emp.id,
            w4_status="single",
            state="NY",
            exemptions=1,
            i9_verified=True
        )
        db.add(tax)
        # Emergency Contact
        ec = EmergencyContact(
            employee_id=emp.id,
            name="Bob Smith",
            relationship="Brother",
            phone="555-1234",
            email="bob.smith@example.com"
        )
        db.add(ec)
        # Contractor
        contractor = Contractor(
            org_id=1,
            contractor_type="individual",
            name="Charlie Contractor",
            email="charlie.contractor@example.com",
            phone="555-5678",
            onboarding_status=OnboardingStatus.PENDING
        )
        db.add(contractor)
        await db.commit()
        print("Seeded onboarding data.")

async def main():
    """Main function to run the seeder"""
    print("🌱 Starting database seeding...")
    
    # Create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    await create_sample_data()
    await seed()
    print("🎉 Database seeding completed!")

if __name__ == "__main__":
    asyncio.run(main())

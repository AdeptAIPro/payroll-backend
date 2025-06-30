import asyncio
import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal
import random
import string

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import AsyncSessionLocal
from backend.orm_models import Employee, UserRole, SalaryType, OnboardingStatus
from backend.services.auth_service import cognito_service

FIRST_NAMES = ["John", "Jane", "Alex", "Emily", "Chris", "Olivia", "Michael", "Sophia", "David", "Emma", "Daniel", "Ava"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Martinez", "Hernandez"]
DEPARTMENTS = ["Engineering", "HR", "Finance", "Sales", "Support", "Marketing", "IT", "Legal"]
POSITIONS = ["Developer", "Manager", "Accountant", "Sales Rep", "Support Agent", "Marketer", "Engineer", "Advisor"]

ORG_IDS = [1, 3, 8]

async def add_w2_employees():
    async with AsyncSessionLocal() as session:
        employees = []
        for i in range(10):
            first_name = random.choice(FIRST_NAMES)
            last_name = random.choice(LAST_NAMES)
            email = f"{first_name.lower()}.{last_name.lower()}{random.randint(100,999)}@example.com"
            department = random.choice(DEPARTMENTS)
            position = random.choice(POSITIONS)
            org_id = random.choice(ORG_IDS)
            salary_type = random.choice([SalaryType.FIXED, SalaryType.HOURLY])
            base_salary = Decimal(random.randint(40000, 120000))
            hourly_rate = Decimal(random.randint(20, 60)) if salary_type == SalaryType.HOURLY else None
            hire_date = datetime.now() - timedelta(days=random.randint(30, 1000))
            ssn = f"{random.randint(100,999)}-{random.randint(10,99)}-{random.randint(1000,9999)}"
            zip_code = f"{random.randint(10000,99999)}"
            birth_date = datetime.now() - timedelta(days=random.randint(8000, 18000))
            employee_id = f"EMP{random.randint(1000,9999)}"

            # Create Cognito user
            try:
                sub, temp_password = cognito_service.create_user(
                    email=email,
                    first_name=first_name,
                    last_name=last_name
                )
            except Exception as e:
                print(f"❌ Failed to create Cognito user for {email}: {e}")
                continue

            # Create Employee record
            employee = Employee(
                cognito_sub=sub,
                org_id=org_id,
                employee_id=employee_id,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=f"(555) 123-{random.randint(1000,9999)}",
                role=UserRole.EMPLOYEE,
                department=department,
                position=position,
                salary_type=salary_type,
                base_salary=base_salary,
                hourly_rate=hourly_rate,
                tax_status=random.choice(["single", "married"]),
                is_active=True,
                hire_date=hire_date,
                ssn=ssn,
                address=f"{random.randint(100,999)} Main St",
                city=random.choice(["New York", "Boston", "Chicago", "Dallas", "Miami", "Seattle", "San Francisco", "Atlanta", "Houston", "Los Angeles"]),
                state=random.choice(["NY", "MA", "IL", "TX", "FL", "WA", "CA", "GA"]),
                zip_code=zip_code,
                birth_date=birth_date,
                onboarding_status=OnboardingStatus.COMPLETE
            )
            session.add(employee)
            employees.append((email, sub, temp_password))
        await session.commit()
        print("\n✅ Added 10 W-2 employees:")
        for email, sub, temp_password in employees:
            print(f"Email: {email} | Cognito Sub: {sub} | Temp Password: {temp_password}")

if __name__ == "__main__":
    asyncio.run(add_w2_employees()) 
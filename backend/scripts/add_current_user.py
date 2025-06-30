"""
Script to add the current logged-in user as an employee
"""
import asyncio
import sys
import os
from datetime import datetime
from sqlalchemy import text

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import AsyncSessionLocal
from backend.orm_models import Employee, UserRole, SalaryType

async def add_current_user_as_employee():
    """Add the current user as an employee"""
    async with AsyncSessionLocal() as session:
        try:
            # The Cognito sub from the logs - updated with the correct one
            cognito_sub = "f113bdea-00f1-706e-ca5c-241ff50af149"
            
            # Check if employee already exists
            existing_employee = await session.execute(
                text("SELECT * FROM employees WHERE cognito_sub = :cognito_sub"),
                {"cognito_sub": cognito_sub}
            )
            
            if existing_employee.fetchone():
                print("✅ Employee already exists for this Cognito user")
                return
            
            # Create employee record
            employee = Employee(
                cognito_sub=cognito_sub,
                org_id=1,  # Acme Corporation from seed data
                employee_id=f"EMP{int(datetime.now().timestamp())}",
                first_name="Admin",
                last_name="User",
                email="admin@example.com",  # This will be updated when we know the actual email
                phone="",
                role=UserRole.ADMIN,
                department="Administration",
                position="System Administrator",
                salary_type=SalaryType.FIXED,
                base_salary=75000.00,
                tax_status="single",
                is_active=True,
                hire_date=datetime.now()
            )
            
            session.add(employee)
            await session.commit()
            
            print("✅ Successfully created employee record for current user")
            print(f"   Employee ID: {employee.employee_id}")
            print(f"   Cognito Sub: {employee.cognito_sub}")
            print(f"   Role: {employee.role}")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Error creating employee: {e}")
            raise

async def main():
    """Main function"""
    print("👤 Adding current user as employee...")
    await add_current_user_as_employee()
    print("🎉 Done!")

if __name__ == "__main__":
    asyncio.run(main()) 
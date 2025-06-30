import asyncio
from database import get_db
from models import Employee, Timesheet
from sqlalchemy import select

async def test_user():
    async for db in get_db():
        try:
            # Check test user employee
            result = await db.execute(select(Employee).where(Employee.cognito_sub == 'test_user_123'))
            employee = result.scalar_one_or_none()
            print(f'Test user employee: {employee.id if employee else None}')
            
            if employee:
                # Check timesheets for this employee
                result = await db.execute(select(Timesheet).where(Timesheet.employee_id == employee.id))
                timesheets = result.scalars().all()
                print(f'Timesheets for test user: {len(timesheets)}')
                for ts in timesheets:
                    print(f'  - ID: {ts.id}, Week: {ts.week_start_date}, Status: {ts.status}')
            
            # Check all timesheets
            result = await db.execute(select(Timesheet).limit(20))
            all_timesheets = result.scalars().all()
            print(f'\nAll timesheets: {len(all_timesheets)}')
            
            # Get employee info for each timesheet
            for ts in all_timesheets:
                emp_result = await db.execute(select(Employee).where(Employee.id == ts.employee_id))
                emp = emp_result.scalar_one_or_none()
                emp_name = f"{emp.first_name} {emp.last_name}" if emp else "Unknown"
                print(f'  - ID: {ts.id}, Employee: {emp_name} (ID: {ts.employee_id}), Week: {ts.week_start_date}, Status: {ts.status}')
                
        except Exception as e:
            print(f"Error: {e}")
        break

if __name__ == "__main__":
    asyncio.run(test_user()) 
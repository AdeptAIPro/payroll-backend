import asyncio
import sys
import os
from sqlalchemy import text
from datetime import datetime, date
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.database import AsyncSessionLocal

def is_invalid_date(val):
    if not val:
        return True
    s = str(val)
    if s in ("0000-00-00", "0000-00-00 00:00:00", "", "None", "null"):
        return True
    try:
        # Try to parse as date
        if isinstance(val, date):
            return False
        datetime.strptime(s[:10], "%Y-%m-%d")
        return False
    except Exception:
        return True

async def fix_birth_dates():
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT id, birth_date FROM employees"))
        employees = result.fetchall()
        fixed = 0
        for emp in employees:
            emp_id, birth_date_val = emp
            if is_invalid_date(birth_date_val):
                await session.execute(text("UPDATE employees SET birth_date = NULL WHERE id = :id"), {"id": emp_id})
                fixed += 1
            elif isinstance(birth_date_val, datetime):
                # Truncate to date if time is not zero
                if birth_date_val.time() != datetime.min.time():
                    just_date = birth_date_val.date()
                    await session.execute(text("UPDATE employees SET birth_date = :d WHERE id = :id"), {"d": just_date, "id": emp_id})
                    fixed += 1
        await session.commit()
        print(f"Fixed {fixed} employee birth_date values.")

if __name__ == "__main__":
    asyncio.run(fix_birth_dates()) 
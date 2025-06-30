#!/usr/bin/env python3
"""
Script to add missing columns to the employees table.
This script adds the columns that are defined in the Employee model but missing from the database.
"""

import asyncio
import sys
import os

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import engine
from sqlalchemy import text

async def add_missing_columns():
    """Add missing columns to the employees table"""
    
    # List of columns to add with their definitions
    columns_to_add = [
        ("ssn", "VARCHAR(255)"),
        ("address", "VARCHAR(255)"),
        ("city", "VARCHAR(100)"),
        ("state", "VARCHAR(50)"),
        ("zip_code", "VARCHAR(20)"),
        ("birth_date", "DATETIME"),
        ("onboarding_status", "ENUM('PENDING', 'COMPLETE') DEFAULT 'PENDING'")
    ]
    
    async with engine.begin() as conn:
        for column_name, column_definition in columns_to_add:
            try:
                # Check if column already exists
                result = await conn.execute(text(f"""
                    SELECT COUNT(*) 
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = DATABASE() 
                    AND TABLE_NAME = 'employees' 
                    AND COLUMN_NAME = '{column_name}'
                """))
                
                count = result.scalar()
                
                if count == 0:
                    # Column doesn't exist, add it
                    print(f"Adding column: {column_name}")
                    await conn.execute(text(f"ALTER TABLE employees ADD COLUMN {column_name} {column_definition}"))
                    print(f"✓ Added column: {column_name}")
                else:
                    print(f"✓ Column {column_name} already exists")
                    
            except Exception as e:
                print(f"✗ Error adding column {column_name}: {e}")
                continue

async def main():
    """Main function"""
    print("Adding missing columns to employees table...")
    await add_missing_columns()
    print("Done!")

if __name__ == "__main__":
    asyncio.run(main()) 
#!/usr/bin/env python3

print("Testing imports...")

try:
    print("1. Testing config import...")
    from config import settings
    print("✓ Config imported successfully")
except Exception as e:
    print(f"✗ Config import failed: {e}")

try:
    print("2. Testing database import...")
    from database import engine, Base
    print("✓ Database imported successfully")
except Exception as e:
    print(f"✗ Database import failed: {e}")

try:
    print("3. Testing models import...")
    from models import Employee
    print("✓ Models imported successfully")
except Exception as e:
    print(f"✗ Models import failed: {e}")

try:
    print("4. Testing schemas import...")
    from schemas import EmployeeCreate
    print("✓ Schemas imported successfully")
except Exception as e:
    print(f"✗ Schemas import failed: {e}")

print("Import test completed.") 
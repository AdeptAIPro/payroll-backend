from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn
from contextlib import asynccontextmanager

from backend.database import engine, Base
from backend.routers import auth, employees, timesheets, payroll, payslips, organizations, bank_accounts
from backend.config import settings
from backend.services.auth_service import verify_token
from backend.middleware.auth_middleware import auth_middleware

# Create tables
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    pass

app = FastAPI(
    title="Payroll Management System",
    description="Complete payroll software with employee management, timesheets, and automated payroll processing",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware - must be first
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Authentication middleware - must be after CORS
app.middleware("http")(auth_middleware)

# Security
security = HTTPBearer()

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(employees.router, prefix="/api/employees", tags=["Employees"])
app.include_router(timesheets.router, prefix="/api/timesheets", tags=["Timesheets"])
app.include_router(payroll.router, prefix="/api/payroll", tags=["Payroll"])
app.include_router(payslips.router, prefix="/api/payslips", tags=["Payslips"])
app.include_router(organizations.router, prefix="/api/organizations", tags=["Organizations"])
app.include_router(bank_accounts.router, prefix="/api/bank-accounts", tags=["Bank Accounts"])

@app.get("/")
async def root():
    return {"message": "Payroll Management System API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

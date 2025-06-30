from fastapi import HTTPException, status

class PayrollException(Exception):
    """Base exception for payroll system"""
    pass

class EmployeeNotFoundException(PayrollException):
    """Employee not found exception"""
    pass

class TimesheetNotFoundException(PayrollException):
    """Timesheet not found exception"""
    pass

class PayrollRunNotFoundException(PayrollException):
    """Payroll run not found exception"""
    pass

class InsufficientPermissionsException(PayrollException):
    """Insufficient permissions exception"""
    pass

class ValidationException(PayrollException):
    """Validation error exception"""
    pass

def raise_http_exception(status_code: int, detail: str):
    """Raise HTTP exception with proper status code"""
    raise HTTPException(status_code=status_code, detail=detail)

def raise_not_found(resource: str):
    """Raise 404 not found exception"""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{resource} not found"
    )

def raise_forbidden(message: str = "Access denied"):
    """Raise 403 forbidden exception"""
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=message
    )

def raise_bad_request(message: str):
    """Raise 400 bad request exception"""
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=message
    )

def raise_unauthorized(message: str = "Authentication required"):
    """Raise 401 unauthorized exception"""
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=message
    )

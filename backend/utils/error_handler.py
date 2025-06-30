from fastapi import HTTPException, status
from typing import Optional, Dict, Any
from backend.utils.logger import api_logger
import traceback

class PayrollSystemError(Exception):
    """Base exception for payroll system errors"""
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

class DatabaseError(PayrollSystemError):
    """Database-related errors"""
    pass

class AuthenticationError(PayrollSystemError):
    """Authentication-related errors"""
    pass

class AuthorizationError(PayrollSystemError):
    """Authorization-related errors"""
    pass

class ValidationError(PayrollSystemError):
    """Data validation errors"""
    pass

class BusinessLogicError(PayrollSystemError):
    """Business logic errors"""
    pass

def handle_database_error(error: Exception, operation: str, user_id: str = None) -> HTTPException:
    """Handle database errors and return appropriate HTTP response"""
    api_logger.error(
        f"Database error during {operation}: {str(error)}",
        user_id=user_id,
        operation=operation,
        error_type=type(error).__name__
    )
    
    # Log full traceback for debugging
    api_logger.error(f"Full traceback: {traceback.format_exc()}")
    
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Database operation failed: {operation}. Please try again later."
    )

def handle_validation_error(error: Exception, field: str = None, user_id: str = None) -> HTTPException:
    """Handle validation errors and return appropriate HTTP response"""
    api_logger.error(
        f"Validation error: {str(error)}",
        user_id=user_id,
        field=field,
        error_type=type(error).__name__
    )
    
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Validation error: {str(error)}"
    )

def handle_authentication_error(error: Exception, user_id: str = None) -> HTTPException:
    """Handle authentication errors and return appropriate HTTP response"""
    api_logger.error(
        f"Authentication error: {str(error)}",
        user_id=user_id,
        error_type=type(error).__name__
    )
    
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication failed. Please log in again."
    )

def handle_authorization_error(error: Exception, user_id: str = None, required_role: str = None) -> HTTPException:
    """Handle authorization errors and return appropriate HTTP response"""
    api_logger.error(
        f"Authorization error: {str(error)}",
        user_id=user_id,
        required_role=required_role,
        error_type=type(error).__name__
    )
    
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You don't have permission to perform this action."
    )

def handle_business_logic_error(error: Exception, operation: str, user_id: str = None) -> HTTPException:
    """Handle business logic errors and return appropriate HTTP response"""
    api_logger.error(
        f"Business logic error during {operation}: {str(error)}",
        user_id=user_id,
        operation=operation,
        error_type=type(error).__name__
    )
    
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=str(error)
    )

def handle_external_service_error(error: Exception, service: str, user_id: str = None) -> HTTPException:
    """Handle external service errors (Cognito, S3, etc.) and return appropriate HTTP response"""
    api_logger.error(
        f"External service error ({service}): {str(error)}",
        user_id=user_id,
        service=service,
        error_type=type(error).__name__
    )
    
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"External service temporarily unavailable. Please try again later."
    )

def handle_generic_error(error: Exception, operation: str, user_id: str = None) -> HTTPException:
    """Handle generic errors and return appropriate HTTP response"""
    api_logger.error(
        f"Unexpected error during {operation}: {str(error)}",
        user_id=user_id,
        operation=operation,
        error_type=type(error).__name__
    )
    
    # Log full traceback for debugging
    api_logger.error(f"Full traceback: {traceback.format_exc()}")
    
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An unexpected error occurred. Please try again later."
    )

def safe_database_operation(operation_func, operation_name: str, user_id: str = None, *args, **kwargs):
    """Safely execute database operations with error handling"""
    try:
        return operation_func(*args, **kwargs)
    except Exception as e:
        raise handle_database_error(e, operation_name, user_id)

async def safe_async_database_operation(operation_func, operation_name: str, user_id: str = None, *args, **kwargs):
    """Safely execute async database operations with error handling"""
    try:
        return await operation_func(*args, **kwargs)
    except Exception as e:
        raise handle_database_error(e, operation_name, user_id)

def validate_required_fields(data: Dict[str, Any], required_fields: list, operation: str) -> None:
    """Validate that required fields are present in the data"""
    missing_fields = [field for field in required_fields if not data.get(field)]
    
    if missing_fields:
        raise ValidationError(
            f"Missing required fields for {operation}: {', '.join(missing_fields)}"
        )

def validate_field_length(field_value: str, field_name: str, max_length: int) -> None:
    """Validate field length"""
    if field_value and len(field_value) > max_length:
        raise ValidationError(
            f"{field_name} cannot exceed {max_length} characters"
        )

def validate_email_format(email: str) -> None:
    """Validate email format"""
    import re
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if email and not re.match(email_pattern, email):
        raise ValidationError("Invalid email format")

def validate_phone_format(phone: str) -> None:
    """Validate phone number format"""
    import re
    phone_pattern = r'^\+?1?\d{9,15}$'
    
    if phone and not re.match(phone_pattern, phone):
        raise ValidationError("Invalid phone number format")

def validate_salary_amount(amount: float, field_name: str = "Salary") -> None:
    """Validate salary amount"""
    if amount is not None and (amount < 0 or amount > 1000000):
        raise ValidationError(f"{field_name} must be between 0 and 1,000,000")

def validate_hours(hours: float, field_name: str = "Hours") -> None:
    """Validate hours worked"""
    if hours is not None and (hours < 0 or hours > 168):  # Max 168 hours per week
        raise ValidationError(f"{field_name} must be between 0 and 168")

def log_operation_start(operation: str, user_id: str = None, **kwargs):
    """Log the start of an operation"""
    api_logger.info(
        f"Starting operation: {operation}",
        user_id=user_id,
        operation=operation,
        **kwargs
    )

def log_operation_success(operation: str, user_id: str = None, **kwargs):
    """Log the successful completion of an operation"""
    api_logger.info(
        f"Operation completed successfully: {operation}",
        user_id=user_id,
        operation=operation,
        **kwargs
    )

def log_operation_failure(operation: str, error: Exception, user_id: str = None, **kwargs):
    """Log the failure of an operation"""
    api_logger.error(
        f"Operation failed: {operation}",
        user_id=user_id,
        operation=operation,
        error=str(error),
        error_type=type(error).__name__,
        **kwargs
    ) 
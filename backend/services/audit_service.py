from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from backend.orm_models import Employee
import logging
import json

logger = logging.getLogger(__name__)

class AuditService:
    def __init__(self):
        pass
    
    async def log_user_action(
        self,
        db: AsyncSession,
        user_id: int,
        action: str,
        resource: str,
        resource_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log user action for audit trail"""
        try:
            audit_log = {
                'timestamp': datetime.utcnow().isoformat(),
                'user_id': user_id,
                'action': action,
                'resource': resource,
                'resource_id': resource_id,
                'details': details or {}
            }
            
            # In a real implementation, this would be stored in an audit table
            logger.info(f"AUDIT: {json.dumps(audit_log)}")
            
        except Exception as e:
            logger.error(f"Failed to log audit action: {e}")
    
    async def log_login_attempt(self, email: str, success: bool, ip_address: str):
        """Log login attempt"""
        try:
            log_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'email': email,
                'success': success,
                'ip_address': ip_address,
                'action': 'login_attempt'
            }
            
            logger.info(f"LOGIN_AUDIT: {json.dumps(log_entry)}")
            
        except Exception as e:
            logger.error(f"Failed to log login attempt: {e}")
    
    async def log_data_access(self, user_id: int, resource: str, resource_id: int):
        """Log data access for compliance"""
        try:
            access_log = {
                'timestamp': datetime.utcnow().isoformat(),
                'user_id': user_id,
                'resource': resource,
                'resource_id': resource_id,
                'action': 'data_access'
            }
            
            logger.info(f"ACCESS_AUDIT: {json.dumps(access_log)}")
            
        except Exception as e:
            logger.error(f"Failed to log data access: {e}")
    
    async def log_payroll_processing(
        self, 
        user_id: int, 
        payroll_run_id: int, 
        employee_count: int,
        total_amount: float
    ):
        """Log payroll processing for audit"""
        try:
            payroll_log = {
                'timestamp': datetime.utcnow().isoformat(),
                'user_id': user_id,
                'payroll_run_id': payroll_run_id,
                'employee_count': employee_count,
                'total_amount': total_amount,
                'action': 'payroll_processing'
            }
            
            logger.info(f"PAYROLL_AUDIT: {json.dumps(payroll_log)}")
            
        except Exception as e:
            logger.error(f"Failed to log payroll processing: {e}")

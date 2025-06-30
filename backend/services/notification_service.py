from typing import List, Dict, Any
from datetime import datetime
from backend.services.email_service import EmailService
import logging

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self):
        self.email_service = EmailService()
    
    async def send_welcome_notification(self, employee_email: str, employee_name: str):
        """Send welcome notification to new employee"""
        try:
            subject = "Welcome to the Payroll System"
            body = f"""
            Dear {employee_name},
            
            Welcome to our payroll system! Your account has been created successfully.
            
            You can now:
            - Submit weekly timesheets
            - View your payslips
            - Update your profile information
            - Manage your bank account details
            
            If you have any questions, please contact HR.
            
            Best regards,
            Payroll Team
            """
            
            await self.email_service.send_email(employee_email, subject, body)
            logger.info(f"Welcome notification sent to {employee_email}")
            
        except Exception as e:
            logger.error(f"Failed to send welcome notification: {e}")
    
    async def send_timesheet_reminder(self, employee_email: str, employee_name: str):
        """Send timesheet submission reminder"""
        try:
            subject = "Timesheet Submission Reminder"
            body = f"""
            Dear {employee_name},
            
            This is a reminder to submit your timesheet for this week.
            
            Please log into the payroll system and submit your hours worked.
            
            Deadline: End of business day Friday
            
            Best regards,
            Payroll Team
            """
            
            await self.email_service.send_email(employee_email, subject, body)
            logger.info(f"Timesheet reminder sent to {employee_email}")
            
        except Exception as e:
            logger.error(f"Failed to send timesheet reminder: {e}")
    
    async def send_payroll_processed_notification(
        self, 
        employee_email: str, 
        employee_name: str, 
        pay_date: datetime,
        net_pay: float
    ):
        """Send payroll processed notification"""
        try:
            subject = f"Payroll Processed - {pay_date.strftime('%B %Y')}"
            body = f"""
            Dear {employee_name},
            
            Your payroll for {pay_date.strftime('%B %Y')} has been processed.
            
            Net Pay: ${net_pay:,.2f}
            Pay Date: {pay_date.strftime('%B %d, %Y')}
            
            Your payslip is available in the payroll system.
            
            Best regards,
            Payroll Team
            """
            
            await self.email_service.send_email(employee_email, subject, body)
            logger.info(f"Payroll notification sent to {employee_email}")
            
        except Exception as e:
            logger.error(f"Failed to send payroll notification: {e}")
    
    async def send_bulk_notifications(self, notifications: List[Dict[str, Any]]):
        """Send bulk notifications"""
        for notification in notifications:
            try:
                await self.email_service.send_email(
                    notification['email'],
                    notification['subject'],
                    notification['body']
                )
            except Exception as e:
                logger.error(f"Failed to send notification to {notification['email']}: {e}")

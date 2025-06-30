import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from backend.config import settings

class EmailService:
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.FROM_EMAIL
    
    async def send_payslip_notification(
        self,
        to_email: str,
        employee_name: str,
        payslip_url: str,
        pay_date: datetime
    ):
        """Send payslip notification email"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = f"Payslip Available - {pay_date.strftime('%B %Y')}"
            
            body = f"""
            Dear {employee_name},
            
            Your payslip for {pay_date.strftime('%B %Y')} is now available.
            
            You can download your payslip using the following link:
            {payslip_url}
            
            This link will expire in 7 days.
            
            If you have any questions about your payslip, please contact HR.
            
            Best regards,
            Payroll Team
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
                
            print(f"Payslip notification sent to {to_email}")
            
        except Exception as e:
            print(f"Error sending email: {e}")
    
    async def send_timesheet_approval_notification(
        self,
        to_email: str,
        employee_name: str,
        week_start: datetime,
        status: str
    ):
        """Send timesheet approval notification"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = f"Timesheet {status.title()} - Week of {week_start.strftime('%B %d, %Y')}"
            
            body = f"""
            Dear {employee_name},
            
            Your timesheet for the week of {week_start.strftime('%B %d, %Y')} has been {status}.
            
            Please log into the payroll system to view the details.
            
            Best regards,
            Payroll Team
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
                
            print(f"Timesheet notification sent to {to_email}")
            
        except Exception as e:
            print(f"Error sending email: {e}")

    async def send_welcome_email(
        self,
        to_email: str,
        employee_name: str,
        temp_password: str,
        login_url: str = "http://localhost:3000/login"
    ):
        """Send welcome email with temporary password"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = "Welcome to the Payroll System - Your Account Details"
            
            body = f"""
            Dear {employee_name},
            
            Welcome to our payroll system! Your account has been created successfully.
            
            Your login credentials:
            Email: {to_email}
            Temporary Password: {temp_password}
            
            Please log in at: {login_url}
            
            IMPORTANT: You will be prompted to change your password on your first login.
            
            You can now:
            - Submit weekly timesheets
            - View your payslips
            - Update your profile information
            - Manage your bank account details
            
            If you have any questions, please contact HR.
            
            Best regards,
            Payroll Team
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
                
            print(f"Welcome email sent to {to_email}")
            
        except Exception as e:
            print(f"Error sending welcome email: {e}")
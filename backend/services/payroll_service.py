from typing import List, Dict, Any
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from backend.orm_models import Employee, Timesheet, PayrollRun, Payslip, TaxConfiguration, TimesheetStatus, PayrollStatus
from backend.services.tax_service import TaxService
from backend.services.payment_service import PaymentService
from backend.services.email_service import EmailService
from backend.services.pdf_service import PDFService

class PayrollService:
    def __init__(self):
        self.tax_service = TaxService()
        self.payment_service = PaymentService()
        self.email_service = EmailService()
        self.pdf_service = PDFService()
    
    async def create_payroll_run(
        self,
        db: AsyncSession,
        org_id: int,
        pay_period_start: datetime,
        pay_period_end: datetime,
        pay_date: datetime,
        processed_by: int
    ) -> PayrollRun:
        """Create a new payroll run"""
        payroll_run = PayrollRun(
            org_id=org_id,
            pay_period_start=pay_period_start,
            pay_period_end=pay_period_end,
            pay_date=pay_date,
            processed_by=processed_by
        )
        
        db.add(payroll_run)
        await db.commit()
        await db.refresh(payroll_run)
        
        return payroll_run
    
    async def process_payroll(self, db: AsyncSession, payroll_run_id: int) -> Dict[str, Any]:
        """Process payroll for all employees in the organization"""
        # Get payroll run
        result = await db.execute(select(PayrollRun).where(PayrollRun.id == payroll_run_id))
        payroll_run = result.scalar_one_or_none()
        
        if not payroll_run:
            raise ValueError("Payroll run not found")
        
        # Update status to processing
        payroll_run.status = PayrollStatus.PROCESSING
        await db.commit()
        
        try:
            # Get all active employees in the organization
            employees_result = await db.execute(
                select(Employee).where(
                    and_(
                        Employee.org_id == payroll_run.org_id,
                        Employee.is_active == True
                    )
                )
            )
            employees = employees_result.scalars().all()
            
            # Get tax configuration
            tax_config_result = await db.execute(
                select(TaxConfiguration).where(
                    and_(
                        TaxConfiguration.org_id == payroll_run.org_id,
                        TaxConfiguration.is_active == True
                    )
                )
            )
            tax_config = tax_config_result.scalar_one_or_none()
            
            if not tax_config:
                raise ValueError("Tax configuration not found for organization")
            
            total_gross_pay = Decimal('0')
            total_net_pay = Decimal('0')
            total_taxes = Decimal('0')
            
            # Process each employee
            for employee in employees:
                payslip = await self._process_employee_payroll(
                    db, employee, payroll_run, tax_config
                )
                
                total_gross_pay += payslip.gross_pay
                total_net_pay += payslip.net_pay
                total_taxes += payslip.total_deductions
            
            # Update payroll run totals
            payroll_run.total_gross_pay = total_gross_pay
            payroll_run.total_net_pay = total_net_pay
            payroll_run.total_taxes = total_taxes
            payroll_run.status = PayrollStatus.COMPLETED
            payroll_run.processed_at = datetime.utcnow()
            
            await db.commit()
            
            return {
                "payroll_run_id": payroll_run_id,
                "status": "completed",
                "total_employees": len(employees),
                "total_gross_pay": float(total_gross_pay),
                "total_net_pay": float(total_net_pay),
                "total_taxes": float(total_taxes)
            }
            
        except Exception as e:
            # Update status to failed
            payroll_run.status = PayrollStatus.FAILED
            await db.commit()
            raise e
    
    async def _process_employee_payroll(
        self,
        db: AsyncSession,
        employee: Employee,
        payroll_run: PayrollRun,
        tax_config: TaxConfiguration
    ) -> Payslip:
        """Process payroll for a single employee"""
        # Get approved timesheets for the pay period
        timesheets_result = await db.execute(
            select(Timesheet).where(
                and_(
                    Timesheet.employee_id == employee.id,
                    Timesheet.status == TimesheetStatus.APPROVED,
                    Timesheet.week_start_date >= payroll_run.pay_period_start,
                    Timesheet.week_end_date <= payroll_run.pay_period_end
                )
            )
        )
        timesheets = timesheets_result.scalars().all()
        
        # Calculate total hours
        total_regular_hours = Decimal('0')
        total_overtime_hours = Decimal('0')
        
        for timesheet in timesheets:
            total_regular_hours += timesheet.total_hours - timesheet.overtime_hours
            total_overtime_hours += timesheet.overtime_hours
        
        # Calculate gross pay
        if employee.salary_type.value == 'hourly':
            regular_pay = total_regular_hours * employee.hourly_rate
            overtime_pay = total_overtime_hours * employee.hourly_rate * Decimal('1.5')
        else:
            # Fixed salary - calculate based on pay period
            days_in_period = (payroll_run.pay_period_end - payroll_run.pay_period_start).days + 1
            regular_pay = (employee.base_salary / Decimal('365')) * Decimal(str(days_in_period))
            overtime_pay = Decimal('0')
        
        gross_pay = regular_pay + overtime_pay
        
        # Calculate taxes and deductions
        tax_calculations = self.tax_service.calculate_taxes(
            gross_pay=gross_pay,
            tax_config=tax_config,
            employee=employee
        )
        
        # Create payslip
        payslip = Payslip(
            employee_id=employee.id,
            payroll_run_id=payroll_run.id,
            pay_period_start=payroll_run.pay_period_start,
            pay_period_end=payroll_run.pay_period_end,
            pay_date=payroll_run.pay_date,
            regular_hours=total_regular_hours,
            overtime_hours=total_overtime_hours,
            regular_pay=regular_pay,
            overtime_pay=overtime_pay,
            gross_pay=gross_pay,
            federal_tax=tax_calculations['federal_tax'],
            state_tax=tax_calculations['state_tax'],
            social_security=tax_calculations['social_security'],
            medicare=tax_calculations['medicare'],
            total_deductions=tax_calculations['total_deductions'],
            net_pay=tax_calculations['net_pay']
        )
        
        db.add(payslip)
        await db.commit()
        await db.refresh(payslip)
        
        # Generate PDF payslip
        await self._generate_payslip_pdf(db, payslip, employee)
        
        # Send payment if configured
        if employee.bank_account_id:
            await self._process_payment(db, payslip, employee)
        
        return payslip
    
    async def _generate_payslip_pdf(self, db: AsyncSession, payslip: Payslip, employee: Employee):
        """Generate PDF payslip and upload to S3"""
        try:
            pdf_url = await self.pdf_service.generate_payslip_pdf(payslip, employee)
            
            payslip.pdf_url = pdf_url
            payslip.pdf_generated_at = datetime.utcnow()
            await db.commit()
            
            # Send email notification
            await self.email_service.send_payslip_notification(
                employee.email,
                employee.first_name,
                pdf_url,
                payslip.pay_date
            )
            
        except Exception as e:
            print(f"Error generating payslip PDF: {e}")
    
    async def _process_payment(self, db: AsyncSession, payslip: Payslip, employee: Employee):
        """Process payment to employee"""
        try:
            # Use Plaid for payment processing
            payment_result = await self.payment_service.send_payment_via_plaid(
                amount=payslip.net_pay,
                employee_id=employee.id,
                description=f"Payroll payment for {payslip.pay_period_start.strftime('%Y-%m-%d')} to {payslip.pay_period_end.strftime('%Y-%m-%d')}",
                db=db
            )
            
            payslip.payment_method = payment_result['method']
            payslip.payment_reference = payment_result.get('payment_id') or payment_result.get('reference')
            payslip.payment_status = payment_result['status']
            
            await db.commit()
            
        except Exception as e:
            logger.error(f"Error processing payment: {e}")
            # Don't fail the entire payroll process if payment fails
            payslip.payment_method = 'failed'
            payslip.payment_status = 'failed'
            await db.commit()

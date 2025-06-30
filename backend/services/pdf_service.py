from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import boto3
from io import BytesIO
from datetime import datetime
from decimal import Decimal
from typing import Any
from backend.config import settings
from backend.orm_models import Payslip, Employee

class PDFService:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.S3_REGION
        )
        self.bucket_name = settings.S3_BUCKET_NAME
    
    async def generate_payslip_pdf(self, payslip: Payslip, employee: Employee) -> str:
        """Generate payslip PDF and upload to S3 (main folder)"""
        
        # Create PDF in memory
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1  # Center alignment
        )
        story.append(Paragraph("PAYSLIP", title_style))
        
        # Employee Information
        emp_info = [
            ['Employee Information', ''],
            ['Name:', f"{employee.first_name} {employee.last_name}"],
            ['Employee ID:', employee.employee_id],
            ['Email:', employee.email],
            ['Department:', employee.department or 'N/A'],
            ['Position:', employee.position or 'N/A'],
        ]
        
        emp_table = Table(emp_info, colWidths=[2*inch, 4*inch])
        emp_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(emp_table)
        story.append(Spacer(1, 20))
        
        # Pay Period Information
        pay_info = [
            ['Pay Period Information', ''],
            ['Pay Period:', f"{payslip.pay_period_start.strftime('%Y-%m-%d')} to {payslip.pay_period_end.strftime('%Y-%m-%d')}"],
            ['Pay Date:', payslip.pay_date.strftime('%Y-%m-%d')],
            ['Regular Hours:', f"{payslip.regular_hours:.2f}"],
            ['Overtime Hours:', f"{payslip.overtime_hours:.2f}"],
        ]
        
        pay_table = Table(pay_info, colWidths=[2*inch, 4*inch])
        pay_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(pay_table)
        story.append(Spacer(1, 20))
        
        # Earnings and Deductions
        earnings_data = [
            ['Earnings', 'Amount'],
            ['Regular Pay', f"${payslip.regular_pay:.2f}"],
            ['Overtime Pay', f"${payslip.overtime_pay:.2f}"],
            ['Gross Pay', f"${payslip.gross_pay:.2f}"],
            ['', ''],
            ['Deductions', 'Amount'],
            ['Federal Tax', f"${payslip.federal_tax:.2f}"],
            ['State Tax', f"${payslip.state_tax:.2f}"],
            ['Social Security', f"${payslip.social_security:.2f}"],
            ['Medicare', f"${payslip.medicare:.2f}"],
            ['Total Deductions', f"${payslip.total_deductions:.2f}"],
            ['', ''],
            ['Net Pay', f"${payslip.net_pay:.2f}"],
        ]
        
        earnings_table = Table(earnings_data, colWidths=[3*inch, 2*inch])
        earnings_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.grey),
            ('BACKGROUND', (0, 5), (1, 5), colors.grey),
            ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
            ('TEXTCOLOR', (0, 5), (1, 5), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 5), (-1, 5), 'Helvetica-Bold'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('FONTSIZE', (0, 5), (-1, 5), 12),
            ('FONTSIZE', (0, -1), (-1, -1), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 5), (-1, 5), 12),
            ('BACKGROUND', (0, 1), (-1, 4), colors.beige),
            ('BACKGROUND', (0, 6), (-1, 10), colors.beige),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgreen),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(earnings_table)
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        # Upload to S3 in the main folder
        file_key = f"payslip_{employee.id}_{payslip.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        self.bucket_name = 'adeptai-payroll'
        try:
            self.s3_client.upload_fileobj(
                buffer,
                self.bucket_name,
                file_key,
                ExtraArgs={'ContentType': 'application/pdf'}
            )
            # Generate presigned URL (valid for 7 days)
            pdf_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': file_key},
                ExpiresIn=604800  # 7 days
            )
            return pdf_url
        except Exception as e:
            print(f"Error uploading PDF to S3: {e}")
            raise e

def generate_payslip_pdf(payslip, employee):
    """Convenience function to generate a payslip PDF and upload to S3."""
    service = PDFService()
    return service.generate_payslip_pdf(payslip, employee)

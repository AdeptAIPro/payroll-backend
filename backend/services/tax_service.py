from decimal import Decimal
from typing import Dict
from backend.orm_models import Employee, TaxConfiguration

class TaxService:
    def calculate_taxes(
        self,
        gross_pay: Decimal,
        tax_config: TaxConfiguration,
        employee: Employee
    ) -> Dict[str, Decimal]:
        """Calculate all tax deductions for an employee"""
        
        # Federal tax calculation (simplified)
        federal_tax = gross_pay * tax_config.federal_tax_rate
        
        # State tax calculation
        state_tax = gross_pay * tax_config.state_tax_rate
        
        # Social Security tax (6.2% up to wage base limit)
        social_security_wage_base = Decimal('160200')  # 2023 limit
        social_security = min(gross_pay, social_security_wage_base) * tax_config.social_security_rate
        
        # Medicare tax (1.45% on all wages)
        medicare = gross_pay * tax_config.medicare_rate
        
        # Additional Medicare tax (0.9% on wages over $200,000)
        medicare_threshold = Decimal('200000')
        if gross_pay > medicare_threshold:
            additional_medicare = (gross_pay - medicare_threshold) * Decimal('0.009')
            medicare += additional_medicare
        
        # Total deductions
        total_deductions = federal_tax + state_tax + social_security + medicare
        
        # Net pay
        net_pay = gross_pay - total_deductions
        
        return {
            'federal_tax': federal_tax.quantize(Decimal('0.01')),
            'state_tax': state_tax.quantize(Decimal('0.01')),
            'social_security': social_security.quantize(Decimal('0.01')),
            'medicare': medicare.quantize(Decimal('0.01')),
            'total_deductions': total_deductions.quantize(Decimal('0.01')),
            'net_pay': net_pay.quantize(Decimal('0.01'))
        }
    
    def calculate_annual_taxes(
        self,
        annual_salary: Decimal,
        tax_status: str = "single"
    ) -> Dict[str, Decimal]:
        """Calculate estimated annual taxes (simplified)"""
        
        # Federal tax brackets for 2023 (single filer)
        federal_brackets = [
            (Decimal('11000'), Decimal('0.10')),
            (Decimal('44725'), Decimal('0.12')),
            (Decimal('95375'), Decimal('0.22')),
            (Decimal('182050'), Decimal('0.24')),
            (Decimal('231250'), Decimal('0.32')),
            (Decimal('578125'), Decimal('0.35')),
            (float('inf'), Decimal('0.37'))
        ]
        
        federal_tax = Decimal('0')
        remaining_income = annual_salary
        previous_bracket = Decimal('0')
        
        for bracket_limit, rate in federal_brackets:
            if remaining_income <= 0:
                break
                
            taxable_in_bracket = min(remaining_income, bracket_limit - previous_bracket)
            federal_tax += taxable_in_bracket * rate
            remaining_income -= taxable_in_bracket
            previous_bracket = bracket_limit
        
        # Social Security and Medicare
        social_security = min(annual_salary, Decimal('160200')) * Decimal('0.062')
        medicare = annual_salary * Decimal('0.0145')
        
        return {
            'federal_tax': federal_tax.quantize(Decimal('0.01')),
            'social_security': social_security.quantize(Decimal('0.01')),
            'medicare': medicare.quantize(Decimal('0.01')),
            'total_annual_taxes': (federal_tax + social_security + medicare).quantize(Decimal('0.01'))
        }

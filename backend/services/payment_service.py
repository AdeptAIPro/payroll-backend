import stripe
from typing import Dict, Any
from decimal import Decimal
from backend.config import settings
from backend.services.plaid_service import plaid_service
import logging
from backend.orm_models import Employee, BankAccount

logger = logging.getLogger(__name__)

class PaymentService:
    def __init__(self):
        stripe.api_key = settings.STRIPE_SECRET_KEY
    
    async def send_payment_via_plaid(
        self,
        amount: Decimal,
        employee_id: int,
        description: str,
        db
    ) -> Dict[str, Any]:
        """Send payment via Plaid Payment Initiation"""
        try:
            from sqlalchemy import select
            
            # Get employee and their bank account
            employee_result = await db.execute(
                select(Employee).where(Employee.id == employee_id)
            )
            employee = employee_result.scalar_one_or_none()
            
            if not employee:
                raise ValueError("Employee not found")
            
            bank_account_result = await db.execute(
                select(BankAccount).where(
                    BankAccount.employee_id == employee_id,
                    BankAccount.is_verified == True
                )
            )
            bank_account = bank_account_result.scalar_one_or_none()
            
            if not bank_account:
                raise ValueError("No verified bank account found for employee")
            
            # Create payment recipient
            recipient_name = f"{employee.first_name} {employee.last_name}"
            recipient_id = await plaid_service.create_payment_recipient(recipient_name)
            
            # Create payment
            payment_id = await plaid_service.create_payment(
                recipient_id=recipient_id,
                reference=description,
                amount=amount
            )
            
            # Get payment status
            payment_status = await plaid_service.get_payment_status(payment_id)
            
            return {
                'method': 'plaid',
                'payment_id': payment_id,
                'recipient_id': recipient_id,
                'status': payment_status['status'],
                'reference': payment_status['reference']
            }
            
        except Exception as e:
            logger.error(f"Plaid payment error: {e}")
            return {
                'method': 'plaid',
                'payment_id': None,
                'status': 'failed',
                'error': str(e)
            }
    
    async def send_payment(
        self,
        amount: Decimal,
        recipient_account_id: str,
        description: str
    ) -> Dict[str, Any]:
        """Send payment via Stripe (legacy method)"""
        try:
            # Convert amount to cents
            amount_cents = int(amount * 100)
            
            # Create transfer (this is a simplified example)
            # In production, you'd need to set up Stripe Connect accounts
            transfer = stripe.Transfer.create(
                amount=amount_cents,
                currency='usd',
                destination=recipient_account_id,
                description=description
            )
            
            return {
                'method': 'stripe',
                'reference': transfer.id,
                'status': 'completed' if transfer.amount_reversed == 0 else 'failed'
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {e}")
            return {
                'method': 'stripe',
                'reference': None,
                'status': 'failed',
                'error': str(e)
            }
    
    async def verify_bank_account(self, plaid_access_token: str) -> Dict[str, Any]:
        """Verify bank account via Plaid"""
        try:
            # Get accounts from Plaid
            accounts = await plaid_service.get_accounts(plaid_access_token)
            
            if not accounts:
                return {
                    'verified': False,
                    'error': 'No accounts found'
                }
            
            # Return first depository account
            depository_accounts = [acc for acc in accounts if acc['type'] == 'depository']
            
            if not depository_accounts:
                return {
                    'verified': False,
                    'error': 'No depository accounts found'
                }
            
            account = depository_accounts[0]
            
            return {
                'verified': True,
                'account_id': account['account_id'],
                'account_name': account['name'],
                'account_type': account['type'],
                'account_subtype': account['subtype'],
                'mask': account['mask']
            }
            
        except Exception as e:
            logger.error(f"Error verifying bank account: {e}")
            return {
                'verified': False,
                'error': str(e)
            }
    
    async def get_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """Get payment status from Plaid"""
        try:
            return await plaid_service.get_payment_status(payment_id)
        except Exception as e:
            logger.error(f"Error getting payment status: {e}")
            return {
                'status': 'unknown',
                'error': str(e)
            } 
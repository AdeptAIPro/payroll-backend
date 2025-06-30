import plaid
from plaid.api import plaid_api
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products
from plaid.model.country_code import CountryCode
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.payment_initiation_payment_create_request import PaymentInitiationPaymentCreateRequest
from plaid.model.payment_amount import PaymentAmount
from plaid.model.payment_amount_currency import PaymentAmountCurrency
from plaid.model.payment_initiation_recipient_create_request import PaymentInitiationRecipientCreateRequest
from plaid.model.payment_initiation_recipient_get_request import PaymentInitiationRecipientGetRequest
from plaid.model.payment_initiation_payment_get_request import PaymentInitiationPaymentGetRequest
from typing import Dict, Any, List, Optional
from decimal import Decimal
from backend.config import settings
import logging

logger = logging.getLogger(__name__)

class PlaidService:
    def __init__(self):
        # Configure Plaid client
        configuration = plaid.Configuration(
            host=plaid.Environment.Sandbox if settings.PLAID_ENV == "sandbox" 
                 else plaid.Environment.Development if settings.PLAID_ENV == "development"
                 else plaid.Environment.Production,
            api_key={
                'clientId': settings.PLAID_CLIENT_ID,
                'secret': settings.PLAID_SECRET,
                'plaidVersion': '2020-09-14'
            }
        )
        
        api_client = plaid.ApiClient(configuration)
        self.client = plaid_api.PlaidApi(api_client)
    
    async def create_link_token(self, user_id: str, client_name: str = "Payroll System") -> str:
        """Create a link token for Plaid Link initialization"""
        try:
            request = LinkTokenCreateRequest(
                user=LinkTokenCreateRequestUser(client_user_id=user_id),
                client_name=client_name,
                products=[Products("auth")],
                country_codes=[CountryCode("US")],
                language="en"
            )
            
            response = self.client.link_token_create(request)
            return response.link_token
            
        except Exception as e:
            logger.error(f"Error creating link token: {e}")
            raise
    
    async def exchange_public_token(self, public_token: str) -> Dict[str, str]:
        """Exchange public token for access token"""
        try:
            request = ItemPublicTokenExchangeRequest(public_token=public_token)
            response = self.client.item_public_token_exchange(request)
            
            return {
                'access_token': response.access_token,
                'item_id': response.item_id
            }
            
        except Exception as e:
            logger.error(f"Error exchanging public token: {e}")
            raise
    
    async def get_accounts(self, access_token: str) -> List[Dict[str, Any]]:
        """Get bank accounts for an access token"""
        try:
            request = AccountsGetRequest(access_token=access_token)
            response = self.client.accounts_get(request)
            
            accounts = []
            for account in response.accounts:
                accounts.append({
                    'account_id': account.account_id,
                    'name': account.name,
                    'official_name': account.official_name,
                    'type': account.type.value,
                    'subtype': account.subtype.value,
                    'mask': account.mask,
                    'balances': {
                        'available': account.balances.available,
                        'current': account.balances.current,
                        'limit': account.balances.limit,
                        'iso_currency_code': account.balances.iso_currency_code
                    }
                })
            
            return accounts
            
        except Exception as e:
            logger.error(f"Error getting accounts: {e}")
            raise
    
    async def create_payment_recipient(
        self, 
        name: str, 
        iban: Optional[str] = None,
        address: Optional[Dict[str, str]] = None
    ) -> str:
        """Create a payment recipient"""
        try:
            request = PaymentInitiationRecipientCreateRequest(
                name=name,
                iban=iban,
                address=address
            )
            
            response = self.client.payment_initiation_recipient_create(request)
            return response.recipient_id
            
        except Exception as e:
            logger.error(f"Error creating payment recipient: {e}")
            raise
    
    async def create_payment(
        self,
        recipient_id: str,
        reference: str,
        amount: Decimal,
        currency: str = "USD"
    ) -> str:
        """Create a payment"""
        try:
            payment_amount = PaymentAmount(
                currency=PaymentAmountCurrency(currency),
                value=float(amount)
            )
            
            request = PaymentInitiationPaymentCreateRequest(
                recipient_id=recipient_id,
                reference=reference,
                amount=payment_amount
            )
            
            response = self.client.payment_initiation_payment_create(request)
            return response.payment_id
            
        except Exception as e:
            logger.error(f"Error creating payment: {e}")
            raise
    
    async def get_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """Get payment status"""
        try:
            request = PaymentInitiationPaymentGetRequest(payment_id=payment_id)
            response = self.client.payment_initiation_payment_get(request)
            
            return {
                'payment_id': response.payment_id,
                'status': response.status.value,
                'amount': {
                    'currency': response.amount.currency.value,
                    'value': response.amount.value
                },
                'reference': response.reference,
                'last_status_update': response.last_status_update,
                'recipient_id': response.recipient_id
            }
            
        except Exception as e:
            logger.error(f"Error getting payment status: {e}")
            raise
    
    async def verify_bank_account(self, access_token: str, account_id: str) -> Dict[str, Any]:
        """Verify a bank account (simplified - in production you'd use micro-deposits)"""
        try:
            # Get account details
            accounts = await self.get_accounts(access_token)
            account = next((acc for acc in accounts if acc['account_id'] == account_id), None)
            
            if not account:
                raise ValueError("Account not found")
            
            # In production, you would implement micro-deposit verification here
            # For now, we'll return the account details
            return {
                'verified': True,
                'account_id': account['account_id'],
                'account_name': account['name'],
                'account_type': account['type'],
                'account_subtype': account['subtype'],
                'mask': account['mask'],
                'balances': account['balances']
            }
            
        except Exception as e:
            logger.error(f"Error verifying bank account: {e}")
            raise

# Global instance
plaid_service = PlaidService() 
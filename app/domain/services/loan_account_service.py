from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from app.core.config import settings


class LoanAccountService(ABC):
    """Abstract base class for loan account service."""
    
    @abstractmethod
    def create_loan_account(self, user_id: int, credit_limit: float, apr: Optional[float] = None) -> Dict[str, Any]:
        """Create a new loan account for a user."""
        pass
    
    @abstractmethod
    def get_loan_account(self, loan_account_id: int) -> Dict[str, Any]:
        """Get loan account details."""
        pass
    
    @abstractmethod
    def update_loan_account(self, loan_account_id: int, **kwargs) -> Dict[str, Any]:
        """Update loan account details."""
        pass
    
    @abstractmethod
    def apply_daily_interest(self, loan_account_id: int) -> Dict[str, Any]:
        """Apply daily interest to a loan account."""
        pass


class StandardLoanAccountService(LoanAccountService):
    """Standard implementation of loan account service."""
    
    def __init__(self, db_session, interest_calculator=None):
        """Initialize the service with database session and interest calculator."""
        self.db = db_session
        from app.domain.services.interest_service import StandardInterestCalculator
        self.interest_calculator = interest_calculator or StandardInterestCalculator()
    
    def create_loan_account(self, user_id: int, credit_limit: float, apr: Optional[float] = None) -> Dict[str, Any]:
        """Create a new loan account for a user."""
        from app.domain.models.models import User, LoanAccount
        
        # Get the user
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User with ID {user_id} not found")
        
        # Use user's APR if not specified
        if apr is None:
            apr = user.apr
        
        # Create loan account
        loan_account = LoanAccount(
            user_id=user_id,
            credit_limit=credit_limit,
            apr=apr,
            current_balance=0.0,
            is_active=True
        )
        self.db.add(loan_account)
        self.db.commit()
        self.db.refresh(loan_account)
        
        return loan_account
    
    def get_loan_account(self, loan_account_id: int) -> Dict[str, Any]:
        """Get loan account details."""
        from app.domain.models.models import LoanAccount
        
        loan_account = self.db.query(LoanAccount).filter(LoanAccount.id == loan_account_id).first()
        if not loan_account:
            raise ValueError(f"Loan account with ID {loan_account_id} not found")
        
        return loan_account
    
    def update_loan_account(self, loan_account_id: int, **kwargs) -> Dict[str, Any]:
        """Update loan account details."""
        from app.domain.models.models import LoanAccount
        
        loan_account = self.db.query(LoanAccount).filter(LoanAccount.id == loan_account_id).first()
        if not loan_account:
            raise ValueError(f"Loan account with ID {loan_account_id} not found")
        
        # Update fields
        for key, value in kwargs.items():
            if hasattr(loan_account, key):
                setattr(loan_account, key, value)
        
        self.db.commit()
        self.db.refresh(loan_account)
        
        return loan_account
    
    def apply_daily_interest(self, loan_account_id: int) -> Dict[str, Any]:
        """Apply daily interest to a loan account.
        
        This method:
        1. Calculates daily interest based on current balance and APR
        2. Adds interest to the current balance
        3. Creates a transaction record for the interest
        4. Returns the interest details
        """
        from app.domain.models.models import LoanAccount, Transaction, TransactionType
        
        # Get the loan account
        loan_account = self.db.query(LoanAccount).filter(LoanAccount.id == loan_account_id).first()
        if not loan_account:
            raise ValueError(f"Loan account with ID {loan_account_id} not found")
        
        # Skip if balance is zero
        if loan_account.current_balance <= 0:
            return {
                "interest_applied": 0.0,
                "new_balance": loan_account.current_balance
            }
        
        # Calculate daily interest
        daily_interest = self.interest_calculator.calculate_daily_interest(
            loan_account.current_balance, loan_account.apr
        )
        
        # Round to 2 decimal places
        daily_interest = round(daily_interest, 2)
        
        # Add interest to balance
        loan_account.current_balance += daily_interest
        
        # Create transaction record
        transaction = Transaction(
            loan_account_id=loan_account_id,
            type=TransactionType.INTEREST,
            amount=daily_interest,
            description=f"Daily interest at {loan_account.apr}% APR"
        )
        self.db.add(transaction)
        
        # Commit changes
        self.db.commit()
        
        return {
            "interest_applied": daily_interest,
            "new_balance": loan_account.current_balance,
            "transaction_id": transaction.id
        }
    
    def apply_late_fee(self, loan_account_id: int) -> Dict[str, Any]:
        """Apply late fee to a loan account if applicable.
        
        Late fees are capped at £5 per month for a maximum of 3 months.
        """
        from app.domain.models.models import LoanAccount, Transaction, TransactionType
        from sqlalchemy import func
        
        # Get the loan account
        loan_account = self.db.query(LoanAccount).filter(LoanAccount.id == loan_account_id).first()
        if not loan_account:
            raise ValueError(f"Loan account with ID {loan_account_id} not found")
        
        # Check if account has an outstanding balance
        if loan_account.current_balance <= 0:
            return {
                "fee_applied": 0.0,
                "reason": "No outstanding balance"
            }
        
        # Count existing late fees in the last 3 months
        three_months_ago = datetime.utcnow() - timedelta(days=90)
        late_fee_count = self.db.query(func.count(Transaction.id)).filter(
            Transaction.loan_account_id == loan_account_id,
            Transaction.type == TransactionType.FEE,
            Transaction.is_late_fee == True,
            Transaction.date >= three_months_ago
        ).scalar()
        
        # Check if we've reached the maximum number of late fees
        if late_fee_count >= settings.MAX_LATE_FEE_MONTHS:
            return {
                "fee_applied": 0.0,
                "reason": f"Maximum number of late fees ({settings.MAX_LATE_FEE_MONTHS}) already applied"
            }
        
        # Apply late fee
        late_fee = settings.LATE_FEE_AMOUNT
        
        # Add fee to balance
        loan_account.current_balance += late_fee
        
        # Create transaction record
        transaction = Transaction(
            loan_account_id=loan_account_id,
            type=TransactionType.FEE,
            amount=late_fee,
            description="Late payment fee",
            is_late_fee=True
        )
        self.db.add(transaction)
        
        # Commit changes
        self.db.commit()
        
        return {
            "fee_applied": late_fee,
            "new_balance": loan_account.current_balance,
            "transaction_id": transaction.id
        }

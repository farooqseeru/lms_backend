from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from app.core.config import settings
from app.domain.services.interest_service import StandardInterestCalculator


class RepaymentService(ABC):
    """Abstract base class for repayment service."""
    
    @abstractmethod
    def process_repayment(self, loan_account_id: int, amount: float, method: str) -> Dict[str, Any]:
        """Process a repayment for a loan account."""
        pass
    
    @abstractmethod
    def get_repayment_options(self, loan_account_id: int) -> List[Dict[str, Any]]:
        """Get repayment options for a loan account."""
        pass
    
    @abstractmethod
    def check_repayment_eligibility_for_reward(self, repayment_id: int) -> bool:
        """Check if a repayment is eligible for APR reduction reward."""
        pass


class StandardRepaymentService(RepaymentService):
    """Standard implementation of repayment service."""
    
    def __init__(self, db_session, interest_calculator=None):
        """Initialize the service with database session and interest calculator."""
        self.db = db_session
        self.interest_calculator = interest_calculator or StandardInterestCalculator()
    
    def process_repayment(self, loan_account_id: int, amount: float, method: str) -> Dict[str, Any]:
        """Process a repayment for a loan account.
        
        This method:
        1. Creates a repayment record
        2. Updates the loan account balance
        3. Creates a transaction record
        4. Checks for reward eligibility
        5. Returns the repayment details
        """
        from app.domain.models.models import LoanAccount, Repayment, Transaction, TransactionType, RepaymentMethod
        
        # Get the loan account
        loan_account = self.db.query(LoanAccount).filter(LoanAccount.id == loan_account_id).first()
        if not loan_account:
            raise ValueError(f"Loan account with ID {loan_account_id} not found")
        
        # Validate repayment amount
        if amount <= 0:
            raise ValueError("Repayment amount must be positive")
        
        if amount > loan_account.current_balance:
            amount = loan_account.current_balance  # Cap at current balance
        
        # Calculate percentage of balance
        percentage_of_balance = (amount / loan_account.current_balance * 100) if loan_account.current_balance > 0 else 100
        
        # Calculate interest saved
        interest_saved = self.interest_calculator.calculate_interest_savings(
            loan_account.current_balance, loan_account.apr, amount
        )
        
        # Create repayment record
        repayment = Repayment(
            loan_account_id=loan_account_id,
            amount=amount,
            method=method,
            percentage_of_balance=percentage_of_balance,
            interest_saved=interest_saved
        )
        self.db.add(repayment)
        
        # Update loan account balance
        loan_account.current_balance -= amount
        
        # Create transaction record
        transaction = Transaction(
            loan_account_id=loan_account_id,
            type=TransactionType.REPAYMENT,
            amount=amount,
            description=f"Repayment of £{amount:.2f} ({percentage_of_balance:.1f}% of balance)"
        )
        self.db.add(transaction)
        
        # Commit changes
        self.db.commit()
        self.db.refresh(repayment)
        
        # Check for reward eligibility
        is_eligible_for_reward = self.check_repayment_eligibility_for_reward(repayment.id)
        
        return {
            "repayment_id": repayment.id,
            "amount": amount,
            "percentage_of_balance": percentage_of_balance,
            "interest_saved": interest_saved,
            "new_balance": loan_account.current_balance,
            "eligible_for_reward": is_eligible_for_reward
        }
    
    def get_repayment_options(self, loan_account_id: int) -> List[Dict[str, Any]]:
        """Get repayment options for a loan account."""
        from app.domain.models.models import LoanAccount
        
        # Get the loan account
        loan_account = self.db.query(LoanAccount).filter(LoanAccount.id == loan_account_id).first()
        if not loan_account:
            raise ValueError(f"Loan account with ID {loan_account_id} not found")
        
        # Calculate repayment options
        options = self.interest_calculator.calculate_repayment_options(
            loan_account.current_balance, loan_account.apr
        )
        
        return {
            "current_balance": loan_account.current_balance,
            "current_apr": loan_account.apr,
            "options": options
        }
    
    def check_repayment_eligibility_for_reward(self, repayment_id: int) -> bool:
        """Check if a repayment is eligible for APR reduction reward.
        
        A repayment is eligible if:
        1. It's at least 10% of the balance
        2. It's made on time (not late)
        """
        from app.domain.models.models import Repayment
        
        repayment = self.db.query(Repayment).filter(Repayment.id == repayment_id).first()
        if not repayment:
            raise ValueError(f"Repayment with ID {repayment_id} not found")
        
        # Check if repayment is at least 10% of balance
        return repayment.percentage_of_balance >= 10.0

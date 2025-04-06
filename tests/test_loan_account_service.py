import pytest
from app.domain.services.loan_account_service import StandardLoanAccountService
from app.domain.models.models import LoanAccount, Transaction, TransactionType


class TestLoanAccountService:
    """Test the loan account service."""
    
    def test_create_loan_account(self, db_session, test_user):
        """Test creating a loan account."""
        # Setup
        loan_account_service = StandardLoanAccountService(db_session)
        credit_limit = 5000.0
        apr = 25.0
        
        # Create loan account
        loan_account = loan_account_service.create_loan_account(
            user_id=test_user.id,
            credit_limit=credit_limit,
            apr=apr
        )
        
        # Verify loan account
        assert loan_account.user_id == test_user.id
        assert loan_account.credit_limit == credit_limit
        assert loan_account.apr == apr
        assert loan_account.current_balance == 0.0
        assert loan_account.is_active is True
    
    def test_get_loan_account(self, db_session, test_loan_account):
        """Test getting a loan account."""
        # Setup
        loan_account_service = StandardLoanAccountService(db_session)
        
        # Get loan account
        loan_account = loan_account_service.get_loan_account(test_loan_account.id)
        
        # Verify loan account
        assert loan_account.id == test_loan_account.id
        assert loan_account.user_id == test_loan_account.user_id
        assert loan_account.credit_limit == test_loan_account.credit_limit
        assert loan_account.apr == test_loan_account.apr
    
    def test_update_loan_account(self, db_session, test_loan_account):
        """Test updating a loan account."""
        # Setup
        loan_account_service = StandardLoanAccountService(db_session)
        new_credit_limit = 7500.0
        new_apr = 23.0
        
        # Update loan account
        updated_loan_account = loan_account_service.update_loan_account(
            loan_account_id=test_loan_account.id,
            credit_limit=new_credit_limit,
            apr=new_apr
        )
        
        # Verify updates
        assert updated_loan_account.credit_limit == new_credit_limit
        assert updated_loan_account.apr == new_apr
        
        # Verify database changes
        db_session.refresh(test_loan_account)
        assert test_loan_account.credit_limit == new_credit_limit
        assert test_loan_account.apr == new_apr
    
    def test_apply_daily_interest_with_balance(self, db_session, test_loan_account):
        """Test applying daily interest to a loan account with balance."""
        # Setup
        loan_account_service = StandardLoanAccountService(db_session)
        initial_balance = test_loan_account.current_balance
        
        # Apply daily interest
        result = loan_account_service.apply_daily_interest(test_loan_account.id)
        
        # Calculate expected interest
        expected_interest = initial_balance * (test_loan_account.apr / 100 / 365)
        expected_interest = round(expected_interest, 2)
        
        # Verify result
        assert result["interest_applied"] == pytest.approx(expected_interest)
        assert result["new_balance"] == pytest.approx(initial_balance + expected_interest)
        
        # Verify database changes
        db_session.refresh(test_loan_account)
        assert test_loan_account.current_balance == pytest.approx(initial_balance + expected_interest)
        
        # Verify transaction record
        transaction = db_session.query(Transaction).filter(
            Transaction.loan_account_id == test_loan_account.id,
            Transaction.type == TransactionType.INTEREST
        ).first()
        assert transaction is not None
        assert transaction.amount == pytest.approx(expected_interest)
    
    def test_apply_daily_interest_zero_balance(self, db_session, test_loan_account):
        """Test applying daily interest to a loan account with zero balance."""
        # Setup
        loan_account_service = StandardLoanAccountService(db_session)
        test_loan_account.current_balance = 0.0
        db_session.commit()
        
        # Apply daily interest
        result = loan_account_service.apply_daily_interest(test_loan_account.id)
        
        # Verify no interest applied
        assert result["interest_applied"] == 0.0
        assert result["new_balance"] == 0.0
        
        # Verify no transaction record created
        transaction_count = db_session.query(Transaction).filter(
            Transaction.loan_account_id == test_loan_account.id,
            Transaction.type == TransactionType.INTEREST
        ).count()
        assert transaction_count == 0
    
    def test_apply_late_fee(self, db_session, test_loan_account):
        """Test applying late fee to a loan account."""
        # Setup
        loan_account_service = StandardLoanAccountService(db_session)
        initial_balance = test_loan_account.current_balance
        
        # Apply late fee
        result = loan_account_service.apply_late_fee(test_loan_account.id)
        
        # Verify result
        assert result["fee_applied"] == 5.0  # £5 late fee
        assert result["new_balance"] == initial_balance + 5.0
        
        # Verify database changes
        db_session.refresh(test_loan_account)
        assert test_loan_account.current_balance == initial_balance + 5.0
        
        # Verify transaction record
        transaction = db_session.query(Transaction).filter(
            Transaction.loan_account_id == test_loan_account.id,
            Transaction.type == TransactionType.FEE,
            Transaction.is_late_fee == True
        ).first()
        assert transaction is not None
        assert transaction.amount == 5.0
    
    def test_apply_late_fee_max_reached(self, db_session, test_loan_account):
        """Test applying late fee when maximum number of late fees is reached."""
        # Setup
        loan_account_service = StandardLoanAccountService(db_session)
        
        # Create 3 late fee transactions (max allowed)
        for _ in range(3):
            transaction = Transaction(
                loan_account_id=test_loan_account.id,
                type=TransactionType.FEE,
                amount=5.0,
                description="Late payment fee",
                is_late_fee=True
            )
            db_session.add(transaction)
        db_session.commit()
        
        # Apply late fee
        result = loan_account_service.apply_late_fee(test_loan_account.id)
        
        # Verify no fee applied
        assert result["fee_applied"] == 0.0
        assert "Maximum number of late fees" in result["reason"]
        
        # Verify no additional transaction record
        transaction_count = db_session.query(Transaction).filter(
            Transaction.loan_account_id == test_loan_account.id,
            Transaction.type == TransactionType.FEE,
            Transaction.is_late_fee == True
        ).count()
        assert transaction_count == 3  # Still only 3 late fees

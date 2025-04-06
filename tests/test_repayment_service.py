import pytest
from app.domain.services.repayment_service import StandardRepaymentService
from app.domain.models.models import LoanAccount, Repayment, Transaction, TransactionType, RepaymentMethod


class TestRepaymentService:
    """Test the repayment service."""
    
    def test_process_repayment(self, db_session, test_loan_account):
        """Test processing a repayment."""
        # Setup
        repayment_service = StandardRepaymentService(db_session)
        initial_balance = test_loan_account.current_balance
        repayment_amount = 250.0  # 25% of 1000.0
        
        # Process repayment
        result = repayment_service.process_repayment(
            loan_account_id=test_loan_account.id,
            amount=repayment_amount,
            method=RepaymentMethod.MANUAL
        )
        
        # Verify result
        assert result["amount"] == repayment_amount
        assert result["percentage_of_balance"] == pytest.approx(25.0)
        assert result["new_balance"] == pytest.approx(initial_balance - repayment_amount)
        
        # Verify database changes
        db_session.refresh(test_loan_account)
        assert test_loan_account.current_balance == pytest.approx(initial_balance - repayment_amount)
        
        # Verify repayment record
        repayment = db_session.query(Repayment).filter(
            Repayment.loan_account_id == test_loan_account.id
        ).first()
        assert repayment is not None
        assert repayment.amount == repayment_amount
        assert repayment.method == RepaymentMethod.MANUAL
        assert repayment.percentage_of_balance == pytest.approx(25.0)
        
        # Verify transaction record
        transaction = db_session.query(Transaction).filter(
            Transaction.loan_account_id == test_loan_account.id,
            Transaction.type == TransactionType.REPAYMENT
        ).first()
        assert transaction is not None
        assert transaction.amount == repayment_amount
    
    def test_process_repayment_full_amount(self, db_session, test_loan_account):
        """Test processing a full repayment."""
        # Setup
        repayment_service = StandardRepaymentService(db_session)
        initial_balance = test_loan_account.current_balance
        
        # Process full repayment
        result = repayment_service.process_repayment(
            loan_account_id=test_loan_account.id,
            amount=initial_balance,
            method=RepaymentMethod.MANUAL
        )
        
        # Verify result
        assert result["amount"] == initial_balance
        assert result["percentage_of_balance"] == pytest.approx(100.0)
        assert result["new_balance"] == 0.0
        
        # Verify database changes
        db_session.refresh(test_loan_account)
        assert test_loan_account.current_balance == 0.0
    
    def test_process_repayment_over_balance(self, db_session, test_loan_account):
        """Test processing a repayment larger than the balance."""
        # Setup
        repayment_service = StandardRepaymentService(db_session)
        initial_balance = test_loan_account.current_balance
        over_amount = initial_balance * 1.5
        
        # Process over-balance repayment
        result = repayment_service.process_repayment(
            loan_account_id=test_loan_account.id,
            amount=over_amount,
            method=RepaymentMethod.MANUAL
        )
        
        # Verify result is capped at current balance
        assert result["amount"] == initial_balance
        assert result["percentage_of_balance"] == pytest.approx(100.0)
        assert result["new_balance"] == 0.0
        
        # Verify database changes
        db_session.refresh(test_loan_account)
        assert test_loan_account.current_balance == 0.0
    
    def test_get_repayment_options(self, db_session, test_loan_account):
        """Test getting repayment options."""
        # Setup
        repayment_service = StandardRepaymentService(db_session)
        
        # Get repayment options
        options = repayment_service.get_repayment_options(test_loan_account.id)
        
        # Verify options
        assert options["current_balance"] == test_loan_account.current_balance
        assert options["current_apr"] == test_loan_account.apr
        assert len(options["options"]) == 5  # 10%, 25%, 50%, 75%, 100%
        
        # Check specific options
        assert options["options"][0]["percentage"] == 10.0
        assert options["options"][0]["amount"] == pytest.approx(test_loan_account.current_balance * 0.1)
        
        assert options["options"][4]["percentage"] == 100.0
        assert options["options"][4]["amount"] == pytest.approx(test_loan_account.current_balance)
    
    def test_check_repayment_eligibility_for_reward(self, db_session, test_loan_account):
        """Test checking if a repayment is eligible for APR reduction reward."""
        # Setup
        repayment_service = StandardRepaymentService(db_session)
        
        # Create a repayment with 10% of balance (eligible)
        eligible_repayment = Repayment(
            loan_account_id=test_loan_account.id,
            amount=test_loan_account.current_balance * 0.1,
            method=RepaymentMethod.MANUAL,
            percentage_of_balance=10.0
        )
        db_session.add(eligible_repayment)
        db_session.commit()
        db_session.refresh(eligible_repayment)
        
        # Check eligibility
        is_eligible = repayment_service.check_repayment_eligibility_for_reward(eligible_repayment.id)
        assert is_eligible is True
        
        # Create a repayment with 5% of balance (not eligible)
        not_eligible_repayment = Repayment(
            loan_account_id=test_loan_account.id,
            amount=test_loan_account.current_balance * 0.05,
            method=RepaymentMethod.MANUAL,
            percentage_of_balance=5.0
        )
        db_session.add(not_eligible_repayment)
        db_session.commit()
        db_session.refresh(not_eligible_repayment)
        
        # Check eligibility
        is_eligible = repayment_service.check_repayment_eligibility_for_reward(not_eligible_repayment.id)
        assert is_eligible is False

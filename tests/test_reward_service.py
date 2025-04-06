import pytest
from app.domain.services.reward_service import StandardRewardService
from app.domain.models.models import User, LoanAccount, Repayment, RewardAdjustment, RepaymentMethod
from app.core.config import settings


class TestRewardService:
    """Test the reward service."""
    
    def test_check_and_apply_apr_reduction_not_eligible_not_enough_repayments(self, db_session, test_user, test_loan_account):
        """Test checking for APR reduction when user doesn't have enough repayments."""
        # Setup
        reward_service = StandardRewardService(db_session)
        
        # Create one good repayment (not enough for reward)
        repayment = Repayment(
            loan_account_id=test_loan_account.id,
            amount=test_loan_account.current_balance * 0.25,
            method=RepaymentMethod.MANUAL,
            percentage_of_balance=25.0
        )
        db_session.add(repayment)
        db_session.commit()
        
        # Check for APR reduction
        result = reward_service.check_and_apply_apr_reduction(test_user.id)
        
        # Verify not eligible
        assert result["eligible"] is False
        assert "Not enough repayments" in result["reason"]
        
        # Verify no changes to APR
        db_session.refresh(test_user)
        assert test_user.apr == 25.0
    
    def test_check_and_apply_apr_reduction_eligible(self, db_session, test_user, test_loan_account):
        """Test checking for APR reduction when user is eligible."""
        # Setup
        reward_service = StandardRewardService(db_session)
        initial_apr = test_user.apr
        
        # Create required number of good repayments
        for _ in range(settings.APR_REDUCTION_AFTER_REPAYMENTS):
            repayment = Repayment(
                loan_account_id=test_loan_account.id,
                amount=test_loan_account.current_balance * 0.25,
                method=RepaymentMethod.MANUAL,
                percentage_of_balance=25.0
            )
            db_session.add(repayment)
        db_session.commit()
        
        # Check for APR reduction
        result = reward_service.check_and_apply_apr_reduction(test_user.id)
        
        # Verify eligible and APR reduced
        assert result["eligible"] is True
        assert result["old_apr"] == initial_apr
        assert result["new_apr"] == initial_apr - settings.APR_REDUCTION_AMOUNT
        
        # Verify changes to user APR
        db_session.refresh(test_user)
        assert test_user.apr == initial_apr - settings.APR_REDUCTION_AMOUNT
        
        # Verify changes to loan account APR
        db_session.refresh(test_loan_account)
        assert test_loan_account.apr == initial_apr - settings.APR_REDUCTION_AMOUNT
        
        # Verify reward adjustment record
        adjustment = db_session.query(RewardAdjustment).filter(
            RewardAdjustment.user_id == test_user.id
        ).first()
        assert adjustment is not None
        assert adjustment.old_apr == initial_apr
        assert adjustment.new_apr == initial_apr - settings.APR_REDUCTION_AMOUNT
    
    def test_check_and_apply_apr_reduction_not_eligible_bad_repayments(self, db_session, test_user, test_loan_account):
        """Test checking for APR reduction when user has some bad repayments."""
        # Setup
        reward_service = StandardRewardService(db_session)
        
        # Create some good repayments
        for _ in range(settings.APR_REDUCTION_AFTER_REPAYMENTS - 1):
            repayment = Repayment(
                loan_account_id=test_loan_account.id,
                amount=test_loan_account.current_balance * 0.25,
                method=RepaymentMethod.MANUAL,
                percentage_of_balance=25.0
            )
            db_session.add(repayment)
        
        # Create one bad repayment (less than 10%)
        bad_repayment = Repayment(
            loan_account_id=test_loan_account.id,
            amount=test_loan_account.current_balance * 0.05,
            method=RepaymentMethod.MANUAL,
            percentage_of_balance=5.0
        )
        db_session.add(bad_repayment)
        db_session.commit()
        
        # Check for APR reduction
        result = reward_service.check_and_apply_apr_reduction(test_user.id)
        
        # Verify not eligible
        assert result["eligible"] is False
        assert "Not all recent repayments meet the minimum percentage requirement" in result["reason"]
        
        # Verify no changes to APR
        db_session.refresh(test_user)
        assert test_user.apr == 25.0
    
    def test_get_reward_history(self, db_session, test_user):
        """Test getting reward history for a user."""
        # Setup
        reward_service = StandardRewardService(db_session)
        
        # Create some reward adjustments
        adjustment1 = RewardAdjustment(
            user_id=test_user.id,
            old_apr=25.0,
            new_apr=23.0,
            reason="Reward for good repayments"
        )
        adjustment2 = RewardAdjustment(
            user_id=test_user.id,
            old_apr=23.0,
            new_apr=21.0,
            reason="Reward for good repayments"
        )
        db_session.add(adjustment1)
        db_session.add(adjustment2)
        db_session.commit()
        
        # Get reward history
        history = reward_service.get_reward_history(test_user.id)
        
        # Verify history
        assert len(history) == 2
        assert history[0].old_apr == 23.0
        assert history[0].new_apr == 21.0
        assert history[1].old_apr == 25.0
        assert history[1].new_apr == 23.0

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from app.core.config import settings


class RewardService(ABC):
    """Abstract base class for reward service."""
    
    @abstractmethod
    def check_and_apply_apr_reduction(self, user_id: int) -> Dict[str, Any]:
        """Check if user is eligible for APR reduction and apply if eligible."""
        pass
    
    @abstractmethod
    def get_reward_history(self, user_id: int) -> List[Dict[str, Any]]:
        """Get reward history for a user."""
        pass


class StandardRewardService(RewardService):
    """Standard implementation of reward service."""
    
    def __init__(self, db_session):
        """Initialize the service with database session."""
        self.db = db_session
    
    def check_and_apply_apr_reduction(self, user_id: int) -> Dict[str, Any]:
        """Check if user is eligible for APR reduction and apply if eligible.
        
        A user is eligible for APR reduction if they have made the required
        number of consecutive good repayments (as defined in settings).
        """
        from app.domain.models.models import User, Repayment, RewardAdjustment, LoanAccount
        
        # Get the user
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User with ID {user_id} not found")
        
        # Get the user's loan accounts
        loan_accounts = self.db.query(LoanAccount).filter(
            LoanAccount.user_id == user_id,
            LoanAccount.is_active == True
        ).all()
        
        if not loan_accounts:
            return {"eligible": False, "reason": "No active loan accounts"}
        
        # Get recent repayments across all loan accounts
        loan_account_ids = [la.id for la in loan_accounts]
        recent_repayments = self.db.query(Repayment).filter(
            Repayment.loan_account_id.in_(loan_account_ids)
        ).order_by(Repayment.repayment_date.desc()).limit(settings.APR_REDUCTION_AFTER_REPAYMENTS).all()
        
        # Check if we have enough repayments
        if len(recent_repayments) < settings.APR_REDUCTION_AFTER_REPAYMENTS:
            return {
                "eligible": False, 
                "reason": f"Not enough repayments. Need {settings.APR_REDUCTION_AFTER_REPAYMENTS}, have {len(recent_repayments)}"
            }
        
        # Check if all repayments are good (at least 10% of balance)
        all_good = all(repayment.percentage_of_balance >= 10.0 for repayment in recent_repayments)
        if not all_good:
            return {"eligible": False, "reason": "Not all recent repayments meet the minimum percentage requirement"}
        
        # User is eligible for APR reduction
        old_apr = user.apr
        
        # Don't reduce below a minimum threshold (e.g., 10%)
        min_apr = 10.0
        new_apr = max(old_apr - settings.APR_REDUCTION_AMOUNT, min_apr)
        
        # If APR is already at minimum, no reduction
        if old_apr <= min_apr:
            return {"eligible": False, "reason": "APR already at minimum threshold"}
        
        # Apply APR reduction
        user.apr = new_apr
        
        # Update APR on all active loan accounts
        for loan_account in loan_accounts:
            loan_account.apr = new_apr
        
        # Create reward adjustment record
        reward_adjustment = RewardAdjustment(
            user_id=user_id,
            old_apr=old_apr,
            new_apr=new_apr,
            reason=f"Reward for {settings.APR_REDUCTION_AFTER_REPAYMENTS} consecutive good repayments"
        )
        self.db.add(reward_adjustment)
        
        # Commit changes
        self.db.commit()
        self.db.refresh(reward_adjustment)
        
        return {
            "eligible": True,
            "old_apr": old_apr,
            "new_apr": new_apr,
            "reduction": old_apr - new_apr,
            "adjustment_id": reward_adjustment.id
        }
    
    def get_reward_history(self, user_id: int) -> List[Dict[str, Any]]:
        """Get reward history for a user."""
        from app.domain.models.models import RewardAdjustment
        
        # Get reward adjustments for the user
        adjustments = self.db.query(RewardAdjustment).filter(
            RewardAdjustment.user_id == user_id
        ).order_by(RewardAdjustment.adjusted_on.desc()).all()
        
        # Convert SQLAlchemy models to dictionaries
        return [
            {
                "id": adj.id,
                "user_id": adj.user_id,
                "old_apr": adj.old_apr,
                "new_apr": adj.new_apr,
                "reason": adj.reason,
                "adjusted_on": adj.adjusted_on,
                "created_at": adj.created_at,
                "updated_at": adj.updated_at
            }
            for adj in adjustments
        ]

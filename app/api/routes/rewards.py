from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List

from app.api.schemas.schemas import (
    RewardAdjustment, DataResponse, ErrorResponse
)
from app.domain.services.reward_service import StandardRewardService
from app.domain.services.security_service import StandardSecurityService
from app.infrastructure.database.base import get_db

router = APIRouter()


@router.post("/users/{user_id}/check-rewards", response_model=DataResponse)
def check_and_apply_rewards(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Check if user is eligible for APR reduction and apply if eligible."""
    reward_service = StandardRewardService(db)
    
    try:
        result = reward_service.check_and_apply_apr_reduction(user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    
    # Log security event if APR was reduced
    if result.get("eligible", False):
        security_service = StandardSecurityService(db)
        security_service.log_security_event(
            user_id=user_id,
            action="APR_REDUCTION",
            entity_type="User",
            entity_id=user_id,
            ip_address=request.client.host,
            details=f"APR reduced from {result['old_apr']}% to {result['new_apr']}%"
        )
    
    return {"status": "success", "data": result}


@router.get("/users/{user_id}/rewards", response_model=DataResponse)
def get_reward_history(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get reward history for a user."""
    from app.domain.models.models import User, RewardAdjustment as RewardAdjustmentModel
    from app.api.schemas.schemas import RewardAdjustment
    
    # Check if user exists
    user = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    reward_service = StandardRewardService(db)
    rewards = reward_service.get_reward_history(user_id)
    
    # Return the list of rewards in the data field
    return {"status": "success", "data": {"rewards": rewards}}

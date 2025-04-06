from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List

from app.api.schemas.schemas import (
    RepaymentCreate, Repayment, RepaymentOptions, DataResponse, ErrorResponse
)
from app.domain.services.repayment_service import StandardRepaymentService
from app.domain.services.reward_service import StandardRewardService
from app.domain.services.security_service import StandardSecurityService
from app.infrastructure.database.base import get_db

router = APIRouter()


@router.post("/", response_model=DataResponse, status_code=status.HTTP_201_CREATED)
def create_repayment(
    repayment_in: RepaymentCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Process a repayment for a loan account."""
    repayment_service = StandardRepaymentService(db)
    
    # Get loan account to check user_id for security logging
    from app.domain.models.models import LoanAccount
    loan_account = db.query(LoanAccount).filter(LoanAccount.id == repayment_in.loan_account_id).first()
    if not loan_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Loan account with ID {repayment_in.loan_account_id} not found"
        )
    
    # Process repayment
    try:
        repayment_result = repayment_service.process_repayment(
            loan_account_id=repayment_in.loan_account_id,
            amount=repayment_in.amount,
            method=repayment_in.method
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # Log security event
    security_service = StandardSecurityService(db)
    security_service.log_security_event(
        user_id=loan_account.user_id,
        action="REPAYMENT_CREATE",
        entity_type="Repayment",
        entity_id=repayment_result["repayment_id"],
        ip_address=request.client.host,
        details=f"Repayment of £{repayment_in.amount:.2f} processed"
    )
    
    # Check if user is eligible for APR reduction reward
    if repayment_result.get("eligible_for_reward", False):
        reward_service = StandardRewardService(db)
        reward_result = reward_service.check_and_apply_apr_reduction(loan_account.user_id)
        
        # If APR was reduced, log it
        if reward_result.get("eligible", False):
            security_service.log_security_event(
                user_id=loan_account.user_id,
                action="APR_REDUCTION",
                entity_type="User",
                entity_id=loan_account.user_id,
                ip_address=request.client.host,
                details=f"APR reduced from {reward_result['old_apr']}% to {reward_result['new_apr']}%"
            )
            
            # Add reward info to response
            repayment_result["reward"] = {
                "apr_reduced": True,
                "old_apr": reward_result["old_apr"],
                "new_apr": reward_result["new_apr"],
                "reduction": reward_result["reduction"]
            }
    
    return {"status": "success", "data": repayment_result}


@router.get("/loan-accounts/{loan_account_id}/repayment-options", response_model=DataResponse)
def get_repayment_options(
    loan_account_id: int,
    db: Session = Depends(get_db)
):
    """Get repayment options for a loan account."""
    repayment_service = StandardRepaymentService(db)
    
    try:
        options = repayment_service.get_repayment_options(loan_account_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    
    # Convert to RepaymentOptions Pydantic model
    options_out = RepaymentOptions.model_validate(options)
    return {"status": "success", "data": options_out.model_dump()}


@router.get("/loan-accounts/{loan_account_id}/repayments", response_model=DataResponse)
def get_repayment_history(
    loan_account_id: int,
    db: Session = Depends(get_db)
):
    """Get repayment history for a loan account."""
    from app.domain.models.models import Repayment as RepaymentModel, LoanAccount
    
    # Check if loan account exists
    loan_account = db.query(LoanAccount).filter(LoanAccount.id == loan_account_id).first()
    if not loan_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Loan account with ID {loan_account_id} not found"
        )
    
    # Get repayments
    repayments = db.query(RepaymentModel).filter(
        RepaymentModel.loan_account_id == loan_account_id
    ).order_by(RepaymentModel.repayment_date.desc()).all()
    
    # Convert SQLAlchemy models to Pydantic models
    repayments_out = [Repayment.model_validate(repayment).model_dump() for repayment in repayments]
    return {"status": "success", "data": repayments_out}

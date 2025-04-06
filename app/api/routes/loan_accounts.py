from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List

from app.api.schemas.schemas import (
    LoanAccountCreate, LoanAccount, LoanAccountUpdate, DataResponse, ErrorResponse
)
from app.domain.services.loan_account_service import StandardLoanAccountService
from app.domain.services.security_service import StandardSecurityService
from app.infrastructure.database.base import get_db

router = APIRouter()


@router.post("/loan-accounts/", response_model=DataResponse, status_code=status.HTTP_201_CREATED)
def create_loan_account(
    loan_account_in: LoanAccountCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Create a new loan account."""
    loan_account_service = StandardLoanAccountService(db)
    
    try:
        loan_account = loan_account_service.create_loan_account(
            user_id=loan_account_in.user_id,
            credit_limit=loan_account_in.credit_limit,
            apr=loan_account_in.apr
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # Log security event
    security_service = StandardSecurityService(db)
    security_service.log_security_event(
        user_id=loan_account_in.user_id,
        action="LOAN_ACCOUNT_CREATE",
        entity_type="LoanAccount",
        entity_id=loan_account.id,
        ip_address=request.client.host,
        details=f"Loan account created with credit limit £{loan_account.credit_limit:.2f} and APR {loan_account.apr}%"
    )
    
    # Convert SQLAlchemy model to Pydantic model
    loan_account_out = LoanAccount.model_validate(loan_account)
    return {"status": "success", "data": loan_account_out.model_dump()}


@router.get("/loan-accounts/{loan_account_id}", response_model=DataResponse)
def get_loan_account(
    loan_account_id: int,
    db: Session = Depends(get_db)
):
    """Get loan account details by ID."""
    loan_account_service = StandardLoanAccountService(db)
    
    try:
        loan_account = loan_account_service.get_loan_account(loan_account_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    
    # Convert SQLAlchemy model to Pydantic model
    loan_account_out = LoanAccount.model_validate(loan_account)
    return {"status": "success", "data": loan_account_out.model_dump()}


@router.put("/loan-accounts/{loan_account_id}", response_model=DataResponse)
def update_loan_account(
    loan_account_id: int,
    loan_account_in: LoanAccountUpdate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Update loan account details."""
    loan_account_service = StandardLoanAccountService(db)
    
    # Get current loan account to check user_id for security logging
    try:
        current_loan_account = loan_account_service.get_loan_account(loan_account_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    
    # Update loan account
    update_data = loan_account_in.model_dump(exclude_unset=True)
    
    try:
        updated_loan_account = loan_account_service.update_loan_account(
            loan_account_id=loan_account_id,
            **update_data
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # Log security event
    security_service = StandardSecurityService(db)
    security_service.log_security_event(
        user_id=current_loan_account.user_id,
        action="LOAN_ACCOUNT_UPDATE",
        entity_type="LoanAccount",
        entity_id=loan_account_id,
        ip_address=request.client.host,
        details="Loan account details updated"
    )
    
    # Convert SQLAlchemy model to Pydantic model
    loan_account_out = LoanAccount.model_validate(updated_loan_account)
    return {"status": "success", "data": loan_account_out.model_dump()}


@router.post("/loan-accounts/{loan_account_id}/apply-interest", response_model=DataResponse)
def apply_daily_interest(
    loan_account_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Apply daily interest to a loan account."""
    loan_account_service = StandardLoanAccountService(db)
    
    # Get current loan account to check user_id for security logging
    try:
        current_loan_account = loan_account_service.get_loan_account(loan_account_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    
    # Apply interest
    try:
        interest_result = loan_account_service.apply_daily_interest(loan_account_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # Log security event if interest was applied
    if interest_result["interest_applied"] > 0:
        security_service = StandardSecurityService(db)
        security_service.log_security_event(
            user_id=current_loan_account.user_id,
            action="INTEREST_APPLY",
            entity_type="LoanAccount",
            entity_id=loan_account_id,
            ip_address=request.client.host,
            details=f"Daily interest of £{interest_result['interest_applied']:.2f} applied"
        )
    
    return {"status": "success", "data": interest_result}


@router.post("/loan-accounts/{loan_account_id}/apply-late-fee", response_model=DataResponse)
def apply_late_fee(
    loan_account_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Apply late fee to a loan account if applicable."""
    loan_account_service = StandardLoanAccountService(db)
    
    # Get current loan account to check user_id for security logging
    try:
        current_loan_account = loan_account_service.get_loan_account(loan_account_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    
    # Apply late fee
    try:
        fee_result = loan_account_service.apply_late_fee(loan_account_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # Log security event if fee was applied
    if fee_result.get("fee_applied", 0) > 0:
        security_service = StandardSecurityService(db)
        security_service.log_security_event(
            user_id=current_loan_account.user_id,
            action="LATE_FEE_APPLY",
            entity_type="LoanAccount",
            entity_id=loan_account_id,
            ip_address=request.client.host,
            details=f"Late fee of £{fee_result['fee_applied']:.2f} applied"
        )
    
    return {"status": "success", "data": fee_result}

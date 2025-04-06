from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List

from app.api.schemas.schemas import (
    DataResponse, ErrorResponse, TransactionCreate, Transaction
)
from app.domain.services.security_service import StandardSecurityService
from app.infrastructure.database.base import get_db

router = APIRouter()


@router.post("/", response_model=DataResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(
    transaction_in: TransactionCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Create a new transaction."""
    from app.domain.models.models import Transaction as TransactionModel, LoanAccount, TransactionType
    
    # Check if loan account exists
    loan_account = db.query(LoanAccount).filter(LoanAccount.id == transaction_in.loan_account_id).first()
    if not loan_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Loan account with ID {transaction_in.loan_account_id} not found"
        )
    
    # Create transaction
    db_transaction = TransactionModel(
        loan_account_id=transaction_in.loan_account_id,
        type=transaction_in.type,
        amount=transaction_in.amount,
        description=transaction_in.description,
        is_late_fee=transaction_in.is_late_fee
    )
    
    # Update loan account balance based on transaction type
    if transaction_in.type == TransactionType.PURCHASE:
        loan_account.current_balance += transaction_in.amount
    elif transaction_in.type == TransactionType.REPAYMENT:
        loan_account.current_balance -= transaction_in.amount
    elif transaction_in.type == TransactionType.FEE or transaction_in.type == TransactionType.INTEREST:
        loan_account.current_balance += transaction_in.amount
    
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    
    # Log security event
    security_service = StandardSecurityService(db)
    security_service.log_security_event(
        user_id=loan_account.user_id,
        action="TRANSACTION_CREATE",
        entity_type="Transaction",
        entity_id=db_transaction.id,
        ip_address=request.client.host,
        details=f"{transaction_in.type} transaction of £{transaction_in.amount:.2f} created"
    )
    
    # Convert SQLAlchemy model to Pydantic model
    transaction_out = Transaction.model_validate(db_transaction)
    return {"status": "success", "data": transaction_out.model_dump()}


@router.get("/{transaction_id}", response_model=DataResponse)
def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_db)
):
    """Get transaction details by ID."""
    from app.domain.models.models import Transaction as TransactionModel
    from app.api.schemas.schemas import Transaction
    
    transaction = db.query(TransactionModel).filter(TransactionModel.id == transaction_id).first()
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    # Convert SQLAlchemy model to Pydantic model
    transaction_out = Transaction.model_validate(transaction)
    return {"status": "success", "data": transaction_out.model_dump()}


@router.get("/loan-accounts/{loan_account_id}/transactions", response_model=DataResponse)
def get_loan_account_transactions(
    loan_account_id: int,
    db: Session = Depends(get_db)
):
    """Get all transactions for a loan account."""
    from app.domain.models.models import Transaction as TransactionModel, LoanAccount
    from app.api.schemas.schemas import Transaction
    
    # Check if loan account exists
    loan_account = db.query(LoanAccount).filter(LoanAccount.id == loan_account_id).first()
    if not loan_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Loan account with ID {loan_account_id} not found"
        )
    
    # Get transactions
    transactions = db.query(TransactionModel).filter(
        TransactionModel.loan_account_id == loan_account_id
    ).order_by(TransactionModel.date.desc()).all()
    
    # Convert SQLAlchemy models to Pydantic models
    transactions_out = [Transaction.model_validate(transaction).model_dump() for transaction in transactions]
    return {"status": "success", "data": transactions_out}


@router.get("/loan-accounts/{loan_account_id}/statement", response_model=DataResponse)
def get_loan_account_statement(
    loan_account_id: int,
    db: Session = Depends(get_db)
):
    """Get a statement for a loan account with transactions and interest summary."""
    from app.domain.models.models import Transaction as TransactionModel, LoanAccount, TransactionType
    from app.api.schemas.schemas import Transaction, LoanAccount as LoanAccountSchema
    from sqlalchemy import func
    from datetime import datetime, timedelta
    
    # Check if loan account exists
    loan_account = db.query(LoanAccount).filter(LoanAccount.id == loan_account_id).first()
    if not loan_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Loan account with ID {loan_account_id} not found"
        )
    
    # Get transactions for the last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    transactions = db.query(TransactionModel).filter(
        TransactionModel.loan_account_id == loan_account_id,
        TransactionModel.date >= thirty_days_ago
    ).order_by(TransactionModel.date.desc()).all()
    
    # Calculate summary
    total_purchases = db.query(func.sum(TransactionModel.amount)).filter(
        TransactionModel.loan_account_id == loan_account_id,
        TransactionModel.type == TransactionType.PURCHASE,
        TransactionModel.date >= thirty_days_ago
    ).scalar() or 0.0
    
    total_repayments = db.query(func.sum(TransactionModel.amount)).filter(
        TransactionModel.loan_account_id == loan_account_id,
        TransactionModel.type == TransactionType.REPAYMENT,
        TransactionModel.date >= thirty_days_ago
    ).scalar() or 0.0
    
    total_interest = db.query(func.sum(TransactionModel.amount)).filter(
        TransactionModel.loan_account_id == loan_account_id,
        TransactionModel.type == TransactionType.INTEREST,
        TransactionModel.date >= thirty_days_ago
    ).scalar() or 0.0
    
    total_fees = db.query(func.sum(TransactionModel.amount)).filter(
        TransactionModel.loan_account_id == loan_account_id,
        TransactionModel.type == TransactionType.FEE,
        TransactionModel.date >= thirty_days_ago
    ).scalar() or 0.0
    
    # Get late fees specifically
    total_late_fees = db.query(func.sum(TransactionModel.amount)).filter(
        TransactionModel.loan_account_id == loan_account_id,
        TransactionModel.type == TransactionType.FEE,
        TransactionModel.is_late_fee == True,
        TransactionModel.date >= thirty_days_ago
    ).scalar() or 0.0
    
    # Convert SQLAlchemy models to Pydantic models
    loan_account_out = LoanAccountSchema.model_validate(loan_account)
    transactions_out = [Transaction.model_validate(transaction).model_dump() for transaction in transactions]
    
    statement = {
        "loan_account": loan_account_out.model_dump(),
        "period_start": thirty_days_ago,
        "period_end": datetime.utcnow(),
        "transactions": transactions_out,
        "summary": {
            "total_purchases": total_purchases,
            "total_repayments": total_repayments,
            "total_interest": total_interest,
            "total_fees": total_fees,
            "total_late_fees": total_late_fees,
            "current_balance": loan_account.current_balance,
            "current_apr": loan_account.apr
        }
    }
    
    return {"status": "success", "data": statement}

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List

from app.api.schemas.schemas import (
    CardCreate, Card, CardUpdate, DataResponse, ErrorResponse, CardList
)
from app.domain.services.security_service import StandardSecurityService
from app.infrastructure.database.base import get_db

router = APIRouter()


@router.post("/", response_model=DataResponse, status_code=status.HTTP_201_CREATED)
def create_card(
    card_in: CardCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Create a new card for a user and loan account."""
    from app.domain.models.models import Card as CardModel, User, LoanAccount
    
    # Check if user exists
    user = db.query(User).filter(User.id == card_in.user_id, User.is_deleted == False).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {card_in.user_id} not found"
        )
    
    # Check if loan account exists and belongs to the user
    loan_account = db.query(LoanAccount).filter(
        LoanAccount.id == card_in.loan_account_id,
        LoanAccount.user_id == card_in.user_id
    ).first()
    if not loan_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Loan account with ID {card_in.loan_account_id} not found for this user"
        )
    
    # Create card
    db_card = CardModel(
        user_id=card_in.user_id,
        loan_account_id=card_in.loan_account_id,
        type=card_in.type,
        status=card_in.status
    )
    
    # For demo purposes, create a masked PAN
    if card_in.type == "physical":
        db_card.masked_pan = "XXXX XXXX XXXX 1234"
    else:
        db_card.masked_pan = "XXXX XXXX XXXX 5678"
    
    db.add(db_card)
    db.commit()
    db.refresh(db_card)
    
    # Log security event
    security_service = StandardSecurityService(db)
    security_service.log_security_event(
        user_id=card_in.user_id,
        action="CARD_CREATE",
        entity_type="Card",
        entity_id=db_card.id,
        ip_address=request.client.host,
        details=f"{card_in.type.capitalize()} card created"
    )
    
    # Convert SQLAlchemy model to Pydantic model
    card_out = Card.model_validate(db_card)
    return {"status": "success", "data": card_out.model_dump()}


@router.get("/{card_id}", response_model=DataResponse)
def get_card(
    card_id: int,
    db: Session = Depends(get_db)
):
    """Get card details by ID."""
    from app.domain.models.models import Card as CardModel
    
    card = db.query(CardModel).filter(CardModel.id == card_id).first()
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found"
        )
    
    # Convert SQLAlchemy model to Pydantic model
    card_out = Card.model_validate(card)
    return {"status": "success", "data": card_out.model_dump()}


@router.put("/{card_id}/lock", response_model=DataResponse)
def lock_card(
    card_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Lock a card."""
    security_service = StandardSecurityService(db)
    
    try:
        result = security_service.lock_card(card_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    
    return {"status": "success", "data": result}


@router.put("/{card_id}/unlock", response_model=DataResponse)
def unlock_card(
    card_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Unlock a card."""
    security_service = StandardSecurityService(db)
    
    try:
        result = security_service.unlock_card(card_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    
    return {"status": "success", "data": result}


@router.get("/users/{user_id}", response_model=DataResponse)
def get_user_cards(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get all cards for a user."""
    from app.domain.models.models import Card as CardModel, User
    
    # Check if user exists
    user = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    # Get cards
    cards = db.query(CardModel).filter(CardModel.user_id == user_id).all()
    
    # Convert SQLAlchemy models to Pydantic models
    cards_out = [Card.model_validate(card) for card in cards]
    return {"status": "success", "data": {"cards": cards_out}}

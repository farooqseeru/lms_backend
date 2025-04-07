from fastapi import APIRouter, Depends, HTTPException, status, Request, Security
from sqlalchemy.orm import Session
from typing import List

from app.api.schemas.schemas import (
    CardCreate, Card, CardUpdate, DataResponse, ErrorResponse, CardList
)
from app.domain.services.security_service import StandardSecurityService
from app.infrastructure.database.base import get_db
from app.core.auth.cognito import get_current_user, requires_scope, CognitoToken

router = APIRouter()


@router.post("/", response_model=DataResponse, status_code=status.HTTP_201_CREATED)
async def create_card(
    card_in: CardCreate,
    request: Request,
    current_user: CognitoToken = Security(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new card for a user and loan account."""
    from app.domain.models.models import Card as CardModel, User, LoanAccount
    
    # Check if user exists and matches the authenticated user
    user = db.query(User).filter(User.id == card_in.user_id, User.is_deleted == False).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {card_in.user_id} not found"
        )
    
    # Ensure the authenticated user can only create cards for themselves
    if user.email != current_user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only create cards for your own account"
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
        details=f"Created {card_in.type} card"
    )
    
    # Convert SQLAlchemy model to Pydantic model
    card_out = Card.model_validate(db_card)
    return {"status": "success", "data": card_out.model_dump()}


@router.get("/{card_id}", response_model=DataResponse)
async def get_card(
    card_id: int,
    current_user: CognitoToken = Security(get_current_user),
    db: Session = Depends(get_db)
):
    """Get card details by ID."""
    from app.domain.models.models import Card as CardModel, User
    
    card = db.query(CardModel).filter(CardModel.id == card_id).first()
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found"
        )
    
    # Check if the card belongs to the authenticated user
    user = db.query(User).filter(User.id == card.user_id, User.is_deleted == False).first()
    if not user or user.email != current_user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own cards"
        )
    
    # Convert SQLAlchemy model to Pydantic model
    card_out = Card.model_validate(card)
    return {"status": "success", "data": card_out.model_dump()}


@router.put("/{card_id}/lock", response_model=DataResponse)
async def lock_card(
    card_id: int,
    request: Request,
    current_user: CognitoToken = Security(get_current_user),
    db: Session = Depends(get_db)
):
    """Lock a card."""
    from app.domain.models.models import Card as CardModel, User
    from datetime import datetime
    
    card = db.query(CardModel).filter(CardModel.id == card_id).first()
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found"
        )
    
    # Check if the card belongs to the authenticated user
    user = db.query(User).filter(User.id == card.user_id, User.is_deleted == False).first()
    if not user or user.email != current_user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only lock your own cards"
        )
    
    card.status = "locked"
    card.updated_at = datetime.utcnow()
    db.commit()
    
    # Log security event
    security_service = StandardSecurityService(db)
    security_service.log_security_event(
        user_id=card.user_id,
        action="CARD_LOCK",
        entity_type="Card",
        entity_id=card.id,
        ip_address=request.client.host,
        details="Card locked"
    )
    
    return {
        "status": "success",
        "data": {
            "success": True,
            "card_id": card.id,
            "status": card.status,
            "timestamp": card.updated_at
        }
    }


@router.put("/{card_id}/unlock", response_model=DataResponse)
async def unlock_card(
    card_id: int,
    request: Request,
    current_user: CognitoToken = Security(get_current_user),
    db: Session = Depends(get_db)
):
    """Unlock a card."""
    from app.domain.models.models import Card as CardModel, User
    from datetime import datetime
    
    card = db.query(CardModel).filter(CardModel.id == card_id).first()
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found"
        )
    
    # Check if the card belongs to the authenticated user
    user = db.query(User).filter(User.id == card.user_id, User.is_deleted == False).first()
    if not user or user.email != current_user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only unlock your own cards"
        )
    
    card.status = "active"
    card.updated_at = datetime.utcnow()
    db.commit()
    
    # Log security event
    security_service = StandardSecurityService(db)
    security_service.log_security_event(
        user_id=card.user_id,
        action="CARD_UNLOCK",
        entity_type="Card",
        entity_id=card.id,
        ip_address=request.client.host,
        details="Card unlocked"
    )
    
    return {
        "status": "success",
        "data": {
            "success": True,
            "card_id": card.id,
            "status": card.status,
            "timestamp": card.updated_at
        }
    }


@router.get("/users/{user_id}", response_model=DataResponse)
async def get_user_cards(
    user_id: int,
    current_user: CognitoToken = Security(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all cards for a user."""
    from app.domain.models.models import Card as CardModel, User
    
    # Check if user exists and matches the authenticated user
    user = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    # Ensure the authenticated user can only view their own cards
    if user.email != current_user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own cards"
        )
    
    # Get cards
    cards = db.query(CardModel).filter(CardModel.user_id == user_id).all()
    
    # Convert SQLAlchemy models to Pydantic models
    cards_out = [Card.model_validate(card) for card in cards]
    return {"status": "success", "data": {"cards": cards_out}}

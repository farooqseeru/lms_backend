from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List

from app.api.schemas.schemas import (
    UserCreate, User, UserUpdate, DataResponse, ErrorResponse
)
from app.domain.services.security_service import StandardSecurityService
from app.infrastructure.database.base import get_db

router = APIRouter()


@router.post("/", response_model=DataResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_in: UserCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Create a new user."""
    from app.domain.models.models import User as UserModel
    from app.use_cases.security.auth import get_password_hash
    
    # Check if user with this email already exists
    existing_user = db.query(UserModel).filter(UserModel.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_in.password)
    db_user = UserModel(
        name=user_in.name,
        email=user_in.email,
        phone=user_in.phone,
        kyc_status=user_in.kyc_status,
        account_status=user_in.account_status,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Log security event
    security_service = StandardSecurityService(db)
    security_service.log_security_event(
        user_id=db_user.id,
        action="USER_CREATE",
        entity_type="User",
        entity_id=db_user.id,
        ip_address=request.client.host,
        details="User account created"
    )
    
    # Convert SQLAlchemy model to Pydantic model
    user_out = User.model_validate(db_user)
    return {"status": "success", "data": user_out.model_dump()}


@router.get("/{user_id}", response_model=DataResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get user details by ID."""
    from app.domain.models.models import User as UserModel
    
    user = db.query(UserModel).filter(UserModel.id == user_id, UserModel.is_deleted == False).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Convert SQLAlchemy model to Pydantic model
    user_out = User.model_validate(user)
    return {"status": "success", "data": user_out.model_dump()}


@router.put("/{user_id}", response_model=DataResponse)
def update_user(
    user_id: int,
    user_in: UserUpdate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Update user details."""
    from app.domain.models.models import User as UserModel
    from app.use_cases.security.auth import get_password_hash
    
    user = db.query(UserModel).filter(UserModel.id == user_id, UserModel.is_deleted == False).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update user fields
    update_data = user_in.model_dump(exclude_unset=True)
    
    # Hash password if provided
    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
    
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    
    # Log security event
    security_service = StandardSecurityService(db)
    security_service.log_security_event(
        user_id=user.id,
        action="USER_UPDATE",
        entity_type="User",
        entity_id=user.id,
        ip_address=request.client.host,
        details="User details updated"
    )
    
    # Convert SQLAlchemy model to Pydantic model
    user_out = User.model_validate(user)
    return {"status": "success", "data": user_out.model_dump()}


@router.delete("/{user_id}", response_model=DataResponse)
def delete_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Soft delete a user (GDPR compliant)."""
    from app.domain.models.models import User as UserModel
    
    user = db.query(UserModel).filter(UserModel.id == user_id, UserModel.is_deleted == False).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Soft delete
    user.is_deleted = True
    
    # Anonymize PII for GDPR compliance
    user.name = f"Deleted User {user_id}"
    user.email = f"deleted_{user_id}@example.com"
    user.phone = None
    
    db.commit()
    
    # Log security event
    security_service = StandardSecurityService(db)
    security_service.log_security_event(
        user_id=user.id,
        action="USER_DELETE",
        entity_type="User",
        entity_id=user.id,
        ip_address=request.client.host,
        details="User account deleted (GDPR compliant)"
    )
    
    return {"status": "success", "data": {"message": "User deleted successfully"}}

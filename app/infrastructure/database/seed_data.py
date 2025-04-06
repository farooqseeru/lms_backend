"""Seed database with initial data for development and testing."""

import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.domain.models.models import (
    User, LoanAccount, Card, CardType, CardStatus, 
    UserKYCStatus, UserAccountStatus
)
from app.infrastructure.database.base import SessionLocal
from app.use_cases.security.auth import get_password_hash


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_users(db: Session) -> list[User]:
    """Create sample users."""
    users = [
        User(
            name="John Doe",
            email="john.doe@example.com",
            phone="+44123456789",
            kyc_status=UserKYCStatus.VERIFIED,
            account_status=UserAccountStatus.ACTIVE,
            apr=25.0,
            hashed_password=get_password_hash("password123")
        ),
        User(
            name="Jane Smith",
            email="jane.smith@example.com",
            phone="+44987654321",
            kyc_status=UserKYCStatus.VERIFIED,
            account_status=UserAccountStatus.ACTIVE,
            apr=23.0,  # Already received a reward
            hashed_password=get_password_hash("password123")
        ),
        User(
            name="Alice Johnson",
            email="alice.johnson@example.com",
            phone="+44555666777",
            kyc_status=UserKYCStatus.PENDING,
            account_status=UserAccountStatus.ACTIVE,
            apr=25.0,
            hashed_password=get_password_hash("password123")
        )
    ]
    
    for user in users:
        db.add(user)
    
    db.commit()
    
    for user in users:
        db.refresh(user)
    
    logger.info(f"Created {len(users)} sample users")
    return users


def create_loan_accounts(db: Session, users: list[User]) -> list[LoanAccount]:
    """Create sample loan accounts."""
    loan_accounts = [
        LoanAccount(
            user_id=users[0].id,
            opened_date=datetime.utcnow() - timedelta(days=90),
            current_balance=1500.0,
            credit_limit=5000.0,
            apr=25.0,
            is_active=True
        ),
        LoanAccount(
            user_id=users[1].id,
            opened_date=datetime.utcnow() - timedelta(days=60),
            current_balance=2500.0,
            credit_limit=7500.0,
            apr=23.0,
            is_active=True
        ),
        LoanAccount(
            user_id=users[2].id,
            opened_date=datetime.utcnow() - timedelta(days=30),
            current_balance=0.0,  # New account with no balance
            credit_limit=2000.0,
            apr=25.0,
            is_active=True
        )
    ]
    
    for loan_account in loan_accounts:
        db.add(loan_account)
    
    db.commit()
    
    for loan_account in loan_accounts:
        db.refresh(loan_account)
    
    logger.info(f"Created {len(loan_accounts)} sample loan accounts")
    return loan_accounts


def create_cards(db: Session, loan_accounts: list[LoanAccount]) -> list[Card]:
    """Create sample cards."""
    cards = [
        Card(
            user_id=loan_accounts[0].user_id,
            loan_account_id=loan_accounts[0].id,
            type=CardType.PHYSICAL,
            status=CardStatus.ACTIVE,
            masked_pan="XXXX XXXX XXXX 1234",
            issued_at=datetime.utcnow() - timedelta(days=85),
            expires_at=datetime.utcnow() + timedelta(days=1000)
        ),
        Card(
            user_id=loan_accounts[0].user_id,
            loan_account_id=loan_accounts[0].id,
            type=CardType.VIRTUAL,
            status=CardStatus.ACTIVE,
            masked_pan="XXXX XXXX XXXX 5678",
            issued_at=datetime.utcnow() - timedelta(days=85),
            expires_at=datetime.utcnow() + timedelta(days=1000)
        ),
        Card(
            user_id=loan_accounts[1].user_id,
            loan_account_id=loan_accounts[1].id,
            type=CardType.PHYSICAL,
            status=CardStatus.ACTIVE,
            masked_pan="XXXX XXXX XXXX 9012",
            issued_at=datetime.utcnow() - timedelta(days=55),
            expires_at=datetime.utcnow() + timedelta(days=1000)
        ),
        Card(
            user_id=loan_accounts[2].user_id,
            loan_account_id=loan_accounts[2].id,
            type=CardType.VIRTUAL,
            status=CardStatus.ACTIVE,
            masked_pan="XXXX XXXX XXXX 3456",
            issued_at=datetime.utcnow() - timedelta(days=25),
            expires_at=datetime.utcnow() + timedelta(days=1000)
        )
    ]
    
    for card in cards:
        db.add(card)
    
    db.commit()
    
    for card in cards:
        db.refresh(card)
    
    logger.info(f"Created {len(cards)} sample cards")
    return cards


def seed_db() -> None:
    """Seed the database with initial data."""
    db = SessionLocal()
    try:
        # Check if database is already seeded
        user_count = db.query(User).count()
        if user_count > 0:
            logger.info("Database already contains data, skipping seeding")
            return
        
        # Create sample data
        users = create_users(db)
        loan_accounts = create_loan_accounts(db, users)
        cards = create_cards(db, loan_accounts)
        
        logger.info("Database seeded successfully")
    except Exception as e:
        logger.error(f"Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_db()

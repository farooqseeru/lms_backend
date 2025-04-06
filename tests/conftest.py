import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.infrastructure.database.base import Base
from app.domain.models.models import User, LoanAccount, Card, Repayment, Transaction, RewardAdjustment


@pytest.fixture(scope="function")
def db_session():
    """Create a clean database session for a test."""
    # Create an in-memory SQLite database for testing
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    # Create a new session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    from app.use_cases.security.auth import get_password_hash
    
    user = User(
        name="Test User",
        email="test@example.com",
        phone="+44123456789",
        kyc_status="verified",
        account_status="active",
        apr=25.0,
        hashed_password=get_password_hash("testpassword")
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    return user


@pytest.fixture
def test_loan_account(db_session, test_user):
    """Create a test loan account."""
    loan_account = LoanAccount(
        user_id=test_user.id,
        credit_limit=5000.0,
        apr=25.0,
        current_balance=1000.0,
        is_active=True
    )
    db_session.add(loan_account)
    db_session.commit()
    db_session.refresh(loan_account)
    
    return loan_account


@pytest.fixture
def test_card(db_session, test_user, test_loan_account):
    """Create a test card."""
    card = Card(
        user_id=test_user.id,
        loan_account_id=test_loan_account.id,
        type="virtual",
        status="active",
        masked_pan="XXXX XXXX XXXX 1234"
    )
    db_session.add(card)
    db_session.commit()
    db_session.refresh(card)
    
    return card

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
import enum

from app.infrastructure.database.base import Base


class UserKYCStatus(str, enum.Enum):
    """Enum for user KYC status."""
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class UserAccountStatus(str, enum.Enum):
    """Enum for user account status."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"


class User(Base):
    """User model."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(20), nullable=True)
    kyc_status = Column(String(20), default=UserKYCStatus.PENDING)
    apr = Column(Float, default=25.0)
    account_status = Column(String(20), default=UserAccountStatus.ACTIVE)
    
    # Hashed password for authentication
    hashed_password = Column(String(255), nullable=False)
    
    # GDPR and audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)  # Soft delete flag
    
    # Relationships
    loan_accounts = relationship("LoanAccount", back_populates="user")
    cards = relationship("Card", back_populates="user")
    reward_adjustments = relationship("RewardAdjustment", back_populates="user")


class CardType(str, enum.Enum):
    """Enum for card types."""
    VIRTUAL = "virtual"
    PHYSICAL = "physical"


class CardStatus(str, enum.Enum):
    """Enum for card status."""
    ACTIVE = "active"
    LOCKED = "locked"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class Card(Base):
    """Card model."""
    __tablename__ = "cards"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    loan_account_id = Column(Integer, ForeignKey("loan_accounts.id"), nullable=False)
    type = Column(String(20), nullable=False)
    status = Column(String(20), default=CardStatus.ACTIVE)
    
    # PCI-sensitive data (masked in responses)
    masked_pan = Column(String(19), nullable=True)  # Format: XXXX XXXX XXXX 1234
    
    issued_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="cards")
    loan_account = relationship("LoanAccount", back_populates="cards")


class LoanAccount(Base):
    """Loan Account model."""
    __tablename__ = "loan_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    opened_date = Column(DateTime, default=datetime.utcnow)
    current_balance = Column(Float, default=0.0)
    credit_limit = Column(Float, nullable=False)
    apr = Column(Float, nullable=False)
    
    # Account status
    is_active = Column(Boolean, default=True)
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="loan_accounts")
    repayments = relationship("Repayment", back_populates="loan_account")
    transactions = relationship("Transaction", back_populates="loan_account")
    cards = relationship("Card", back_populates="loan_account")


class RepaymentMethod(str, enum.Enum):
    """Enum for repayment methods."""
    AUTO = "auto"
    MANUAL = "manual"


class Repayment(Base):
    """Repayment model."""
    __tablename__ = "repayments"

    id = Column(Integer, primary_key=True, index=True)
    loan_account_id = Column(Integer, ForeignKey("loan_accounts.id"), nullable=False)
    amount = Column(Float, nullable=False)
    repayment_date = Column(DateTime, default=datetime.utcnow)
    method = Column(String(20), default=RepaymentMethod.MANUAL)
    
    # Additional fields for repayment tracking
    percentage_of_balance = Column(Float, nullable=True)
    interest_saved = Column(Float, nullable=True)
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    loan_account = relationship("LoanAccount", back_populates="repayments")


class TransactionType(str, enum.Enum):
    """Enum for transaction types."""
    PURCHASE = "purchase"
    REPAYMENT = "repayment"
    FEE = "fee"
    INTEREST = "interest"


class Transaction(Base):
    """Transaction model."""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    loan_account_id = Column(Integer, ForeignKey("loan_accounts.id"), nullable=False)
    type = Column(String(20), nullable=False)
    amount = Column(Float, nullable=False)
    date = Column(DateTime, default=datetime.utcnow)
    description = Column(Text, nullable=True)
    
    # For fees and interest
    is_late_fee = Column(Boolean, default=False)
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    loan_account = relationship("LoanAccount", back_populates="transactions")


class RewardAdjustment(Base):
    """Reward Adjustment model for APR changes."""
    __tablename__ = "reward_adjustments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    old_apr = Column(Float, nullable=False)
    new_apr = Column(Float, nullable=False)
    adjusted_on = Column(DateTime, default=datetime.utcnow)
    reason = Column(Text, nullable=True)
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="reward_adjustments")


class AuditLog(Base):
    """Audit Log model for compliance requirements."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(255), nullable=False)
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(Integer, nullable=True)
    ip_address = Column(String(50), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    details = Column(Text, nullable=True)

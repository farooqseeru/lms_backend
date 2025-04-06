from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, validator, constr
from enum import Enum


class UserKYCStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class UserAccountStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"


class CardType(str, Enum):
    VIRTUAL = "virtual"
    PHYSICAL = "physical"


class CardStatus(str, Enum):
    ACTIVE = "active"
    LOCKED = "locked"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class RepaymentMethod(str, Enum):
    AUTO = "auto"
    MANUAL = "manual"


class TransactionType(str, Enum):
    PURCHASE = "purchase"
    REPAYMENT = "repayment"
    FEE = "fee"
    INTEREST = "interest"


# Base schemas
class UserBase(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    kyc_status: UserKYCStatus = UserKYCStatus.PENDING
    account_status: UserAccountStatus = UserAccountStatus.ACTIVE

    class Config:
        from_attributes = True


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    kyc_status: Optional[UserKYCStatus] = None
    account_status: Optional[UserAccountStatus] = None
    password: Optional[str] = Field(None, min_length=8)

    class Config:
        from_attributes = True


class UserInDB(UserBase):
    id: int
    apr: float = 25.0
    created_at: datetime
    updated_at: datetime
    is_deleted: bool = False

    class Config:
        from_attributes = True


class User(UserInDB):
    pass


# Card schemas
class CardBase(BaseModel):
    type: CardType
    status: CardStatus = CardStatus.ACTIVE

    class Config:
        from_attributes = True


class CardCreate(CardBase):
    user_id: int
    loan_account_id: int


class CardUpdate(BaseModel):
    status: Optional[CardStatus] = None

    class Config:
        from_attributes = True


class CardInDB(CardBase):
    id: int
    user_id: int
    loan_account_id: int
    masked_pan: Optional[str] = None
    issued_at: datetime
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Card(CardInDB):
    pass


# Loan Account schemas
class LoanAccountBase(BaseModel):
    credit_limit: float = Field(..., gt=0)
    apr: float = Field(..., gt=0)

    class Config:
        from_attributes = True


class LoanAccountCreate(LoanAccountBase):
    user_id: int


class LoanAccountUpdate(BaseModel):
    credit_limit: Optional[float] = Field(None, gt=0)
    apr: Optional[float] = Field(None, gt=0)
    is_active: Optional[bool] = None

    class Config:
        from_attributes = True


class LoanAccountInDB(LoanAccountBase):
    id: int
    user_id: int
    opened_date: datetime
    current_balance: float = 0.0
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LoanAccount(LoanAccountInDB):
    pass


# Repayment schemas
class RepaymentBase(BaseModel):
    amount: float = Field(..., gt=0)
    method: RepaymentMethod = RepaymentMethod.MANUAL
    percentage_of_balance: Optional[float] = None

    class Config:
        from_attributes = True


class RepaymentCreate(RepaymentBase):
    loan_account_id: int


class RepaymentInDB(RepaymentBase):
    id: int
    loan_account_id: int
    repayment_date: datetime
    interest_saved: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Repayment(RepaymentInDB):
    pass


# Transaction schemas
class TransactionBase(BaseModel):
    type: TransactionType
    amount: float
    description: Optional[str] = None
    is_late_fee: bool = False

    class Config:
        from_attributes = True


class TransactionCreate(TransactionBase):
    loan_account_id: int


class TransactionInDB(TransactionBase):
    id: int
    loan_account_id: int
    date: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Transaction(TransactionInDB):
    pass


# Reward Adjustment schemas
class RewardAdjustmentBase(BaseModel):
    old_apr: float
    new_apr: float
    reason: Optional[str] = None

    class Config:
        from_attributes = True


class RewardAdjustmentCreate(RewardAdjustmentBase):
    user_id: int


class RewardAdjustmentInDB(RewardAdjustmentBase):
    id: int
    user_id: int
    adjusted_on: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RewardAdjustment(RewardAdjustmentInDB):
    pass


# Interest Calculation schemas
class InterestCalculationResult(BaseModel):
    daily_interest_rate: float
    daily_interest_amount: float
    monthly_interest_amount: float
    annual_interest_amount: float


# Repayment Option schemas
class RepaymentOption(BaseModel):
    percentage: float
    amount: float
    interest_to_pay: float
    interest_saved: float


class RepaymentOptions(BaseModel):
    current_balance: float
    current_apr: float
    options: List[RepaymentOption]


# API Response schemas
class ResponseBase(BaseModel):
    status: str = "success"


class DataResponse(ResponseBase):
    data: dict


class ErrorResponse(ResponseBase):
    status: str = "error"
    error: str
    details: Optional[dict] = None

import os
from pydantic_settings import BaseSettings
from pydantic import PostgresDsn


class Settings(BaseSettings):
    """Application settings."""
    
    PROJECT_NAME: str = "Loan Management System"
    API_V1_STR: str = "/api/v1"
    
    # Database settings
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "localhost")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "lms_db")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        """Get the database URI."""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # JWT settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "supersecretkey")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Default APR settings
    DEFAULT_APR: float = 25.0
    
    # Late fee settings
    LATE_FEE_AMOUNT: float = 5.0  # £5 per month
    MAX_LATE_FEE_MONTHS: int = 3  # Maximum 3 months of late fees
    
    # Repayment options
    REPAYMENT_PERCENTAGES: list[float] = [10.0, 25.0, 50.0, 75.0, 100.0]
    
    # APR reduction settings
    APR_REDUCTION_AFTER_REPAYMENTS: int = 3  # Number of good repayments before APR reduction
    APR_REDUCTION_AMOUNT: float = 2.0  # Reduce APR by 2% after good repayments


settings = Settings()

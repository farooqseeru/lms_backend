from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Optional

from app.core.config import settings


class InterestCalculator(ABC):
    """Abstract base class for interest calculation."""
    
    @abstractmethod
    def calculate_daily_interest(self, balance: float, apr: float) -> float:
        """Calculate daily interest amount based on balance and APR."""
        pass
    
    @abstractmethod
    def calculate_interest_for_period(self, balance: float, apr: float, days: int) -> float:
        """Calculate interest amount for a specific period."""
        pass
    
    @abstractmethod
    def calculate_interest_savings(self, balance: float, apr: float, repayment_amount: float) -> float:
        """Calculate interest savings from making a repayment."""
        pass


class StandardInterestCalculator(InterestCalculator):
    """Standard implementation of interest calculator."""
    
    def calculate_daily_interest_rate(self, apr: float) -> float:
        """Calculate daily interest rate from APR."""
        return apr / 100 / 365
    
    def calculate_daily_interest(self, balance: float, apr: float) -> float:
        """Calculate daily interest amount based on balance and APR."""
        daily_rate = self.calculate_daily_interest_rate(apr)
        return balance * daily_rate
    
    def calculate_interest_for_period(self, balance: float, apr: float, days: int) -> float:
        """Calculate interest amount for a specific period."""
        daily_interest = self.calculate_daily_interest(balance, apr)
        return daily_interest * days
    
    def calculate_interest_savings(self, balance: float, apr: float, repayment_amount: float) -> float:
        """Calculate interest savings from making a repayment.
        
        This calculates how much interest would be saved over a month by making
        a repayment now rather than later.
        """
        # Calculate interest on the repayment amount for 30 days
        return self.calculate_interest_for_period(repayment_amount, apr, 30)
    
    def calculate_repayment_options(self, balance: float, apr: float) -> List[dict]:
        """Calculate different repayment options and their impact."""
        options = []
        
        for percentage in settings.REPAYMENT_PERCENTAGES:
            amount = (percentage / 100) * balance
            interest_to_pay = self.calculate_interest_for_period(balance - amount, apr, 30)
            interest_saved = self.calculate_interest_savings(balance, apr, amount)
            
            options.append({
                "percentage": percentage,
                "amount": round(amount, 2),
                "interest_to_pay": round(interest_to_pay, 2),
                "interest_saved": round(interest_saved, 2)
            })
        
        return options

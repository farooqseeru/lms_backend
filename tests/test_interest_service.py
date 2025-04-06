import pytest
from app.domain.services.interest_service import StandardInterestCalculator


class TestInterestCalculator:
    """Test the interest calculator service."""
    
    def test_calculate_daily_interest_rate(self):
        """Test calculating daily interest rate from APR."""
        calculator = StandardInterestCalculator()
        
        # Test with 25% APR
        daily_rate = calculator.calculate_daily_interest_rate(25.0)
        expected_rate = 25.0 / 100 / 365
        assert daily_rate == pytest.approx(expected_rate)
        
        # Test with 0% APR
        daily_rate = calculator.calculate_daily_interest_rate(0.0)
        assert daily_rate == 0.0
    
    def test_calculate_daily_interest(self):
        """Test calculating daily interest amount."""
        calculator = StandardInterestCalculator()
        
        # Test with balance and 25% APR
        daily_interest = calculator.calculate_daily_interest(1000.0, 25.0)
        expected_interest = 1000.0 * (25.0 / 100 / 365)
        assert daily_interest == pytest.approx(expected_interest)
        
        # Test with zero balance
        daily_interest = calculator.calculate_daily_interest(0.0, 25.0)
        assert daily_interest == 0.0
        
        # Test with zero APR
        daily_interest = calculator.calculate_daily_interest(1000.0, 0.0)
        assert daily_interest == 0.0
    
    def test_calculate_interest_for_period(self):
        """Test calculating interest for a specific period."""
        calculator = StandardInterestCalculator()
        
        # Test for 30 days
        interest = calculator.calculate_interest_for_period(1000.0, 25.0, 30)
        expected_interest = 1000.0 * (25.0 / 100 / 365) * 30
        assert interest == pytest.approx(expected_interest)
        
        # Test for 0 days
        interest = calculator.calculate_interest_for_period(1000.0, 25.0, 0)
        assert interest == 0.0
    
    def test_calculate_interest_savings(self):
        """Test calculating interest savings from making a repayment."""
        calculator = StandardInterestCalculator()
        
        # Test with partial repayment
        savings = calculator.calculate_interest_savings(1000.0, 25.0, 500.0)
        expected_savings = 500.0 * (25.0 / 100 / 365) * 30
        assert savings == pytest.approx(expected_savings)
        
        # Test with full repayment
        savings = calculator.calculate_interest_savings(1000.0, 25.0, 1000.0)
        expected_savings = 1000.0 * (25.0 / 100 / 365) * 30
        assert savings == pytest.approx(expected_savings)
    
    def test_calculate_repayment_options(self):
        """Test calculating different repayment options."""
        calculator = StandardInterestCalculator()
        
        # Test with balance of 1000.0 and 25% APR
        options = calculator.calculate_repayment_options(1000.0, 25.0)
        
        # Should have 5 options (10%, 25%, 50%, 75%, 100%)
        assert len(options) == 5
        
        # Check first option (10%)
        assert options[0]["percentage"] == 10.0
        assert options[0]["amount"] == pytest.approx(100.0)
        
        # Check last option (100%)
        assert options[4]["percentage"] == 100.0
        assert options[4]["amount"] == pytest.approx(1000.0)
        
        # Interest to pay should be less for higher repayment amounts
        assert options[0]["interest_to_pay"] > options[1]["interest_to_pay"]
        assert options[1]["interest_to_pay"] > options[2]["interest_to_pay"]
        
        # Interest saved should be more for higher repayment amounts
        assert options[0]["interest_saved"] < options[1]["interest_saved"]
        assert options[1]["interest_saved"] < options[2]["interest_saved"]

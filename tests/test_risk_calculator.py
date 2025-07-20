"""
Unit tests for risk calculator module.
"""
import pytest
from datetime import datetime
from unittest.mock import Mock

from risk.calculator import RiskCalculator, RiskMetrics
from exchanges.base import Position, MarketData

class TestRiskCalculator:
    """Test cases for RiskCalculator class."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.calculator = RiskCalculator()
        
        # Create test position
        self.test_position = Position(
            symbol="BTC",
            size=100.0,
            side="long",
            entry_price=45000.0,
            current_price=46000.0,
            unrealized_pnl=100000.0,
            timestamp=datetime.now(),
            exchange="test"
        )
        
        # Create test market data
        self.test_market_data = MarketData(
            symbol="BTC",
            price=46000.0,
            volume_24h=1000000.0,
            change_24h=0.02,
            timestamp=datetime.now(),
            exchange="test"
        )
    
    def test_calculate_position_greeks_long(self):
        """Test Greeks calculation for long position."""
        metrics = self.calculator.calculate_position_greeks(
            self.test_position, self.test_market_data
        )
        
        assert metrics is not None
        assert metrics.delta == 100.0  # Long position delta
        assert metrics.gamma == 0.0    # Spot position gamma
        assert metrics.theta == 0.0    # Spot position theta
        assert metrics.vega == 0.0     # Spot position vega
        assert metrics.var_95 > 0      # VaR should be positive
        assert metrics.var_99 > metrics.var_95  # 99% VaR > 95% VaR
        assert metrics.correlation == 0.8  # Default correlation
        assert metrics.beta == 1.0     # Default beta
    
    def test_calculate_position_greeks_short(self):
        """Test Greeks calculation for short position."""
        short_position = Position(
            symbol="BTC",
            size=100.0,
            side="short",
            entry_price=45000.0,
            current_price=46000.0,
            unrealized_pnl=-100000.0,
            timestamp=datetime.now(),
            exchange="test"
        )
        
        metrics = self.calculator.calculate_position_greeks(
            short_position, self.test_market_data
        )
        
        assert metrics is not None
        assert metrics.delta == -100.0  # Short position delta
    
    def test_calculate_portfolio_risk(self):
        """Test portfolio risk calculation."""
        positions = [self.test_position]
        market_data_dict = {"BTC": self.test_market_data}
        
        metrics = self.calculator.calculate_portfolio_risk(positions, market_data_dict)
        
        assert metrics is not None
        assert metrics.delta == 100.0  # Portfolio delta
        assert metrics.var_95 > 0      # Portfolio VaR
        assert metrics.var_99 > metrics.var_95  # 99% VaR > 95% VaR
    
    def test_calculate_hedge_ratio(self):
        """Test hedge ratio calculation."""
        hedge_market_data = MarketData(
            symbol="BTC-PERP",
            price=46000.0,
            volume_24h=1000000.0,
            change_24h=0.02,
            timestamp=datetime.now(),
            exchange="test"
        )
        
        ratio = self.calculator.calculate_hedge_ratio(
            self.test_position, "BTC-PERP", self.test_market_data, hedge_market_data
        )
        
        assert ratio == -1.0  # Short hedge for long position
    
    def test_generate_hedge_recommendation_high_risk(self):
        """Test hedge recommendation for high risk."""
        # Create high-risk metrics
        high_risk_metrics = RiskMetrics(
            delta=1000000.0,  # High delta exposure
            gamma=0.0,
            theta=0.0,
            vega=0.0,
            var_95=50000.0,
            var_99=70000.0,
            max_drawdown=100000.0,
            correlation=0.8,
            beta=1.0,
            timestamp=datetime.now()
        )
        
        recommendation = self.calculator.generate_hedge_recommendation(
            self.test_position, high_risk_metrics, self.test_market_data, threshold=0.05
        )
        
        assert recommendation is not None
        assert recommendation.hedge_size > 0
        assert recommendation.urgency in ["medium", "high"]
        assert "Delta exposure" in recommendation.reason
    
    def test_generate_hedge_recommendation_low_risk(self):
        """Test hedge recommendation for low risk."""
        # Create low-risk metrics
        low_risk_metrics = RiskMetrics(
            delta=1000.0,  # Low delta exposure
            gamma=0.0,
            theta=0.0,
            vega=0.0,
            var_95=1000.0,
            var_99=1500.0,
            max_drawdown=2000.0,
            correlation=0.8,
            beta=1.0,
            timestamp=datetime.now()
        )
        
        recommendation = self.calculator.generate_hedge_recommendation(
            self.test_position, low_risk_metrics, self.test_market_data, threshold=0.05
        )
        
        assert recommendation is None  # No recommendation for low risk
    
    def test_calculate_volatility(self):
        """Test volatility calculation."""
        price_history = [100, 101, 99, 102, 98, 103, 97, 104, 96, 105]
        volatility = self.calculator.calculate_volatility(price_history, window=5)
        
        assert volatility > 0
        assert isinstance(volatility, float)
    
    def test_calculate_correlation(self):
        """Test correlation calculation."""
        returns1 = [0.01, -0.02, 0.03, -0.01, 0.02]
        returns2 = [0.02, -0.01, 0.02, -0.02, 0.01]
        
        correlation = self.calculator.calculate_correlation(returns1, returns2)
        
        assert -1 <= correlation <= 1
        assert isinstance(correlation, float)
    
    def test_stress_test(self):
        """Test stress testing."""
        positions = [self.test_position]
        market_data_dict = {"BTC": self.test_market_data}
        scenarios = {
            "Market Crash": -0.20,
            "Moderate Decline": -0.10,
            "Small Rise": 0.05
        }
        
        results = self.calculator.stress_test(positions, market_data_dict, scenarios)
        
        assert len(results) == 3
        assert "Market Crash" in results
        assert "Moderate Decline" in results
        assert "Small Rise" in results
        
        # Market crash should result in negative P&L for long position
        assert results["Market Crash"] < 0
        # Small rise should result in positive P&L for long position
        assert results["Small Rise"] > 0
    
    def test_invalid_inputs(self):
        """Test handling of invalid inputs."""
        # Test with None inputs
        metrics = self.calculator.calculate_position_greeks(None, None)
        assert metrics is None
        
        # Test with empty price history
        volatility = self.calculator.calculate_volatility([], window=10)
        assert volatility == 0.3  # Default volatility
        
        # Test with mismatched returns
        correlation = self.calculator.calculate_correlation([1, 2, 3], [1, 2])
        assert correlation == 0.5  # Default correlation 
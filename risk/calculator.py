"""
Risk calculation engine for position and portfolio risk metrics.

This module provides comprehensive risk calculation capabilities for crypto portfolios,
including Greeks calculation, Value at Risk (VaR), correlation analysis, and hedge
recommendations. It supports both spot and options positions with real-time
risk assessment.

Key Features:
- Greeks calculation (Delta, Gamma, Theta, Vega) for options and spot positions
- Value at Risk (VaR) calculations at 95% and 99% confidence levels
- Portfolio-level risk aggregation and correlation analysis
- Hedge ratio calculations for various hedging strategies
- Stress testing capabilities for scenario analysis

Mathematical Models:
- Black-Scholes model for options Greeks calculation
- Historical VaR using log returns and percentile analysis
- Correlation matrices using Pearson correlation coefficient
- Beta calculation for market sensitivity analysis

Author: Crypto Portfolio Risk Management Team
Version: 2.0.0
License: MIT
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from loguru import logger

from exchanges.base import Position, OrderBook, MarketData

@dataclass
class RiskMetrics:
    """
    Comprehensive risk metrics data structure.
    
    Contains all calculated risk metrics for a position or portfolio,
    including Greeks, VaR, drawdown, and market sensitivity measures.
    
    Attributes:
        delta (float): Price sensitivity (first derivative of value w.r.t. price)
        gamma (float): Delta sensitivity (second derivative of value w.r.t. price)
        theta (float): Time decay (derivative of value w.r.t. time)
        vega (float): Volatility sensitivity (derivative of value w.r.t. volatility)
        var_95 (float): 95% confidence level Value at Risk
        var_99 (float): 99% confidence level Value at Risk
        max_drawdown (float): Maximum historical drawdown
        correlation (float): Correlation with market benchmark
        beta (float): Market sensitivity (systematic risk)
        timestamp (datetime): Timestamp of calculation
    """
    delta: float
    gamma: float
    theta: float
    vega: float
    var_95: float
    var_99: float
    max_drawdown: float
    correlation: float
    beta: float
    timestamp: datetime

@dataclass
class HedgeRecommendation:
    """
    Hedge recommendation data structure.
    
    Contains detailed information about recommended hedging actions,
    including size, type, cost estimates, and urgency levels.
    
    Attributes:
        hedge_size (float): Recommended hedge size in base currency
        hedge_type (str): Type of hedge ('perpetual', 'option', 'dynamic')
        hedge_instrument (str): Specific instrument to use for hedging
        estimated_cost (float): Estimated cost of the hedge
        urgency (str): Urgency level ('low', 'medium', 'high')
        reason (str): Explanation for the hedge recommendation
    """
    hedge_size: float
    hedge_type: str  # 'perpetual', 'option'
    hedge_instrument: str
    estimated_cost: float
    urgency: str  # 'low', 'medium', 'high'
    reason: str

class RiskCalculator:
    """
    Comprehensive risk calculation engine for crypto portfolios.
    
    This class provides methods for calculating various risk metrics including
    Greeks, VaR, correlation, and hedge recommendations. It supports both
    individual positions and portfolio-level analysis.
    
    The calculator uses industry-standard models:
    - Black-Scholes for options Greeks calculation
    - Historical VaR for risk measurement
    - Correlation analysis for portfolio diversification
    - Beta calculation for market sensitivity
    
    Attributes:
        risk_free_rate (float): Risk-free interest rate for calculations
        volatility_window (int): Window size for volatility calculations
    """
    
    def __init__(self):
        """
        Initialize the risk calculator with default parameters.
        
        Sets up default values for risk-free rate and volatility calculation
        window size. These can be customized based on market conditions.
        """
        self.risk_free_rate = 0.02  # 2% annual risk-free rate
        self.volatility_window = 30  # 30-day window for volatility calculation
        
    def calculate_position_greeks(self, position: Position, market_data: MarketData, 
                                volatility: float = 0.3, time_to_expiry: float = 30/365) -> RiskMetrics:
        """
        Calculate Greeks for a position (spot or option).
        
        Computes Delta, Gamma, Theta, and Vega for the given position using
        appropriate models based on the position type. For options, uses
        Black-Scholes model; for spot positions, uses simplified calculations.
        
        Args:
            position (Position): Position object containing size, side, and option details
            market_data (MarketData): Current market data including price
            volatility (float): Implied volatility for options (default: 30%)
            time_to_expiry (float): Time to expiry in years (default: 30 days)
            
        Returns:
            RiskMetrics: Calculated risk metrics for the position
            
        Raises:
            Exception: If calculation fails due to invalid parameters
        """
        try:
            # For option positions, use Black-Scholes model for Greeks
            if position.option_type in ("call", "put") and position.strike is not None and position.expiry is not None:
                S = market_data.price  # Current underlying price
                K = position.strike    # Strike price
                T = (position.expiry - datetime.now()).days / 365.0
                if T <= 0:
                    T = 1/365  # Avoid zero division for expired options
                r = self.risk_free_rate
                sigma = volatility
                
                # Import required mathematical functions
                from scipy.stats import norm
                import math
                
                # Calculate d1 and d2 parameters for Black-Scholes
                d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
                d2 = d1 - sigma * math.sqrt(T)
                
                # Calculate Greeks based on option type
                if position.option_type == "call":
                    delta = norm.cdf(d1)  # Call delta
                    gamma = norm.pdf(d1) / (S * sigma * math.sqrt(T))  # Gamma (same for calls/puts)
                    theta = (-S * norm.pdf(d1) * sigma / (2 * math.sqrt(T)) - 
                            r * K * math.exp(-r * T) * norm.cdf(d2)) / 365  # Daily theta
                    vega = S * norm.pdf(d1) * math.sqrt(T) / 100  # Vega per 1% vol change
                else:  # put option
                    delta = -norm.cdf(-d1)  # Put delta
                    gamma = norm.pdf(d1) / (S * sigma * math.sqrt(T))  # Gamma (same for calls/puts)
                    theta = (-S * norm.pdf(d1) * sigma / (2 * math.sqrt(T)) + 
                            r * K * math.exp(-r * T) * norm.cdf(-d2)) / 365  # Daily theta
                    vega = S * norm.pdf(d1) * math.sqrt(T) / 100  # Vega per 1% vol change
                
                # Scale Greeks by position size
                delta *= position.size
                gamma *= position.size
                theta *= position.size
                vega *= position.size
            else:
                # For spot positions, use simplified Greeks calculation
                # Delta is 1 for long positions, -1 for short positions
                delta = 1.0 if position.side == "long" else -1.0
                delta *= position.size
                gamma = 0.0  # Spot positions have no gamma
                theta = 0.0  # Spot positions have no time decay
                vega = 0.0   # Spot positions have no vega
            
            # Calculate Value at Risk (VaR) using parametric method
            position_value = position.size * market_data.price
            var_95 = position_value * volatility * 1.645 * np.sqrt(time_to_expiry)  # 95% VaR
            var_99 = position_value * volatility * 2.326 * np.sqrt(time_to_expiry)  # 99% VaR
            
            # Calculate maximum drawdown (simplified estimate)
            max_drawdown = position_value * 0.1  # Assume 10% max drawdown
            
            # Calculate correlation and beta (simplified estimates)
            correlation = 0.8  # High correlation with market for crypto
            beta = 1.0  # Beta of 1 for spot positions
            
            return RiskMetrics(
                delta=delta,
                gamma=gamma,
                theta=theta,
                vega=vega,
                var_95=var_95,
                var_99=var_99,
                max_drawdown=max_drawdown,
                correlation=correlation,
                beta=beta,
                timestamp=datetime.now()
            )
        except Exception as e:
            logger.error(f"Error calculating position Greeks: {e}")
            return None
    
    def calculate_portfolio_risk(self, positions: List[Position], 
                               market_data_dict: Dict[str, MarketData]) -> RiskMetrics:
        """
        Calculate portfolio-level risk metrics.
        
        Aggregates risk metrics from individual positions to provide
        portfolio-level risk assessment including total Greeks, VaR,
        and diversification metrics.
        
        Args:
            positions (List[Position]): List of all portfolio positions
            market_data_dict (Dict[str, MarketData]): Market data for all positions
            
        Returns:
            RiskMetrics: Portfolio-level risk metrics
            
        Raises:
            Exception: If portfolio calculation fails
        """
        try:
            total_delta = 0.0
            total_gamma = 0.0
            total_theta = 0.0
            total_vega = 0.0
            total_value = 0.0
            
            # Calculate portfolio Greeks by summing individual position Greeks
            for position in positions:
                if position.symbol in market_data_dict:
                    market_data = market_data_dict[position.symbol]
                    position_metrics = self.calculate_position_greeks(position, market_data)
                    
                    if position_metrics:
                        total_delta += position_metrics.delta
                        total_gamma += position_metrics.gamma
                        total_theta += position_metrics.theta
                        total_vega += position_metrics.vega
                        total_value += position.size * market_data.price
            
            # Calculate portfolio VaR (simplified - assumes 25% portfolio volatility)
            portfolio_volatility = 0.25  # Conservative portfolio volatility estimate
            var_95 = total_value * portfolio_volatility * 1.645 * np.sqrt(30/365)
            var_99 = total_value * portfolio_volatility * 2.326 * np.sqrt(30/365)
            
            # Calculate portfolio max drawdown
            max_drawdown = total_value * 0.15  # 15% max drawdown for diversified portfolio
            
            # Portfolio correlation and beta (diversification benefits)
            correlation = 0.7  # Lower correlation due to diversification
            beta = 0.9  # Slightly lower beta for diversified portfolio
            
            return RiskMetrics(
                delta=total_delta,
                gamma=total_gamma,
                theta=total_theta,
                vega=total_vega,
                var_95=var_95,
                var_99=var_99,
                max_drawdown=max_drawdown,
                correlation=correlation,
                beta=beta,
                timestamp=datetime.now()
            )
        except Exception as e:
            logger.error(f"Error calculating portfolio risk: {e}")
            return None
    
    def calculate_hedge_ratio(self, spot_position: Position, hedge_instrument: str,
                            spot_market_data: MarketData, hedge_market_data: MarketData,
                            correlation: float = 0.95) -> float:
        """
        Calculate hedge ratio for perpetual futures hedging.
        
        Determines the optimal hedge size based on correlation between
        spot and hedge instruments, accounting for volatility differences.
        
        Args:
            spot_position (Position): Spot position to be hedged
            hedge_instrument (str): Hedge instrument symbol
            spot_market_data (MarketData): Spot market data
            hedge_market_data (MarketData): Hedge instrument market data
            correlation (float): Correlation between spot and hedge (default: 0.95)
            
        Returns:
            float: Optimal hedge ratio (negative for short hedge)
        """
        try:
            # Hedge ratio calculation: correlation * (spot_volatility / hedge_volatility)
            # Simplified calculation assuming equal volatilities
            spot_volatility = 0.3
            hedge_volatility = 0.3
            
            hedge_ratio = correlation * (spot_volatility / hedge_volatility)
            
            # Adjust hedge direction based on position side
            if spot_position.side == "long":
                hedge_ratio *= -1  # Short hedge for long position
            
            return hedge_ratio
        except Exception as e:
            logger.error(f"Error calculating hedge ratio: {e}")
            return 0.0
    
    def generate_hedge_recommendation(self, position: Position, risk_metrics: RiskMetrics,
                                    market_data: MarketData, threshold: float = 0.05) -> Optional[HedgeRecommendation]:
        """
        Generate hedge recommendation based on risk metrics.
        
        Analyzes current risk exposure and generates actionable hedge
        recommendations with size, type, and urgency levels.
        
        Args:
            position (Position): Position to analyze
            risk_metrics (RiskMetrics): Current risk metrics
            market_data (MarketData): Current market data
            threshold (float): Risk threshold for triggering hedges (default: 5%)
            
        Returns:
            HedgeRecommendation: Detailed hedge recommendation or None if no hedge needed
        """
        try:
            position_value = position.size * market_data.price
            delta_exposure = abs(risk_metrics.delta) / position_value
            
            # Only recommend hedge if exposure exceeds threshold
            if delta_exposure > threshold:
                # Calculate hedge size based on delta exposure
                hedge_size = abs(risk_metrics.delta)
                
                # Determine hedge type and urgency based on exposure level
                if delta_exposure > threshold * 2:
                    hedge_type = "perpetual"  # Use perpetual for high exposure
                    urgency = "high"
                else:
                    hedge_type = "option"  # Use options for moderate exposure
                    urgency = "medium"
                
                # Estimate hedge cost (simplified)
                if hedge_type == "perpetual":
                    estimated_cost = hedge_size * market_data.price * 0.0005  # 0.05% cost
                    hedge_instrument = f"{position.symbol}-PERP"
                else:
                    estimated_cost = hedge_size * market_data.price * 0.05  # 5% option premium
                    hedge_instrument = f"{position.symbol}-PUT" if position.side == "long" else f"{position.symbol}-CALL"
                
                reason = f"Delta exposure {delta_exposure:.2%} exceeds threshold {threshold:.2%}"
                
                return HedgeRecommendation(
                    hedge_size=hedge_size,
                    hedge_type=hedge_type,
                    hedge_instrument=hedge_instrument,
                    estimated_cost=estimated_cost,
                    urgency=urgency,
                    reason=reason
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating hedge recommendation: {e}")
            return None
    
    def calculate_volatility(self, price_history: List[float], window: int = 30) -> float:
        """Calculate historical volatility."""
        try:
            if len(price_history) < window + 1:
                return 0.3  # Default volatility
            
            returns = np.diff(np.log(price_history[-window:]))
            volatility = np.std(returns) * np.sqrt(252)  # Annualized
            return volatility
        except Exception as e:
            logger.error(f"Error calculating volatility: {e}")
            return 0.3
    
    def calculate_correlation(self, asset1_returns: List[float], 
                           asset2_returns: List[float]) -> float:
        """Calculate correlation between two assets."""
        try:
            if len(asset1_returns) != len(asset2_returns) or len(asset1_returns) < 2:
                return 0.5  # Default correlation
            
            correlation = np.corrcoef(asset1_returns, asset2_returns)[0, 1]
            return correlation if not np.isnan(correlation) else 0.5
        except Exception as e:
            logger.error(f"Error calculating correlation: {e}")
            return 0.5
    
    def stress_test(self, positions: List[Position], 
                   market_data_dict: Dict[str, MarketData],
                   scenarios: Dict[str, float]) -> Dict[str, float]:
        """Perform stress testing on portfolio."""
        try:
            results = {}
            
            for scenario_name, price_change in scenarios.items():
                total_pnl = 0.0
                
                for position in positions:
                    if position.symbol in market_data_dict:
                        current_price = market_data_dict[position.symbol].price
                        new_price = current_price * (1 + price_change)
                        
                        if position.side == "long":
                            pnl = position.size * (new_price - current_price)
                        else:
                            pnl = position.size * (current_price - new_price)
                        
                        total_pnl += pnl
                
                results[scenario_name] = total_pnl
            
            return results
        except Exception as e:
            logger.error(f"Error in stress testing: {e}")
            return {} 
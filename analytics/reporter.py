"""
Analytics reporter for generating comprehensive risk reports and visualizations.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io
import base64
from loguru import logger

from exchanges.base import Position, MarketData
from risk.calculator import RiskMetrics

@dataclass
class PortfolioSnapshot:
    """Portfolio snapshot data structure."""
    timestamp: datetime
    total_value: float
    total_delta: float
    total_gamma: float
    total_theta: float
    total_vega: float
    var_95: float
    var_99: float
    max_drawdown: float
    positions: List[Position]

@dataclass
class PerformanceMetrics:
    """Performance metrics data structure."""
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    volatility: float
    beta: float
    alpha: float
    information_ratio: float

class AnalyticsReporter:
    """Analytics reporter for portfolio analysis."""
    
    def __init__(self):
        self.snapshots: List[PortfolioSnapshot] = []
        self.performance_history: List[Dict[str, float]] = []
    
    def add_snapshot(self, snapshot: PortfolioSnapshot):
        """Add a portfolio snapshot."""
        self.snapshots.append(snapshot)
        
        # Keep only last 1000 snapshots
        if len(self.snapshots) > 1000:
            self.snapshots = self.snapshots[-1000:]
    
    def generate_portfolio_report(self, positions: List[Position], 
                                market_data_dict: Dict[str, MarketData],
                                risk_metrics: RiskMetrics) -> Dict[str, Any]:
        """Generate comprehensive portfolio report."""
        try:
            report = {
                "timestamp": datetime.now(),
                "summary": self._generate_summary(positions, market_data_dict, risk_metrics),
                "risk_metrics": self._format_risk_metrics(risk_metrics),
                "position_breakdown": self._generate_position_breakdown(positions, market_data_dict),
                "correlation_matrix": self._calculate_correlation_matrix(positions),
                "stress_test_results": self._run_stress_tests(positions, market_data_dict),
                "performance_metrics": self._calculate_performance_metrics(),
                "recommendations": self._generate_recommendations(risk_metrics)
            }
            
            return report
        except Exception as e:
            logger.error(f"Error generating portfolio report: {e}")
            return {}
    
    def _generate_summary(self, positions: List[Position], 
                         market_data_dict: Dict[str, MarketData],
                         risk_metrics: RiskMetrics) -> Dict[str, Any]:
        """Generate portfolio summary."""
        try:
            total_value = 0.0
            total_pnl = 0.0
            position_count = len(positions)
            
            for position in positions:
                if position.symbol in market_data_dict:
                    market_data = market_data_dict[position.symbol]
                    position_value = position.size * market_data.price
                    total_value += position_value
                    total_pnl += position.unrealized_pnl
            
            return {
                "total_value": total_value,
                "total_pnl": total_pnl,
                "position_count": position_count,
                "return_pct": (total_pnl / total_value * 100) if total_value > 0 else 0,
                "risk_level": self._determine_risk_level(risk_metrics)
            }
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return {}
    
    def _format_risk_metrics(self, risk_metrics: RiskMetrics) -> Dict[str, Any]:
        """Format risk metrics for reporting."""
        return {
            "delta": risk_metrics.delta,
            "gamma": risk_metrics.gamma,
            "theta": risk_metrics.theta,
            "vega": risk_metrics.vega,
            "var_95": risk_metrics.var_95,
            "var_99": risk_metrics.var_99,
            "max_drawdown": risk_metrics.max_drawdown,
            "correlation": risk_metrics.correlation,
            "beta": risk_metrics.beta
        }
    
    def _generate_position_breakdown(self, positions: List[Position],
                                   market_data_dict: Dict[str, MarketData]) -> List[Dict[str, Any]]:
        """Generate position breakdown."""
        breakdown = []
        
        for position in positions:
            if position.symbol in market_data_dict:
                market_data = market_data_dict[position.symbol]
                position_value = position.size * market_data.price
                
                breakdown.append({
                    "symbol": position.symbol,
                    "side": position.side,
                    "size": position.size,
                    "current_price": market_data.price,
                    "position_value": position_value,
                    "unrealized_pnl": position.unrealized_pnl,
                    "return_pct": (position.unrealized_pnl / position_value * 100) if position_value > 0 else 0
                })
        
        return breakdown
    
    def _calculate_correlation_matrix(self, positions: List[Position], price_history_dict: Dict[str, List[float]] = None) -> Dict[str, Dict[str, float]]:
        """Calculate correlation matrix between positions using real price history if available."""
        try:
            symbols = [pos.symbol for pos in positions]
            correlation_matrix = {}
            for i, symbol1 in enumerate(symbols):
                correlation_matrix[symbol1] = {}
                for j, symbol2 in enumerate(symbols):
                    if i == j:
                        correlation_matrix[symbol1][symbol2] = 1.0
                    else:
                        if price_history_dict and symbol1 in price_history_dict and symbol2 in price_history_dict:
                            ph1 = price_history_dict[symbol1]
                            ph2 = price_history_dict[symbol2]
                            if len(ph1) == len(ph2) and len(ph1) > 2:
                                returns1 = np.diff(np.log(ph1))
                                returns2 = np.diff(np.log(ph2))
                                corr = np.corrcoef(returns1, returns2)[0, 1]
                                correlation_matrix[symbol1][symbol2] = float(corr) if not np.isnan(corr) else 0.0
                            else:
                                correlation_matrix[symbol1][symbol2] = 0.7
                        else:
                            correlation_matrix[symbol1][symbol2] = 0.7  # Default correlation
            return correlation_matrix
        except Exception as e:
            logger.error(f"Error calculating correlation matrix: {e}")
            return {}
    
    def _run_stress_tests(self, positions: List[Position],
                         market_data_dict: Dict[str, MarketData]) -> Dict[str, float]:
        """Run stress tests on portfolio."""
        try:
            scenarios = {
                "Market Crash (-20%)": -0.20,
                "Moderate Decline (-10%)": -0.10,
                "Small Decline (-5%)": -0.05,
                "Small Rise (+5%)": 0.05,
                "Moderate Rise (+10%)": 0.10,
                "Bull Market (+20%)": 0.20
            }
            
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
            logger.error(f"Error running stress tests: {e}")
            return {}
    
    def _calculate_performance_metrics(self) -> PerformanceMetrics:
        """Calculate performance metrics."""
        try:
            if len(self.snapshots) < 2:
                return PerformanceMetrics(
                    total_return=0.0,
                    sharpe_ratio=0.0,
                    max_drawdown=0.0,
                    volatility=0.0,
                    beta=1.0,
                    alpha=0.0,
                    information_ratio=0.0
                )
            
            # Calculate returns
            values = [snapshot.total_value for snapshot in self.snapshots]
            returns = np.diff(values) / values[:-1]
            
            # Calculate metrics
            total_return = (values[-1] - values[0]) / values[0] if values[0] > 0 else 0
            volatility = np.std(returns) * np.sqrt(252) if len(returns) > 0 else 0
            sharpe_ratio = (np.mean(returns) * 252) / volatility if volatility > 0 else 0
            
            # Calculate max drawdown
            peak = values[0]
            max_drawdown = 0.0
            for value in values:
                if value > peak:
                    peak = value
                drawdown = (peak - value) / peak
                max_drawdown = max(max_drawdown, drawdown)
            
            return PerformanceMetrics(
                total_return=total_return,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                volatility=volatility,
                beta=1.0,  # Simplified
                alpha=0.0,  # Simplified
                information_ratio=0.0  # Simplified
            )
        except Exception as e:
            logger.error(f"Error calculating performance metrics: {e}")
            return PerformanceMetrics(0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    
    def _generate_recommendations(self, risk_metrics: RiskMetrics) -> List[str]:
        """Generate recommendations based on risk metrics."""
        recommendations = []
        
        # Delta recommendations
        if abs(risk_metrics.delta) > 100000:  # $100k threshold
            recommendations.append("Consider reducing delta exposure through hedging")
        
        # VaR recommendations
        if risk_metrics.var_95 > 50000:  # $50k threshold
            recommendations.append("VaR exceeds comfortable levels - review position sizing")
        
        # Correlation recommendations
        if risk_metrics.correlation > 0.8:
            recommendations.append("High correlation detected - consider diversification")
        
        # Beta recommendations
        if risk_metrics.beta > 1.2:
            recommendations.append("High beta portfolio - consider defensive positioning")
        
        if not recommendations:
            recommendations.append("Portfolio risk levels are within acceptable ranges")
        
        return recommendations
    
    def _determine_risk_level(self, risk_metrics: RiskMetrics) -> str:
        """Determine overall risk level."""
        risk_score = 0
        
        # Score based on various metrics
        if abs(risk_metrics.delta) > 100000:
            risk_score += 2
        elif abs(risk_metrics.delta) > 50000:
            risk_score += 1
        
        if risk_metrics.var_95 > 50000:
            risk_score += 2
        elif risk_metrics.var_95 > 25000:
            risk_score += 1
        
        if risk_metrics.correlation > 0.8:
            risk_score += 1
        
        if risk_metrics.beta > 1.2:
            risk_score += 1
        
        if risk_score >= 4:
            return "HIGH"
        elif risk_score >= 2:
            return "MEDIUM"
        else:
            return "LOW"
    
    def create_portfolio_chart(self, positions: List[Position],
                             market_data_dict: Dict[str, MarketData]) -> str:
        """Create portfolio allocation chart."""
        try:
            # Prepare data
            labels = []
            sizes = []
            
            for position in positions:
                if position.symbol in market_data_dict:
                    market_data = market_data_dict[position.symbol]
                    position_value = position.size * market_data.price
                    labels.append(f"{position.symbol} ({position.side})")
                    sizes.append(position_value)
            
            if not sizes:
                return ""
            
            # Create pie chart
            fig, ax = plt.subplots(figsize=(10, 8))
            wedges, texts, autotexts = ax.pie(sizes, labels=labels, autopct='%1.1f%%')
            
            # Style the chart
            ax.set_title('Portfolio Allocation', fontsize=16, fontweight='bold')
            plt.setp(autotexts, size=10, weight="bold")
            plt.setp(texts, size=12)
            
            # Save to base64 string
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', bbox_inches='tight', dpi=300)
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            plt.close()
            
            return image_base64
            
        except Exception as e:
            logger.error(f"Error creating portfolio chart: {e}")
            return ""
    
    def create_risk_metrics_chart(self, risk_metrics: RiskMetrics) -> str:
        """Create risk metrics visualization."""
        try:
            # Create subplots
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=('Greeks Exposure', 'VaR Analysis', 'Risk Metrics', 'Correlation & Beta'),
                specs=[[{"type": "bar"}, {"type": "bar"}],
                       [{"type": "indicator"}, {"type": "scatter"}]]
            )
            
            # Greeks bar chart
            greeks = ['Delta', 'Gamma', 'Theta', 'Vega']
            values = [risk_metrics.delta, risk_metrics.gamma, risk_metrics.theta, risk_metrics.vega]
            
            fig.add_trace(
                go.Bar(x=greeks, y=values, name="Greeks", marker_color='lightblue'),
                row=1, col=1
            )
            
            # VaR bar chart
            var_labels = ['VaR 95%', 'VaR 99%']
            var_values = [risk_metrics.var_95, risk_metrics.var_99]
            
            fig.add_trace(
                go.Bar(x=var_labels, y=var_values, name="VaR", marker_color='lightcoral'),
                row=1, col=2
            )
            
            # Risk level gauge
            fig.add_trace(
                go.Indicator(
                    mode="gauge+number",
                    value=risk_metrics.correlation * 100,
                    title={'text': "Correlation %"},
                    gauge={'axis': {'range': [0, 100]},
                           'bar': {'color': "darkblue"},
                           'steps': [{'range': [0, 50], 'color': "lightgray"},
                                    {'range': [50, 80], 'color': "yellow"},
                                    {'range': [80, 100], 'color': "red"}]},
                ),
                row=2, col=1
            )
            
            # Beta scatter
            fig.add_trace(
                go.Scatter(
                    x=[risk_metrics.correlation],
                    y=[risk_metrics.beta],
                    mode='markers',
                    name='Portfolio',
                    marker=dict(size=20, color='red')
                ),
                row=2, col=2
            )
            
            # Update layout
            fig.update_layout(
                title_text="Portfolio Risk Metrics Dashboard",
                showlegend=False,
                height=800
            )
            
            # Convert to base64
            buffer = io.BytesIO()
            fig.write_image(buffer, format='png')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            return image_base64
            
        except Exception as e:
            logger.error(f"Error creating risk metrics chart: {e}")
            return ""
    
    def generate_telegram_report(self, report: Dict[str, Any]) -> str:
        """Generate formatted report for Telegram."""
        try:
            summary = report.get("summary", {})
            risk_metrics = report.get("risk_metrics", {})
            recommendations = report.get("recommendations", [])
            
            report_text = f"""
📊 *Portfolio Risk Report*
*Generated:* {report['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}

💰 *Portfolio Summary*
• Total Value: ${summary.get('total_value', 0):,.2f}
• Total P&L: ${summary.get('total_pnl', 0):,.2f}
• Return: {summary.get('return_pct', 0):.2f}%
• Risk Level: {summary.get('risk_level', 'UNKNOWN')}
• Positions: {summary.get('position_count', 0)}

📈 *Risk Metrics*
• Delta: ${risk_metrics.get('delta', 0):,.2f}
• Gamma: ${risk_metrics.get('gamma', 0):,.2f}
• VaR (95%): ${risk_metrics.get('var_95', 0):,.2f}
• VaR (99%): ${risk_metrics.get('var_99', 0):,.2f}
• Max Drawdown: ${risk_metrics.get('max_drawdown', 0):,.2f}
• Beta: {risk_metrics.get('beta', 0):.2f}

💡 *Recommendations*
"""
            
            for rec in recommendations:
                report_text += f"• {rec}\n"
            
            return report_text
            
        except Exception as e:
            logger.error(f"Error generating Telegram report: {e}")
            return "❌ Error generating report"
    
    def calculate_pnl_attribution(self, positions: List[Position],
                                market_data_dict: Dict[str, MarketData],
                                previous_positions: List[Position] = None) -> Dict[str, Any]:
        """Calculate P&L attribution by factor."""
        try:
            attribution = {
                "total_pnl": 0.0,
                "delta_pnl": 0.0,
                "gamma_pnl": 0.0,
                "theta_pnl": 0.0,
                "vega_pnl": 0.0,
                "position_breakdown": {}
            }
            
            for position in positions:
                if position.symbol not in market_data_dict:
                    continue
                
                market_data = market_data_dict[position.symbol]
                position_pnl = position.unrealized_pnl
                attribution["total_pnl"] += position_pnl
                
                # Calculate factor contributions (simplified)
                # In a real implementation, you'd need historical data for accurate attribution
                position_value = position.size * market_data.price
                
                # Delta contribution (price movement)
                delta_contribution = position_pnl * 0.7  # Assume 70% from delta
                attribution["delta_pnl"] += delta_contribution
                
                # Gamma contribution (convexity)
                gamma_contribution = position_pnl * 0.1  # Assume 10% from gamma
                attribution["gamma_pnl"] += gamma_contribution
                
                # Theta contribution (time decay)
                theta_contribution = position_pnl * 0.1  # Assume 10% from theta
                attribution["theta_pnl"] += theta_contribution
                
                # Vega contribution (volatility)
                vega_contribution = position_pnl * 0.1  # Assume 10% from vega
                attribution["vega_pnl"] += vega_contribution
                
                # Position breakdown
                attribution["position_breakdown"][position.symbol] = {
                    "total_pnl": position_pnl,
                    "delta_contribution": delta_contribution,
                    "gamma_contribution": gamma_contribution,
                    "theta_contribution": theta_contribution,
                    "vega_contribution": vega_contribution,
                    "position_value": position_value
                }
            
            return attribution
            
        except Exception as e:
            logger.error(f"Error calculating P&L attribution: {e}")
            return {"total_pnl": 0.0, "delta_pnl": 0.0, "gamma_pnl": 0.0, "theta_pnl": 0.0, "vega_pnl": 0.0, "position_breakdown": {}} 
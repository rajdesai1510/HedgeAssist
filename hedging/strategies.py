"""
Hedging strategy implementations.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from loguru import logger

from exchanges.base import Position, OrderBook, MarketData
from risk.calculator import RiskMetrics, HedgeRecommendation

@dataclass
class HedgeOrder:
    """Hedge order data structure."""
    symbol: str
    side: str  # 'buy' or 'sell'
    size: float
    order_type: str  # 'market' or 'limit'
    price: Optional[float] = None
    exchange: str = ""
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

@dataclass
class HedgeResult:
    """Hedge execution result."""
    success: bool
    orders: List[HedgeOrder]
    total_cost: float
    execution_time: float
    message: str
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class BaseHedgingStrategy(ABC):
    """Base class for all hedging strategies."""
    
    def __init__(self, name: str):
        self.name = name
        self.is_active = False
    
    @abstractmethod
    async def calculate_hedge(self, position: Position, risk_metrics: RiskMetrics,
                            market_data: MarketData, orderbook: OrderBook) -> Optional[HedgeOrder]:
        """Calculate hedge order for a position."""
        pass
    
    @abstractmethod
    async def execute_hedge(self, hedge_order: HedgeOrder, exchange, position: Position = None) -> HedgeResult:
        """Execute hedge order."""
        pass
    
    def validate_hedge(self, hedge_order: HedgeOrder, position: Position) -> bool:
        """Validate hedge order."""
        try:
            # Basic validation
            if hedge_order is None:
                logger.warning("Hedge order is None")
                return False
                
            if hedge_order.size <= 0:
                logger.warning("Hedge size must be positive")
                return False
            
            if hedge_order.side not in ['buy', 'sell']:
                logger.warning("Invalid hedge side")
                return False
            
            # Check if hedge direction is correct (only if position is provided)
            if position is not None and hasattr(position, 'side'):
                if position.side == "long" and hedge_order.side == "buy":
                    logger.warning("Long position should be hedged with sell order")
                    return False
                
                if position.side == "short" and hedge_order.side == "sell":
                    logger.warning("Short position should be hedged with buy order")
                    return False
            
            return True
        except Exception as e:
            logger.error(f"Error validating hedge: {e}")
            return False

class DeltaNeutralStrategy(BaseHedgingStrategy):
    """Delta-neutral hedging strategy using perpetual futures."""
    
    def __init__(self):
        super().__init__("Delta Neutral")
        self.hedge_ratio_threshold = 0.1  # 10% threshold for rebalancing
    
    async def calculate_hedge(self, position: Position, risk_metrics: RiskMetrics,
                            market_data: MarketData, orderbook: OrderBook) -> Optional[HedgeOrder]:
        """Calculate delta-neutral hedge."""
        try:
            # Calculate required hedge size
            required_hedge_size = abs(risk_metrics.delta)
            
            # Determine hedge side
            if position.side == "long":
                hedge_side = "sell"  # Short hedge for long position
            else:
                hedge_side = "buy"   # Long hedge for short position
            
            # Calculate hedge price (mid price from orderbook)
            if orderbook:
                best_bid = orderbook.bids[0]['price'] if orderbook.bids else market_data.price
                best_ask = orderbook.asks[0]['price'] if orderbook.asks else market_data.price
                hedge_price = (best_bid + best_ask) / 2
            else:
                hedge_price = market_data.price
            
            # Create hedge order
            hedge_order = HedgeOrder(
                symbol=f"{position.symbol}-PERP",
                side=hedge_side,
                size=required_hedge_size,
                order_type="market",
                price=hedge_price,
                exchange=market_data.exchange
            )
            
            logger.info(f"Calculated delta-neutral hedge: {hedge_side} {required_hedge_size} {hedge_order.symbol}")
            return hedge_order
            
        except Exception as e:
            logger.error(f"Error calculating delta-neutral hedge: {e}")
            return None
    
    async def execute_hedge(self, hedge_order: HedgeOrder, exchange, position: Position = None) -> HedgeResult:
        """Execute delta-neutral hedge."""
        try:
            start_time = datetime.now()
            
            # Validate hedge order
            if not self.validate_hedge(hedge_order, position):
                return HedgeResult(
                    success=False,
                    orders=[],
                    total_cost=0.0,
                    execution_time=0.0,
                    message="Invalid hedge order"
                )
            
            # Execute order (simulated for demo)
            logger.info(f"Executing delta-neutral hedge: {hedge_order.side} {hedge_order.size} {hedge_order.symbol}")
            
            # Calculate execution cost
            execution_cost = hedge_order.size * hedge_order.price * 0.0005  # 0.05% cost
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return HedgeResult(
                success=True,
                orders=[hedge_order],
                total_cost=execution_cost,
                execution_time=execution_time,
                message="Delta-neutral hedge executed successfully"
            )
            
        except Exception as e:
            logger.error(f"Error executing delta-neutral hedge: {e}")
            return HedgeResult(
                success=False,
                orders=[],
                total_cost=0.0,
                execution_time=0.0,
                message=f"Error: {str(e)}"
            )

class OptionsHedgingStrategy(BaseHedgingStrategy):
    """Options-based hedging strategy."""
    
    def __init__(self):
        super().__init__("Options Hedging")
        self.option_types = ["protective_put", "covered_call", "collar"]
    
    async def calculate_hedge(self, position: Position, risk_metrics: RiskMetrics,
                            market_data: MarketData, orderbook: OrderBook) -> Optional[HedgeOrder]:
        """Calculate options hedge."""
        try:
            # Determine option type based on position and risk
            if position.side == "long":
                option_type = "protective_put"
                hedge_side = "buy"
            else:
                option_type = "covered_call"
                hedge_side = "sell"
            
            # Calculate option size (simplified)
            option_size = abs(risk_metrics.delta)
            
            # Calculate option price (simplified)
            option_price = market_data.price * 0.05  # 5% of underlying price
            
            # Create hedge order
            hedge_order = HedgeOrder(
                symbol=f"{position.symbol}-{option_type.upper()}",
                side=hedge_side,
                size=option_size,
                order_type="market",
                price=option_price,
                exchange=market_data.exchange
            )
            
            logger.info(f"Calculated options hedge: {hedge_side} {option_size} {hedge_order.symbol}")
            return hedge_order
            
        except Exception as e:
            logger.error(f"Error calculating options hedge: {e}")
            return None
    
    async def execute_hedge(self, hedge_order: HedgeOrder, exchange, position: Position = None) -> HedgeResult:
        """Execute options hedge."""
        try:
            start_time = datetime.now()
            
            # Validate hedge order
            if not self.validate_hedge(hedge_order, position):
                return HedgeResult(
                    success=False,
                    orders=[],
                    total_cost=0.0,
                    execution_time=0.0,
                    message="Invalid hedge order"
                )
            
            # Execute order (simulated for demo)
            logger.info(f"Executing options hedge: {hedge_order.side} {hedge_order.size} {hedge_order.symbol}")
            
            # Calculate execution cost
            execution_cost = hedge_order.size * hedge_order.price * 0.02  # 2% cost for options
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return HedgeResult(
                success=True,
                orders=[hedge_order],
                total_cost=execution_cost,
                execution_time=execution_time,
                message="Options hedge executed successfully"
            )
            
        except Exception as e:
            logger.error(f"Error executing options hedge: {e}")
            return HedgeResult(
                success=False,
                orders=[],
                total_cost=0.0,
                execution_time=0.0,
                message=f"Error: {str(e)}"
            )

class DynamicHedgingStrategy(BaseHedgingStrategy):
    """Dynamic hedging strategy with rebalancing."""
    
    def __init__(self):
        super().__init__("Dynamic Hedging")
        self.rebalance_threshold = 0.05  # 5% threshold for rebalancing
        self.max_hedge_size = 1000000  # Maximum hedge size in USD
    
    async def calculate_hedge(self, position: Position, risk_metrics: RiskMetrics,
                            market_data: MarketData, orderbook: OrderBook) -> Optional[HedgeOrder]:
        """Calculate dynamic hedge."""
        try:
            # Calculate current hedge ratio
            position_value = position.size * market_data.price
            current_hedge_ratio = abs(risk_metrics.delta) / position_value
            
            # Check if rebalancing is needed
            if current_hedge_ratio < self.rebalance_threshold:
                logger.info("Hedge ratio below threshold, no rebalancing needed")
                return None
            
            # Calculate required hedge size
            required_hedge_size = min(abs(risk_metrics.delta), self.max_hedge_size)
            
            # Determine hedge side
            if position.side == "long":
                hedge_side = "sell"
            else:
                hedge_side = "buy"
            
            # Calculate hedge price
            if orderbook:
                best_bid = orderbook.bids[0]['price'] if orderbook.bids else market_data.price
                best_ask = orderbook.asks[0]['price'] if orderbook.asks else market_data.price
                hedge_price = (best_bid + best_ask) / 2
            else:
                hedge_price = market_data.price
            
            # Create hedge order
            hedge_order = HedgeOrder(
                symbol=f"{position.symbol}-PERP",
                side=hedge_side,
                size=required_hedge_size,
                order_type="market",
                price=hedge_price,
                exchange=market_data.exchange
            )
            
            logger.info(f"Calculated dynamic hedge: {hedge_side} {required_hedge_size} {hedge_order.symbol}")
            return hedge_order
            
        except Exception as e:
            logger.error(f"Error calculating dynamic hedge: {e}")
            return None
    
    async def execute_hedge(self, hedge_order: HedgeOrder, exchange, position: Position = None) -> HedgeResult:
        """Execute dynamic hedge."""
        try:
            start_time = datetime.now()
            
            # Validate hedge order
            if not self.validate_hedge(hedge_order, position):
                return HedgeResult(
                    success=False,
                    orders=[],
                    total_cost=0.0,
                    execution_time=0.0,
                    message="Invalid hedge order"
                )
            
            # Execute order (simulated for demo)
            logger.info(f"Executing dynamic hedge: {hedge_order.side} {hedge_order.size} {hedge_order.symbol}")
            
            # Calculate execution cost
            execution_cost = hedge_order.size * hedge_order.price * 0.0005  # 0.05% cost
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return HedgeResult(
                success=True,
                orders=[hedge_order],
                total_cost=execution_cost,
                execution_time=execution_time,
                message="Dynamic hedge executed successfully"
            )
            
        except Exception as e:
            logger.error(f"Error executing dynamic hedge: {e}")
            return HedgeResult(
                success=False,
                orders=[],
                total_cost=0.0,
                execution_time=0.0,
                message=f"Error: {str(e)}"
            )

class HedgingManager:
    """Manager for coordinating hedging strategies."""
    
    def __init__(self):
        self.strategies = {
            "delta_neutral": DeltaNeutralStrategy(),
            "options": OptionsHedgingStrategy(),
            "dynamic": DynamicHedgingStrategy()
        }
        self.active_strategy = None
    
    def set_strategy(self, strategy_name: str) -> bool:
        """Set active hedging strategy."""
        if strategy_name in self.strategies:
            self.active_strategy = self.strategies[strategy_name]
            logger.info(f"Set active strategy: {strategy_name}")
            return True
        else:
            logger.error(f"Unknown strategy: {strategy_name}")
            return False
    
    async def execute_hedge(self, position: Position, risk_metrics: RiskMetrics,
                          market_data: MarketData, orderbook: OrderBook, exchange) -> HedgeResult:
        """Execute hedge using active strategy."""
        try:
            if not self.active_strategy:
                return HedgeResult(
                    success=False,
                    orders=[],
                    total_cost=0.0,
                    execution_time=0.0,
                    message="No active strategy set"
                )
            
            # Calculate hedge order
            hedge_order = await self.active_strategy.calculate_hedge(
                position, risk_metrics, market_data, orderbook
            )
            
            if not hedge_order:
                return HedgeResult(
                    success=False,
                    orders=[],
                    total_cost=0.0,
                    execution_time=0.0,
                    message="No hedge order calculated"
                )
            
            # Execute hedge
            result = await self.active_strategy.execute_hedge(hedge_order, exchange, position)
            return result
            
        except Exception as e:
            logger.error(f"Error executing hedge: {e}")
            return HedgeResult(
                success=False,
                orders=[],
                total_cost=0.0,
                execution_time=0.0,
                message=f"Error: {str(e)}"
            )
    
    def get_available_strategies(self) -> List[str]:
        """Get list of available strategies."""
        return list(self.strategies.keys())
    
    def get_strategy_info(self, strategy_name: str) -> Dict[str, Any]:
        """Get information about a strategy."""
        if strategy_name in self.strategies:
            strategy = self.strategies[strategy_name]
            return {
                "name": strategy.name,
                "description": f"{strategy.name} hedging strategy",
                "is_active": strategy == self.active_strategy
            }
        return {} 
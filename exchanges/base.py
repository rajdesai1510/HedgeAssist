"""
Base exchange interface for all exchange implementations.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class OrderBook:
    """Order book data structure."""
    symbol: str
    bids: List[Dict[str, float]]  # [price, size]
    asks: List[Dict[str, float]]  # [price, size]
    timestamp: datetime
    exchange: str

@dataclass
class Position:
    """Position data structure."""
    symbol: str
    size: float
    side: str  # 'long' or 'short'
    entry_price: float
    current_price: float
    unrealized_pnl: float
    timestamp: datetime
    exchange: str
    # Option-specific fields
    option_type: Optional[str] = None  # 'call' or 'put'
    strike: Optional[float] = None
    expiry: Optional[datetime] = None
    underlying: Optional[str] = None

@dataclass
class MarketData:
    """Market data structure."""
    symbol: str
    price: float
    volume_24h: float
    change_24h: float
    timestamp: datetime
    exchange: str
    # Option-specific fields
    option_type: Optional[str] = None  # 'call' or 'put'
    strike: Optional[float] = None
    expiry: Optional[datetime] = None
    underlying: Optional[str] = None

class BaseExchange(ABC):
    """Base class for all exchange implementations."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.is_connected = False
    
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the exchange."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from the exchange."""
        pass
    
    @abstractmethod
    async def get_orderbook(self, symbol: str, depth: int = 20) -> Optional[OrderBook]:
        """Get order book for a symbol."""
        pass
    
    @abstractmethod
    async def get_market_data(self, symbol: str) -> Optional[MarketData]:
        """Get market data for a symbol."""
        pass
    
    @abstractmethod
    async def get_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """Get current positions."""
        pass
    
    @abstractmethod
    async def place_order(self, symbol: str, side: str, size: float, 
                         order_type: str = "market", price: Optional[float] = None) -> Dict[str, Any]:
        """Place an order."""
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an order."""
        pass
    
    @abstractmethod
    async def get_balance(self, currency: str) -> float:
        """Get balance for a currency."""
        pass
    
    def get_best_bid_ask(self, orderbook: OrderBook) -> tuple[float, float]:
        """Get best bid and ask prices from orderbook."""
        if not orderbook.bids or not orderbook.asks:
            return None, None
        
        best_bid = orderbook.bids[0]['price']
        best_ask = orderbook.asks[0]['price']
        return best_bid, best_ask
    
    def calculate_mid_price(self, orderbook: OrderBook) -> float:
        """Calculate mid price from orderbook."""
        best_bid, best_ask = self.get_best_bid_ask(orderbook)
        if best_bid and best_ask:
            return (best_bid + best_ask) / 2
        return None 
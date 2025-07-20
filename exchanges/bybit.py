"""
Bybit exchange integration using public API.
"""
import aiohttp
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from loguru import logger

from exchanges.base import BaseExchange, OrderBook, Position, MarketData

class BybitExchange(BaseExchange):
    """Bybit exchange implementation."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("Bybit", config)
        self.base_url = "https://api.bybit.com"
        self.session = None
    
    async def connect(self) -> bool:
        """Connect to Bybit API."""
        try:
            self.session = aiohttp.ClientSession()
            # Test connection with a simple API call
            async with self.session.get(f"{self.base_url}/v5/market/time") as response:
                if response.status == 200:
                    self.is_connected = True
                    logger.info(f"Connected to {self.name}")
                    return True
                else:
                    logger.error(f"Failed to connect to {self.name}: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"Error connecting to {self.name}: {e}")
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from Bybit API."""
        try:
            if self.session:
                await self.session.close()
            self.is_connected = False
            logger.info(f"Disconnected from {self.name}")
            return True
        except Exception as e:
            logger.error(f"Error disconnecting from {self.name}: {e}")
            return False
    
    async def get_orderbook(self, symbol: str, depth: int = 20) -> Optional[OrderBook]:
        """Get order book for a symbol."""
        if not self.is_connected:
            return None
        
        try:
            url = f"{self.base_url}/v5/market/orderbook"
            params = {
                "category": "spot",
                "symbol": symbol,
                "limit": depth
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("retCode") == 0 and data.get("result"):
                        orderbook_data = data["result"]
                        
                        bids = [
                            {"price": float(bid[0]), "size": float(bid[1])}
                            for bid in orderbook_data.get("b", [])
                        ]
                        asks = [
                            {"price": float(ask[0]), "size": float(ask[1])}
                            for ask in orderbook_data.get("a", [])
                        ]
                        
                        return OrderBook(
                            symbol=symbol,
                            bids=bids,
                            asks=asks,
                            timestamp=datetime.fromtimestamp(int(orderbook_data.get("ts", 0)) / 1000),
                            exchange=self.name
                        )
                else:
                    logger.error(f"Failed to get orderbook for {symbol}: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error getting orderbook for {symbol}: {e}")
            return None
    
    async def get_market_data(self, symbol: str) -> Optional[MarketData]:
        """Get market data for a symbol."""
        if not self.is_connected:
            return None
        
        try:
            url = f"{self.base_url}/v5/market/tickers"
            params = {
                "category": "spot",
                "symbol": symbol
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("retCode") == 0 and data.get("result", {}).get("list"):
                        ticker_data = data["result"]["list"][0]
                        
                        return MarketData(
                            symbol=symbol,
                            price=float(ticker_data.get("lastPrice", 0)),
                            volume_24h=float(ticker_data.get("volume24h", 0)),
                            change_24h=float(ticker_data.get("price24hPcnt", 0)),
                            timestamp=datetime.fromtimestamp(int(ticker_data.get("time", 0)) / 1000),
                            exchange=self.name
                        )
                else:
                    logger.error(f"Failed to get market data for {symbol}: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error getting market data for {symbol}: {e}")
            return None
    
    async def get_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """Get current positions (requires authentication)."""
        # For demo purposes, return empty list since we're using public API
        logger.warning("Position data requires authentication - returning empty list for demo")
        return []
    
    async def place_order(self, symbol: str, side: str, size: float, 
                         order_type: str = "market", price: Optional[float] = None) -> Dict[str, Any]:
        """Place an order (requires authentication)."""
        logger.warning("Order placement requires authentication - not implemented for demo")
        return {"success": False, "message": "Authentication required"}
    
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an order (requires authentication)."""
        logger.warning("Order cancellation requires authentication - not implemented for demo")
        return False
    
    async def get_balance(self, currency: str) -> float:
        """Get balance for a currency (requires authentication)."""
        logger.warning("Balance data requires authentication - returning 0 for demo")
        return 0.0
    
    async def get_perpetual_contracts(self) -> List[str]:
        """Get available perpetual contract symbols."""
        if not self.is_connected:
            return []
        
        try:
            url = f"{self.base_url}/v5/market/instruments-info"
            params = {"category": "linear"}
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("retCode") == 0 and data.get("result", {}).get("list"):
                        return [item["symbol"] for item in data["result"]["list"]]
                return []
        except Exception as e:
            logger.error(f"Error getting perpetual contracts: {e}")
            return [] 
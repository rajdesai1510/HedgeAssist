"""
Deribit exchange integration using public API.
"""
import aiohttp
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from loguru import logger

from exchanges.base import BaseExchange, OrderBook, Position, MarketData

class DeribitExchange(BaseExchange):
    """Deribit exchange implementation."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("Deribit", config)
        self.base_url = "https://www.deribit.com"
        self.session = None
    
    async def connect(self) -> bool:
        """Connect to Deribit API."""
        try:
            self.session = aiohttp.ClientSession()
            # Test connection with a simple API call
            async with self.session.get(f"{self.base_url}/api/v2/public/test") as response:
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
        """Disconnect from Deribit API."""
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
            url = f"{self.base_url}/api/v2/public/get_order_book"
            params = {
                "instrument_name": symbol,
                "depth": depth
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("result"):
                        orderbook_data = data["result"]
                        
                        bids = [
                            {"price": float(bid[0]), "size": float(bid[1])}
                            for bid in orderbook_data.get("bids", [])
                        ]
                        asks = [
                            {"price": float(ask[0]), "size": float(ask[1])}
                            for ask in orderbook_data.get("asks", [])
                        ]
                        
                        return OrderBook(
                            symbol=symbol,
                            bids=bids,
                            asks=asks,
                            timestamp=datetime.fromtimestamp(int(orderbook_data.get("timestamp", 0)) / 1000),
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
            url = f"{self.base_url}/api/v2/public/ticker"
            params = {"instrument_name": symbol}
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("result"):
                        ticker_data = data["result"]
                        
                        return MarketData(
                            symbol=symbol,
                            price=float(ticker_data.get("last_price", 0)),
                            volume_24h=float(ticker_data.get("volume_24h", 0)),
                            change_24h=float(ticker_data.get("price_change_24h", 0)),
                            timestamp=datetime.fromtimestamp(int(ticker_data.get("timestamp", 0)) / 1000),
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
        if not self.config.get("api_key") or not self.config.get("secret"):
            logger.warning("Deribit API credentials not configured - returning empty list")
            return []
        
        try:
            # This would require implementing authenticated API calls
            # For now, return empty list as placeholder
            logger.info("Deribit positions API not fully implemented yet")
            return []
        except Exception as e:
            logger.error(f"Error getting Deribit positions: {e}")
            return []
    
    async def place_order(self, symbol: str, side: str, size: float, 
                         order_type: str = "market", price: Optional[float] = None) -> Dict[str, Any]:
        """Place an order (requires authentication)."""
        if not self.config.get("api_key") or not self.config.get("secret"):
            return {"success": False, "message": "Deribit API credentials not configured"}
        
        try:
            # This would require implementing authenticated API calls
            # For now, return success simulation
            logger.info(f"Simulating Deribit order: {side} {size} {symbol}")
            return {
                "success": True,
                "order_id": f"deribit_{datetime.now().timestamp()}",
                "message": "Order placed successfully (simulated)"
            }
        except Exception as e:
            logger.error(f"Error placing Deribit order: {e}")
            return {"success": False, "message": f"Error: {str(e)}"}
    
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an order (requires authentication)."""
        logger.warning("Order cancellation requires authentication - not implemented for demo")
        return False
    
    async def get_balance(self, currency: str) -> float:
        """Get balance for a currency (requires authentication)."""
        if not self.config.get("api_key") or not self.config.get("secret"):
            logger.warning("Deribit API credentials not configured - returning 0")
            return 0.0
        
        try:
            # This would require implementing authenticated API calls
            # For now, return simulated balance
            logger.info(f"Simulating Deribit balance for {currency}")
            return 10000.0  # Simulated balance
        except Exception as e:
            logger.error(f"Error getting Deribit balance: {e}")
            return 0.0
    
    async def get_instruments(self, currency: str = "BTC") -> List[str]:
        """Get available instruments for a currency."""
        if not self.is_connected:
            return []
        
        try:
            url = f"{self.base_url}/api/v2/public/get_instruments"
            params = {
                "currency": currency,
                "expired": "false"
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("result"):
                        return [item["instrument_name"] for item in data["result"]]
                return []
        except Exception as e:
            logger.error(f"Error getting instruments: {e}")
            if self.session:
                await self.session.close()
            return []
    
    async def get_options_chain(self, underlying: str, expiration_date: str) -> List[str]:
        """Get options chain for a specific underlying and expiration."""
        if not self.is_connected:
            return []
        
        try:
            url = f"{self.base_url}/api/v2/public/get_instruments"
            params = {
                "currency": underlying,
                "expired": "false",
                "kind": "option"
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("result"):
                        # Filter by expiration date
                        options = [
                            item["instrument_name"] 
                            for item in data["result"] 
                            if expiration_date in item["instrument_name"]
                        ]
                        return options
                return []
        except Exception as e:
            logger.error(f"Error getting options chain: {e}")
            if self.session:
                await self.session.close()
            return [] 
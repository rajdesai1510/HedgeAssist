"""
Configuration management for the hedging bot.
"""
import os
from typing import Optional
from dotenv import load_dotenv
from loguru import logger

# Load environment variables
load_dotenv()

class Config:
    """Configuration class for the hedging bot."""
    
    # Telegram Bot Configuration
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    
    # Exchange API Configuration
    EXCHANGES = {
        "okx": {
            "name": "OKX",
            "base_url": "https://www.okx.com",
            "api_key": os.getenv("OKX_API_KEY", ""),
            "secret": os.getenv("OKX_SECRET", ""),
            "passphrase": os.getenv("OKX_PASSPHRASE", ""),
            "enabled": False  # Disabled - no credentials
        },
        "bybit": {
            "name": "Bybit",
            "base_url": "https://api.bybit.com",
            "api_key": os.getenv("BYBIT_API_KEY", ""),
            "secret": os.getenv("BYBIT_SECRET", ""),
            "enabled": False  # Disabled - no credentials
        },
        "deribit": {
            "name": "Deribit",
            "base_url": "https://www.deribit.com",
            "api_key": os.getenv("DERIBIT_API_KEY", ""),
            "secret": os.getenv("DERIBIT_SECRET", ""),
            "enabled": True  # Enabled - credentials available
        }
    }
    
    # Risk Management Configuration
    DEFAULT_RISK_THRESHOLD = 0.05  # 5% default risk threshold
    MAX_POSITION_SIZE = 1000000    # Maximum position size in USD
    HEDGE_RATIO_THRESHOLD = 0.1    # 10% threshold for hedge ratio adjustments
    
    # Monitoring Configuration
    UPDATE_INTERVAL = 30  # seconds between risk calculations
    ALERT_INTERVAL = 300  # seconds between alerts
    
    # Logging Configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = "hedging_bot.log"
    
    @classmethod
    def validate(cls) -> bool:
        """Validate configuration settings."""
        if not cls.TELEGRAM_BOT_TOKEN:
            logger.error("TELEGRAM_BOT_TOKEN is required")
            return False
        
        # Check if at least one exchange is enabled
        enabled_exchanges = [name for name, config in cls.EXCHANGES.items() if config.get("enabled", False)]
        if not enabled_exchanges:
            logger.warning("No exchanges are enabled. Only Deribit is configured for trading.")
        else:
            logger.info(f"Enabled exchanges: {', '.join(enabled_exchanges)}")
        
        logger.info("Configuration validated successfully")
        return True
    
    @classmethod
    def get_exchange_config(cls, exchange_name: str) -> Optional[dict]:
        """Get configuration for a specific exchange."""
        return cls.EXCHANGES.get(exchange_name.lower()) 
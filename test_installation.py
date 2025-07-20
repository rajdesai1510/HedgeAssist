"""
Test script to verify installation and basic functionality.
"""
import sys
import asyncio
from loguru import logger

def test_imports():
    """Test if all required modules can be imported."""
    logger.info("Testing imports...")
    
    try:
        import numpy as np
        logger.info("✅ NumPy imported successfully")
    except ImportError as e:
        logger.error(f"❌ NumPy import failed: {e}")
        return False
    
    try:
        import pandas as pd
        logger.info("✅ Pandas imported successfully")
    except ImportError as e:
        logger.error(f"❌ Pandas import failed: {e}")
        return False
    
    try:
        import aiohttp
        logger.info("✅ aiohttp imported successfully")
    except ImportError as e:
        logger.error(f"❌ aiohttp import failed: {e}")
        return False
    
    try:
        from telegram import Update
        logger.info("✅ python-telegram-bot imported successfully")
    except ImportError as e:
        logger.error(f"❌ python-telegram-bot import failed: {e}")
        return False
    
    try:
        from utils.config import Config
        logger.info("✅ Local modules imported successfully")
    except ImportError as e:
        logger.error(f"❌ Local modules import failed: {e}")
        return False
    
    return True

def test_config():
    """Test configuration loading."""
    logger.info("Testing configuration...")
    
    try:
        from utils.config import Config
        config = Config()
        logger.info("✅ Configuration loaded successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Configuration test failed: {e}")
        return False

async def test_basic_functionality():
    """Test basic functionality."""
    logger.info("Testing basic functionality...")
    
    try:
        from risk.calculator import RiskCalculator
        from exchanges.base import Position, MarketData
        from datetime import datetime
        
        # Create test data
        position = Position(
            symbol="BTC",
            size=100.0,
            side="long",
            entry_price=45000.0,
            current_price=46000.0,
            unrealized_pnl=100000.0,
            timestamp=datetime.now(),
            exchange="test"
        )
        
        market_data = MarketData(
            symbol="BTC",
            price=46000.0,
            volume_24h=1000000.0,
            change_24h=0.02,
            timestamp=datetime.now(),
            exchange="test"
        )
        
        # Test risk calculation
        calculator = RiskCalculator()
        risk_metrics = calculator.calculate_position_greeks(position, market_data)
        
        if risk_metrics:
            logger.info("✅ Risk calculation working")
            logger.info(f"   Delta: {risk_metrics.delta}")
            logger.info(f"   VaR (95%): ${risk_metrics.var_95:,.2f}")
        else:
            logger.error("❌ Risk calculation failed")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Basic functionality test failed: {e}")
        return False

def main():
    """Main test function."""
    logger.info("🧪 Testing Hedging Bot Installation")
    logger.info("=" * 50)
    
    # Test imports
    if not test_imports():
        logger.error("❌ Import tests failed")
        return False
    
    logger.info("-" * 30)
    
    # Test configuration
    if not test_config():
        logger.error("❌ Configuration test failed")
        return False
    
    logger.info("-" * 30)
    
    # Test basic functionality
    try:
        result = asyncio.run(test_basic_functionality())
        if not result:
            logger.error("❌ Basic functionality test failed")
            return False
    except Exception as e:
        logger.error(f"❌ Async test failed: {e}")
        return False
    
    logger.info("-" * 30)
    logger.info("✅ All tests passed! Installation is working correctly.")
    logger.info("=" * 50)
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 
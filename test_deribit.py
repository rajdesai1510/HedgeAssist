"""
Test script specifically for Deribit functionality.
"""
import asyncio
import os
from loguru import logger
from dotenv import load_dotenv

from exchanges.deribit import DeribitExchange
from utils.config import Config

async def test_deribit_connection():
    """Test Deribit connection and basic functionality."""
    logger.info("🔗 Testing Deribit Connection")
    logger.info("=" * 40)
    
    # Load environment variables
    load_dotenv()
    
    # Get Deribit config
    config = Config.get_exchange_config("deribit")
    if not config:
        logger.error("❌ Deribit configuration not found")
        return False
    
    logger.info(f"Exchange: {config['name']}")
    logger.info(f"Base URL: {config['base_url']}")
    logger.info(f"API Key configured: {'Yes' if config.get('api_key') else 'No'}")
    logger.info(f"Secret configured: {'Yes' if config.get('secret') else 'No'}")
    
    # Create Deribit exchange instance
    deribit = DeribitExchange(config)
    
    try:
        # Test connection
        logger.info("\n📡 Testing connection...")
        connected = await deribit.connect()
        
        if not connected:
            logger.error("❌ Failed to connect to Deribit")
            return False
        
        logger.info("✅ Successfully connected to Deribit")
        
        # Test public market data
        logger.info("\n📊 Testing market data...")
        market_data = await deribit.get_market_data("BTC-PERPETUAL")
        
        if market_data:
            logger.info(f"✅ BTC Price: ${market_data.price:,.2f}")
            logger.info(f"   24h Volume: {market_data.volume_24h:,.0f}")
            logger.info(f"   24h Change: {market_data.change_24h:.2%}")
        else:
            logger.warning("⚠️ Could not fetch BTC market data")
        
        # Test orderbook
        logger.info("\n📚 Testing orderbook...")
        orderbook = await deribit.get_orderbook("BTC-PERPETUAL", depth=5)
        
        if orderbook:
            logger.info(f"✅ Orderbook received")
            logger.info(f"   Best Bid: ${orderbook.bids[0]['price']:,.2f}")
            logger.info(f"   Best Ask: ${orderbook.asks[0]['price']:,.2f}")
            logger.info(f"   Spread: ${orderbook.asks[0]['price'] - orderbook.bids[0]['price']:,.2f}")
        else:
            logger.warning("⚠️ Could not fetch orderbook")
        
        # Test instruments
        logger.info("\n🎯 Testing instruments...")
        instruments = await deribit.get_instruments("BTC")
        
        if instruments:
            logger.info(f"✅ Found {len(instruments)} BTC instruments")
            # Show first few instruments
            for i, instrument in enumerate(instruments[:5]):
                logger.info(f"   {i+1}. {instrument}")
            if len(instruments) > 5:
                logger.info(f"   ... and {len(instruments) - 5} more")
        else:
            logger.warning("⚠️ Could not fetch instruments")
        
        # Test options chain
        logger.info("\n📈 Testing options chain...")
        options = await deribit.get_options_chain("BTC", "2024-12-27")
        
        if options:
            logger.info(f"✅ Found {len(options)} options for 2024-12-27")
            # Show first few options
            for i, option in enumerate(options[:3]):
                logger.info(f"   {i+1}. {option}")
        else:
            logger.info("ℹ️ No options found for 2024-12-27 (this is normal)")
        
        # Test authenticated endpoints (if credentials available)
        if config.get("api_key") and config.get("secret"):
            logger.info("\n🔐 Testing authenticated endpoints...")
            
            # Test balance
            balance = await deribit.get_balance("BTC")
            logger.info(f"✅ BTC Balance: {balance:,.8f}")
            
            # Test positions
            positions = await deribit.get_positions()
            if positions:
                logger.info(f"✅ Found {len(positions)} positions")
                for pos in positions:
                    logger.info(f"   {pos.symbol}: {pos.size} ({pos.side})")
            else:
                logger.info("ℹ️ No open positions")
        else:
            logger.info("\n🔐 Skipping authenticated endpoints (no credentials)")
        
        # Disconnect
        await deribit.disconnect()
        logger.info("\n✅ Disconnected from Deribit")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error testing Deribit: {e}")
        return False

async def test_deribit_trading_simulation():
    """Test Deribit trading simulation."""
    logger.info("\n🔄 Testing Deribit Trading Simulation")
    logger.info("=" * 40)
    
    # Load environment variables
    load_dotenv()
    
    # Get Deribit config
    config = Config.get_exchange_config("deribit")
    if not config:
        logger.error("❌ Deribit configuration not found")
        return False
    
    # Create Deribit exchange instance
    deribit = DeribitExchange(config)
    
    try:
        # Connect
        connected = await deribit.connect()
        if not connected:
            logger.error("❌ Failed to connect to Deribit")
            return False
        
        # Test order placement simulation
        logger.info("📝 Testing order placement simulation...")
        
        order_result = await deribit.place_order(
            symbol="BTC-PERPETUAL",
            side="buy",
            size=0.1,
            order_type="market"
        )
        
        if order_result.get("success"):
            logger.info(f"✅ Order simulation successful")
            logger.info(f"   Order ID: {order_result.get('order_id')}")
            logger.info(f"   Message: {order_result.get('message')}")
        else:
            logger.warning(f"⚠️ Order simulation failed: {order_result.get('message')}")
        
        # Disconnect
        await deribit.disconnect()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error in trading simulation: {e}")
        return False

async def main():
    """Main test function."""
    logger.info("🚀 Deribit Integration Test")
    logger.info("=" * 50)
    
    # Test basic connection and data
    success1 = await test_deribit_connection()
    
    # Test trading simulation
    success2 = await test_deribit_trading_simulation()
    
    logger.info("\n" + "=" * 50)
    if success1 and success2:
        logger.info("✅ All Deribit tests passed!")
    else:
        logger.error("❌ Some Deribit tests failed")
    
    return success1 and success2

if __name__ == "__main__":
    asyncio.run(main()) 
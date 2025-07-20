"""
Demo script to test the hedging system components.
"""
import asyncio
from datetime import datetime
from loguru import logger

from utils.config import Config
from exchanges.okx import OKXExchange
from exchanges.bybit import BybitExchange
from exchanges.deribit import DeribitExchange
from risk.calculator import RiskCalculator, RiskMetrics
from hedging.strategies import HedgingManager
from analytics.reporter import AnalyticsReporter
from exchanges.base import Position, MarketData

async def test_exchange_connections():
    """Test exchange connections."""
    logger.info("Testing exchange connections...")
    
    # Test Deribit (primary exchange)
    try:
        deribit = DeribitExchange({})
        connected = await deribit.connect()
        if connected:
            logger.info("✅ Deribit connection successful")
            
            # Test market data
            market_data = await deribit.get_market_data("BTC-PERPETUAL")
            if market_data:
                logger.info(f"✅ Deribit BTC price: ${market_data.price:,.2f}")
            
            # Test options chain
            options = await deribit.get_instruments("BTC")
            if options:
                logger.info(f"✅ Deribit instruments available: {len(options)}")
            
            await deribit.disconnect()
        else:
            logger.error("❌ Deribit connection failed")
    except Exception as e:
        logger.error(f"❌ Deribit error: {e}")
    
    # Test OKX (public data only)
    try:
        okx = OKXExchange({})
        connected = await okx.connect()
        if connected:
            logger.info("✅ OKX connection successful (public data only)")
            
            # Test market data
            market_data = await okx.get_market_data("BTC-USDT")
            if market_data:
                logger.info(f"✅ OKX BTC price: ${market_data.price:,.2f}")
            
            await okx.disconnect()
        else:
            logger.error("❌ OKX connection failed")
    except Exception as e:
        logger.error(f"❌ OKX error: {e}")
    
    # Test Bybit (public data only)
    try:
        bybit = BybitExchange({})
        connected = await bybit.connect()
        if connected:
            logger.info("✅ Bybit connection successful (public data only)")
            
            # Test market data
            market_data = await bybit.get_market_data("BTCUSDT")
            if market_data:
                logger.info(f"✅ Bybit BTC price: ${market_data.price:,.2f}")
            
            await bybit.disconnect()
        else:
            logger.error("❌ Bybit connection failed")
    except Exception as e:
        logger.error(f"❌ Bybit error: {e}")

async def test_risk_calculations():
    """Test risk calculations."""
    logger.info("Testing risk calculations...")
    
    # Create test position
    position = Position(
        symbol="BTC",
        size=100.0,
        side="long",
        entry_price=45000.0,
        current_price=46000.0,
        unrealized_pnl=100000.0,
        timestamp=datetime.now(),
        exchange="demo"
    )
    
    # Create test market data
    market_data = MarketData(
        symbol="BTC",
        price=46000.0,
        volume_24h=1000000.0,
        change_24h=0.02,
        timestamp=datetime.now(),
        exchange="demo"
    )
    
    # Test risk calculator
    calculator = RiskCalculator()
    risk_metrics = calculator.calculate_position_greeks(position, market_data)
    
    if risk_metrics:
        logger.info("✅ Risk calculation successful")
        logger.info(f"   Delta: {risk_metrics.delta:,.2f}")
        logger.info(f"   VaR (95%): ${risk_metrics.var_95:,.2f}")
        logger.info(f"   VaR (99%): ${risk_metrics.var_99:,.2f}")
    else:
        logger.error("❌ Risk calculation failed")
    
    # Test hedge recommendation
    recommendation = calculator.generate_hedge_recommendation(
        position, risk_metrics, market_data, threshold=0.05
    )
    
    if recommendation:
        logger.info("✅ Hedge recommendation generated")
        logger.info(f"   Hedge size: {recommendation.hedge_size:,.2f}")
        logger.info(f"   Hedge type: {recommendation.hedge_type}")
        logger.info(f"   Estimated cost: ${recommendation.estimated_cost:,.2f}")
    else:
        logger.info("ℹ️ No hedge recommendation (risk below threshold)")

async def test_hedging_strategies():
    """Test hedging strategies."""
    logger.info("Testing hedging strategies...")
    
    # Create test data
    position = Position(
        symbol="BTC",
        size=100.0,
        side="long",
        entry_price=45000.0,
        current_price=46000.0,
        unrealized_pnl=100000.0,
        timestamp=datetime.now(),
        exchange="demo"
    )
    
    market_data = MarketData(
        symbol="BTC",
        price=46000.0,
        volume_24h=1000000.0,
        change_24h=0.02,
        timestamp=datetime.now(),
        exchange="demo"
    )
    
    risk_metrics = RiskMetrics(
        delta=1000000.0,
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
    
    # Test hedging manager
    manager = HedgingManager()
    
    # Test delta-neutral strategy
    manager.set_strategy("delta_neutral")
    logger.info(f"✅ Active strategy: {manager.active_strategy.name}")
    
    # Test hedge calculation
    hedge_order = await manager.active_strategy.calculate_hedge(
        position, risk_metrics, market_data, None
    )
    
    if hedge_order:
        logger.info("✅ Hedge order calculated")
        logger.info(f"   Symbol: {hedge_order.symbol}")
        logger.info(f"   Side: {hedge_order.side}")
        logger.info(f"   Size: {hedge_order.size:,.2f}")
    else:
        logger.error("❌ Hedge order calculation failed")

async def test_analytics():
    """Test analytics reporting."""
    logger.info("Testing analytics reporting...")
    
    # Create test data
    position = Position(
        symbol="BTC",
        size=100.0,
        side="long",
        entry_price=45000.0,
        current_price=46000.0,
        unrealized_pnl=100000.0,
        timestamp=datetime.now(),
        exchange="demo"
    )
    
    market_data = MarketData(
        symbol="BTC",
        price=46000.0,
        volume_24h=1000000.0,
        change_24h=0.02,
        timestamp=datetime.now(),
        exchange="demo"
    )
    
    risk_metrics = RiskMetrics(
        delta=1000000.0,
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
    
    # Test analytics reporter
    reporter = AnalyticsReporter()
    report = reporter.generate_portfolio_report(
        [position], {"BTC": market_data}, risk_metrics
    )
    
    if report:
        logger.info("✅ Analytics report generated")
        logger.info(f"   Total value: ${report['summary'].get('total_value', 0):,.2f}")
        logger.info(f"   Risk level: {report['summary'].get('risk_level', 'UNKNOWN')}")
        logger.info(f"   Recommendations: {len(report['recommendations'])}")
    else:
        logger.error("❌ Analytics report generation failed")
    
    # Test Telegram report
    telegram_report = reporter.generate_telegram_report(report)
    if telegram_report:
        logger.info("✅ Telegram report generated")
        logger.info(f"   Report length: {len(telegram_report)} characters")
    else:
        logger.error("❌ Telegram report generation failed")

async def main():
    """Main demo function."""
    logger.info("🚀 Starting Hedging System Demo")
    logger.info("=" * 50)
    
    # Test exchange connections
    await test_exchange_connections()
    logger.info("-" * 30)
    
    # Test risk calculations
    await test_risk_calculations()
    logger.info("-" * 30)
    
    # Test hedging strategies
    await test_hedging_strategies()
    logger.info("-" * 30)
    
    # Test analytics
    await test_analytics()
    logger.info("-" * 30)
    
    logger.info("✅ Demo completed successfully!")
    logger.info("=" * 50)

if __name__ == "__main__":
    asyncio.run(main()) 
# API Documentation

## Overview

This document provides comprehensive API documentation for the Crypto Portfolio Risk Management & Hedging Bot. The bot is built with a modular architecture that separates concerns into distinct components for risk calculation, hedging strategies, analytics, and user interaction.

## Core Modules

### 1. Main Application (`main.py`)

#### `HedgingBotApp`
Main application class that manages the bot lifecycle.

**Methods:**
- `__init__()`: Initialize application with configuration and signal handlers
- `signal_handler(signum, frame)`: Handle shutdown signals gracefully
- `start()`: Start the bot application
- `stop()`: Stop the bot application gracefully
- `run()`: Main application loop

### 2. Telegram Bot (`bot/telegram_bot.py`)

#### `HedgingBot`
Core Telegram bot class with multi-user support.

**Key Attributes:**
- `user_data`: Dictionary mapping chat_id to user state
- `risk_calculator`: Risk calculation engine
- `hedging_manager`: Hedging strategy manager
- `analytics_reporter`: Analytics and reporting engine

**Command Handlers:**
- `/start`: Initialize bot and show welcome message
- `/help`: Display comprehensive help information
- `/monitor_risk <asset> <size> <threshold>`: Start monitoring position
- `/auto_hedge <strategy> <threshold>`: Enable automated hedging
- `/hedge_now <asset> <size>`: Execute manual hedge
- `/risk_analytics`: Generate comprehensive risk dashboard
- `/pnl_attribution`: Show P&L attribution analysis
- `/set_alert <metric> <condition> <value>`: Configure custom alerts
- `/status`: Show system status and health
- `/version`: Display bot version and features

**Background Tasks:**
- `price_polling_loop()`: Continuous price monitoring
- `_periodic_summary_task()`: Scheduled risk summaries
- `_check_custom_alerts()`: Custom alert monitoring

### 3. Risk Calculator (`risk/calculator.py`)

#### `RiskCalculator`
Comprehensive risk calculation engine.

**Methods:**
- `calculate_position_greeks(position, market_data, volatility, time_to_expiry)`: Calculate Greeks for position
- `calculate_portfolio_risk(positions, market_data_dict)`: Calculate portfolio-level risk
- `calculate_hedge_ratio(spot_position, hedge_instrument, spot_market_data, hedge_market_data, correlation)`: Calculate optimal hedge ratio
- `generate_hedge_recommendation(position, risk_metrics, market_data, threshold)`: Generate hedge recommendations
- `calculate_volatility(price_history, window)`: Calculate historical volatility
- `calculate_correlation(asset1_returns, asset2_returns)`: Calculate correlation between assets
- `stress_test(positions, market_data_dict, scenarios)`: Run stress tests

#### `RiskMetrics`
Data structure for risk metrics.

**Attributes:**
- `delta`: Price sensitivity
- `gamma`: Delta sensitivity to price changes
- `theta`: Time decay
- `vega`: Volatility sensitivity
- `var_95`: 95% Value at Risk
- `var_99`: 99% Value at Risk
- `max_drawdown`: Maximum historical drawdown
- `correlation`: Correlation with market
- `beta`: Market sensitivity
- `timestamp`: Calculation timestamp

#### `HedgeRecommendation`
Data structure for hedge recommendations.

**Attributes:**
- `hedge_size`: Recommended hedge size
- `hedge_type`: Type of hedge ('perpetual', 'option')
- `hedge_instrument`: Specific instrument to use
- `estimated_cost`: Estimated hedge cost
- `urgency`: Urgency level ('low', 'medium', 'high')
- `reason`: Explanation for recommendation

### 4. Hedging Strategies (`hedging/strategies.py`)

#### `BaseHedgingStrategy`
Abstract base class for all hedging strategies.

**Methods:**
- `calculate_hedge(position, risk_metrics, market_data, orderbook)`: Calculate hedge order
- `execute_hedge(hedge_order, exchange, position)`: Execute hedge order
- `validate_hedge(hedge_order, position)`: Validate hedge order

#### `DeltaNeutralStrategy`
Delta-neutral hedging using perpetual futures.

**Methods:**
- `calculate_hedge()`: Calculate delta-neutral hedge size and direction
- `execute_hedge()`: Execute delta-neutral hedge

#### `OptionsHedgingStrategy`
Options-based hedging strategy.

**Methods:**
- `calculate_hedge()`: Calculate options hedge (puts/calls)
- `execute_hedge()`: Execute options hedge

#### `DynamicHedgingStrategy`
Dynamic hedging with rebalancing.

**Methods:**
- `calculate_hedge()`: Calculate dynamic hedge with rebalancing
- `execute_hedge()`: Execute dynamic hedge

#### `HedgingManager`
Manages multiple hedging strategies.

**Methods:**
- `set_strategy(strategy_name)`: Set active hedging strategy
- `execute_hedge(position, risk_metrics, market_data, orderbook, exchange)`: Execute hedge using active strategy
- `get_available_strategies()`: Get list of available strategies
- `get_strategy_info(strategy_name)`: Get strategy information

### 5. Analytics Reporter (`analytics/reporter.py`)

#### `AnalyticsReporter`
Comprehensive analytics and reporting engine.

**Methods:**
- `generate_portfolio_report(positions, market_data_dict, risk_metrics)`: Generate comprehensive portfolio report
- `create_portfolio_chart(positions, market_data_dict)`: Create portfolio allocation chart
- `create_risk_metrics_chart(risk_metrics)`: Create risk metrics visualization
- `calculate_pnl_attribution(positions, market_data_dict, previous_positions)`: Calculate P&L attribution
- `generate_telegram_report(report)`: Format report for Telegram

#### `PortfolioSnapshot`
Data structure for portfolio snapshots.

**Attributes:**
- `timestamp`: Snapshot timestamp
- `total_value`: Total portfolio value
- `total_delta`: Total portfolio delta
- `total_gamma`: Total portfolio gamma
- `total_theta`: Total portfolio theta
- `total_vega`: Total portfolio vega
- `var_95`: 95% VaR
- `var_99`: 99% VaR
- `max_drawdown`: Maximum drawdown
- `positions`: List of positions

#### `PerformanceMetrics`
Data structure for performance metrics.

**Attributes:**
- `total_return`: Total portfolio return
- `sharpe_ratio`: Sharpe ratio
- `max_drawdown`: Maximum drawdown
- `volatility`: Portfolio volatility
- `beta`: Portfolio beta
- `alpha`: Portfolio alpha
- `information_ratio`: Information ratio

### 6. Machine Learning Models

#### `VolatilityForecaster` (`ml/volatility_model.py`)
Random Forest model for volatility forecasting.

**Methods:**
- `fit(prices, window)`: Train model on price data
- `predict(prices, window)`: Predict future volatility
- `save()`: Save trained model
- `load()`: Load trained model

#### `HedgeTimingClassifier` (`ml/hedge_timing_model.py`)
Random Forest classifier for optimal hedge timing.

**Methods:**
- `fit(features, labels)`: Train timing model
- `predict(features)`: Predict optimal hedge timing
- `save()`: Save trained model
- `load()`: Load trained model

### 7. Exchange Integration (`exchanges/`)

#### Base Classes
- `Position`: Position data structure
- `MarketData`: Market data structure
- `OrderBook`: Order book data structure

#### Exchange Implementations
- `DeribitExchange`: Deribit API integration
- `BybitExchange`: Bybit API integration
- `OKXExchange`: OKX API integration

### 8. Utilities (`utils/`)

#### `Config` (`utils/config.py`)
Configuration management.

**Methods:**
- `validate()`: Validate configuration
- `get_exchange_config(exchange_name)`: Get exchange configuration

#### `Logger` (`utils/logger.py`)
Logging configuration.

**Functions:**
- `setup_logger()`: Configure logging system

## Data Structures

### Position
```python
@dataclass
class Position:
    symbol: str
    side: str  # 'long' or 'short'
    size: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    option_type: Optional[str] = None  # 'call', 'put', or None
    strike: Optional[float] = None
    expiry: Optional[datetime] = None
```

### MarketData
```python
@dataclass
class MarketData:
    symbol: str
    price: float
    volume: float
    timestamp: datetime
    exchange: str
    bid: Optional[float] = None
    ask: Optional[float] = None
```

### OrderBook
```python
@dataclass
class OrderBook:
    symbol: str
    bids: List[Dict[str, float]]  # [{'price': float, 'size': float}]
    asks: List[Dict[str, float]]  # [{'price': float, 'size': float}]
    timestamp: datetime
```

## Error Handling

All API methods include comprehensive error handling with:
- Try-catch blocks for exception handling
- Detailed error logging using loguru
- Graceful degradation when possible
- User-friendly error messages

## Configuration

The bot uses environment variables for configuration:
- `TELEGRAM_BOT_TOKEN`: Telegram bot token
- `DERIBIT_API_KEY`: Deribit API key
- `DERIBIT_SECRET`: Deribit API secret
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)

## Security Features

- User confirmation for large trades (>$100k)
- Emergency stop functionality
- Comprehensive audit logging
- Input validation and sanitization
- Rate limiting for API calls

## Performance Considerations

- Asynchronous operations for non-blocking execution
- Efficient data structures for real-time processing
- Caching of frequently accessed data
- Background tasks for continuous monitoring
- Memory management for large datasets

## Extensibility

The modular architecture allows for easy extension:
- New hedging strategies can be added by implementing `BaseHedgingStrategy`
- Additional exchanges can be integrated by implementing exchange interfaces
- New risk metrics can be added to `RiskCalculator`
- Custom analytics can be added to `AnalyticsReporter`
- Machine learning models can be extended or replaced 
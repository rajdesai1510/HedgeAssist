# Developer Guide

## Overview

This guide provides comprehensive information for developers who want to extend, modify, or contribute to the Crypto Portfolio Risk Management & Hedging Bot. The bot is built with a modular architecture that makes it easy to add new features, integrate additional exchanges, or implement custom hedging strategies.

## Architecture Overview

### Modular Design

The bot follows a clean, modular architecture with clear separation of concerns:

```
QUANT/
├── main.py                 # Application entry point
├── bot/                    # Telegram bot interface
│   └── telegram_bot.py     # Main bot implementation
├── risk/                   # Risk calculation engine
│   └── calculator.py       # Risk metrics and Greeks
├── hedging/                # Hedging strategies
│   └── strategies.py       # Strategy implementations
├── analytics/              # Analytics and reporting
│   └── reporter.py         # Portfolio analysis
├── ml/                     # Machine learning models
│   ├── volatility_model.py # Volatility forecasting
│   └── hedge_timing_model.py # Hedge timing
├── exchanges/              # Exchange integrations
│   ├── base.py            # Base exchange interface
│   ├── deribit.py         # Deribit implementation
│   ├── bybit.py           # Bybit implementation
│   └── okx.py             # OKX implementation
└── utils/                  # Utilities
    ├── config.py          # Configuration management
    └── logger.py          # Logging setup
```

### Design Patterns

1. **Strategy Pattern**: Used for hedging strategies
2. **Factory Pattern**: Used for exchange creation
3. **Observer Pattern**: Used for price monitoring
4. **Command Pattern**: Used for Telegram commands

## Development Setup

### Prerequisites

1. **Python 3.8+**: The bot requires Python 3.8 or higher
2. **Git**: For version control
3. **Virtual Environment**: Recommended for dependency management

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd QUANT

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp env_template.txt .env
# Edit .env with your API credentials
```

### Development Dependencies

```bash
# Install development dependencies
pip install pytest pytest-asyncio black flake8 mypy
```

## Adding New Features

### 1. Adding a New Hedging Strategy

To add a new hedging strategy, implement the `BaseHedgingStrategy` abstract class:

```python
from hedging.strategies import BaseHedgingStrategy, HedgeOrder, HedgeResult
from risk.calculator import RiskMetrics
from exchanges.base import Position, MarketData, OrderBook

class MyCustomStrategy(BaseHedgingStrategy):
    """Custom hedging strategy implementation."""
    
    def __init__(self):
        super().__init__("My Custom Strategy")
        self.custom_parameter = 0.5
    
    async def calculate_hedge(self, position: Position, risk_metrics: RiskMetrics,
                            market_data: MarketData, orderbook: OrderBook) -> Optional[HedgeOrder]:
        """Calculate hedge order for your custom strategy."""
        try:
            # Your custom hedge calculation logic here
            hedge_size = self._calculate_custom_hedge_size(position, risk_metrics)
            hedge_side = "sell" if position.side == "long" else "buy"
            
            return HedgeOrder(
                symbol=f"{position.symbol}-PERP",
                side=hedge_side,
                size=hedge_size,
                order_type="market",
                price=market_data.price
            )
        except Exception as e:
            logger.error(f"Error calculating custom hedge: {e}")
            return None
    
    async def execute_hedge(self, hedge_order: HedgeOrder, exchange, position: Position = None) -> HedgeResult:
        """Execute your custom hedge."""
        try:
            # Your custom execution logic here
            start_time = datetime.now()
            
            # Validate and execute
            if not self.validate_hedge(hedge_order, position):
                return HedgeResult(success=False, orders=[], total_cost=0.0, 
                                 execution_time=0.0, message="Invalid hedge order")
            
            # Execute the hedge
            execution_cost = hedge_order.size * hedge_order.price * 0.0005
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return HedgeResult(
                success=True,
                orders=[hedge_order],
                total_cost=execution_cost,
                execution_time=execution_time,
                message="Custom hedge executed successfully"
            )
        except Exception as e:
            logger.error(f"Error executing custom hedge: {e}")
            return HedgeResult(success=False, orders=[], total_cost=0.0, 
                             execution_time=0.0, message=f"Error: {str(e)}")
    
    def _calculate_custom_hedge_size(self, position: Position, risk_metrics: RiskMetrics) -> float:
        """Your custom hedge size calculation."""
        # Implement your custom logic here
        return abs(risk_metrics.delta) * self.custom_parameter
```

Then register your strategy in the `HedgingManager`:

```python
# In hedging/strategies.py, add to HedgingManager.__init__
self.strategies["my_custom"] = MyCustomStrategy()
```

### 2. Adding a New Exchange

To add support for a new exchange, implement the base exchange interface:

```python
from exchanges.base import BaseExchange, Position, MarketData, OrderBook
from typing import Dict, List, Optional
import aiohttp
import hmac
import hashlib
import time

class NewExchange(BaseExchange):
    """Implementation for a new exchange."""
    
    def __init__(self, api_key: str, secret: str, testnet: bool = False):
        super().__init__("NewExchange", api_key, secret, testnet)
        self.base_url = "https://api.newexchange.com" if not testnet else "https://testnet-api.newexchange.com"
    
    async def get_market_data(self, symbol: str) -> Optional[MarketData]:
        """Fetch market data from the exchange."""
        try:
            url = f"{self.base_url}/market/ticker/{symbol}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return MarketData(
                            symbol=symbol,
                            price=float(data['price']),
                            volume=float(data['volume']),
                            timestamp=datetime.fromtimestamp(data['timestamp']),
                            exchange=self.name,
                            bid=float(data.get('bid', 0)),
                            ask=float(data.get('ask', 0))
                        )
        except Exception as e:
            logger.error(f"Error fetching market data from {self.name}: {e}")
        return None
    
    async def get_order_book(self, symbol: str) -> Optional[OrderBook]:
        """Fetch order book from the exchange."""
        try:
            url = f"{self.base_url}/market/orderbook/{symbol}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return OrderBook(
                            symbol=symbol,
                            bids=data['bids'],
                            asks=data['asks'],
                            timestamp=datetime.fromtimestamp(data['timestamp'])
                        )
        except Exception as e:
            logger.error(f"Error fetching order book from {self.name}: {e}")
        return None
    
    async def place_order(self, symbol: str, side: str, size: float, 
                         order_type: str = "market", price: Optional[float] = None) -> bool:
        """Place an order on the exchange."""
        try:
            # Implement order placement logic
            # Include authentication, signature generation, etc.
            pass
        except Exception as e:
            logger.error(f"Error placing order on {self.name}: {e}")
            return False
    
    def _generate_signature(self, method: str, path: str, data: str = "") -> str:
        """Generate API signature for authentication."""
        timestamp = str(int(time.time() * 1000))
        message = timestamp + method + path + data
        signature = hmac.new(
            self.secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
```

### 3. Adding New Risk Metrics

To add new risk metrics, extend the `RiskCalculator` class:

```python
class RiskCalculator:
    def calculate_custom_risk_metric(self, position: Position, market_data: MarketData) -> float:
        """Calculate a custom risk metric."""
        try:
            # Your custom risk calculation logic here
            position_value = position.size * market_data.price
            custom_metric = position_value * 0.1  # Example calculation
            return custom_metric
        except Exception as e:
            logger.error(f"Error calculating custom risk metric: {e}")
            return 0.0
    
    def calculate_portfolio_custom_metric(self, positions: List[Position], 
                                        market_data_dict: Dict[str, MarketData]) -> float:
        """Calculate portfolio-level custom metric."""
        try:
            total_metric = 0.0
            for position in positions:
                if position.symbol in market_data_dict:
                    metric = self.calculate_custom_risk_metric(position, market_data_dict[position.symbol])
                    total_metric += metric
            return total_metric
        except Exception as e:
            logger.error(f"Error calculating portfolio custom metric: {e}")
            return 0.0
```

### 4. Adding New Analytics

To add new analytics capabilities, extend the `AnalyticsReporter` class:

```python
class AnalyticsReporter:
    def generate_custom_analysis(self, positions: List[Position], 
                               market_data_dict: Dict[str, MarketData]) -> Dict[str, Any]:
        """Generate custom analytics."""
        try:
            analysis = {
                "custom_metric": self._calculate_custom_metric(positions, market_data_dict),
                "custom_chart": self._create_custom_chart(positions, market_data_dict),
                "custom_recommendations": self._generate_custom_recommendations(positions)
            }
            return analysis
        except Exception as e:
            logger.error(f"Error generating custom analysis: {e}")
            return {}
    
    def _calculate_custom_metric(self, positions: List[Position], 
                               market_data_dict: Dict[str, MarketData]) -> float:
        """Calculate custom metric for analysis."""
        # Your custom calculation logic here
        return 0.0
    
    def _create_custom_chart(self, positions: List[Position], 
                           market_data_dict: Dict[str, MarketData]) -> str:
        """Create custom chart using Plotly."""
        try:
            # Your custom chart creation logic here
            fig = go.Figure()
            # Add traces, layout, etc.
            return fig.to_html()
        except Exception as e:
            logger.error(f"Error creating custom chart: {e}")
            return ""
```

### 5. Adding New Telegram Commands

To add new Telegram commands, extend the `HedgingBot` class:

```python
class HedgingBot:
    def setup_handlers(self):
        """Setup bot command handlers."""
        # Add your new command handler
        self.application.add_handler(CommandHandler("my_command", self.my_command_handler))
        # ... existing handlers ...
    
    async def my_command_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle your custom command."""
        try:
            chat_id = update.effective_chat.id
            user = self._get_user(chat_id)
            
            # Your command logic here
            response = "Your custom command response"
            
            await update.message.reply_text(response, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"Error in custom command: {e}")
            await update.message.reply_text("Error executing command")
```

## Testing

### Unit Testing

Create tests for your new features:

```python
# tests/test_my_feature.py
import pytest
from unittest.mock import Mock, patch
from my_module import MyClass

class TestMyFeature:
    def test_my_method(self):
        """Test my custom method."""
        obj = MyClass()
        result = obj.my_method("test_input")
        assert result == "expected_output"
    
    @pytest.mark.asyncio
    async def test_async_method(self):
        """Test async method."""
        obj = MyClass()
        result = await obj.async_method("test_input")
        assert result == "expected_output"
```

### Integration Testing

Test integration with other components:

```python
# tests/test_integration.py
import pytest
from bot.telegram_bot import HedgingBot
from risk.calculator import RiskCalculator

class TestIntegration:
    @pytest.fixture
    def bot(self):
        """Create bot instance for testing."""
        return HedgingBot()
    
    def test_risk_calculation_integration(self, bot):
        """Test risk calculation integration."""
        # Test that risk calculation works with bot
        pass
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_my_feature.py

# Run with coverage
pytest --cov=.

# Run async tests
pytest --asyncio-mode=auto
```

## Code Quality

### Code Style

The project uses:
- **Black**: Code formatting
- **Flake8**: Linting
- **MyPy**: Type checking

```bash
# Format code
black .

# Check linting
flake8 .

# Check types
mypy .
```

### Documentation

- Use docstrings for all public methods
- Follow Google docstring format
- Include type hints
- Document complex algorithms

```python
def complex_algorithm(param1: str, param2: int) -> Dict[str, Any]:
    """
    Perform complex algorithm calculation.
    
    This function implements a sophisticated algorithm that processes
    input parameters and returns structured results.
    
    Args:
        param1: String parameter for processing
        param2: Integer parameter for calculation
        
    Returns:
        Dictionary containing algorithm results with keys:
        - 'result': The calculated result
        - 'confidence': Confidence score (0-1)
        - 'metadata': Additional processing metadata
        
    Raises:
        ValueError: If parameters are invalid
        RuntimeError: If algorithm fails to converge
        
    Example:
        >>> result = complex_algorithm("test", 42)
        >>> print(result['result'])
        123.45
    """
    # Implementation here
    pass
```

## Performance Optimization

### Profiling

Use profiling to identify bottlenecks:

```python
import cProfile
import pstats

def profile_function():
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Your code here
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)
```

### Memory Management

- Use generators for large datasets
- Implement proper cleanup in destructors
- Monitor memory usage with `memory_profiler`

### Async Optimization

- Use `asyncio.gather()` for concurrent operations
- Implement proper error handling in async functions
- Use connection pooling for HTTP requests

## Deployment

### Docker

Create a Dockerfile for containerized deployment:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

### Environment Configuration

Use environment-specific configuration:

```python
# config.py
import os

class Config:
    def __init__(self):
        self.environment = os.getenv('ENVIRONMENT', 'development')
        self.debug = self.environment == 'development'
        
        if self.environment == 'production':
            # Production settings
            self.log_level = 'INFO'
            self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        else:
            # Development settings
            self.log_level = 'DEBUG'
            self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN_DEV')
```

## Contributing

### Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Implement your changes
4. Add tests for new functionality
5. Update documentation
6. Run all tests and checks
7. Submit a pull request

### Code Review Checklist

- [ ] Code follows project style guidelines
- [ ] All tests pass
- [ ] Documentation is updated
- [ ] No security vulnerabilities introduced
- [ ] Performance impact is considered
- [ ] Error handling is comprehensive

### Release Process

1. Update version numbers
2. Update changelog
3. Create release tag
4. Deploy to production
5. Monitor for issues

## Troubleshooting

### Common Issues

1. **Import Errors**: Check Python path and virtual environment
2. **API Rate Limits**: Implement proper rate limiting
3. **Memory Leaks**: Use memory profiling tools
4. **Async Deadlocks**: Review async/await patterns

### Debugging

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Use the debugger:

```python
import pdb; pdb.set_trace()
```

### Performance Monitoring

Monitor key metrics:
- Response times
- Memory usage
- CPU usage
- API call frequency
- Error rates

## Support

For questions or issues:
1. Check the documentation
2. Search existing issues
3. Create a new issue with detailed information
4. Contact the development team 
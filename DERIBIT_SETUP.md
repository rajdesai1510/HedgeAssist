# Deribit Integration Setup Guide

## Overview

The hedging bot has been configured to use **Deribit as the primary exchange** for trading and options, while OKX and Bybit are used for additional market data only.

## Configuration Changes

### 1. Exchange Priority
- **Deribit**: Primary exchange for trading, options, and hedging
- **OKX & Bybit**: Secondary sources for market data only

### 2. Environment Variables

Create a `.env` file with your Deribit credentials:

```bash
# Required - Telegram Bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Required - Deribit API (Primary Exchange)
DERIBIT_API_KEY=your_deribit_api_key_here
DERIBIT_SECRET=your_deribit_secret_here

# Optional - Additional Market Data
OKX_API_KEY=your_okx_api_key_here
OKX_SECRET=your_okx_secret_here
OKX_PASSPHRASE=your_okx_passphrase_here

BYBIT_API_KEY=your_bybit_api_key_here
BYBIT_SECRET=your_bybit_secret_here

# Logging
LOG_LEVEL=INFO
```

## Getting Deribit API Credentials

### 1. Create Deribit Account
1. Go to [Deribit](https://www.deribit.com)
2. Sign up for an account
3. Complete KYC verification

### 2. Generate API Keys
1. Log into your Deribit account
2. Go to **Account** → **API**
3. Click **Create New Key**
4. Set permissions:
   - ✅ **Read** (required for market data)
   - ✅ **Trade** (required for hedging)
   - ✅ **Transfer** (optional, for withdrawals)
5. Save your **API Key** and **Secret**

### 3. Security Notes
- Never share your API credentials
- Use IP whitelisting if available
- Start with small amounts for testing
- Consider using testnet first

## Testing Deribit Integration

### 1. Test Basic Connection
```bash
python test_deribit.py
```

This will test:
- Connection to Deribit
- Market data retrieval
- Orderbook access
- Instrument listing
- Options chain access
- Balance and position queries (if authenticated)

### 2. Test Full System
```bash
python demo.py
```

This will test the complete system with Deribit as the primary exchange.

## Deribit-Specific Features

### 1. Options Trading
The bot supports Deribit's options for hedging:
- **Protective Puts**: Hedge long positions
- **Covered Calls**: Hedge short positions
- **Options Chains**: Access to various expirations and strikes

### 2. Perpetual Futures
- **BTC-PERPETUAL**: Bitcoin perpetual futures
- **ETH-PERPETUAL**: Ethereum perpetual futures
- **Other assets**: Available on Deribit

### 3. Advanced Features
- **Real-time Greeks**: Delta, Gamma, Theta, Vega
- **Options Analytics**: Implied volatility, skew
- **Portfolio Margining**: Efficient capital usage

## Telegram Bot Commands for Deribit

### Basic Commands
```
/start - Initialize bot
/help - Show all commands
```

### Risk Monitoring
```
/monitor_risk BTC 1.0 0.05 - Monitor 1 BTC with 5% risk threshold
/monitor_risk ETH 10.0 0.03 - Monitor 10 ETH with 3% risk threshold
```

### Hedging Commands
```
/auto_hedge delta_neutral 0.05 - Enable delta-neutral hedging
/auto_hedge options 0.03 - Enable options-based hedging
/hedge_now BTC 0.5 - Manually hedge 0.5 BTC
```

### Status Commands
```
/hedge_status BTC - Check BTC hedging status
/hedge_history BTC 7d - View 7-day hedging history
/risk_analytics - View comprehensive analytics
```

## Trading Strategies Available

### 1. Delta-Neutral Hedging
- Uses perpetual futures to hedge spot positions
- Low cost, high liquidity
- Suitable for large positions

### 2. Options-Based Hedging
- Uses Deribit options for hedging
- Protective puts for long positions
- Covered calls for short positions
- More expensive but better protection

### 3. Dynamic Hedging
- Continuously rebalances hedges
- Responds to market movements
- Optimizes for cost and effectiveness

## Risk Management

### 1. Position Sizing
- Maximum position size: $1,000,000 (configurable)
- Risk threshold: 5% default (configurable)
- Automatic alerts when thresholds exceeded

### 2. Hedging Triggers
- Delta exposure > threshold
- VaR exceeds limits
- Portfolio correlation too high
- Market volatility spikes

### 3. Safety Features
- Order size limits
- Maximum drawdown protection
- Correlation monitoring
- Stress testing

## Troubleshooting

### Common Issues

1. **Connection Failed**
   - Check internet connection
   - Verify Deribit API endpoints
   - Check firewall settings

2. **Authentication Error**
   - Verify API key and secret
   - Check API permissions
   - Ensure account is active

3. **Order Placement Failed**
   - Check account balance
   - Verify symbol format
   - Check position limits

### Support
- Check logs in `hedging_bot.log`
- Run `python test_deribit.py` for diagnostics
- Review Deribit API documentation

## Next Steps

1. **Install dependencies**: `pip install -r requirements.txt`
2. **Set up environment**: Create `.env` file with credentials
3. **Test connection**: `python test_deribit.py`
4. **Start bot**: `python main.py`
5. **Monitor performance**: Use Telegram commands

## Security Reminders

- Keep API credentials secure
- Start with small amounts
- Monitor bot activity regularly
- Have stop-loss mechanisms in place
- Test thoroughly before live trading 
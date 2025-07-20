# User Manual

## Getting Started

### Prerequisites

Before using the Crypto Portfolio Risk Management & Hedging Bot, ensure you have:

1. **Telegram Account**: You need a Telegram account to interact with the bot
2. **Deribit Account**: Set up a Deribit account with API access
3. **API Credentials**: Obtain your Deribit API key and secret
4. **Python Environment**: The bot runs on Python 3.8+

### Initial Setup

1. **Get Bot Token**: Contact the bot administrator to get your Telegram bot token
2. **Configure Environment**: Set up your `.env` file with API credentials
3. **Start the Bot**: Run `python main.py` to start the bot
4. **Start Chat**: Open Telegram and start a chat with your bot

## Basic Commands

### Starting the Bot

```
/start
```
- Initializes the bot for your account
- Shows welcome message and available commands
- Sets up your portfolio for real Deribit integration

### Getting Help

```
/help
```
- Displays comprehensive help information
- Shows all available commands with examples
- Explains risk thresholds and strategies

## Risk Monitoring

### Start Monitoring a Position

```
/monitor_risk <asset> <size> <threshold>
```

**Parameters:**
- `<asset>`: Asset symbol (e.g., BTC, ETH, SOL)
- `<size>`: Position size in base currency
- `<threshold>`: Risk threshold (0.01-0.20)

**Examples:**
```
/monitor_risk BTC 1000 0.05
```
Monitors 1000 BTC with 5% risk threshold

```
/monitor_risk ETH 500 0.03
```
Monitors 500 ETH with 3% risk threshold

### Configure Monitoring

```
/configure_monitor <asset> <delta_threshold> [var_threshold]
```

**Parameters:**
- `<asset>`: Asset to configure
- `<delta_threshold>`: Delta exposure threshold
- `[var_threshold]`: Optional VaR threshold

**Example:**
```
/configure_monitor BTC 0.03 0.02
```
Sets BTC delta threshold to 3% and VaR threshold to 2%

### Stop Monitoring

```
/stop_monitoring <asset>
```

**Example:**
```
/stop_monitoring BTC
```
Stops monitoring BTC position

## Hedging Commands

### Enable Automated Hedging

```
/auto_hedge <strategy> <threshold>
```

**Available Strategies:**
- `delta_neutral`: Delta-neutral hedging with perpetuals
- `options`: Options-based hedging (puts/calls)
- `dynamic`: Dynamic hedging with rebalancing

**Examples:**
```
/auto_hedge delta_neutral 0.05
```
Enables delta-neutral hedging with 5% threshold

```
/auto_hedge options 0.03
```
Enables options-based hedging with 3% threshold

### Manual Hedge Execution

```
/hedge_now <asset> <size>
```

**Example:**
```
/hedge_now BTC 100
```
Manually hedges 100 BTC

### Check Hedging Status

```
/hedge_status <asset>
```

**Example:**
```
/hedge_status BTC
```
Shows current hedging status for BTC

### View Hedging History

```
/hedge_history <asset> [timeframe]
```

**Timeframes:**
- `1d`: Last 24 hours
- `7d`: Last 7 days
- `30d`: Last 30 days
- `all`: All history

**Example:**
```
/hedge_history BTC 7d
```
Shows BTC hedging history for the last 7 days

## Analytics and Reporting

### Portfolio Risk Analytics

```
/risk_analytics
```
- Displays comprehensive risk dashboard
- Shows current risk metrics
- Provides portfolio overview
- Includes interactive charts

### P&L Attribution

```
/pnl_attribution
```
- Shows profit/loss breakdown by factor
- Analyzes Delta, Gamma, Theta, Vega contributions
- Provides factor-based performance analysis

### Risk Report

```
/risk_report
```
- Generates detailed risk report
- Includes stress testing results
- Provides export options (PDF)
- Shows correlation matrices

### Risk Charts

```
/risk_charts
```
- Interactive charts for risk metrics
- VaR, drawdown, Greeks visualizations
- Portfolio allocation charts
- Export capabilities

### Asset-Specific Charts

```
/chart <asset>
```

**Example:**
```
/chart BTC
```
Shows interactive charts for BTC including:
- Price history
- P&L over time
- Risk metrics
- Volume analysis

## Alerts and Notifications

### Set Custom Alerts

```
/set_alert <metric> <condition> <value>
```

**Available Metrics:**
- `delta`: Delta exposure
- `var`: Value at Risk
- `pnl`: Profit/Loss
- `price`: Asset price
- `volume`: Trading volume

**Conditions:**
- `above`: Alert when metric goes above value
- `below`: Alert when metric goes below value

**Examples:**
```
/set_alert delta above 0.05
```
Alert when delta exposure exceeds 5%

```
/set_alert price below 50000
```
Alert when BTC price drops below $50,000

### View Alert Status

```
/alerts_status
```
- Shows all configured alerts
- Displays alert IDs and settings
- Shows alert status (active/inactive)

### Delete Alerts

```
/delete_alert <id>
```

**Example:**
```
/delete_alert 123
```
Deletes alert with ID 123

## Periodic Summaries

### Schedule Risk Summaries

```
/schedule_summary <frequency>
```

**Frequencies:**
- `daily`: Daily summaries at 9 AM UTC
- `weekly`: Weekly summaries on Sundays at 9 AM UTC
- `off`: Disable periodic summaries

**Examples:**
```
/schedule_summary daily
```
Enables daily risk summaries

```
/schedule_summary weekly
```
Enables weekly risk summaries

### Check Summary Status

```
/summary_status
```
- Shows current summary schedule
- Displays next summary time
- Shows summary configuration

### Send Summary Now

```
/send_summary_now
```
- Triggers immediate risk summary
- Sends current portfolio status
- Includes all risk metrics

## System Commands

### Check System Status

```
/status
```
- Shows overall bot status
- Displays system health
- Shows active monitoring
- Lists connected exchanges

### Bot Version

```
/version
```
- Shows bot version number
- Lists available features
- Displays last update date

### Emergency Stop

```
/emergency_stop
```
- Stops all monitoring and hedging
- Cancels pending orders
- Disables automated features
- Requires confirmation

### Reset Alerts

```
/reset_alerts
```
- Resets all alert suppression
- Clears alert history
- Re-enables all alerts

## Risk Management Best Practices

### Setting Risk Thresholds

**Conservative (1-3%):**
- Use for large positions
- Suitable for risk-averse users
- Frequent hedging activity

**Moderate (3-7%):**
- Balanced approach
- Good for most users
- Reasonable hedging frequency

**Aggressive (7-15%):**
- Higher risk tolerance
- Less frequent hedging
- Higher potential returns

### Position Sizing

1. **Start Small**: Begin with small positions to test the system
2. **Scale Gradually**: Increase position sizes as you gain confidence
3. **Diversify**: Don't put all your capital in one asset
4. **Monitor Closely**: Keep track of your positions and risk metrics

### Hedging Strategies

**Delta-Neutral:**
- Best for: Large positions, high volatility
- Pros: Effective risk reduction, simple implementation
- Cons: Higher transaction costs

**Options-Based:**
- Best for: Moderate positions, defined risk
- Pros: Limited downside, leverage
- Cons: Time decay, complexity

**Dynamic:**
- Best for: Active traders, changing markets
- Pros: Adaptive to market conditions
- Cons: Requires more attention

## Troubleshooting

### Common Issues

**Bot Not Responding:**
1. Check if bot is running
2. Verify internet connection
3. Check bot token validity
4. Restart the bot

**API Errors:**
1. Verify API credentials
2. Check API permissions
3. Ensure sufficient balance
4. Check rate limits

**Incorrect Risk Calculations:**
1. Verify position data
2. Check market data accuracy
3. Review risk thresholds
4. Contact support

### Error Messages

**"Configuration validation failed":**
- Check your `.env` file
- Verify API credentials
- Ensure all required fields are set

**"Position not found":**
- Verify asset symbol
- Check if monitoring is active
- Ensure position exists in exchange

**"Insufficient balance":**
- Check account balance
- Verify position size
- Consider reducing hedge size

### Getting Help

1. **Use `/help`**: Get command reference
2. **Check `/status`**: Verify system health
3. **Review logs**: Check for error messages
4. **Contact support**: Reach out to development team

## Advanced Features

### Machine Learning Integration

The bot uses ML models for:
- **Volatility Forecasting**: Predicts future volatility
- **Hedge Timing**: Determines optimal hedge timing
- **Risk Assessment**: Enhanced risk calculations

### Multi-Exchange Support

Currently supports:
- **Deribit**: Primary exchange
- **Bybit**: Additional exchange
- **OKX**: Additional exchange

### Custom Analytics

Advanced analytics include:
- **Stress Testing**: Scenario analysis
- **Correlation Analysis**: Portfolio diversification
- **Performance Attribution**: Factor-based analysis

## Security Considerations

### API Security
- Use API keys with minimal required permissions
- Regularly rotate API keys
- Monitor API usage for unusual activity
- Never share API credentials

### Risk Management
- Set appropriate risk thresholds
- Monitor positions regularly
- Use emergency stop when needed
- Keep backup of important data

### Best Practices
- Start with small positions
- Test features in demo mode first
- Monitor bot performance
- Keep software updated

## Performance Tips

### Optimization
- Use appropriate risk thresholds
- Monitor during active trading hours
- Regular system maintenance
- Efficient alert configuration

### Monitoring
- Check system status regularly
- Review risk reports periodically
- Monitor hedging effectiveness
- Track performance metrics

## Support and Resources

### Documentation
- This user manual
- API documentation
- Developer guide
- Project documentation

### Community
- GitHub repository
- Issue tracker
- Discussion forums
- User groups

### Contact
- Technical support
- Feature requests
- Bug reports
- General inquiries 
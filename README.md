# 🤖 Crypto Portfolio Risk Management & Hedging Bot

A comprehensive Telegram-based crypto portfolio risk management and automated hedging system with real-time monitoring, advanced analytics, and professional-grade risk controls.

### **Note**: Currently the project works on sort of Demo portfolio. Further it will be given the functionality to connect to real accounts and manage accordingly. Although it uses real time price and data from Deribit api.

### Demo Video: https://drive.google.com/file/d/1D8F2v5gf4QGUcbW1JmvrDMdScwASWMD1/view?usp=sharing
## 🚀 **FULLY IMPLEMENTED FEATURES**

### 📊 **Real-Time Risk Monitoring**
- **Greeks Calculation**: Delta, Gamma, Theta, Vega for all assets including options
- **VaR Analysis**: 95% and 99% Value at Risk calculations
- **Portfolio Metrics**: Maximum drawdown, correlation matrices, beta calculation
- **Continuous Monitoring**: 30-second intervals with configurable thresholds
- **Real-time Alerts**: Instant notifications for risk threshold breaches

### 🛡️ **Automated Hedging System**
- **Multiple Strategies**: Delta-neutral, options-based, dynamic rebalancing
- **Smart Order Routing**: Multi-exchange support with slippage estimation
- **User Confirmation**: Large trade confirmation (>$100k) for safety
- **Manual Hedging**: Direct hedge execution with real-time feedback
- **Hedge History**: Complete audit trail of all hedging activities

### 📈 **Advanced Analytics & Reporting**
- **Portfolio Analytics**: Comprehensive risk dashboard with interactive charts
- **P&L Attribution**: Factor-based profit/loss breakdown (Delta, Gamma, Theta, Vega)
- **Stress Testing**: Scenario analysis for market crashes, bull runs, etc.
- **Risk Reports**: Detailed PDF/text reports with export capabilities
- **Interactive Charts**: VaR, drawdown, Greeks, allocation visualizations

### 🔔 **Custom Alerts & Notifications**
- **Flexible Alerts**: Configure alerts for any risk metric (delta, var, pnl, etc.)
- **Condition Support**: Above/below thresholds with real-time monitoring
- **Alert Management**: Add, view, delete custom alerts via Telegram
- **Emergency Controls**: Instant stop all monitoring and hedging activities

### 📅 **Periodic Reporting**
- **Scheduled Summaries**: Daily/weekly risk summaries with key metrics
- **Performance Tracking**: Portfolio performance over time
- **Summary Management**: Configure frequency, view status, manual triggers
- **Background Delivery**: Automatic delivery at specified times

### 🎯 **Professional Features**
- **Multi-User Support**: Independent user sessions and data
- **Real Exchange Integration**: Deribit API for live market data
- **Error Handling**: Comprehensive error handling and logging
- **System Health**: Status monitoring and health checks
- **Version Control**: Bot versioning and feature tracking

## 🛠️ **COMMANDS REFERENCE**

### **Risk Monitoring**
- `/monitor_risk <asset> <size> <threshold>` - Start monitoring position
- `/stop_monitoring <asset>` - Stop monitoring position
- `/configure_monitor <asset> <delta_threshold> [var_threshold]` - Update thresholds

### **Hedging**
- `/auto_hedge <strategy> <threshold>` - Enable automated hedging
- `/hedge_now <asset> <size>` - Manual hedge execution
- `/hedge_status <asset>` - Check hedging status
- `/hedge_history <asset> [timeframe]` - View hedging history

### **Analytics**
- `/risk_analytics` - Comprehensive risk dashboard
- `/pnl_attribution` - P&L breakdown by factor
- `/risk_report` - Detailed risk report with export
- `/risk_charts` - Interactive risk metric charts
- `/chart <asset>` - Asset-specific charts

### **Alerts & Summaries**
- `/set_alert <metric> <condition> <value>` - Configure custom alerts
- `/alerts_status` - View current alert settings
- `/delete_alert <id>` - Remove specific alerts
- `/schedule_summary <frequency>` - Configure periodic summaries
- `/summary_status` - Check summary schedule
- `/send_summary_now` - Trigger immediate summary

### **System**
- `/status` - Overall bot status and system health
- `/version` - Bot version and features
- `/emergency_stop` - Emergency stop all activities
- `/help` - Complete command reference

## 📋 **SETUP INSTRUCTIONS**

### **Prerequisites**
```bash
pip install -r requirements.txt
```

### **Configuration**
1. Copy `env_template.txt` to `.env`
2. Add your Telegram Bot Token
3. Configure Deribit API credentials
4. Set risk thresholds and preferences

### **Running the Bot**
```bash
python main.py
```

## 🎯 **USE CASES**

### **Institutional Trading**
- Real-time portfolio risk monitoring
- Automated hedging for large positions
- Professional-grade analytics and reporting
- Custom alert systems for risk management

### **Retail Traders**
- Simple position monitoring
- Automated risk management
- Educational analytics and insights
- Mobile-friendly Telegram interface

### **Risk Managers**
- Comprehensive risk metrics
- Stress testing and scenario analysis
- Audit trails and compliance reporting
- Custom alert configurations

## 🔧 **TECHNICAL ARCHITECTURE**

### **Core Components**
- **Risk Calculator**: Greeks, VaR, correlation calculations
- **Hedging Manager**: Strategy execution and order management
- **Analytics Reporter**: Portfolio analysis and reporting
- **Exchange Integration**: Real-time market data and execution
- **Telegram Interface**: User interaction and notifications

### **Data Flow**
1. **Price Polling**: Continuous market data collection
2. **Risk Calculation**: Real-time portfolio risk metrics
3. **Alert Checking**: Custom alert condition evaluation
4. **Hedge Execution**: Automated/manual hedging actions
5. **Reporting**: Analytics, summaries, and notifications

### **Security Features**
- User confirmation for large trades
- Emergency stop functionality
- Comprehensive error handling
- Audit logging for all actions

## 📊 **RISK METRICS SUPPORTED**

- **Delta**: Price sensitivity
- **Gamma**: Delta sensitivity to price changes
- **Theta**: Time decay
- **Vega**: Volatility sensitivity
- **VaR**: Value at Risk (95%, 99%)
- **Maximum Drawdown**: Worst historical loss
- **Correlation**: Asset correlation matrices
- **Beta**: Market sensitivity
- **P&L Attribution**: Factor-based profit/loss analysis

## 🎨 **INTERACTIVE FEATURES**

- **Real-time Charts**: Price, PnL, VaR, allocation
- **Interactive Buttons**: Quick actions and navigation
- **Export Capabilities**: PDF reports and chart exports
- **Customizable Alerts**: Flexible alert conditions
- **Status Dashboards**: System health and portfolio status

## 🚀 **PRODUCTION READY**

This bot is **production-ready** with:
- ✅ Comprehensive error handling
- ✅ Multi-user support
- ✅ Real exchange integration
- ✅ Professional risk management
- ✅ Automated hedging strategies
- ✅ Advanced analytics
- ✅ Custom alerting system
- ✅ Periodic reporting
- ✅ Emergency controls
- ✅ Complete documentation

## 📞 **SUPPORT**

For questions or issues:
1. Check the `/help` command in the bot
2. Review the command reference above
3. Check system status with `/status`
4. Use `/version` for feature information

---

**Version**: 2.0.0  
**Status**: Production Ready  
**Last Updated**: 2024 

# Installation Guide

## Overview

This guide provides step-by-step instructions for installing and setting up the Crypto Portfolio Risk Management & Hedging Bot. The bot requires Python 3.8+ and integrates with Telegram and Deribit for real-time risk management and automated hedging.

## Prerequisites

### System Requirements

- **Operating System**: Windows 10+, macOS 10.14+, or Linux (Ubuntu 18.04+)
- **Python**: Python 3.8 or higher
- **Memory**: Minimum 4GB RAM (8GB recommended)
- **Storage**: At least 2GB free disk space
- **Internet**: Stable internet connection for API access

### Required Accounts

1. **Telegram Account**: For bot interaction
2. **Deribit Account**: For trading and market data
3. **GitHub Account**: For code access (optional)

## Installation Steps

### Step 1: Clone the Repository

```bash
# Clone the repository
git clone https://github.com/your-username/crypto-hedging-bot.git
cd crypto-hedging-bot

# Or download and extract the ZIP file
# Then navigate to the extracted directory
```

### Step 2: Set Up Python Environment

#### Option A: Using Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate

# Verify Python version
python --version  # Should be 3.8 or higher
```

#### Option B: Using Conda

```bash
# Create conda environment
conda create -n hedging-bot python=3.9
conda activate hedging-bot
```

### Step 3: Install Dependencies

```bash
# Install required packages
pip install -r requirements.txt

# Verify installation
python -c "import telegram, numpy, pandas, plotly; print('All packages installed successfully')"
```

### Step 4: Set Up Configuration

#### Create Environment File

```bash
# Copy the template file
cp env_template.txt .env

# Edit the .env file with your credentials
# Use your preferred text editor
```

#### Configure Environment Variables

Edit the `.env` file with your actual credentials:

```env
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Deribit API Configuration
DERIBIT_API_KEY=your_deribit_api_key_here
DERIBIT_SECRET=your_deribit_secret_here
DERIBIT_TESTNET=false

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=hedging_bot.log

# Risk Management Configuration
DEFAULT_RISK_THRESHOLD=0.05
LARGE_TRADE_THRESHOLD=100000
ALERT_SUPPRESSION_HOURS=1

# Machine Learning Configuration
ML_MODELS_ENABLED=true
VOLATILITY_MODEL_PATH=ml/vol_model.pkl
HEDGE_TIMING_MODEL_PATH=ml/hedge_timing_model.pkl
```

### Step 5: Set Up Telegram Bot

#### Create Telegram Bot

1. **Open Telegram** and search for `@BotFather`
2. **Start a chat** with BotFather
3. **Send command**: `/newbot`
4. **Follow instructions**:
   - Choose a name for your bot
   - Choose a username (must end with 'bot')
5. **Copy the bot token** provided by BotFather
6. **Add token to `.env` file**

#### Test Telegram Bot

```bash
# Start the bot
python main.py

# In Telegram, search for your bot username
# Send /start to initialize the bot
```

### Step 6: Set Up Deribit Account

#### Create Deribit Account

1. **Visit** [Deribit.com](https://www.deribit.com)
2. **Sign up** for an account
3. **Complete KYC** verification
4. **Enable API access** in account settings

#### Generate API Keys

1. **Go to Account Settings** → API
2. **Create new API key**:
   - Name: "Hedging Bot"
   - Permissions: Read, Trade
   - IP restrictions: Your server IP (optional)
3. **Copy API key and secret**
4. **Add to `.env` file**

#### Test API Connection

```bash
# Test Deribit connection
python -c "
from exchanges.deribit import DeribitExchange
import asyncio

async def test():
    exchange = DeribitExchange('your_key', 'your_secret')
    data = await exchange.get_market_data('BTC-PERP')
    print(f'Connection successful: {data}')

asyncio.run(test())
"
```

### Step 7: Train Machine Learning Models

```bash
# Train volatility forecasting model
python ml/train_models.py

# Verify models are created
ls ml/*.pkl
```

## Configuration Options

### Risk Management Settings

```env
# Risk thresholds (0.01 = 1%, 0.05 = 5%, etc.)
DEFAULT_RISK_THRESHOLD=0.05
DELTA_THRESHOLD=0.03
VAR_THRESHOLD=0.02

# Large trade confirmation
LARGE_TRADE_THRESHOLD=100000

# Alert suppression
ALERT_SUPPRESSION_HOURS=1
```

### Exchange Settings

```env
# Deribit settings
DERIBIT_TESTNET=false
DERIBIT_RATE_LIMIT=100

# Additional exchanges (optional)
BYBIT_API_KEY=your_bybit_key
BYBIT_SECRET=your_bybit_secret
OKX_API_KEY=your_okx_key
OKX_SECRET=your_okx_secret
```

### Logging Configuration

```env
# Log levels: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL=INFO

# Log file settings
LOG_FILE=hedging_bot.log
LOG_MAX_SIZE=10MB
LOG_BACKUP_COUNT=5
```

## Running the Bot

### Development Mode

```bash
# Activate virtual environment
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Run in development mode
python main.py
```

### Production Mode

#### Using Systemd (Linux)

```bash
# Create service file
sudo nano /etc/systemd/system/hedging-bot.service
```

Add the following content:

```ini
[Unit]
Description=Crypto Hedging Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/crypto-hedging-bot
Environment=PATH=/path/to/crypto-hedging-bot/venv/bin
ExecStart=/path/to/crypto-hedging-bot/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl enable hedging-bot
sudo systemctl start hedging-bot
sudo systemctl status hedging-bot
```

#### Using Docker

```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

```bash
# Build and run Docker container
docker build -t hedging-bot .
docker run -d --name hedging-bot --env-file .env hedging-bot
```

### Using Scripts

#### Windows

```batch
# run_bot.bat
@echo off
cd /d "%~dp0"
call venv\Scripts\activate
python main.py
pause
```

#### Linux/macOS

```bash
# run_bot.sh
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python main.py
```

```bash
# Make executable
chmod +x run_bot.sh
```

## Verification and Testing

### Test Bot Functionality

1. **Start the bot**: `python main.py`
2. **Open Telegram** and find your bot
3. **Send commands**:
   ```
   /start
   /help
   /status
   /version
   ```

### Test Risk Monitoring

```bash
# Monitor a test position
/monitor_risk BTC 1000 0.05
```

### Test Hedging

```bash
# Enable automated hedging
/auto_hedge delta_neutral 0.05

# Manual hedge
/hedge_now BTC 100
```

### Test Analytics

```bash
# Generate risk analytics
/risk_analytics

# Create risk report
/risk_report
```

## Troubleshooting

### Common Issues

#### Python Version Issues

```bash
# Check Python version
python --version

# If version is too old, install Python 3.8+
# On Ubuntu:
sudo apt update
sudo apt install python3.9 python3.9-venv

# On macOS:
brew install python@3.9
```

#### Package Installation Issues

```bash
# Upgrade pip
pip install --upgrade pip

# Install packages individually
pip install python-telegram-bot
pip install numpy pandas plotly
pip install scikit-learn joblib
pip install loguru python-dotenv
```

#### API Connection Issues

```bash
# Test API credentials
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print(f'Telegram token: {os.getenv(\"TELEGRAM_BOT_TOKEN\")[:10]}...')
print(f'Deribit key: {os.getenv(\"DERIBIT_API_KEY\")[:10]}...')
"
```

#### Permission Issues

```bash
# Fix file permissions
chmod +x run_bot.sh
chmod 600 .env

# Create log directory
mkdir -p logs
chmod 755 logs
```

### Debug Mode

```bash
# Run with debug logging
LOG_LEVEL=DEBUG python main.py

# Check logs
tail -f hedging_bot.log
```

### Performance Issues

```bash
# Monitor system resources
htop  # or top on some systems

# Check Python memory usage
pip install memory-profiler
python -m memory_profiler main.py
```

## Security Considerations

### API Key Security

1. **Never commit API keys** to version control
2. **Use environment variables** for sensitive data
3. **Rotate API keys** regularly
4. **Use IP restrictions** when possible
5. **Monitor API usage** for unusual activity

### File Permissions

```bash
# Secure configuration files
chmod 600 .env
chmod 600 *.pem  # SSL certificates

# Secure log files
chmod 644 *.log
```

### Network Security

1. **Use HTTPS** for all API communications
2. **Enable firewall** rules
3. **Use VPN** if running on cloud servers
4. **Monitor network traffic**

## Updates and Maintenance

### Updating the Bot

```bash
# Pull latest changes
git pull origin main

# Update dependencies
pip install -r requirements.txt --upgrade

# Restart the bot
sudo systemctl restart hedging-bot  # if using systemd
```

### Backup Configuration

```bash
# Backup important files
cp .env .env.backup
cp ml/*.pkl ml/backup/
```

### Monitoring and Alerts

```bash
# Check bot status
sudo systemctl status hedging-bot

# Monitor logs
tail -f hedging_bot.log | grep ERROR

# Set up log rotation
sudo logrotate /etc/logrotate.d/hedging-bot
```

## Support and Resources

### Documentation

- **User Manual**: `docs/User_Manual.md`
- **API Documentation**: `docs/API_Documentation.md`
- **Developer Guide**: `docs/Developer_Guide.md`
- **Project Documentation**: `docs/Project_Documentation.md`

### Community Support

- **GitHub Issues**: Report bugs and request features
- **Discord/Telegram**: Community chat channels
- **Email Support**: Technical support contact

### Additional Resources

- **Deribit API Documentation**: [Deribit API Docs](https://docs.deribit.com/)
- **Telegram Bot API**: [Telegram Bot API](https://core.telegram.org/bots/api)
- **Python Documentation**: [Python Docs](https://docs.python.org/)

## Next Steps

After successful installation:

1. **Read the User Manual** for detailed usage instructions
2. **Start with small positions** to test the system
3. **Configure risk thresholds** based on your risk tolerance
4. **Set up monitoring and alerts** for automated oversight
5. **Join the community** for support and updates 
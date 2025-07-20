#!/usr/bin/env python3
"""
Launcher script for the Telegram bot.
This script sets up the Python path correctly before running the bot.
"""
import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Now import and run the bot
from bot.telegram_bot import HedgingBot

if __name__ == "__main__":
    bot = HedgingBot()
    try:
        bot.run()
    except KeyboardInterrupt:
        print("\nBot stopped by user.")
        bot.stop()
    except Exception as e:
        print(f"Error running bot: {e}")
        bot.stop() 
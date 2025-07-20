"""
Main entry point for the Crypto Portfolio Risk Management & Hedging Bot.

This module serves as the primary entry point for the hedging bot application.
It initializes the bot, handles graceful shutdown, and manages the application lifecycle.

The bot provides:
- Real-time portfolio risk monitoring
- Automated and manual hedging capabilities
- Advanced analytics and reporting
- Custom alerts and notifications
- Multi-user support via Telegram

Author: Crypto Portfolio Risk Management Team
Version: 2.0.0
License: MIT
"""
import asyncio
import signal
import sys
from loguru import logger

from utils.config import Config
from utils.logger import setup_logger
from bot.telegram_bot import HedgingBot

class HedgingBotApp:
    """
    Main application class for the crypto portfolio hedging bot.
    
    This class manages the complete lifecycle of the hedging bot application,
    including initialization, startup, shutdown, and signal handling.
    
    Attributes:
        config (Config): Application configuration instance
        bot (HedgingBot): Telegram bot instance
        running (bool): Application running state flag
    """
    
    def __init__(self):
        """
        Initialize the hedging bot application.
        
        Sets up configuration, logging, and signal handlers for graceful shutdown.
        """
        self.config = Config()
        self.bot = None
        self.running = False
        
        # Setup logging with proper configuration
        setup_logger()
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """
        Handle shutdown signals for graceful application termination.
        
        Args:
            signum (int): Signal number received
            frame: Current stack frame (unused)
        """
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.running = False
    
    def start(self):
        """
        Start the hedging bot application.
        
        Validates configuration, initializes the bot, and starts the main
        application loop.
        
        Returns:
            bool: True if startup successful, False otherwise
        """
        try:
            # Validate configuration before starting
            if not self.config.validate():
                logger.error("Configuration validation failed - check your .env file")
                return False
            
            logger.info("Starting Crypto Portfolio Risk Management & Hedging Bot...")
            logger.info("Version: 2.0.0")
            logger.info("Features: Real-time monitoring, automated hedging, analytics")
            
            # Initialize the Telegram bot
            self.bot = HedgingBot()
            
            # Start the bot and set running flag
            self.running = True
            self.bot.run()
            
            return True
            
        except Exception as e:
            logger.error(f"Critical error during application startup: {e}")
            return False
    
    def stop(self):
        """
        Stop the hedging bot application gracefully.
        
        Performs cleanup operations and ensures all resources are properly released.
        """
        try:
            logger.info("Initiating application shutdown...")
            self.running = False
            
            if self.bot:
                self.bot.stop()
            
            logger.info("Application shutdown completed successfully")
            
        except Exception as e:
            logger.error(f"Error during application shutdown: {e}")
    
    def run(self):
        """
        Run the main application loop.
        
        Starts the application and keeps it running until a shutdown signal
        is received or an error occurs.
        """
        try:
            # Attempt to start the application
            success = self.start()
            if not success:
                logger.error("Failed to start application - exiting")
                return
            
            logger.info("Application started successfully - waiting for shutdown signal")
            
            # Keep the application running until shutdown signal
            while self.running:
                pass
                
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt - shutting down")
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
        finally:
            # Ensure cleanup happens even if errors occur
            self.stop()

if __name__ == "__main__":
    """
    Main entry point for the hedging bot application.
    
    Creates and runs the HedgingBotApp instance with proper error handling.
    """
    try:
        app = HedgingBotApp()
        app.run()
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Fatal application error: {e}")
        sys.exit(1) 
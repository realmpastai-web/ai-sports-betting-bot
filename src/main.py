"""
AI Sports Betting Discord Bot - Main Entry Point
"""
import asyncio
import logging
import os
from datetime import datetime

from src.bot.discord_bot import BettingBot
from src.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Main entry point for the bot."""
    logger.info("🚀 Starting AI Sports Betting Bot...")
    
    # Load configuration
    config = Config()
    
    # Initialize and run bot
    bot = BettingBot(config)
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())

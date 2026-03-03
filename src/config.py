"""
Configuration management for the betting bot.
"""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """Bot configuration loaded from environment variables."""
    
    # Discord
    discord_token: str = ""
    discord_channel_id: int = 0
    discord_guild_id: Optional[int] = None
    
    # The Odds API
    odds_api_key: str = ""
    odds_api_region: str = "us"
    odds_api_markets: str = "h2h"
    
    # Database
    database_url: str = "sqlite:///betting.db"
    
    # Risk Management
    max_units_per_bet: float = 2.0
    max_daily_loss: float = 5.0
    max_bets_per_day: int = 5
    ev_threshold: float = 0.05
    
    # Betting
    default_sports: list = None
    
    def __post_init__(self):
        """Load from environment variables."""
        # Discord
        self.discord_token = os.getenv("DISCORD_BOT_TOKEN", "")
        self.discord_channel_id = int(os.getenv("DISCORD_CHANNEL_ID", "0"))
        guild_id = os.getenv("DISCORD_GUILD_ID")
        self.discord_guild_id = int(guild_id) if guild_id else None
        
        # The Odds API
        self.odds_api_key = os.getenv("ODDS_API_KEY", "")
        self.odds_api_region = os.getenv("ODDS_API_REGION", "us")
        self.odds_api_markets = os.getenv("ODDS_API_MARKETS", "h2h")
        
        # Database
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///betting.db")
        
        # Risk Management
        self.max_units_per_bet = float(os.getenv("MAX_UNITS_PER_BET", "2.0"))
        self.max_daily_loss = float(os.getenv("MAX_DAILY_LOSS", "5.0"))
        self.max_bets_per_day = int(os.getenv("MAX_BETS_PER_DAY", "5"))
        self.ev_threshold = float(os.getenv("EV_THRESHOLD", "0.05"))
        
        # Default sports
        sports = os.getenv("DEFAULT_SPORTS", "basketball_nba,americanfootball_nfl,soccer_epl")
        self.default_sports = [s.strip() for s in sports.split(",")]
    
    def validate(self) -> list:
        """Validate configuration and return list of errors."""
        errors = []
        
        if not self.discord_token:
            errors.append("DISCORD_BOT_TOKEN is required")
        if not self.discord_channel_id:
            errors.append("DISCORD_CHANNEL_ID is required")
        if not self.odds_api_key:
            errors.append("ODDS_API_KEY is required")
        
        return errors

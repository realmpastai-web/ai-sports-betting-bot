"""
The Odds API client for fetching sports betting data.
"""
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class GameOdds:
    """Represents odds for a single game."""
    event_id: str
    sport: str
    home_team: str
    away_team: str
    commence_time: str
    home_odds: float
    away_odds: float
    draw_odds: Optional[float] = None
    bookmaker: str = ""
    
    @property
    def implied_prob_home(self) -> float:
        """Calculate implied probability for home team."""
        if self.home_odds > 0:
            return 100 / (self.home_odds + 100)
        else:
            return abs(self.home_odds) / (abs(self.home_odds) + 100)
    
    @property
    def implied_prob_away(self) -> float:
        """Calculate implied probability for away team."""
        if self.away_odds > 0:
            return 100 / (self.away_odds + 100)
        else:
            return abs(self.away_odds) / (abs(self.away_odds) + 100)


class OddsAPI:
    """Client for The Odds API."""
    
    BASE_URL = "https://api.the-odds-api.com/v4"
    
    def __init__(self, api_key: str, region: str = "us", markets: str = "h2h"):
        self.api_key = api_key
        self.region = region
        self.markets = markets
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_sports(self) -> List[Dict[str, Any]]:
        """Get list of available sports."""
        url = f"{self.BASE_URL}/sports"
        params = {"apiKey": self.api_key}
        
        async with self.session.get(url, params=params) as response:
            if response.status == 200:
                return await response.json()
            else:
                logger.error(f"Failed to get sports: {response.status}")
                return []
    
    async def get_odds(self, sport: str) -> List[GameOdds]:
        """Get odds for a specific sport."""
        url = f"{self.BASE_URL}/sports/{sport}/odds"
        params = {
            "apiKey": self.api_key,
            "regions": self.region,
            "markets": self.markets,
            "oddsFormat": "american"
        }
        
        async with self.session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return self._parse_odds(data, sport)
            else:
                logger.error(f"Failed to get odds for {sport}: {response.status}")
                return []
    
    def _parse_odds(self, data: List[Dict], sport: str) -> List[GameOdds]:
        """Parse API response into GameOdds objects."""
        games = []
        
        for event in data:
            event_id = event.get("id")
            home_team = event.get("home_team")
            away_team = event.get("away_team")
            commence_time = event.get("commence_time")
            
            # Get odds from first bookmaker
            bookmakers = event.get("bookmakers", [])
            if not bookmakers:
                continue
            
            bookmaker = bookmakers[0]
            bookmaker_title = bookmaker.get("title", "Unknown")
            
            # Find h2h market
            markets = bookmaker.get("markets", [])
            h2h_market = None
            for market in markets:
                if market.get("key") == "h2h":
                    h2h_market = market
                    break
            
            if not h2h_market:
                continue
            
            outcomes = h2h_market.get("outcomes", [])
            home_odds = None
            away_odds = None
            draw_odds = None
            
            for outcome in outcomes:
                name = outcome.get("name")
                price = outcome.get("price")
                
                if name == home_team:
                    home_odds = price
                elif name == away_team:
                    away_odds = price
                elif name == "Draw":
                    draw_odds = price
            
            if home_odds and away_odds:
                games.append(GameOdds(
                    event_id=event_id,
                    sport=sport,
                    home_team=home_team,
                    away_team=away_team,
                    commence_time=commence_time,
                    home_odds=home_odds,
                    away_odds=away_odds,
                    draw_odds=draw_odds,
                    bookmaker=bookmaker_title
                ))
        
        return games
    
    async def get_scores(self, sport: str, days_from: int = 1) -> List[Dict[str, Any]]:
        """Get scores for completed games."""
        url = f"{self.BASE_URL}/sports/{sport}/scores"
        params = {
            "apiKey": self.api_key,
            "daysFrom": days_from
        }
        
        async with self.session.get(url, params=params) as response:
            if response.status == 200:
                return await response.json()
            else:
                logger.error(f"Failed to get scores for {sport}: {response.status}")
                return []

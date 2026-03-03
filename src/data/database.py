"""
Database models and operations for betting data.
"""
import json
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict

import aiosqlite


@dataclass
class Bet:
    """Represents a single bet."""
    id: Optional[int] = None
    sport: str = ""
    event_id: str = ""
    home_team: str = ""
    away_team: str = ""
    selection: str = ""  # Which team/side we're betting on
    odds: float = 0.0
    implied_probability: float = 0.0
    predicted_probability: float = 0.0
    ev_percent: float = 0.0
    edge_percent: float = 0.0
    units: float = 0.0
    result: Optional[str] = None  # 'win', 'loss', 'push', 'pending'
    profit_loss: Optional[float] = None
    placed_at: Optional[datetime] = None
    settled_at: Optional[datetime] = None
    commsport_key: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DailyStats:
    """Daily betting statistics."""
    date: date
    total_bets: int = 0
    wins: int = 0
    losses: int = 0
    pushes: int = 0
    units_wagered: float = 0.0
    units_profit: float = 0.0
    roi_percent: float = 0.0


class Database:
    """SQLite database manager for betting data."""
    
    def __init__(self, db_path: str = "betting.db"):
        self.db_path = db_path
    
    async def initialize(self):
        """Create tables if they don't exist."""
        async with aiosqlite.connect(self.db_path) as db:
            # Bets table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS bets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sport TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    home_team TEXT NOT NULL,
                    away_team TEXT NOT NULL,
                    selection TEXT NOT NULL,
                    odds REAL NOT NULL,
                    implied_probability REAL NOT NULL,
                    predicted_probability REAL NOT NULL,
                    ev_percent REAL NOT NULL,
                    edge_percent REAL NOT NULL,
                    units REAL NOT NULL,
                    result TEXT,
                    profit_loss REAL,
                    placed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    settled_at TIMESTAMP,
                    sport_key TEXT
                )
            """)
            
            # Daily stats table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS daily_stats (
                    date DATE PRIMARY KEY,
                    total_bets INTEGER DEFAULT 0,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    pushes INTEGER DEFAULT 0,
                    units_wagered REAL DEFAULT 0,
                    units_profit REAL DEFAULT 0,
                    roi_percent REAL DEFAULT 0
                )
            """)
            
            # Odds history table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS odds_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL,
                    sport TEXT NOT NULL,
                    home_team TEXT NOT NULL,
                    away_team TEXT NOT NULL,
                    odds_home REAL,
                    odds_away REAL,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await db.commit()
    
    async def place_bet(self, bet: Bet) -> int:
        """Place a new bet and return its ID."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO bets 
                (sport, event_id, home_team, away_team, selection, odds, 
                 implied_probability, predicted_probability, ev_percent, 
                 edge_percent, units, result, sport_key)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                bet.sport, bet.event_id, bet.home_team, bet.away_team,
                bet.selection, bet.odds, bet.implied_probability,
                bet.predicted_probability, bet.ev_percent, bet.edge_percent,
                bet.units, bet.result or "pending", bet.sport
            ))
            await db.commit()
            return cursor.lastrowid
    
    async def get_bets_today(self) -> List[Bet]:
        """Get all bets placed today."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM bets 
                WHERE date(placed_at) = date('now')
                ORDER BY placed_at DESC
            """)
            rows = await cursor.fetchall()
            return [Bet(**dict(row)) for row in rows]
    
    async def get_pending_bets(self) -> List[Bet]:
        """Get all pending bets."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM bets 
                WHERE result = 'pending'
                ORDER BY placed_at DESC
            """)
            rows = await cursor.fetchall()
            return [Bet(**dict(row)) for row in rows]
    
    async def settle_bet(self, bet_id: int, result: str, profit_loss: float):
        """Settle a bet with the result."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE bets 
                SET result = ?, profit_loss = ?, settled_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (result, profit_loss, bet_id))
            await db.commit()
    
    async def get_daily_stats(self, stats_date: date = None) -> DailyStats:
        """Get stats for a specific date (defaults to today)."""
        stats_date = stats_date or date.today()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT 
                    COUNT(*) as total_bets,
                    SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN result = 'loss' THEN 1 ELSE 0 END) as losses,
                    SUM(CASE WHEN result = 'push' THEN 1 ELSE 0 END) as pushes,
                    SUM(units) as units_wagered,
                    SUM(CASE WHEN profit_loss IS NOT NULL THEN profit_loss ELSE 0 END) as units_profit
                FROM bets 
                WHERE date(placed_at) = ?
            """, (stats_date.isoformat(),))
            
            row = await cursor.fetchone()
            total_bets, wins, losses, pushes, wagered, profit = row
            
            # Calculate ROI
            roi = 0.0
            if wagered and wagered > 0:
                roi = (profit or 0) / wagered * 100
            
            return DailyStats(
                date=stats_date,
                total_bets=total_bets or 0,
                wins=wins or 0,
                losses=losses or 0,
                pushes=pushes or 0,
                units_wagered=wagered or 0,
                units_profit=profit or 0,
                roi_percent=roi
            )
    
    async def get_all_time_stats(self) -> Dict[str, Any]:
        """Get all-time betting statistics."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT 
                    COUNT(*) as total_bets,
                    SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN result = 'loss' THEN 1 ELSE 0 END) as losses,
                    SUM(CASE WHEN result = 'push' THEN 1 ELSE 0 END) as pushes,
                    SUM(units) as units_wagered,
                    SUM(CASE WHEN profit_loss IS NOT NULL THEN profit_loss ELSE 0 END) as units_profit
                FROM bets
            """)
            
            row = await cursor.fetchone()
            total, wins, losses, pushes, wagered, profit = row
            
            roi = 0.0
            if wagered and wagered > 0:
                roi = (profit or 0) / wagered * 100
            
            win_rate = 0.0
            if wins or losses:
                win_rate = (wins or 0) / ((wins or 0) + (losses or 0)) * 100
            
            return {
                "total_bets": total or 0,
                "wins": wins or 0,
                "losses": losses or 0,
                "pushes": pushes or 0,
                "win_rate": win_rate,
                "units_wagered": wagered or 0,
                "units_profit": profit or 0,
                "roi_percent": roi
            }
    
    async def record_odds(self, event_id: str, sport: str, home_team: str, 
                          away_team: str, odds_home: float, odds_away: float):
        """Record odds snapshot for CLV tracking."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO odds_history 
                (event_id, sport, home_team, away_team, odds_home, odds_away)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (event_id, sport, home_team, away_team, odds_home, odds_away))
            await db.commit()

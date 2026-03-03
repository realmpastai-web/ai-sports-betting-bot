"""
Discord bot implementation for AI Sports Betting.
"""
import asyncio
import logging
from datetime import datetime, date
from typing import Optional

import discord
from discord.ext import commands, tasks

from src.config import Config
from src.data.database import Database, Bet
from src.data.odds_api import OddsAPI
from src.models.predictor import BaselineModel, XGBoostModel, BettingAnalyzer

logger = logging.getLogger(__name__)


class BettingBot:
    """Main betting bot class."""
    
    def __init__(self, config: Config):
        self.config = config
        self.db = Database()
        self.baseline_model = BaselineModel()
        self.xgboost_model = XGBoostModel()
        self.analyzer = BettingAnalyzer()
        
        # Discord bot
        intents = discord.Intents.default()
        intents.message_content = True
        
        self.bot = commands.Bot(
            command_prefix="!",
            intents=intents,
            help_command=None
        )
        
        self.is_running = False
        self.setup_commands()
    
    def setup_commands(self):
        """Setup Discord commands."""
        
        @self.bot.event
        async def on_ready():
            logger.info(f"✅ Logged in as {self.bot.user}")
            await self.bot.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name="for +EV bets"
                )
            )
            # Start background tasks
            self.check_odds.start()
        
        @self.bot.command(name="start")
        @commands.has_permissions(administrator=True)
        async def start_cmd(ctx):
            """Start automated betting."""
            self.is_running = True
            await ctx.send("🚀 **Betting automation STARTED**\nI'll scan for +EV opportunities every 15 minutes.")
        
        @self.bot.command(name="stop")
        @commands.has_permissions(administrator=True)
        async def stop_cmd(ctx):
            """Stop automated betting."""
            self.is_running = False
            await ctx.send("🛑 **Betting automation STOPPED**")
        
        @self.bot.command(name="status")
        async def status_cmd(ctx):
            """Show system status."""
            embed = discord.Embed(
                title="📊 Betting Bot Status",
                color=0x00ff00 if self.is_running else 0xff6600,
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="Automation",
                value="🟢 Running" if self.is_running else "🟡 Paused",
                inline=True
            )
            
            # Daily stats
            stats = await self.db.get_daily_stats()
            embed.add_field(
                name="Today's Bets",
                value=f"{stats.total_bets}/{self.config.max_bets_per_day}",
                inline=True
            )
            embed.add_field(
                name="Today's P/L",
                value=f"{stats.units_profit:+.2f}u",
                inline=True
            )
            
            # All-time stats
            all_time = await self.db.get_all_time_stats()
            embed.add_field(
                name="Total Bets",
                value=f"{all_time['total_bets']}",
                inline=True
            )
            embed.add_field(
                name="Win Rate",
                value=f"{all_time['win_rate']:.1f}%",
                inline=True
            )
            embed.add_field(
                name="All-Time ROI",
                value=f"{all_time['roi_percent']:+.2f}%",
                inline=True
            )
            
            await ctx.send(embed=embed)
        
        @self.bot.command(name="history")
        async def history_cmd(ctx, limit: int = 10):
            """Show recent bets."""
            bets = await self.db.get_pending_bets()
            
            if not bets:
                await ctx.send("📭 No pending bets found.")
                return
            
            embed = discord.Embed(
                title="📜 Recent Bets",
                color=0x3498db,
                timestamp=datetime.now()
            )
            
            for bet in bets[:limit]:
                status_emoji = "⏳" if bet.result == "pending" else "✅" if bet.result == "win" else "❌"
                embed.add_field(
                    name=f"{status_emoji} {bet.home_team} vs {bet.away_team}",
                    value=f"Pick: **{bet.selection}** @ {bet.odds:+.0f}\n"
                          f"EV: {bet.ev_percent*100:.1f}% | Edge: {bet.edge_percent*100:.1f}% | Units: {bet.units:.2f}",
                    inline=False
                )
            
            await ctx.send(embed=embed)
        
        @self.bot.command(name="stats")
        async def stats_cmd(ctx):
            """Show detailed statistics."""
            all_time = await self.db.get_all_time_stats()
            
            embed = discord.Embed(
                title="📈 All-Time Statistics",
                color=0x9b59b6,
                timestamp=datetime.now()
            )
            
            embed.add_field(name="Total Bets", value=all_time['total_bets'], inline=True)
            embed.add_field(name="Wins", value=all_time['wins'], inline=True)
            embed.add_field(name="Losses", value=all_time['losses'], inline=True)
            embed.add_field(name="Win Rate", value=f"{all_time['win_rate']:.1f}%", inline=True)
            embed.add_field(name="Units Wagered", value=f"{all_time['units_wagered']:.2f}u", inline=True)
            embed.add_field(name="Units Profit", value=f"{all_time['units_profit']:+.2f}u", inline=True)
            embed.add_field(name="ROI", value=f"{all_time['roi_percent']:+.2f}%", inline=False)
            
            await ctx.send(embed=embed)
        
        @self.bot.command(name="scan")
        @commands.has_permissions(administrator=True)
        async def scan_cmd(ctx):
            """Manually scan for opportunities."""
            await ctx.send("🔍 Scanning for +EV opportunities...")
            opportunities = await self.scan_for_opportunities()
            
            if opportunities:
                await ctx.send(f"Found {len(opportunities)} opportunities!")
                for opp in opportunities:
                    await self.post_bet_to_discord(opp)
            else:
                await ctx.send("No +EV opportunities found at this time.")
        
        @self.bot.command(name="help")
        async def help_cmd(ctx):
            """Show help message."""
            embed = discord.Embed(
                title="🎯 AI Sports Betting Bot - Help",
                description="Automated sports betting with AI predictions",
                color=0x00ff00
            )
            
            embed.add_field(
                name="Admin Commands",
                value="`!start` - Start automation\n"
                      "`!stop` - Stop automation\n"
                      "`!scan` - Manual scan",
                inline=False
            )
            
            embed.add_field(
                name="User Commands",
                value="`!status` - Bot status\n"
                      "`!history` - Recent bets\n"
                      "`!stats` - All-time stats\n"
                      "`!help` - This message",
                inline=False
            )
            
            embed.add_field(
                name="Risk Management",
                value=f"• Max {self.config.max_bets_per_day} bets/day\n"
                      f"• Max {self.config.max_units_per_bet} units/bet\n"
                      f"• EV threshold: {self.config.ev_threshold*100:.0f}%\n"
                      f"• Max daily loss: {self.config.max_daily_loss} units",
                inline=False
            )
            
            await ctx.send(embed=embed)
    
    async def start(self):
        """Start the bot."""
        # Validate config
        errors = self.config.validate()
        if errors:
            logger.error(f"Configuration errors: {errors}")
            return
        
        # Initialize database
        await self.db.initialize()
        
        # Start Discord bot
        await self.bot.start(self.config.discord_token)
    
    @tasks.loop(minutes=15)
    async def check_odds(self):
        """Background task to check odds periodically."""
        if not self.is_running:
            return
        
        logger.info("🔍 Checking for betting opportunities...")
        opportunities = await self.scan_for_opportunities()
        
        for opp in opportunities:
            # Check daily limits
            daily_stats = await self.db.get_daily_stats()
            if daily_stats.total_bets >= self.config.max_bets_per_day:
                logger.info("Daily bet limit reached")
                break
            
            if daily_stats.units_profit <= -self.config.max_daily_loss:
                logger.info("Daily loss limit reached")
                break
            
            # Place the bet
            await self.place_bet(opp)
    
    async def scan_for_opportunities(self) -> list:
        """Scan all sports for betting opportunities."""
        opportunities = []
        
        async with OddsAPI(self.config.odds_api_key) as api:
            for sport in self.config.default_sports:
                try:
                    games = await api.get_odds(sport)
                    
                    for game in games:
                        game_data = {
                            "event_id": game.event_id,
                            "sport": sport,
                            "home_team": game.home_team,
                            "away_team": game.away_team,
                            "home_odds": game.home_odds,
                            "away_odds": game.away_odds,
                            "implied_prob_home": game.implied_prob_home,
                            "implied_prob_away": game.implied_prob_away
                        }
                        
                        # Get prediction
                        prediction = self.baseline_model.predict(game_data)
                        
                        # Analyze opportunity
                        opp = self.analyzer.analyze_opportunity(
                            prediction, game_data, self.config.ev_threshold
                        )
                        
                        if opp:
                            opportunities.append(opp)
                            
                except Exception as e:
                    logger.error(f"Error scanning {sport}: {e}")
        
        # Sort by EV
        opportunities.sort(key=lambda x: x['ev_percent'], reverse=True)
        return opportunities
    
    async def place_bet(self, opp: dict):
        """Place a bet and post to Discord."""
        # Calculate units (capped)
        units = min(opp['kelly_units'], self.config.max_units_per_bet)
        if units < 0.5:  # Minimum bet size
            units = 0.5
        
        # Create bet record
        bet = Bet(
            sport=opp['sport'],
            event_id=opp['event_id'],
            home_team=opp['home_team'],
            away_team=opp['away_team'],
            selection=opp['selection'],
            odds=opp['odds'],
            implied_probability=opp['implied_probability'],
            predicted_probability=opp['predicted_probability'],
            ev_percent=opp['ev_percent'],
            edge_percent=opp['edge_percent'],
            units=units,
            result="pending"
        )
        
        # Save to database
        bet_id = await self.db.place_bet(bet)
        
        # Post to Discord
        await self.post_bet_to_discord(opp, units, bet_id)
        
        logger.info(f"✅ Bet placed: {opp['selection']} @ {opp['odds']}")
    
    async def post_bet_to_discord(self, opp: dict, units: float = None, bet_id: int = None):
        """Post a bet recommendation to Discord."""
        channel = self.bot.get_channel(self.config.discord_channel_id)
        if not channel:
            logger.error("Discord channel not found")
            return
        
        if units is None:
            units = min(opp['kelly_units'], self.config.max_units_per_bet)
        
        embed = discord.Embed(
            title="🎯 NEW BET ALERT",
            description=f"**{opp['home_team']}** vs **{opp['away_team']}**",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="Pick",
            value=f"**{opp['selection']}**\nOdds: {opp['odds']:+.0f}",
            inline=True
        )
        
        embed.add_field(
            name="Expected Value",
            value=f"{opp['ev_percent']*100:.1f}%",
            inline=True
        )
        
        embed.add_field(
            name="Edge",
            value=f"{opp['edge_percent']*100:.1f}%",
            inline=True
        )
        
        embed.add_field(
            name="Units",
            value=f"{units:.2f}u",
            inline=True
        )
        
        embed.add_field(
            name="Model",
            value=opp['model_used'].upper(),
            inline=True
        )
        
        embed.add_field(
            name="Confidence",
            value=f"{opp['confidence']*100:.0f}%",
            inline=True
        )
        
        if bet_id:
            embed.set_footer(text=f"Bet ID: {bet_id}")
        
        await channel.send(embed=embed)

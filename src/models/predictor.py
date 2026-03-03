"""
Prediction models for sports betting.
"""
import logging
from typing import List, Tuple, Optional
from dataclasses import dataclass

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class Prediction:
    """Prediction result for a game."""
    event_id: str
    home_team: str
    away_team: str
    home_prob: float
    away_prob: float
    confidence: float
    model_used: str
    features: dict = None


class BaselineModel:
    """Logistic Regression baseline model."""
    
    def __init__(self):
        self.model = LogisticRegression(random_state=42, max_iter=1000)
        self.scaler = StandardScaler()
        self.is_trained = False
    
    def _extract_features(self, game_data: dict) -> np.ndarray:
        """Extract features from game data."""
        # Simple features based on implied probabilities
        home_implied = game_data.get("implied_prob_home", 0.5)
        away_implied = game_data.get("implied_prob_away", 0.5)
        
        # Odds differential
        odds_diff = abs(game_data.get("home_odds", 0) - game_data.get("away_odds", 0))
        
        # Create feature vector
        features = [
            home_implied,
            away_implied,
            odds_diff / 100,  # Normalize
            home_implied - away_implied,  # Market bias
        ]
        
        return np.array(features).reshape(1, -1)
    
    def train(self, X: np.ndarray, y: np.ndarray):
        """Train the model."""
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)
        self.is_trained = True
        logger.info("✅ Baseline model trained")
    
    def predict(self, game_data: dict) -> Prediction:
        """Make prediction for a single game."""
        features = self._extract_features(game_data)
        
        if self.is_trained:
            features_scaled = self.scaler.transform(features)
            probs = self.model.predict_proba(features_scaled)[0]
            home_prob = probs[1]  # Assuming class 1 is home win
        else:
            # Fallback to market-implied probabilities with slight adjustment
            home_prob = game_data.get("implied_prob_home", 0.5)
            # Slight regression to mean
            home_prob = 0.3 + 0.4 * home_prob
        
        away_prob = 1 - home_prob
        
        # Confidence based on probability distance from 0.5
        confidence = abs(home_prob - 0.5) * 2
        
        return Prediction(
            event_id=game_data.get("event_id", ""),
            home_team=game_data.get("home_team", ""),
            away_team=game_data.get("away_team", ""),
            home_prob=home_prob,
            away_prob=away_prob,
            confidence=confidence,
            model_used="baseline",
            features={"home_implied": game_data.get("implied_prob_home")}
        )


class XGBoostModel:
    """XGBoost prediction model."""
    
    def __init__(self):
        if not XGBOOST_AVAILABLE:
            logger.warning("XGBoost not available, using baseline model")
            self.model = None
        else:
            self.model = xgb.XGBClassifier(
                n_estimators=100,
                max_depth=4,
                learning_rate=0.1,
                random_state=42
            )
        self.scaler = StandardScaler()
        self.is_trained = False
    
    def _extract_features(self, game_data: dict) -> np.ndarray:
        """Extract features from game data."""
        home_implied = game_data.get("implied_prob_home", 0.5)
        away_implied = game_data.get("implied_prob_away", 0.5)
        home_odds = game_data.get("home_odds", 0)
        away_odds = game_data.get("away_odds", 0)
        
        features = [
            home_implied,
            away_implied,
            abs(home_odds - away_odds) / 100,
            home_implied - away_implied,
            1 / home_implied if home_implied > 0 else 0,  # Decimal odds
            1 / away_implied if away_implied > 0 else 0,
            (home_implied - 0.5) ** 2,  # Non-linear market bias
        ]
        
        return np.array(features).reshape(1, -1)
    
    def train(self, X: np.ndarray, y: np.ndarray):
        """Train the model."""
        if self.model is None:
            logger.warning("XGBoost not available, skipping training")
            return
        
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)
        self.is_trained = True
        logger.info("✅ XGBoost model trained")
    
    def predict(self, game_data: dict) -> Prediction:
        """Make prediction for a single game."""
        features = self._extract_features(game_data)
        
        if self.is_trained and self.model is not None:
            features_scaled = self.scaler.transform(features)
            probs = self.model.predict_proba(features_scaled)[0]
            home_prob = probs[1]
        else:
            # Fallback
            home_prob = game_data.get("implied_prob_home", 0.5)
            home_prob = 0.3 + 0.4 * home_prob
        
        away_prob = 1 - home_prob
        confidence = abs(home_prob - 0.5) * 2
        
        return Prediction(
            event_id=game_data.get("event_id", ""),
            home_team=game_data.get("home_team", ""),
            away_team=game_data.get("away_team", ""),
            home_prob=home_prob,
            away_prob=away_prob,
            confidence=confidence,
            model_used="xgboost",
            features={"home_implied": game_data.get("implied_prob_home")}
        )


class BettingAnalyzer:
    """Analyzes predictions and calculates EV/Edge."""
    
    @staticmethod
    def calculate_ev(predicted_prob: float, odds: float) -> float:
        """Calculate Expected Value percentage."""
        # Convert American odds to decimal
        if odds > 0:
            decimal_odds = (odds / 100) + 1
        else:
            decimal_odds = (100 / abs(odds)) + 1
        
        # EV = (Probability * Win Amount) - (1 - Probability) * Stake
        # Simplified: EV% = (P * Decimal Odds) - 1
        ev = (predicted_prob * decimal_odds) - 1
        return ev
    
    @staticmethod
    def calculate_edge(predicted_prob: float, implied_prob: float) -> float:
        """Calculate edge over market."""
        return predicted_prob - implied_prob
    
    @staticmethod
    def calculate_kelly_units(edge: float, odds: float, fraction: float = 0.25) -> float:
        """Calculate Kelly Criterion bet size (fractional)."""
        # Convert to decimal odds
        if odds > 0:
            decimal_odds = (odds / 100) + 1
        else:
            decimal_odds = (100 / abs(odds)) + 1
        
        # Kelly = (bp - q) / b
        # b = decimal odds - 1, p = win prob, q = lose prob
        b = decimal_odds - 1
        p = edge + 0.5  # Approximate from edge
        q = 1 - p
        
        kelly = (b * p - q) / b
        kelly = max(0, kelly)  # Don't bet negative
        
        # Apply fraction for safety
        return kelly * fraction
    
    def analyze_opportunity(self, prediction: Prediction, game_odds: dict,
                           ev_threshold: float = 0.05) -> Optional[dict]:
        """Analyze if a game is a betting opportunity."""
        # Determine which side to bet
        home_ev = self.calculate_ev(prediction.home_prob, game_odds.get("home_odds", 0))
        away_ev = self.calculate_ev(prediction.away_prob, game_odds.get("away_odds", 0))
        
        if home_ev > away_ev and home_ev >= ev_threshold:
            selection = game_odds.get("home_team")
            odds = game_odds.get("home_odds")
            implied_prob = game_odds.get("implied_prob_home")
            predicted_prob = prediction.home_prob
            ev = home_ev
        elif away_ev >= ev_threshold:
            selection = game_odds.get("away_team")
            odds = game_odds.get("away_odds")
            implied_prob = game_odds.get("implied_prob_away")
            predicted_prob = prediction.away_prob
            ev = away_ev
        else:
            return None  # No value bet
        
        edge = self.calculate_edge(predicted_prob, implied_prob)
        kelly_units = self.calculate_kelly_units(edge, odds)
        
        return {
            "event_id": prediction.event_id,
            "sport": game_odds.get("sport"),
            "home_team": game_odds.get("home_team"),
            "away_team": game_odds.get("away_team"),
            "selection": selection,
            "odds": odds,
            "implied_probability": implied_prob,
            "predicted_probability": predicted_prob,
            "ev_percent": ev,
            "edge_percent": edge,
            "kelly_units": kelly_units,
            "confidence": prediction.confidence,
            "model_used": prediction.model_used
        }

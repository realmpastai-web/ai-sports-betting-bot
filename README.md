# AI Sports Betting Discord Bot

🎯 **Automated sports betting analytics with AI predictions**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Discord.py](https://img.shields.io/badge/discord.py-v2.3+-blue.svg)](https://discordpy.readthedocs.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

AI-powered sports betting system that:
- Fetches live odds from The Odds API
- Predicts outcomes using Logistic Regression + XGBoost
- Calculates Expected Value (EV) and Edge
- Applies risk management rules
- Auto-posts picks to Discord

## Features

### 🤖 AI Prediction Models
- **Baseline**: Logistic Regression for probability estimation
- **Advanced**: XGBoost for improved accuracy
- **Metrics**: True probability, Implied probability, EV, Edge %

### 📊 Risk Management
- EV threshold filtering (>5%)
- Max 2 units per bet
- Max daily loss: 5 units
- Max 5 bets per day

### 💬 Discord Integration
- Auto-post picks to channel
- Role-based access control
- Real-time notifications
- Bet tracking and history

### 📈 Analytics Dashboard
- ROI tracking
- Drawdown monitoring
- CLV (Closing Line Value) analysis
- Performance reports

## Quick Start

### 1. Clone & Setup

```bash
git clone https://github.com/realmpastai-web/ai-sports-betting-bot.git
cd ai-sports-betting-bot
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your credentials
```

Required variables:
```env
# Discord
DISCORD_BOT_TOKEN=your_discord_bot_token
DISCORD_CHANNEL_ID=your_channel_id

# The Odds API
ODDS_API_KEY=your_odds_api_key

# Database
DATABASE_URL=postgresql://user:pass@localhost/betting_db

# Risk Management
MAX_UNITS_PER_BET=2
MAX_DAILY_LOSS=5
MAX_BETS_PER_DAY=5
EV_THRESHOLD=0.05
```

### 3. Run with Docker

```bash
docker-compose up -d
```

### 4. Or Run Locally

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run bot
python src/main.py
```

## Project Structure

```
ai-sports-betting-bot/
├── src/
│   ├── main.py              # Entry point
│   ├── bot/
│   │   ├── discord_bot.py   # Discord bot handlers
│   │   └── commands.py      # Slash commands
│   ├── models/
│   │   ├── baseline.py      # Logistic Regression
│   │   ├── xgboost_model.py # XGBoost predictor
│   │   └── features.py      # Feature engineering
│   ├── data/
│   │   ├── odds_api.py      # The Odds API client
│   │   └── database.py      # PostgreSQL operations
│   └── config.py            # Configuration
├── notebooks/               # Jupyter notebooks for analysis
├── tests/                   # Unit tests
├── config/                  # Config files
├── .env.example             # Environment template
├── docker-compose.yml       # Docker setup
├── Dockerfile               # Container definition
├── requirements.txt         # Python dependencies
└── README.md                # This file
```

## Discord Commands

| Command | Description | Access |
|---------|-------------|--------|
| `/start` | Start automated betting | Admin |
| `/stop` | Stop automated betting | Admin |
| `/status` | Show system status | All |
| `/history` | Show recent bets | All |
| `/stats` | Show ROI and analytics | All |
| `/settings` | Configure risk params | Admin |

## Model Performance

### Logistic Regression (Baseline)
- Accuracy: ~52-55%
- Calibration: Good for probability estimates
- Speed: Fast inference

### XGBoost (Advanced)
- Accuracy: ~55-58%
- Feature importance analysis
- Hyperparameter tuned

## Risk Management Rules

1. **EV Filter**: Only bet if Expected Value > 5%
2. **Unit Sizing**: Max 2 units per bet (Kelly Criterion adjusted)
3. **Daily Limits**: Max 5 bets per day, max 5 unit daily loss
4. **Bankroll Protection**: Stop if drawdown exceeds 20%

## Deployment

### Railway (Recommended)

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template)

### Fly.io

```bash
fly deploy
```

### VPS

```bash
docker-compose up -d
```

## Tech Stack

- **Python 3.11+**: Core language
- **discord.py**: Discord bot framework
- **scikit-learn**: Logistic Regression
- **XGBoost**: Gradient boosting model
- **PostgreSQL**: Data persistence
- **SQLAlchemy**: ORM
- **pandas/numpy**: Data processing
- **Docker**: Containerization

## API References

- [The Odds API](https://the-odds-api.com/)
- [Discord.py Documentation](https://discordpy.readthedocs.io/)

## License

MIT License — see [LICENSE](LICENSE) for details.

---

Built with 🎯 by [QuantBitRealm](https://github.com/realmpastai-web)

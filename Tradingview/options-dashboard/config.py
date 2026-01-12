"""
Configuration Module for Options Supergraph Dashboard
Loads API credentials and default settings from keys.env
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from keys.env
env_path = Path(__file__).parent.parent / "keys.env"
load_dotenv(env_path)

# Alpaca API Configuration
ALPACA_API_KEY = os.getenv("APCA_API_KEY_ID", "")
ALPACA_API_SECRET = os.getenv("APCA_API_SECRET_KEY", "")
ALPACA_ENDPOINT = os.getenv("APCA_ENDPOINT", "https://paper-api.alpaca.markets")

# Default Market Settings
DEFAULT_RISK_FREE_RATE = 0.05  # 5% annual risk-free rate (approximate current rates)
DEFAULT_DIVIDEND_YIELD = 0.0  # Assume no dividends for simplicity

# Chart Settings
PRICE_RANGE_PERCENT = 0.20  # Show +/- 20% from current price
NUM_PRICE_POINTS = 200  # Number of points for smooth curves

# Strategy Templates
STRATEGY_TEMPLATES = {
    "Long Call": [{"type": "call", "position": "long", "quantity": 1}],
    "Long Put": [{"type": "put", "position": "long", "quantity": 1}],
    "Short Call": [{"type": "call", "position": "short", "quantity": 1}],
    "Short Put": [{"type": "put", "position": "short", "quantity": 1}],
    "Bull Call Spread": [
        {"type": "call", "position": "long", "quantity": 1, "strike_offset": -1},
        {"type": "call", "position": "short", "quantity": 1, "strike_offset": 1}
    ],
    "Bear Put Spread": [
        {"type": "put", "position": "long", "quantity": 1, "strike_offset": 1},
        {"type": "put", "position": "short", "quantity": 1, "strike_offset": -1}
    ],
    "Long Straddle": [
        {"type": "call", "position": "long", "quantity": 1, "strike_offset": 0},
        {"type": "put", "position": "long", "quantity": 1, "strike_offset": 0}
    ],
    "Short Straddle": [
        {"type": "call", "position": "short", "quantity": 1, "strike_offset": 0},
        {"type": "put", "position": "short", "quantity": 1, "strike_offset": 0}
    ],
    "Long Strangle": [
        {"type": "call", "position": "long", "quantity": 1, "strike_offset": 1},
        {"type": "put", "position": "long", "quantity": 1, "strike_offset": -1}
    ],
    "Iron Condor": [
        {"type": "put", "position": "long", "quantity": 1, "strike_offset": -2},
        {"type": "put", "position": "short", "quantity": 1, "strike_offset": -1},
        {"type": "call", "position": "short", "quantity": 1, "strike_offset": 1},
        {"type": "call", "position": "long", "quantity": 1, "strike_offset": 2}
    ],
    "Iron Butterfly": [
        {"type": "put", "position": "long", "quantity": 1, "strike_offset": -1},
        {"type": "put", "position": "short", "quantity": 1, "strike_offset": 0},
        {"type": "call", "position": "short", "quantity": 1, "strike_offset": 0},
        {"type": "call", "position": "long", "quantity": 1, "strike_offset": 1}
    ],
    "Covered Call": [
        {"type": "stock", "position": "long", "quantity": 100},
        {"type": "call", "position": "short", "quantity": 1, "strike_offset": 1}
    ],
    "Protective Put": [
        {"type": "stock", "position": "long", "quantity": 100},
        {"type": "put", "position": "long", "quantity": 1, "strike_offset": -1}
    ],
    "Custom": []
}

# Default strike interval (will be overridden by actual option chain)
DEFAULT_STRIKE_INTERVAL = 5.0

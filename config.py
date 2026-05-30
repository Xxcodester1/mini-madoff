import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env", override=True)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

# Risk parameters
MAX_POSITION_SIZE = 0.10       # max 10% of portfolio in any single stock
MAX_NEW_TRADE_SIZE = 0.02      # max 2% of portfolio per new entry
STOP_LOSS_PCT = 0.05           # 5% hard stop loss
MAX_SHORT_TERM_ALLOCATION = 0.30  # short-term agent controls at most 30% of portfolio

# Watchlists
LONG_TERM_WATCHLIST = [
    "AAPL", "MSFT", "GOOGL", "BRK.B", "JNJ",
    "VTI", "VOO", "QQQ", "VYM", "SCHD",
    "V", "MA", "UNH", "HD", "PG",
]

SHORT_TERM_WATCHLIST = [
    "NVDA", "AMD", "SMCI", "MARA", "RIOT",
    "PLTR", "IONQ", "RKLB", "ASTS", "LUNR",
    "COIN", "HOOD", "SOFI", "UPST", "AFRM",
]

MODEL = "claude-opus-4-7"
HISTORICAL_DAYS = 60

"""
Configuration file for data pipeline
"""

import os
from datetime import datetime, timedelta

# Load environment variables from .env file
try:
    from env_loader import load_env_file
    load_env_file()
except ImportError:
    pass

# API Configuration
ALPACA_API_KEY = os.getenv('ALPACA_API_KEY', '')
ALPACA_SECRET_KEY = os.getenv('ALPACA_SECRET_KEY', '')
ALPACA_BASE_URL = 'https://paper-api.alpaca.markets'  # Use paper trading URL for testing

BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
BINANCE_SECRET_KEY = os.getenv('BINANCE_SECRET_KEY', '')

# Data Configuration
DATA_ROOT = os.path.join(os.path.dirname(__file__), '..', 'data')
EQUITY_DATA_PATH = os.path.join(DATA_ROOT, 'equity', 'usa')
CRYPTO_DATA_PATH = os.path.join(DATA_ROOT, 'crypto', 'binance')
FUTURES_DATA_PATH = os.path.join(DATA_ROOT, 'futures', 'yahoo')
OPTIONS_DATA_PATH = os.path.join(DATA_ROOT, 'options', 'yahoo')

# Date Range Configuration
DEFAULT_START_DATE = datetime.now() - timedelta(days=365)  # 1 year of data
DEFAULT_END_DATE = datetime.now()

# Supported resolutions
SUPPORTED_RESOLUTIONS = ['tick', 'second', 'minute', 'hour', 'daily']

# Default symbols to download
DEFAULT_EQUITY_SYMBOLS = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'NVDA', 'AMZN', 'META', 'NFLX', 'SPY', 'QQQ']
DEFAULT_CRYPTO_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT', 'BNBUSDT', 'SOLUSDT', 'AVAXUSDT']
DEFAULT_FUTURES_SYMBOLS = ['ES=F', 'NQ=F', 'YM=F', 'RTY=F', 'CL=F', 'GC=F', 'SI=F', 'ZB=F', 'ZN=F', 'ZF=F']
DEFAULT_OPTIONS_UNDERLYINGS = ['SPY', 'QQQ', 'AAPL', 'TSLA', 'NVDA', 'MSFT']

# Lean format configuration
LEAN_TIME_FORMAT = "%Y%m%d"
LEAN_PRICE_MULTIPLIER = 10000  # Lean uses deci-cents for equity prices
LEAN_CRYPTO_PRICE_MULTIPLIER = 1  # Crypto uses actual prices

# Rate limiting
ALPACA_RATE_LIMIT = 200  # requests per minute
BINANCE_RATE_LIMIT = 1200  # requests per minute
YAHOO_RATE_LIMIT = 2000  # requests per minute (Yahoo is quite generous)

# Timezone configuration
LEAN_TIMEZONE_EQUITY = 'America/New_York'
LEAN_TIMEZONE_CRYPTO = 'UTC'

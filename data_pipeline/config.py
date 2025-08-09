"""
Configuration file for data pipeline
"""

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()

# API Configuration
ALPACA_API_KEY = os.getenv('ALPACA_API_KEY', '')
ALPACA_SECRET_KEY = os.getenv('ALPACA_SECRET_KEY', '')
ALPACA_BASE_URL = 'https://paper-api.alpaca.markets'  # Use paper trading URL for testing

BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
BINANCE_SECRET_KEY = os.getenv('BINANCE_SECRET_KEY', '')

# Polygon.io Configuration
POLYGON_API_KEY = os.getenv('POLYGON_API_KEY', '')

# Databento Configuration
DATA_BENTO_API_KEY = os.getenv('DATA_BENTO_API_KEY', '')
DATA_BENTO_USER_ID = os.getenv('DATA_BENTO_USER_ID', '')
DATA_BENTO_PROD_NAME = os.getenv('DATA_BENTO_PROD_NAME', 'prod-001')
# NQ (NASDAQ-100) API Configuration
NQ_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY', '')  # Alpha Vantage free tier

# Data Configuration
DATA_ROOT = os.path.join(os.path.dirname(__file__), '..', 'data')
EQUITY_DATA_PATH = os.path.join(DATA_ROOT, 'equity', 'usa')
CRYPTO_DATA_PATH = os.path.join(DATA_ROOT, 'crypto', 'binance')
OPTION_DATA_PATH = os.path.join(DATA_ROOT, 'option', 'usa')

# Date Range Configuration
DEFAULT_START_DATE = datetime.now() - timedelta(days=365)  # 1 year of data
DEFAULT_END_DATE = datetime.now()

# Supported resolutions
SUPPORTED_RESOLUTIONS = ['tick', 'second', 'minute', 'hour', 'daily']

# Default symbols to download
DEFAULT_EQUITY_SYMBOLS = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'NVDA', 'AMZN', 'META', 'NFLX', 'SPY', 'QQQ']
DEFAULT_CRYPTO_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT', 'BNBUSDT', 'SOLUSDT', 'AVAXUSDT']
DEFAULT_OPTION_SYMBOLS = ['SPY', 'QQQ', 'AAPL', 'TSLA', 'MSFT']  # Popular options symbols
DEFAULT_FUTURES_SYMBOLS = ['ES', 'CL', 'ZS']  # Working futures symbols (Polygon.io free tier)
DEFAULT_DATABENTO_FUTURES_SYMBOLS = ['ES.FUT', 'NQ.FUT', 'YM.FUT', 'RTY.FUT', 'CL.FUT', 'GC.FUT', 'SI.FUT', 'ZB.FUT', 'ZN.FUT', 'NG.FUT']  # Databento futures symbols

# NQ (NASDAQ-100) related symbols
NQ_SYMBOLS = [
    'QQQ',    # NASDAQ-100 ETF (primary proxy for NQ futures)
    'TQQQ',   # 3x Leveraged NASDAQ-100 ETF
    'SQQQ',   # 3x Inverse NASDAQ-100 ETF
    'QQQS',   # NASDAQ-100 Ex-Technology Sector Index ETF
    'QQQM',   # NASDAQ-100 ETF (lower expense ratio)
]

# Lean format configuration
LEAN_TIME_FORMAT = "%Y%m%d"
LEAN_PRICE_MULTIPLIER = 10000  # Lean uses deci-cents for equity prices
LEAN_CRYPTO_PRICE_MULTIPLIER = 1  # Crypto uses actual prices

# Rate limiting
ALPACA_RATE_LIMIT = 200  # requests per minute
BINANCE_RATE_LIMIT = 1200  # requests per minute
NQ_RATE_LIMIT = 5  # Alpha Vantage free tier: 5 requests per minute

# Timezone configuration
LEAN_TIMEZONE_EQUITY = 'America/New_York'
LEAN_TIMEZONE_CRYPTO = 'UTC'

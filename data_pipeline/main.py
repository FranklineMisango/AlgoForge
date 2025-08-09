"""
Main data pipeline script
"""

import argparse
import sys
from datetime import datetime, timedelta
from typing import List
import logging

# Setup logging first
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from config import (
    DEFAULT_EQUITY_SYMBOLS, DEFAULT_CRYPTO_SYMBOLS, NQ_SYMBOLS,
    DEFAULT_START_DATE, DEFAULT_END_DATE,
    SUPPORTED_RESOLUTIONS
)

# Import downloaders with error handling
try:
    from alpaca_downloader import AlpacaDataDownloader
    ALPACA_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Alpaca downloader not available: {e}")
    ALPACA_AVAILABLE = False

try:
    from binance_downloader import BinanceDataDownloader
    BINANCE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Binance downloader not available: {e}")
    BINANCE_AVAILABLE = False

try:
    from nq_downloader import NQDataDownloader
    NQ_AVAILABLE = True
except ImportError as e:
    logger.warning(f"NQ downloader not available: {e}")
    NQ_AVAILABLE = False

# Try to import utils, but continue if not available
try:
    from utils import setup_logging
    logger = setup_logging()
except ImportError:
    logger.warning("Utils module not available, using basic logging")

def parse_date(date_str: str) -> datetime:
    """Parse date string to datetime object"""
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: {date_str}. Use YYYY-MM-DD")

def main():
    parser = argparse.ArgumentParser(description='Download financial data and convert to Lean format')
    
    # Data source arguments
    parser.add_argument('--source', choices=['alpaca', 'binance', 'nq', 'both', 'all'], default='both',
                       help='Data source to download from (nq = NASDAQ-100 via free APIs)')
    
    # Symbol arguments
    parser.add_argument('--equity-symbols', nargs='+', default=DEFAULT_EQUITY_SYMBOLS,
                       help='Equity symbols to download (for Alpaca)')
    parser.add_argument('--crypto-symbols', nargs='+', default=DEFAULT_CRYPTO_SYMBOLS,
                       help='Crypto symbols to download (for Binance)')
    parser.add_argument('--nq-symbols', nargs='+', default=NQ_SYMBOLS,
                       help='NASDAQ-100 symbols to download (for NQ downloader)')
    
    # Date range arguments
    parser.add_argument('--start-date', type=parse_date, default=DEFAULT_START_DATE,
                       help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=parse_date, default=DEFAULT_END_DATE,
                       help='End date (YYYY-MM-DD)')
    
    # Resolution arguments
    parser.add_argument('--resolution', choices=SUPPORTED_RESOLUTIONS, default='minute',
                       help='Data resolution')
    
    # Other arguments
    parser.add_argument('--test', action='store_true',
                       help='Run in test mode with limited symbols and date range')
    
    args = parser.parse_args()
    
    # Test mode adjustments
    if args.test:
        args.equity_symbols = ['AAPL', 'GOOGL', 'MSFT'][:2]
        args.crypto_symbols = ['BTCUSDT', 'ETHUSDT'][:2]
        args.nq_symbols = ['QQQ', 'TQQQ'][:2]
        args.start_date = datetime.now() - timedelta(days=7)
        args.end_date = datetime.now()
        logger.info("Running in test mode with limited symbols and date range")
    
    # Validate date range
    if args.start_date >= args.end_date:
        logger.error("Start date must be before end date")
        sys.exit(1)
    
    logger.info(f"Starting data download from {args.start_date.strftime('%Y-%m-%d')} to {args.end_date.strftime('%Y-%m-%d')}")
    logger.info(f"Resolution: {args.resolution}")
    
    # Download equity data from Alpaca
    if args.source in ['alpaca', 'both', 'all']:
        if ALPACA_AVAILABLE:
            try:
                logger.info("Starting Alpaca data download...")
                alpaca_downloader = AlpacaDataDownloader()
                alpaca_downloader.download_multiple_symbols(
                    args.equity_symbols, 
                    args.resolution, 
                    args.start_date, 
                    args.end_date
                )
                logger.info("Alpaca download completed")
            except Exception as e:
                logger.error(f"Error with Alpaca download: {str(e)}")
                if args.source == 'alpaca':
                    sys.exit(1)
        else:
            logger.warning("Alpaca downloader not available - skipping")
            if args.source == 'alpaca':
                logger.error("Alpaca downloader requested but not available")
                sys.exit(1)
    
    # Download crypto data from Binance
    if args.source in ['binance', 'both', 'all']:
        if BINANCE_AVAILABLE:
            try:
                logger.info("Starting Binance data download...")
                binance_downloader = BinanceDataDownloader()
                binance_downloader.download_multiple_symbols(
                    args.crypto_symbols, 
                    args.resolution, 
                    args.start_date, 
                    args.end_date
                )
                logger.info("Binance download completed")
            except Exception as e:
                logger.error(f"Error with Binance download: {str(e)}")
                if args.source == 'binance':
                    sys.exit(1)
        else:
            logger.warning("Binance downloader not available - skipping")
            if args.source == 'binance':
                logger.error("Binance downloader requested but not available")
                sys.exit(1)
    
    # Download NQ data from free APIs
    if args.source in ['nq', 'all']:
        if NQ_AVAILABLE:
            try:
                logger.info("Starting NQ (NASDAQ-100) data download...")
                nq_downloader = NQDataDownloader()
                nq_downloader.download_multiple_symbols(
                    args.nq_symbols, 
                    args.resolution, 
                    args.start_date, 
                    args.end_date
                )
                logger.info("NQ download completed")
            except Exception as e:
                logger.error(f"Error with NQ download: {str(e)}")
                if args.source == 'nq':
                    sys.exit(1)
        else:
            logger.error("NQ downloader not available")
            if args.source == 'nq':
                sys.exit(1)
    
    logger.info("Data pipeline completed successfully!")

if __name__ == "__main__":
    main()

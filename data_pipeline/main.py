"""
Main data pipeline script
"""

import argparse
import sys
from datetime import datetime, timedelta
from typing import List

from config import (
    DEFAULT_EQUITY_SYMBOLS, DEFAULT_CRYPTO_SYMBOLS, DEFAULT_FUTURES_SYMBOLS, DEFAULT_OPTIONS_UNDERLYINGS,
    DEFAULT_START_DATE, DEFAULT_END_DATE,
    SUPPORTED_RESOLUTIONS
)
from utils import setup_logging

logger = setup_logging()

def parse_date(date_str: str) -> datetime:
    """Parse date string to datetime object"""
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: {date_str}. Use YYYY-MM-DD")

def main():
    parser = argparse.ArgumentParser(description='Download financial data and convert to Lean format')
    
    # Data source arguments
    parser.add_argument('--source', choices=['alpaca', 'binance', 'yahoo', 'all'], default='all',
                       help='Data source to download from')
    
    # Symbol arguments
    parser.add_argument('--equity-symbols', nargs='+', default=DEFAULT_EQUITY_SYMBOLS,
                       help='Equity symbols to download (for Alpaca)')
    parser.add_argument('--crypto-symbols', nargs='+', default=DEFAULT_CRYPTO_SYMBOLS,
                       help='Crypto symbols to download (for Binance)')
    parser.add_argument('--futures-symbols', nargs='+', default=DEFAULT_FUTURES_SYMBOLS,
                       help='Futures symbols to download (for Yahoo Finance)')
    parser.add_argument('--options-underlyings', nargs='+', default=DEFAULT_OPTIONS_UNDERLYINGS,
                       help='Options underlying symbols to download (for Yahoo Finance)')
    
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
        args.futures_symbols = ['ES=F', 'NQ=F'][:2]
        args.options_underlyings = ['SPY'][:1]
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
    if args.source in ['alpaca', 'all']:
        try:
            logger.info("Starting Alpaca data download...")
            from alpaca_downloader import AlpacaDataDownloader
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
    
    # Download crypto data from Binance
    if args.source in ['binance', 'all']:
        try:
            logger.info("Starting Binance data download...")
            from binance_downloader import BinanceDataDownloader
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
    
    # Download futures and options data from Yahoo Finance
    if args.source in ['yahoo', 'all']:
        try:
            logger.info("Starting Yahoo Finance data download...")
            from yahoo_downloader import YahooDataDownloader
            yahoo_downloader = YahooDataDownloader()
            
            # Download futures data
            if args.futures_symbols:
                logger.info("Downloading futures data...")
                yahoo_downloader.download_multiple_symbols(
                    args.futures_symbols, 
                    args.resolution, 
                    args.start_date, 
                    args.end_date,
                    'futures'
                )
            
            # Download options data (only for daily resolution as minute options data is limited)
            if args.options_underlyings and args.resolution == 'daily':
                logger.info("Downloading options data...")
                # For options, we'll download the underlying and get options chain info
                # Note: Minute-level options data is not typically available from free sources
                for underlying in args.options_underlyings:
                    try:
                        yahoo_downloader.download_symbol_data(
                            underlying, 
                            args.resolution, 
                            args.start_date, 
                            args.end_date,
                            'options'
                        )
                    except Exception as e:
                        logger.error(f"Error downloading options for {underlying}: {str(e)}")
            
            logger.info("Yahoo Finance download completed")
        except Exception as e:
            logger.error(f"Error with Yahoo Finance download: {str(e)}")
            if args.source == 'yahoo':
                sys.exit(1)
    
    logger.info("Data pipeline completed successfully!")

if __name__ == "__main__":
    main()

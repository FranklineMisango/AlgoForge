"""
Yahoo Finance data downloader for futures and options data in Lean format
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import pytz
import time
import os
from typing import List, Dict, Optional
from tqdm import tqdm

from config import (
    FUTURES_DATA_PATH, OPTIONS_DATA_PATH, LEAN_TIMEZONE_EQUITY, LEAN_TIME_FORMAT,
    YAHOO_RATE_LIMIT
)
from utils import (
    setup_logging, ensure_directory_exists, format_lean_date,
    create_lean_futures_csv, write_lean_zip_file, get_trading_days,
    DataValidator
)

logger = setup_logging()

class YahooDataDownloader:
    """Download futures and options data from Yahoo Finance and convert to Lean format"""
    
    def __init__(self):
        self.rate_limit_delay = 60 / YAHOO_RATE_LIMIT
        
    def get_bars(self, symbol: str, timeframe: str, start_date: datetime, end_date: datetime, asset_type: str = 'futures') -> List[Dict]:
        """Get bar data from Yahoo Finance"""
        try:
            # Convert timeframe to Yahoo Finance format
            yf_interval = self._convert_timeframe(timeframe)
            
            # Get data from Yahoo Finance
            ticker = yf.Ticker(symbol)
            
            # Download historical data
            hist = ticker.history(
                start=start_date.strftime('%Y-%m-%d'),
                end=end_date.strftime('%Y-%m-%d'),
                interval=yf_interval,
                auto_adjust=False,
                prepost=True
            )
            
            if hist.empty:
                logger.warning(f"No data returned for {symbol}")
                return []
            
            # Convert to our format
            data = []
            for timestamp, row in hist.iterrows():
                # Handle timezone for futures (usually trades in exchange timezone)
                if timestamp.tzinfo is None:
                    # Assume UTC for futures if no timezone info
                    timestamp = pytz.UTC.localize(timestamp)
                
                data.append({
                    'timestamp': timestamp.astimezone(pytz.timezone(LEAN_TIMEZONE_EQUITY)),
                    'open': float(row['Open']),
                    'high': float(row['High']),
                    'low': float(row['Low']),
                    'close': float(row['Close']),
                    'volume': int(row['Volume']) if pd.notna(row['Volume']) else 0
                })
            
            # Rate limiting
            time.sleep(self.rate_limit_delay)
            
            return data
            
        except Exception as e:
            logger.error(f"Error getting bars for {symbol}: {str(e)}")
            return []
    
    def _convert_timeframe(self, timeframe: str) -> str:
        """Convert resolution to Yahoo Finance interval"""
        timeframe_map = {
            'minute': '1m',
            '5minute': '5m',
            '15minute': '15m',
            '30minute': '30m',
            'hour': '1h',
            'daily': '1d',
            'weekly': '1wk',
            'monthly': '1mo'
        }
        
        return timeframe_map.get(timeframe, '1m')
    
    def download_symbol_data(self, symbol: str, resolution: str, start_date: datetime, end_date: datetime, asset_type: str = 'futures'):
        """Download and save data for a single symbol"""
        logger.info(f"Downloading {symbol} {asset_type} data for {resolution} resolution")
        
        # Choose appropriate data path based on asset type
        base_path = FUTURES_DATA_PATH if asset_type == 'futures' else OPTIONS_DATA_PATH
        
        if resolution == 'daily' or resolution == 'hour':
            # For daily/hour, save all data in one file
            data = self.get_bars(symbol, resolution, start_date, end_date, asset_type)
            
            if data:
                # Clean and validate data
                cleaned_data = DataValidator.clean_ohlcv_data(data)
                
                if cleaned_data:
                    output_path = os.path.join(base_path, resolution, f"{symbol.lower()}.zip")
                    csv_filename = f"{symbol.lower()}_{resolution}_trade.csv"
                    
                    # Group data by date for processing
                    daily_data = {}
                    for bar in cleaned_data:
                        date_key = bar['timestamp'].strftime(LEAN_TIME_FORMAT)
                        if date_key not in daily_data:
                            daily_data[date_key] = []
                        daily_data[date_key].append(bar)
                    
                    # Create CSV content for all dates
                    all_csv_content = []
                    for date_key in sorted(daily_data.keys()):
                        date_bars = daily_data[date_key]
                        csv_content = create_lean_futures_csv(date_bars, symbol, date_bars[0]['timestamp'], resolution, asset_type)
                        all_csv_content.extend(csv_content)
                    
                    if all_csv_content:
                        write_lean_zip_file(all_csv_content, output_path, csv_filename)
                        logger.info(f"Saved {len(all_csv_content)} bars for {symbol} {resolution}")
        
        else:
            # For minute/second, save data by date
            trading_days = get_trading_days(start_date, end_date)
            
            for date in tqdm(trading_days, desc=f"Downloading {symbol} {resolution}"):
                date_start = date.replace(hour=0, minute=0, second=0)
                date_end = date.replace(hour=23, minute=59, second=59)
                
                data = self.get_bars(symbol, resolution, date_start, date_end, asset_type)
                
                if data:
                    # Clean and validate data
                    cleaned_data = DataValidator.clean_ohlcv_data(data)
                    
                    if cleaned_data:
                        # Create directory structure
                        symbol_dir = os.path.join(base_path, resolution, symbol.lower())
                        ensure_directory_exists(symbol_dir)
                        
                        # Create file paths
                        date_str = format_lean_date(date)
                        output_path = os.path.join(symbol_dir, f"{date_str}_trade.zip")
                        csv_filename = f"{date_str}_{symbol.lower()}_{resolution}_trade.csv"
                        
                        # Convert to Lean format
                        csv_content = create_lean_futures_csv(cleaned_data, symbol, date, resolution, asset_type)
                        
                        if csv_content:
                            write_lean_zip_file(csv_content, output_path, csv_filename)
                            logger.debug(f"Saved {len(csv_content)} bars for {symbol} on {date_str}")
                
                # Rate limiting
                time.sleep(self.rate_limit_delay)
    
    def download_multiple_symbols(self, symbols: List[str], resolution: str, start_date: datetime, end_date: datetime, asset_type: str = 'futures'):
        """Download data for multiple symbols"""
        logger.info(f"Starting download for {len(symbols)} {asset_type} symbols")
        
        for symbol in tqdm(symbols, desc=f"Downloading {asset_type} symbols"):
            try:
                self.download_symbol_data(symbol, resolution, start_date, end_date, asset_type)
            except Exception as e:
                logger.error(f"Error downloading {symbol}: {str(e)}")
                continue
        
        logger.info("Download completed")
    
    def get_futures_info(self, symbol: str) -> Dict:
        """Get futures contract information"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            return {
                'symbol': symbol,
                'name': info.get('shortName', symbol),
                'exchange': info.get('exchange', 'Unknown'),
                'currency': info.get('currency', 'USD'),
                'contract_size': info.get('contractSize', 1),
                'tick_size': info.get('tickSize', 0.01),
                'expiry_date': info.get('expiryDate', None)
            }
        except Exception as e:
            logger.error(f"Error getting info for {symbol}: {str(e)}")
            return {'symbol': symbol}
    
    def get_options_chain(self, underlying_symbol: str, expiry_date: str = None) -> Dict:
        """Get options chain for an underlying symbol"""
        try:
            ticker = yf.Ticker(underlying_symbol)
            
            if expiry_date:
                options = ticker.option_chain(expiry_date)
            else:
                # Get first available expiry
                expirations = ticker.options
                if expirations:
                    options = ticker.option_chain(expirations[0])
                else:
                    return {}
            
            return {
                'calls': options.calls.to_dict('records'),
                'puts': options.puts.to_dict('records'),
                'underlying': underlying_symbol,
                'expiry': expiry_date
            }
            
        except Exception as e:
            logger.error(f"Error getting options chain for {underlying_symbol}: {str(e)}")
            return {}

def main():
    """Main function for testing"""
    from config import DEFAULT_FUTURES_SYMBOLS, DEFAULT_START_DATE, DEFAULT_END_DATE
    
    downloader = YahooDataDownloader()
    
    # Test with a small set of futures symbols
    test_symbols = ['ES=F', 'NQ=F', 'CL=F']  # S&P 500, NASDAQ, Crude Oil futures
    test_start = datetime.now() - timedelta(days=30)
    test_end = datetime.now()
    
    # Download minute data
    downloader.download_multiple_symbols(test_symbols, 'minute', test_start, test_end, 'futures')
    
    # Download daily data
    downloader.download_multiple_symbols(test_symbols, 'daily', test_start, test_end, 'futures')

if __name__ == "__main__":
    main()
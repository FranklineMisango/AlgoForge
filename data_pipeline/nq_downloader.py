"""
NQ (NASDAQ-100) data downloader using free APIs
"""

import requests
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import os

from config import (
    EQUITY_DATA_PATH, LEAN_TIMEZONE_EQUITY, LEAN_TIME_FORMAT,
    NQ_API_KEY, NQ_RATE_LIMIT, NQ_SYMBOLS
)

# Simplified logging for compatibility
import logging
logger = logging.getLogger(__name__)

def setup_logging_simple():
    """Simple logging setup"""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    return logging.getLogger(__name__)

def ensure_directory_exists_simple(path: str):
    """Simple directory creation"""
    os.makedirs(path, exist_ok=True)

class SimpleProgressBar:
    """Simple progress indicator to replace tqdm"""
    def __init__(self, items, desc="Processing"):
        self.items = items
        self.desc = desc
        self.total = len(items)
        self.current = 0
    
    def __iter__(self):
        for item in self.items:
            self.current += 1
            print(f"{self.desc}: {self.current}/{self.total} - {item}")
            yield item

class NQDataDownloader:
    """Download NASDAQ-100 related data from free APIs"""
    
    def __init__(self):
        self.rate_limit_delay = 60 / NQ_RATE_LIMIT
        self.base_url_av = "https://www.alphavantage.co/query"
        self.logger = setup_logging_simple()
        
    def get_alpha_vantage_data(self, symbol: str, api_key: str, interval: str = "1min") -> List[Dict]:
        """Get minute data from Alpha Vantage free API"""
        try:
            params = {
                'function': 'TIME_SERIES_INTRADAY',
                'symbol': symbol,
                'interval': interval,
                'apikey': api_key,
                'outputsize': 'full',
                'datatype': 'json'
            }
            
            response = requests.get(self.base_url_av, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Check for API error
            if 'Error Message' in data:
                self.logger.error(f"Alpha Vantage API error: {data['Error Message']}")
                return []
            
            if 'Note' in data:
                self.logger.warning(f"Alpha Vantage rate limit: {data['Note']}")
                time.sleep(60)  # Wait 60 seconds on rate limit
                return []
            
            # Extract time series data
            time_series_key = f'Time Series ({interval})'
            if time_series_key not in data:
                self.logger.error(f"Expected key '{time_series_key}' not found in response")
                return []
            
            time_series = data[time_series_key]
            
            # Convert to our format
            bars = []
            for timestamp_str, values in time_series.items():
                try:
                    # Parse timestamp (format: "2023-12-01 16:00:00")
                    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                    
                    bar = {
                        'timestamp': timestamp,
                        'open': float(values['1. open']),
                        'high': float(values['2. high']),
                        'low': float(values['3. low']),
                        'close': float(values['4. close']),
                        'volume': int(values['5. volume'])
                    }
                    bars.append(bar)
                except (ValueError, KeyError) as e:
                    self.logger.debug(f"Skipping invalid bar data: {e}")
                    continue
            
            # Sort by timestamp (oldest first)
            bars.sort(key=lambda x: x['timestamp'])
            
            self.logger.info(f"Retrieved {len(bars)} bars for {symbol} from Alpha Vantage")
            return bars
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching data from Alpha Vantage: {e}")
            return []
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing Alpha Vantage response: {e}")
            return []
    
    def get_yahoo_finance_data(self, symbol: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get data from Yahoo Finance using their public API"""
        try:
            # Convert dates to timestamps
            start_timestamp = int(start_date.timestamp())
            end_timestamp = int(end_date.timestamp())
            
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
            params = {
                'period1': start_timestamp,
                'period2': end_timestamp,
                'interval': '1m',
                'includePrePost': 'false',
                'events': 'div,splits'
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if 'chart' not in data or not data['chart']['result']:
                self.logger.error(f"No data found for {symbol}")
                return []
            
            result = data['chart']['result'][0]
            
            # Extract data
            timestamps = result['timestamp']
            indicators = result['indicators']['quote'][0]
            
            bars = []
            for i, ts in enumerate(timestamps):
                try:
                    # Skip if any required data is None
                    if (indicators['open'][i] is None or 
                        indicators['high'][i] is None or 
                        indicators['low'][i] is None or 
                        indicators['close'][i] is None or
                        indicators['volume'][i] is None):
                        continue
                    
                    timestamp = datetime.fromtimestamp(ts)
                    
                    bar = {
                        'timestamp': timestamp,
                        'open': float(indicators['open'][i]),
                        'high': float(indicators['high'][i]),
                        'low': float(indicators['low'][i]),
                        'close': float(indicators['close'][i]),
                        'volume': int(indicators['volume'][i])
                    }
                    bars.append(bar)
                except (ValueError, TypeError, IndexError) as e:
                    self.logger.debug(f"Skipping invalid bar data at index {i}: {e}")
                    continue
            
            self.logger.info(f"Retrieved {len(bars)} bars for {symbol} from Yahoo Finance")
            return bars
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching data from Yahoo Finance: {e}")
            return []
        except (json.JSONDecodeError, KeyError) as e:
            self.logger.error(f"Error parsing Yahoo Finance response: {e}")
            return []
    
    def get_bars(self, symbol: str, resolution: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get bar data using available free APIs"""
        all_bars = []
        
        # Try Alpha Vantage first if API key is available
        if NQ_API_KEY:
            interval_map = {
                'minute': '1min',
                'hour': '60min',
                'daily': 'daily'
            }
            interval = interval_map.get(resolution, '1min')
            bars = self.get_alpha_vantage_data(symbol, NQ_API_KEY, interval)
            if bars:
                # Filter by date range for Alpha Vantage data
                filtered_bars = [
                    bar for bar in bars 
                    if start_date <= bar['timestamp'] <= end_date
                ]
                all_bars.extend(filtered_bars)
        
        # If no Alpha Vantage data or no API key, try Yahoo Finance for minute data
        if not all_bars and resolution == 'minute':
            bars = self.get_yahoo_finance_data(symbol, start_date, end_date)
            all_bars.extend(bars)
        
        # Rate limiting
        time.sleep(self.rate_limit_delay)
        
        return all_bars
    
    def validate_ohlcv_data_simple(self, data: Dict) -> bool:
        """Simple OHLCV validation without external dependencies"""
        required_fields = ['open', 'high', 'low', 'close', 'volume', 'timestamp']
        
        for field in required_fields:
            if field not in data:
                return False
        
        # Validate OHLC logic
        if not (data['low'] <= data['open'] <= data['high'] and 
                data['low'] <= data['close'] <= data['high']):
            return False
        
        # Validate volume is non-negative
        if data['volume'] < 0:
            return False
        
        return True
    
    def clean_ohlcv_data_simple(self, data: List[Dict]) -> List[Dict]:
        """Simple data cleaning without external dependencies"""
        cleaned_data = []
        
        for bar in data:
            if self.validate_ohlcv_data_simple(bar):
                cleaned_data.append(bar)
        
        return cleaned_data
    
    def create_lean_csv_simple(self, data: List[Dict], symbol: str, resolution: str) -> List[str]:
        """Create simple CSV lines for LEAN format"""
        csv_lines = []
        
        for bar in data:
            if resolution == 'daily':
                # For daily data, use full date format YYYYMMDD HH:MM
                time_str = bar['timestamp'].strftime("%Y%m%d %H:%M")
            else:
                # For intraday data, use milliseconds since midnight
                midnight = bar['timestamp'].replace(hour=0, minute=0, second=0, microsecond=0)
                delta = bar['timestamp'] - midnight
                time_str = int(delta.total_seconds() * 1000)
            
            # Format: Time, Open, High, Low, Close, Volume
            line = f"{time_str},{int(bar['open'] * 10000)},{int(bar['high'] * 10000)},{int(bar['low'] * 10000)},{int(bar['close'] * 10000)},{int(bar['volume'])}"
            csv_lines.append(line)
        
        return csv_lines
    
    def save_data_simple(self, csv_lines: List[str], output_path: str):
        """Simple data saving without zip compression"""
        ensure_directory_exists_simple(os.path.dirname(output_path))
        
        with open(output_path, 'w') as f:
            for line in csv_lines:
                f.write(line + '\n')
    
    def download_symbol_data(self, symbol: str, resolution: str, start_date: datetime, end_date: datetime):
        """Download and save data for a single NQ-related symbol"""
        self.logger.info(f"Downloading {symbol} NQ data for {resolution} resolution")
        
        # For testing, limit to 7 days for Yahoo Finance API
        if resolution == 'minute':
            chunk_days = 7
            current_start = start_date
            
            while current_start <= end_date:
                chunk_end = min(current_start + timedelta(days=chunk_days), end_date)
                
                self.logger.info(f"Downloading {symbol} from {current_start.strftime('%Y-%m-%d')} to {chunk_end.strftime('%Y-%m-%d')}")
                
                data = self.get_bars(symbol, resolution, current_start, chunk_end)
                
                if data:
                    # Clean and validate data
                    cleaned_data = self.clean_ohlcv_data_simple(data)
                    
                    if cleaned_data:
                        # Create CSV content
                        csv_lines = self.create_lean_csv_simple(cleaned_data, symbol, resolution)
                        
                        if csv_lines:
                            # Create output path
                            date_str = current_start.strftime("%Y%m%d")
                            output_dir = os.path.join(EQUITY_DATA_PATH, resolution, 'nq')
                            ensure_directory_exists_simple(output_dir)
                            output_path = os.path.join(output_dir, f"{symbol.lower()}_{date_str}_{resolution}.csv")
                            
                            # Save data
                            self.save_data_simple(csv_lines, output_path)
                            self.logger.info(f"Saved {len(csv_lines)} bars for {symbol} to {output_path}")
                
                current_start = chunk_end + timedelta(days=1)
                time.sleep(self.rate_limit_delay * 2)  # Extra delay between chunks
        else:
            # For daily/hourly data
            data = self.get_bars(symbol, resolution, start_date, end_date)
            
            if data:
                cleaned_data = self.clean_ohlcv_data_simple(data)
                
                if cleaned_data:
                    csv_lines = self.create_lean_csv_simple(cleaned_data, symbol, resolution)
                    
                    if csv_lines:
                        output_dir = os.path.join(EQUITY_DATA_PATH, resolution, 'nq')
                        ensure_directory_exists_simple(output_dir)
                        output_path = os.path.join(output_dir, f"{symbol.lower()}_{resolution}.csv")
                        
                        self.save_data_simple(csv_lines, output_path)
                        self.logger.info(f"Saved {len(csv_lines)} bars for {symbol} to {output_path}")
    
    def download_multiple_symbols(self, symbols: List[str], resolution: str, start_date: datetime, end_date: datetime):
        """Download data for multiple NQ-related symbols"""
        self.logger.info(f"Starting NQ download for {len(symbols)} symbols")
        
        progress = SimpleProgressBar(symbols, "Downloading NQ symbols")
        for symbol in progress:
            try:
                self.download_symbol_data(symbol, resolution, start_date, end_date)
            except Exception as e:
                self.logger.error(f"Error downloading {symbol}: {str(e)}")
                continue
        
        self.logger.info("NQ download completed")

def main():
    """Main function for testing"""
    # Test with NQ-related symbols
    test_symbols = ['QQQ', 'TQQQ', 'SQQQ']  # NASDAQ-100 ETF and leveraged versions
    test_start = datetime.now() - timedelta(days=7)
    test_end = datetime.now()
    
    downloader = NQDataDownloader()
    
    # Download minute data
    downloader.download_multiple_symbols(test_symbols, 'minute', test_start, test_end)

if __name__ == "__main__":
    main()
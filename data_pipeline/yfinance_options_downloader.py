"""
Alternative Options Data Downloader using yfinance (free, no API key required)
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from tqdm import tqdm
import time
from typing import List, Dict, Any, Optional
import yfinance as yf

from config import (
    OPTION_DATA_PATH, 
    LEAN_PRICE_MULTIPLIER,
    DEFAULT_OPTION_SYMBOLS
)
from utils import ensure_directory_exists, setup_logging


class YFinanceOptionsDownloader:
    """Download options data using yfinance (free, no API key required)"""
    
    def __init__(self):
        self.data_path = OPTION_DATA_PATH
        self.logger = setup_logging()
        
    def get_options_expirations(self, symbol: str) -> List[str]:
        """Get available options expiration dates for a symbol"""
        try:
            ticker = yf.Ticker(symbol)
            
            # Add a small delay to avoid rate limiting
            time.sleep(0.5)
            
            # Get options expirations with error handling
            expirations = ticker.options
            if not expirations:
                self.logger.warning(f"No options available for {symbol}")
                return []
            
            return list(expirations)
        except Exception as e:
            self.logger.error(f"Error getting options expirations for {symbol}: {e}")
            # Try alternative approach
            try:
                # Sometimes yfinance needs a different approach
                ticker = yf.Ticker(symbol)
                info = ticker.info
                if info.get('symbol'):
                    # Try to get at least some basic info
                    self.logger.info(f"Symbol {symbol} exists but options may not be available")
                return []
            except:
                self.logger.error(f"Symbol {symbol} may not exist or have options")
                return []
    
    def get_options_chain(self, symbol: str, expiration: str) -> Dict:
        """Get options chain for a specific expiration"""
        try:
            ticker = yf.Ticker(symbol)
            
            # Add delay to avoid rate limiting
            time.sleep(0.5)
            
            opt_chain = ticker.option_chain(expiration)
            
            return {
                'calls': opt_chain.calls,
                'puts': opt_chain.puts,
                'expiration': expiration
            }
        except Exception as e:
            self.logger.error(f"Error getting options chain for {symbol} {expiration}: {e}")
            return {}
    
    def format_options_data_for_lean(self, options_df: pd.DataFrame, 
                                   symbol: str, expiration: str, option_type: str) -> List[Dict]:
        """Format options data for Lean and create historical data"""
        contracts = []
        
        if options_df.empty:
            return contracts
        
        # Get current date
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        for _, row in options_df.iterrows():
            try:
                strike = float(row['strike'])
                last_price = float(row.get('lastPrice', 0))
                volume = int(row.get('volume', 0)) if not pd.isna(row.get('volume', 0)) else 0
                open_interest = int(row.get('openInterest', 0)) if not pd.isna(row.get('openInterest', 0)) else 0
                
                # Create a simple OHLC record (yfinance only gives us last price)
                # For demo purposes, we'll create OHLC around the last price
                if last_price > 0:
                    # Simple OHLC estimation (not real historical data)
                    open_price = last_price * 0.98
                    high_price = last_price * 1.02
                    low_price = last_price * 0.96
                    close_price = last_price
                    
                    contract_data = {
                        'symbol': symbol,
                        'expiration': expiration,
                        'option_type': option_type,
                        'strike': strike,
                        'date': current_date,
                        'open': int(open_price * LEAN_PRICE_MULTIPLIER),
                        'high': int(high_price * LEAN_PRICE_MULTIPLIER),
                        'low': int(low_price * LEAN_PRICE_MULTIPLIER),
                        'close': int(close_price * LEAN_PRICE_MULTIPLIER),
                        'volume': volume,
                        'openinterest': open_interest
                    }
                    
                    contracts.append(contract_data)
                    
            except Exception as e:
                self.logger.warning(f"Error processing options contract: {e}")
                continue
        
        return contracts
    
    def get_lean_filepath(self, symbol: str, expiration: str, option_type: str, strike: float) -> str:
        """Generate file path for Lean format"""
        symbol_lower = symbol.lower()
        
        # Convert expiration date format
        exp_date = datetime.strptime(expiration, '%Y-%m-%d')
        exp_str = exp_date.strftime('%Y%m%d')
        
        # Create directory structure: option/usa/daily/symbol/
        directory = os.path.join(self.data_path, 'daily', symbol_lower)
        ensure_directory_exists(directory)
        
        # File naming: symbol_expiration_type_strike.csv
        # Example: spy_20241220_call_00500000.csv
        filename = f"{symbol_lower}_{exp_str}_{option_type}_{int(strike * 1000):08d}.csv"
        
        return os.path.join(directory, filename)
    
    def save_contract_data(self, contract_data: Dict):
        """Save individual contract data to file"""
        filepath = self.get_lean_filepath(
            contract_data['symbol'],
            contract_data['expiration'],
            contract_data['option_type'],
            contract_data['strike']
        )
        
        # Create CSV row for Lean format
        csv_row = [
            contract_data['open'],
            contract_data['high'],
            contract_data['low'],
            contract_data['close'],
            contract_data['volume'],
            contract_data['openinterest']
        ]
        
        # Save to file
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Check if file exists and append or create
        if os.path.exists(filepath):
            # For now, just overwrite (in real scenario, you'd append new dates)
            pass
            
        with open(filepath, 'w') as f:
            f.write(','.join(map(str, csv_row)) + '\n')
        
        self.logger.debug(f"Saved contract: {os.path.basename(filepath)}")
    
    def download_options_for_symbol(self, symbol: str, max_expirations: int = 3, 
                                   max_contracts_per_expiration: int = 20):
        """Download options data for a single symbol"""
        self.logger.info(f"Downloading options for {symbol}")
        
        # Get available expirations
        expirations = self.get_options_expirations(symbol)
        
        if not expirations:
            self.logger.warning(f"No options expirations found for {symbol}")
            return
        
        # Limit to recent expirations
        expirations = expirations[:max_expirations]
        self.logger.info(f"Found {len(expirations)} expirations for {symbol}")
        
        total_contracts = 0
        
        for expiration in expirations:
            try:
                self.logger.info(f"Processing {symbol} expiration: {expiration}")
                
                # Get options chain
                chain_data = self.get_options_chain(symbol, expiration)
                
                if not chain_data:
                    continue
                
                # Process calls
                if 'calls' in chain_data and not chain_data['calls'].empty:
                    calls_df = chain_data['calls'].head(max_contracts_per_expiration)
                    call_contracts = self.format_options_data_for_lean(
                        calls_df, symbol, expiration, 'call'
                    )
                    
                    for contract in call_contracts:
                        self.save_contract_data(contract)
                        total_contracts += 1
                
                # Process puts
                if 'puts' in chain_data and not chain_data['puts'].empty:
                    puts_df = chain_data['puts'].head(max_contracts_per_expiration)
                    put_contracts = self.format_options_data_for_lean(
                        puts_df, symbol, expiration, 'put'
                    )
                    
                    for contract in put_contracts:
                        self.save_contract_data(contract)
                        total_contracts += 1
                
                # Small delay between expirations
                time.sleep(0.5)
                
            except Exception as e:
                self.logger.error(f"Error processing {symbol} expiration {expiration}: {e}")
                continue
        
        self.logger.info(f"Downloaded {total_contracts} contracts for {symbol}")
    
    def download_symbols(self, symbols: List[str]):
        """Download options data for multiple symbols"""
        self.logger.info(f"Starting options download for {len(symbols)} symbols")
        
        for symbol in tqdm(symbols, desc="Downloading options"):
            try:
                self.download_options_for_symbol(symbol)
                # Small delay between symbols
                time.sleep(1)
            except Exception as e:
                self.logger.error(f"Error downloading options for {symbol}: {e}")
                continue
        
        self.logger.info("Options download completed")


def main():
    """Main function for testing"""
    downloader = YFinanceOptionsDownloader()
    
    # Test with a single symbol
    downloader.download_symbols(['SPY'])


if __name__ == "__main__":
    main()

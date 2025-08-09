#!/usr/bin/env python3
"""
NQ Downloader Demo - Shows NQ functionality with mock data when APIs are unavailable
"""

import os
import sys
from datetime import datetime, timedelta

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_mock_nq_data():
    """Create mock NQ data to demonstrate the functionality"""
    from nq_downloader import NQDataDownloader
    
    print("NQ Data Downloader Demo")
    print("=" * 40)
    
    # Initialize downloader
    downloader = NQDataDownloader()
    print("✓ NQ downloader initialized")
    
    # Create mock data
    mock_data = []
    base_time = datetime(2024, 1, 15, 9, 30)  # Market open time
    base_price = 382.50  # Typical QQQ price
    
    for i in range(10):  # Create 10 minutes of data
        timestamp = base_time + timedelta(minutes=i)
        price_change = (i % 3 - 1) * 0.25  # Small price movements
        
        bar = {
            'timestamp': timestamp,
            'open': base_price + price_change,
            'high': base_price + price_change + 0.15,
            'low': base_price + price_change - 0.10,
            'close': base_price + price_change + 0.05,
            'volume': 1000000 + i * 50000
        }
        mock_data.append(bar)
    
    print(f"✓ Created {len(mock_data)} mock data bars")
    
    # Test data validation
    cleaned_data = downloader.clean_ohlcv_data_simple(mock_data)
    print(f"✓ Data validation passed: {len(cleaned_data)}/{len(mock_data)} bars valid")
    
    # Test CSV conversion
    csv_lines = downloader.create_lean_csv_simple(cleaned_data, 'QQQ', 'minute')
    print(f"✓ CSV conversion successful: {len(csv_lines)} lines")
    
    # Show sample data
    print("\nSample Mock Data:")
    print("Timestamp           | Open    | High    | Low     | Close   | Volume")
    print("-" * 70)
    for i, bar in enumerate(mock_data[:3]):
        print(f"{bar['timestamp'].strftime('%Y-%m-%d %H:%M')} | "
              f"{bar['open']:7.2f} | {bar['high']:7.2f} | "
              f"{bar['low']:7.2f} | {bar['close']:7.2f} | {bar['volume']:8d}")
    
    print("\nSample LEAN CSV Format:")
    print("Time(ms), Open, High, Low, Close, Volume")
    print("-" * 50)
    for line in csv_lines[:3]:
        print(line)
    
    # Test file saving
    test_output_dir = "../data/equity/usa/minute/nq"
    os.makedirs(test_output_dir, exist_ok=True)
    test_file = os.path.join(test_output_dir, "qqq_demo_minute.csv")
    
    downloader.save_data_simple(csv_lines, test_file)
    print(f"\n✓ Demo data saved to: {test_file}")
    
    # Verify file was created
    if os.path.exists(test_file):
        file_size = os.path.getsize(test_file)
        print(f"✓ File verification passed: {file_size} bytes")
        
        # Show file content
        with open(test_file, 'r') as f:
            content = f.read()
            print(f"\nActual file content (first 200 chars):")
            print(content[:200] + "..." if len(content) > 200 else content)
    
    return True

def test_nq_configuration():
    """Test NQ configuration and show available symbols"""
    from config import NQ_SYMBOLS, NQ_RATE_LIMIT
    
    print("\nNQ Configuration:")
    print("-" * 20)
    print(f"Available NQ symbols: {NQ_SYMBOLS}")
    print(f"Rate limit: {NQ_RATE_LIMIT} requests/minute")
    print(f"Symbol count: {len(NQ_SYMBOLS)}")
    
    # Show symbol descriptions
    symbol_descriptions = {
        'QQQ': 'NASDAQ-100 ETF (primary NQ proxy)',
        'TQQQ': '3x Leveraged NASDAQ-100 ETF',
        'SQQQ': '3x Inverse NASDAQ-100 ETF',
        'QQQS': 'NASDAQ-100 Ex-Technology Sector ETF',
        'QQQM': 'NASDAQ-100 ETF (lower fees)'
    }
    
    print("\nSymbol Details:")
    for symbol in NQ_SYMBOLS:
        desc = symbol_descriptions.get(symbol, 'NASDAQ-100 related instrument')
        print(f"  {symbol}: {desc}")

def show_usage_examples():
    """Show practical usage examples"""
    print("\nUsage Examples:")
    print("-" * 20)
    
    examples = [
        ("Download NQ data with minute granularity (basic)", 
         "python main.py --source nq --resolution minute"),
        
        ("Test mode with limited data", 
         "python main.py --source nq --resolution minute --test"),
        
        ("Specific symbols and date range", 
         "python main.py --source nq --nq-symbols QQQ TQQQ --resolution minute --start-date 2024-01-01 --end-date 2024-01-31"),
        
        ("Include NQ with all other sources", 
         "python main.py --source all --resolution minute"),
        
        ("Daily granularity for longer history", 
         "python main.py --source nq --resolution daily --start-date 2023-01-01 --end-date 2024-01-01"),
    ]
    
    for i, (description, command) in enumerate(examples, 1):
        print(f"\n{i}. {description}:")
        print(f"   {command}")

def main():
    try:
        # Test mock data functionality
        if create_mock_nq_data():
            print("\n" + "=" * 50)
            print("✓ NQ Downloader Demo Completed Successfully!")
            
            # Show configuration
            test_nq_configuration()
            
            # Show usage examples
            show_usage_examples()
            
            print("\n" + "=" * 50)
            print("Next Steps:")
            print("1. Set up Alpha Vantage API key (optional): export ALPHA_VANTAGE_API_KEY=your_key")
            print("2. Run: python main.py --source nq --test")
            print("3. Check output in: ../data/equity/usa/minute/nq/")
            print("4. Use data with LEAN for backtesting")
            
        else:
            print("Demo failed")
            
    except Exception as e:
        print(f"Demo error: {e}")
        return False

if __name__ == "__main__":
    main()
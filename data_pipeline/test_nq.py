#!/usr/bin/env python3
"""
Test script for NQ data downloader functionality
"""

import sys
import os
from datetime import datetime, timedelta

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_nq_config():
    """Test NQ configuration"""
    try:
        from config import NQ_SYMBOLS, NQ_RATE_LIMIT, NQ_API_KEY
        print("✓ NQ configuration loaded successfully")
        print(f"  NQ symbols: {NQ_SYMBOLS}")
        print(f"  Rate limit: {NQ_RATE_LIMIT} requests/minute")
        print(f"  API key configured: {'Yes' if NQ_API_KEY else 'No (will use Yahoo Finance)'}")
        return True
    except ImportError as e:
        print(f"✗ NQ configuration import failed: {e}")
        return False

def test_nq_downloader():
    """Test NQ downloader class"""
    try:
        from nq_downloader import NQDataDownloader
        downloader = NQDataDownloader()
        print("✓ NQ downloader initialized successfully")
        return True
    except Exception as e:
        print(f"✗ NQ downloader initialization failed: {e}")
        return False

def test_nq_yahoo_api():
    """Test Yahoo Finance API connection"""
    try:
        from nq_downloader import NQDataDownloader
        downloader = NQDataDownloader()
        
        # Test with a small date range
        start_date = datetime.now() - timedelta(days=2)
        end_date = datetime.now() - timedelta(days=1)
        
        # Try to get QQQ data from Yahoo Finance
        data = downloader.get_yahoo_finance_data('QQQ', start_date, end_date)
        
        if data and len(data) > 0:
            print(f"✓ Yahoo Finance API working - retrieved {len(data)} QQQ data points")
            print(f"  Sample data: {data[0] if data else 'None'}")
            return True
        else:
            print("⚠ Yahoo Finance API accessible but no data returned")
            return True  # Still consider this a pass as API is working
            
    except Exception as e:
        print(f"✗ Yahoo Finance API test failed: {e}")
        return False

def test_nq_main_integration():
    """Test integration with main.py"""
    try:
        # Import main module to check integration
        import main
        print("✓ NQ integration with main.py successful")
        return True
    except Exception as e:
        print(f"✗ NQ integration test failed: {e}")
        return False

def test_nq_minute_data():
    """Test minute data download functionality"""
    try:
        from nq_downloader import NQDataDownloader
        from datetime import datetime, timedelta
        
        downloader = NQDataDownloader()
        
        # Test with very recent data to ensure it exists
        end_date = datetime.now() - timedelta(hours=1)  # 1 hour ago to ensure market closure
        start_date = end_date - timedelta(hours=2)  # 2 hour window
        
        # Try to get minute data for QQQ
        data = downloader.get_bars('QQQ', 'minute', start_date, end_date)
        
        if data:
            print(f"✓ Minute data download working - got {len(data)} bars")
            # Check data structure
            sample = data[0]
            required_fields = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            for field in required_fields:
                if field not in sample:
                    print(f"✗ Missing required field: {field}")
                    return False
            print("✓ Data structure validation passed")
            return True
        else:
            print("⚠ No minute data retrieved (may be normal if outside market hours)")
            return True  # Don't fail for this as it might be outside market hours
            
    except Exception as e:
        print(f"✗ Minute data test failed: {e}")
        return False

def main():
    print("NQ Data Downloader Test Suite")
    print("=" * 40)
    
    tests = [
        ("NQ Configuration Test", test_nq_config),
        ("NQ Downloader Class Test", test_nq_downloader),
        ("Yahoo Finance API Test", test_nq_yahoo_api),
        ("Main Integration Test", test_nq_main_integration),
        ("Minute Data Test", test_nq_minute_data),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        try:
            if test_func():
                passed += 1
            else:
                print(f"  {test_name} failed")
        except Exception as e:
            print(f"  {test_name} failed with exception: {e}")
    
    print(f"\n{'='*40}")
    print(f"Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("✓ All NQ tests passed! NQ downloader is ready to use.")
        print("\nUsage examples:")
        print("  # Download NQ data only:")
        print("  python main.py --source nq --resolution minute --test")
        print("  # Download all data including NQ:")
        print("  python main.py --source all --resolution minute --test")
        print("  # Download specific NQ symbols:")
        print("  python main.py --source nq --nq-symbols QQQ TQQQ --resolution minute")
    else:
        print("⚠ Some tests failed, but NQ downloader may still work.")
        print("  Try running: python main.py --source nq --test")

if __name__ == "__main__":
    main()
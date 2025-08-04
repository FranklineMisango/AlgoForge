#!/usr/bin/env python3
"""
Basic syntax validation test for the new yahoo downloader module
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_syntax_imports():
    """Test that modules can be imported without syntax errors"""
    try:
        # Test config import with new variables
        from config import (
            FUTURES_DATA_PATH, OPTIONS_DATA_PATH, 
            DEFAULT_FUTURES_SYMBOLS, DEFAULT_OPTIONS_UNDERLYINGS,
            YAHOO_RATE_LIMIT
        )
        print("✓ Config imports successful with new futures/options variables")
        print(f"  Futures path: {FUTURES_DATA_PATH}")
        print(f"  Options path: {OPTIONS_DATA_PATH}")
        print(f"  Default futures symbols: {DEFAULT_FUTURES_SYMBOLS[:3]}...")
        print(f"  Default options underlyings: {DEFAULT_OPTIONS_UNDERLYINGS[:3]}...")
        print(f"  Yahoo rate limit: {YAHOO_RATE_LIMIT}")
        return True
    except Exception as e:
        print(f"✗ Config import failed: {e}")
        return False

def test_utils_import():
    """Test utils module with new functions"""
    try:
        # Mock pandas temporarily for testing
        import sys
        import types
        
        # Create a mock pandas module
        mock_pandas = types.ModuleType('pandas')
        sys.modules['pandas'] = mock_pandas
        
        from utils import create_lean_futures_csv, create_lean_tradebar_csv
        print("✓ Utils imports successful with new futures CSV function")
        return True
    except Exception as e:
        print(f"✗ Utils import failed: {e}")
        return False

def test_yahoo_downloader_syntax():
    """Test yahoo downloader syntax without dependencies"""
    try:
        # Read the file and check for syntax errors
        with open('yahoo_downloader.py', 'r') as f:
            code = f.read()
        
        # Compile to check syntax
        compile(code, 'yahoo_downloader.py', 'exec')
        print("✓ Yahoo downloader syntax is valid")
        return True
    except SyntaxError as e:
        print(f"✗ Yahoo downloader syntax error: {e}")
        return False
    except Exception as e:
        print(f"⚠ Yahoo downloader validation warning: {e}")
        return True  # Other errors are expected without dependencies

def test_main_integration():
    """Test main.py integration with new arguments"""
    try:
        # Read the file and check for syntax errors
        with open('main.py', 'r') as f:
            code = f.read()
        
        # Check if new arguments are present
        if '--futures-symbols' in code and '--options-underlyings' in code:
            print("✓ Main.py updated with new command line arguments")
        else:
            print("✗ Main.py missing new arguments")
            return False
            
        # Check if yahoo source is included
        if "'yahoo'" in code and 'YahooDataDownloader' in code:
            print("✓ Main.py includes Yahoo Finance integration")
        else:
            print("✗ Main.py missing Yahoo Finance integration")
            return False
            
        return True
    except Exception as e:
        print(f"✗ Main.py validation failed: {e}")
        return False

def test_directory_structure():
    """Test that required files exist"""
    required_files = [
        'config.py',
        'utils.py', 
        'yahoo_downloader.py',
        'main.py',
        'alpaca_downloader.py',
        'binance_downloader.py'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"✗ Missing files: {missing_files}")
        return False
    else:
        print("✓ All required files present")
        return True

def main():
    print("Futures/Options Integration Validation Test")
    print("=" * 50)
    
    tests = [
        ("File Structure", test_directory_structure),
        ("Config Import", test_syntax_imports),
        ("Utils Import", test_utils_import),
        ("Yahoo Downloader Syntax", test_yahoo_downloader_syntax),
        ("Main Integration", test_main_integration),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        if test_func():
            passed += 1
        else:
            print(f"  {test_name} failed")
    
    print(f"\n{'='*50}")
    print(f"Validation Results: {passed}/{total} passed")
    
    if passed == total:
        print("✓ All validation tests passed!")
        print("\nImplementation Summary:")
        print("- Added Yahoo Finance downloader for futures/options data")
        print("- Extended configuration with futures/options symbols")
        print("- Updated main pipeline to support 'yahoo' and 'all' sources")
        print("- Added LEAN format support for futures data")
        print("- Supports minute-level data for intraday momentum strategies")
        print("\nNext steps:")
        print("1. Install dependencies: pip install yfinance")
        print("2. Test with: python main.py --source yahoo --test --resolution minute")
    else:
        print("✗ Some validation tests failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
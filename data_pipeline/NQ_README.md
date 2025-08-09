# NQ Data Downloader Documentation

## Overview

The NQ Data Downloader provides access to NASDAQ-100 related financial data via free APIs, with support for minute granularity data. This feature addresses the need for downloading NQ (NASDAQ-100) data without requiring expensive API subscriptions.

## Features

- **Free API Sources**: Uses Yahoo Finance and Alpha Vantage free tier APIs
- **Minute Granularity**: Supports minute-level data collection as requested
- **NASDAQ-100 Focus**: Specialized for NQ/NASDAQ-100 related instruments
- **Multiple Symbols**: Downloads data for various NASDAQ-100 ETFs and related instruments
- **LEAN Format**: Converts data to QuantConnect LEAN format for backtesting

## Supported Symbols

The NQ downloader includes these NASDAQ-100 related symbols by default:

- **QQQ**: NASDAQ-100 ETF (primary proxy for NQ futures)
- **TQQQ**: 3x Leveraged NASDAQ-100 ETF  
- **SQQQ**: 3x Inverse NASDAQ-100 ETF
- **QQQS**: NASDAQ-100 Ex-Technology Sector Index ETF
- **QQQM**: NASDAQ-100 ETF (lower expense ratio version)

## API Sources

### 1. Yahoo Finance (Primary - Free)
- **Availability**: No API key required
- **Data**: Minute-level OHLCV data
- **Limitations**: 7-day chunks for minute data, rate limited
- **Coverage**: All major ETFs including QQQ, TQQQ, SQQQ

### 2. Alpha Vantage (Secondary - Free Tier)
- **Availability**: Requires free API key (optional)
- **Data**: Minute, hourly, and daily data
- **Limitations**: 5 requests per minute on free tier
- **Coverage**: Comprehensive market data

## Usage

### Basic Usage

```bash
# Download NQ data only with minute granularity
python main.py --source nq --resolution minute

# Test mode with limited data
python main.py --source nq --resolution minute --test

# Specific symbols and date range
python main.py --source nq --nq-symbols QQQ TQQQ --resolution minute --start-date 2024-01-01 --end-date 2024-01-31
```

### Advanced Usage

```bash
# Download all data sources including NQ
python main.py --source all --resolution minute

# Custom NQ symbols
python main.py --source nq --nq-symbols QQQ TQQQ SQQQ --resolution minute

# Different resolutions
python main.py --source nq --resolution daily    # Daily data
python main.py --source nq --resolution hour     # Hourly data
```

### Configuration

#### Environment Variables (Optional)

Create a `.env` file in the data_pipeline directory:

```bash
# Alpha Vantage API key (optional, for enhanced data access)
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_api_key_here
```

#### Command Line Options

- `--source nq`: Use NQ downloader specifically
- `--nq-symbols`: Specify which NASDAQ-100 symbols to download
- `--resolution minute`: Set data granularity (minute, hour, daily)
- `--start-date YYYY-MM-DD`: Set start date
- `--end-date YYYY-MM-DD`: Set end date
- `--test`: Run in test mode with limited data

## Output Format

The NQ downloader saves data in LEAN-compatible CSV format:

### File Structure
```
data/
└── equity/
    └── usa/
        └── minute/
            └── nq/
                ├── qqq_20240101_minute.csv
                ├── tqqq_20240101_minute.csv
                └── ...
```

### CSV Format
```csv
# Format: Time(ms), Open, High, Low, Close, Volume
32400000,38250,38300,38200,38275,1250000
32460000,38275,38350,38250,38325,1100000
...
```

## Rate Limiting

The NQ downloader implements rate limiting to respect API limits:

- **Yahoo Finance**: Built-in delays between requests
- **Alpha Vantage**: 5 requests per minute (free tier)
- **Chunk Processing**: 7-day chunks for minute data to avoid timeouts

## Error Handling

The downloader includes robust error handling:

- **Network Issues**: Retries and graceful degradation
- **API Limits**: Automatic rate limiting and backoff
- **Data Validation**: OHLCV data integrity checks
- **Missing Data**: Skips invalid bars, continues processing

## Integration with LEAN

The downloaded NQ data is automatically formatted for use with QuantConnect LEAN:

1. **CSV Format**: Compatible with LEAN's expected format
2. **Directory Structure**: Follows LEAN data organization
3. **Time Zones**: Properly handled for equity markets
4. **Price Format**: Converted to deci-cents for equity data

## Testing

Test the NQ downloader functionality:

```bash
# Run NQ-specific tests
python test_nq.py

# Test integration with main pipeline
python main.py --source nq --test

# Verify configuration
python -c "from config import NQ_SYMBOLS; print(NQ_SYMBOLS)"
```

## Troubleshooting

### Common Issues

1. **Network Connectivity**: The downloader requires internet access to financial APIs
2. **Rate Limiting**: If you see rate limit errors, reduce request frequency
3. **Data Availability**: Some data may not be available outside market hours
4. **API Keys**: Alpha Vantage key is optional but provides better access

### Debug Mode

Enable verbose logging for troubleshooting:

```bash
python main.py --source nq --test --verbose
```

## Performance Notes

- **Minute Data**: Limited to 7-day chunks due to API constraints
- **Historical Data**: Yahoo Finance provides extensive historical data
- **Memory Usage**: Efficient processing with data streaming
- **Storage**: CSV files are compact and LEAN-compatible

## Future Enhancements

Potential improvements for the NQ downloader:

1. **Additional APIs**: Integration with more free data sources
2. **Real Futures Data**: Access to actual NQ futures (if free sources become available)
3. **Enhanced Validation**: More sophisticated data quality checks
4. **Caching**: Local caching to reduce API calls
5. **Live Data**: Real-time data streaming capabilities

## Example: Complete Workflow

```bash
# 1. Download recent NQ data
python main.py --source nq --resolution minute --start-date 2024-01-01 --end-date 2024-01-31

# 2. Verify data was saved
ls -la ../data/equity/usa/minute/nq/

# 3. Use with LEAN for backtesting
cd ../Sample_Strategies/Python_Algorithms/DiversifiedLeverage
lean backtest --data-folder ../../../data
```

This provides a complete solution for downloading NQ (NASDAQ-100) data via free APIs with minute granularity, addressing the requirements specified in the issue.
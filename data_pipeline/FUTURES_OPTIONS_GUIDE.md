# Futures and Options Data Download Guide

This document explains how to use the new futures and options data download functionality integrated with Yahoo Finance.

## Overview

The data pipeline now supports downloading futures and options data from Yahoo Finance, providing free access to:

- **Futures contracts**: ES=F (S&P 500), NQ=F (NASDAQ), CL=F (Crude Oil), GC=F (Gold), etc.
- **Options data**: For major ETFs and stocks like SPY, QQQ, AAPL, TSLA, etc.
- **Multiple resolutions**: Minute, hour, and daily data for intraday momentum strategies

## Installation

First, install the required dependencies:

```bash
pip install yfinance pandas numpy
```

## Usage

### Basic Futures Data Download

Download minute-level futures data for the last 30 days:

```bash
python main.py --source yahoo --resolution minute --futures-symbols ES=F NQ=F CL=F
```

### Test Mode for Quick Testing

Run in test mode with limited symbols and date range:

```bash
python main.py --source yahoo --test --resolution minute
```

### Daily Data for Options

Download daily data including options information:

```bash
python main.py --source yahoo --resolution daily --options-underlyings SPY QQQ AAPL
```

### Custom Date Range

Download data for a specific date range:

```bash
python main.py --source yahoo --resolution minute \
  --futures-symbols ES=F NQ=F \
  --start-date 2024-01-01 \
  --end-date 2024-01-31
```

### All Data Sources

Download from all sources (Alpaca + Binance + Yahoo):

```bash
python main.py --source all --resolution minute --test
```

## Supported Futures Symbols

The default futures symbols include:

- **Stock Index Futures**: ES=F, NQ=F, YM=F, RTY=F
- **Commodity Futures**: CL=F (Crude Oil), GC=F (Gold), SI=F (Silver)
- **Bond Futures**: ZB=F, ZN=F, ZF=F

### Custom Futures Symbols

You can specify any Yahoo Finance futures symbol:

```bash
python main.py --source yahoo --futures-symbols ES=F NQ=F CL=F GC=F NG=F
```

## Data Output Structure

Data is saved in LEAN format under:

```
data/
├── futures/yahoo/
│   ├── minute/
│   │   └── es=f/
│   │       └── 20240101_trade.zip
│   └── daily/
│       └── es=f.zip
└── options/yahoo/
    ├── daily/
    │   └── spy.zip
    └── ...
```

## Intraday Momentum Strategy Support

The new functionality specifically addresses the issue: "intra-day momentum strategies will fail without minute data"

### Example: Minute-Level Futures Data

```bash
# Download minute-level S&P 500 futures data for momentum strategies
python main.py --source yahoo --resolution minute --futures-symbols ES=F --test
```

This provides the high-frequency data needed for intraday momentum strategies that were previously limited to daily data.

## Integration with LEAN Engine

The downloaded data is automatically converted to LEAN format and can be used directly with QuantConnect LEAN backtesting engine. The files are properly compressed and follow LEAN naming conventions.

## Troubleshooting

### Missing Dependencies

If you see `No module named 'yfinance'`, install it:

```bash
pip install yfinance
```

### Network Issues

Yahoo Finance may occasionally be slow. The downloader includes rate limiting and retry logic.

### Invalid Symbols

If a futures symbol doesn't work, verify it exists on Yahoo Finance by checking: `https://finance.yahoo.com/quote/ES=F`

## Command Line Reference

```
--source yahoo              Use Yahoo Finance as data source
--source all                Use all data sources (includes Yahoo)
--futures-symbols [SYMBOLS] List of futures symbols (ES=F, NQ=F, etc.)
--options-underlyings [SYMBOLS] List of options underlying symbols
--resolution minute         Download minute-level data
--resolution daily          Download daily data
--test                      Test mode with limited data
--start-date YYYY-MM-DD     Custom start date
--end-date YYYY-MM-DD       Custom end date
```

## Advanced Usage

### Custom Configuration

You can modify the default symbols in `config.py`:

```python
DEFAULT_FUTURES_SYMBOLS = ['ES=F', 'NQ=F', 'YM=F', 'RTY=F', 'CL=F', 'GC=F']
DEFAULT_OPTIONS_UNDERLYINGS = ['SPY', 'QQQ', 'AAPL', 'TSLA', 'NVDA']
```

### Rate Limiting

Yahoo Finance rate limiting is configured in `config.py`:

```python
YAHOO_RATE_LIMIT = 2000  # requests per minute
```

This ensures compliance with Yahoo's API limits while maximizing download speed.
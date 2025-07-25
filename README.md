# AlgoForge

A comprehensive command-line backtesting platform that integrates with QuantConnect's LEAN engine, featuring automated data acquisition from Alpaca Markets (US equities) and Binance (cryptocurrencies) with seamless conversion to LEAN format.

## Overview

AlgoForge solves the costly data problem in algorithmic trading by providing:
- Free market data acquisition from Alpaca and Binance
- Automatic conversion to QuantConnect LEAN format
- Command-line backtesting interface
- Interactive visualization of backtest results
- Sample trading strategies in both Python and C#

## Features

### Data Pipeline
- **Multiple Data Sources**: Download from Alpaca (US equities) and Binance (cryptocurrencies)
- **LEAN Format Conversion**: Automatic conversion to QuantConnect's CSV format with proper compression
- **Multiple Resolutions**: Support for minute, hour, and daily data frequencies
- **Rate Limiting**: Built-in API rate limiting to prevent throttling
- **Data Validation**: Comprehensive OHLCV data integrity checks
- **Timezone Handling**: Proper timezone conversion for different markets

### Backtesting Platform
- **LEAN Integration**: Full compatibility with QuantConnect's LEAN engine
- **Multi-Language Support**: Algorithms in Python and C#
- **Sample Strategies**: Pre-built strategies including diversified leverage portfolios
- **Command-Line Interface**: Easy-to-use CLI for running backtests

### Visualization
- **Interactive Charts**: TradingView-style charts for backtest analysis
- **Performance Metrics**: Comprehensive performance statistics and analysis
- **Multi-Strategy Comparison**: Compare multiple strategies side-by-side
- **Streamlit Interface**: Web-based visualization dashboard

## Installation

### Prerequisites
- Python 3.8 or higher
- Git
- QuantConnect LEAN CLI (optional, for advanced features)

### Quick Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/FranklineMisango/AlgoForge.git
   cd AlgoForge
   ```

2. **Set up the data pipeline**:
   ```bash
   cd data_pipeline
   chmod +x setup.sh
   ./setup.sh
   ```

3. **Configure API keys** (create a `.env` file in the data_pipeline directory):
   ```bash
   # Alpaca API keys (required for equity data)
   ALPACA_API_KEY=your_alpaca_api_key
   ALPACA_SECRET_KEY=your_alpaca_secret_key
   
   # Binance API keys (optional for public crypto data)
   BINANCE_API_KEY=your_binance_api_key
   BINANCE_SECRET_KEY=your_binance_secret_key
   ```

4. **Test the setup**:
   ```bash
   python test_setup.py
   ```

## Getting API Keys

### Alpaca Markets (For US Equity Data)
1. Visit [Alpaca Markets](https://alpaca.markets/)
2. Create a free account
3. Navigate to your dashboard and generate API keys
4. Use paper trading keys for testing purposes

### Binance (For Cryptocurrency Data)
1. Visit [Binance](https://www.binance.com/)
2. Create an account
3. Generate API keys in your account settings
4. Note: Public data can be accessed without API keys

## Usage

### Data Download

**Download equity data from Alpaca**:
```bash
cd data_pipeline
python main.py --source alpaca --equity-symbols AAPL GOOGL MSFT --resolution daily
```

**Download cryptocurrency data from Binance**:
```bash
python main.py --source binance --crypto-symbols BTCUSDT ETHUSDT --resolution minute
```

**Download from both sources**:
```bash
python main.py --source both --start-date 2023-01-01 --end-date 2023-12-31
```

### Running Sample Strategies

**Python Strategy**:
```bash
cd Sample_Strategies/Python_Algorithms/DiversifiedLeverage
# Configure the strategy parameters in config.json
# Run with LEAN CLI or your preferred backtesting environment
```

**C# Strategy**:
```bash
cd Sample_Strategies/C#_Algorithms/DiversifiedLeverage
dotnet build
# Run with LEAN CLI or your preferred backtesting environment
```

### Visualization

**Launch the interactive visualizer**:
```bash
chmod +x launch_visualizer.sh
./launch_visualizer.sh
```

This will start a Streamlit web application at `http://localhost:8501` where you can:
- Upload and analyze backtest results
- View interactive charts and performance metrics
- Compare multiple strategies
- Export analysis reports

## Project Structure

```
AlgoForge/
├── README.md                          # This file
├── LICENSE                           # Project license
├── backtest_visualizer.py           # Interactive visualization tool
├── launch_visualizer.sh             # Visualizer launcher script
├── data_pipeline/                   # Data acquisition and processing
│   ├── main.py                     # Main pipeline script
│   ├── alpaca_downloader.py        # Alpaca data downloader
│   ├── binance_downloader.py       # Binance data downloader
│   ├── config.py                   # Configuration settings
│   ├── setup.sh                    # Automated setup script
│   └── requirements.txt            # Python dependencies
└── Sample_Strategies/              # Example trading strategies
    ├── Python_Algorithms/          # Python-based strategies
    │   └── DiversifiedLeverage/    # Sample diversified leverage strategy
    └── C#_Algorithms/              # C#-based strategies
        └── DiversifiedLeverage/    # Sample diversified leverage strategy
```

## Configuration

### Data Pipeline Configuration

Edit `data_pipeline/config.py` to customize:
- Default symbols to download
- Date ranges
- Data resolutions
- Output paths
- API rate limits

### Strategy Configuration

Each sample strategy includes a `config.json` file where you can modify:
- Portfolio weights
- Rebalancing frequency
- Risk management parameters
- Backtesting date ranges

## Data Formats

The pipeline converts data to LEAN's standard format:
- **Equity data**: `YYYYMMDD HH:mm,open,high,low,close,volume`
- **Crypto data**: `YYYYMMDD HH:mm,open,high,low,close,volume`
- **Compression**: Automatic ZIP compression for storage efficiency
- **Timezone**: UTC for consistency across markets

## Command Line Options

### Data Pipeline (`main.py`)

```bash
python main.py [options]

Options:
  --source {alpaca,binance,both}    Data source selection
  --equity-symbols SYMBOL [SYMBOL ...] Equity symbols to download
  --crypto-symbols SYMBOL [SYMBOL ...] Crypto symbols to download
  --start-date YYYY-MM-DD           Start date for data download
  --end-date YYYY-MM-DD             End date for data download
  --resolution {minute,hour,daily}  Data resolution
  --test                           Run with test data
```

## Troubleshooting

### Common Issues

1. **API Key Errors**: Ensure your API keys are correctly set in the `.env` file
2. **Rate Limiting**: If you encounter rate limits, increase the delay in `config.py`
3. **Data Format Issues**: Verify that downloaded data matches LEAN's expected format
4. **Permission Errors**: Make sure scripts have execute permissions (`chmod +x`)

### Getting Help

1. Check the detailed documentation in `data_pipeline/README.md`
2. Review the setup guide in `data_pipeline/SETUP_GUIDE.md`
3. Run the test setup script to verify your configuration
4. Check the sample strategies for implementation examples

## Contributing

Contributions are welcome! Please feel free to submit pull requests, report bugs, or suggest new features.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the terms specified in the LICENSE file.

## Disclaimer

This software is for educational and research purposes only. Past performance does not guarantee future results. Always test strategies thoroughly before using real capital.

## Acknowledgments

- QuantConnect for the LEAN algorithmic trading engine
- Alpaca Markets for providing free equity data API
- Binance for cryptocurrency market data
- The open-source community for various dependencies and tools

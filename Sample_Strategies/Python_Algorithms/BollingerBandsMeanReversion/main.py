# region imports
from AlgorithmImports import *
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
# endregion

class BollingerBandsMeanReversion(QCAlgorithm):
    """
    Bollinger Bands Mean Reversion Strategy
    
    This strategy uses Bollinger Bands to identify overbought and oversold conditions:
    - Enters long positions when price touches the lower band (oversold)
    - Enters short positions when price touches the upper band (overbought)
    - Exits positions when price returns to the middle band (20-day SMA)
    - Includes volatility filtering and position sizing
    - Uses multiple timeframes for confirmation
    """
    
    def Initialize(self):
        self.SetStartDate(2020, 1, 1)
        self.SetEndDate(2024, 12, 31)
        self.SetCash(100000)
        
        # Universe of stocks to trade
        self.symbols = ["SPY", "QQQ", "IWM", "EFA", "EEM", "TLT", "GLD", "AAPL", "MSFT", "GOOGL"]
        
        # Strategy parameters
        self.bb_period = 20
        self.bb_std = 2.0
        self.rsi_period = 14
        self.volume_period = 20
        self.max_position_size = 0.08  # 8% max position size
        self.stop_loss_pct = 0.05      # 5% stop loss
        self.take_profit_pct = 0.10    # 10% take profit
        self.volatility_threshold = 0.02  # 2% daily volatility threshold
        
        # Data storage
        self.symbol_data = {}
        
        # Add securities and create indicators
        for ticker in self.symbols:
            symbol = self.AddEquity(ticker, Resolution.Daily).Symbol
            
            # Create symbol data container
            symbol_data = SymbolData(symbol, self.bb_period, self.bb_std, self.rsi_period, self.volume_period)
            self.symbol_data[symbol] = symbol_data
            
            # Register for consolidation
            self.RegisterIndicator(symbol, symbol_data.bollinger_bands, Resolution.Daily)
            self.RegisterIndicator(symbol, symbol_data.rsi, Resolution.Daily)
            self.RegisterIndicator(symbol, symbol_data.volume_sma, Resolution.Daily)
            self.RegisterIndicator(symbol, symbol_data.atr, Resolution.Daily)
        
        # Set benchmark
        self.SetBenchmark("SPY")
        
        # Schedule rebalancing
        self.Schedule.On(self.DateRules.EveryDay("SPY"), 
                        self.TimeRules.AfterMarketOpen("SPY", 30), 
                        self.CheckSignals)
        
        # Risk management
        self.Schedule.On(self.DateRules.EveryDay("SPY"), 
                        self.TimeRules.AfterMarketOpen("SPY", 60), 
                        self.ManageRisk)
        
        self.Log("Bollinger Bands Mean Reversion Strategy Initialized")
    
    def OnData(self, data):
        """Process new data and update indicators"""
        for symbol in self.symbol_data:
            if symbol in data.Bars:
                bar = data.Bars[symbol]
                symbol_data = self.symbol_data[symbol]
                
                # Update price history for volatility calculation
                symbol_data.price_history.append(bar.Close)
                if len(symbol_data.price_history) > 252:  # Keep 1 year of data
                    symbol_data.price_history.pop(0)
    
    def CheckSignals(self):
        """Check for entry and exit signals"""
        for symbol, symbol_data in self.symbol_data.items():
            if not self.IsValidForTrading(symbol, symbol_data):
                continue
            
            current_price = self.Securities[symbol].Price
            holdings = self.Portfolio[symbol]
            
            # Get indicator values
            bb_upper = symbol_data.bollinger_bands.UpperBand.Current.Value
            bb_middle = symbol_data.bollinger_bands.MiddleBand.Current.Value
            bb_lower = symbol_data.bollinger_bands.LowerBand.Current.Value
            rsi = symbol_data.rsi.Current.Value
            
            # Check for entry signals
            if not holdings.Invested:
                self.CheckEntrySignals(symbol, symbol_data, current_price, bb_upper, bb_middle, bb_lower, rsi)
            else:
                self.CheckExitSignals(symbol, symbol_data, current_price, bb_middle, holdings)
    
    def CheckEntrySignals(self, symbol, symbol_data, current_price, bb_upper, bb_middle, bb_lower, rsi):
        """Check for entry signals based on Bollinger Bands and RSI"""
        
        # Long signal: Price touches lower band + RSI oversold
        if (current_price <= bb_lower * 1.005 and  # Allow small tolerance
            rsi < 35 and  # Oversold condition
            self.IsVolumeConfirmed(symbol_data) and
            self.IsVolatilityAcceptable(symbol_data)):
            
            position_size = self.CalculatePositionSize(symbol, symbol_data)
            if position_size > 0:
                self.SetHoldings(symbol, position_size)
                self.Log(f"Long entry for {symbol}: Price={current_price:.2f}, BB_Lower={bb_lower:.2f}, RSI={rsi:.2f}")
        
        # Short signal: Price touches upper band + RSI overbought
        elif (current_price >= bb_upper * 0.995 and  # Allow small tolerance
              rsi > 65 and  # Overbought condition
              self.IsVolumeConfirmed(symbol_data) and
              self.IsVolatilityAcceptable(symbol_data)):
            
            position_size = self.CalculatePositionSize(symbol, symbol_data)
            if position_size > 0:
                self.SetHoldings(symbol, -position_size)
                self.Log(f"Short entry for {symbol}: Price={current_price:.2f}, BB_Upper={bb_upper:.2f}, RSI={rsi:.2f}")
    
    def CheckExitSignals(self, symbol, symbol_data, current_price, bb_middle, holdings):
        """Check for exit signals based on mean reversion"""
        
        quantity = holdings.Quantity
        
        # Exit long positions when price reaches middle band
        if quantity > 0 and current_price >= bb_middle:
            self.Liquidate(symbol)
            self.Log(f"Exit long for {symbol}: Price={current_price:.2f}, BB_Middle={bb_middle:.2f}")
        
        # Exit short positions when price reaches middle band
        elif quantity < 0 and current_price <= bb_middle:
            self.Liquidate(symbol)
            self.Log(f"Exit short for {symbol}: Price={current_price:.2f}, BB_Middle={bb_middle:.2f}")
    
    def ManageRisk(self):
        """Manage risk for existing positions"""
        for symbol in self.Portfolio.Values:
            if symbol.Invested:
                self.CheckStopLossAndTakeProfit(symbol.Symbol)
    
    def CheckStopLossAndTakeProfit(self, symbol):
        """Check stop loss and take profit conditions"""
        holdings = self.Portfolio[symbol]
        current_price = self.Securities[symbol].Price
        avg_price = holdings.AveragePrice
        quantity = holdings.Quantity
        
        if quantity > 0:  # Long position
            pnl_pct = (current_price - avg_price) / avg_price
            
            if pnl_pct <= -self.stop_loss_pct:
                self.Liquidate(symbol)
                self.Log(f"Stop loss triggered for {symbol}: {pnl_pct:.2%}")
            elif pnl_pct >= self.take_profit_pct:
                self.Liquidate(symbol)
                self.Log(f"Take profit triggered for {symbol}: {pnl_pct:.2%}")
        
        elif quantity < 0:  # Short position
            pnl_pct = (avg_price - current_price) / avg_price
            
            if pnl_pct <= -self.stop_loss_pct:
                self.Liquidate(symbol)
                self.Log(f"Stop loss triggered for {symbol}: {pnl_pct:.2%}")
            elif pnl_pct >= self.take_profit_pct:
                self.Liquidate(symbol)
                self.Log(f"Take profit triggered for {symbol}: {pnl_pct:.2%}")
    
    def IsValidForTrading(self, symbol, symbol_data):
        """Check if the symbol is valid for trading"""
        return (symbol_data.bollinger_bands.IsReady and 
                symbol_data.rsi.IsReady and 
                symbol_data.volume_sma.IsReady and
                self.Securities[symbol].Price > 5)  # Avoid penny stocks
    
    def IsVolumeConfirmed(self, symbol_data):
        """Check if current volume confirms the signal"""
        if not symbol_data.volume_sma.IsReady:
            return False
        
        current_volume = symbol_data.volume_sma.Current.Value
        avg_volume = symbol_data.volume_sma.Current.Value
        
        return current_volume > avg_volume * 0.8  # At least 80% of average volume
    
    def IsVolatilityAcceptable(self, symbol_data):
        """Check if volatility is within acceptable range"""
        if len(symbol_data.price_history) < 20:
            return True
        
        # Calculate daily volatility
        returns = []
        for i in range(1, min(21, len(symbol_data.price_history))):
            ret = (symbol_data.price_history[i] - symbol_data.price_history[i-1]) / symbol_data.price_history[i-1]
            returns.append(ret)
        
        if len(returns) > 0:
            volatility = np.std(returns)
            return volatility < self.volatility_threshold
        
        return True
    
    def CalculatePositionSize(self, symbol, symbol_data):
        """Calculate position size based on volatility and risk management"""
        base_size = self.max_position_size
        
        # Adjust for volatility using ATR
        if symbol_data.atr.IsReady:
            current_price = self.Securities[symbol].Price
            atr = symbol_data.atr.Current.Value
            volatility_ratio = atr / current_price
            
            # Reduce position size for higher volatility
            if volatility_ratio > 0.02:  # 2% daily ATR
                base_size *= 0.5
            elif volatility_ratio > 0.04:  # 4% daily ATR
                base_size *= 0.25
        
        return min(base_size, self.max_position_size)


class SymbolData:
    """Container for symbol-specific data and indicators"""
    
    def __init__(self, symbol, bb_period, bb_std, rsi_period, volume_period):
        self.symbol = symbol
        
        # Technical indicators
        self.bollinger_bands = BollingerBands(bb_period, bb_std)
        self.rsi = RelativeStrengthIndex(rsi_period, MovingAverageType.Wilders)
        self.volume_sma = SimpleMovingAverage(volume_period)
        self.atr = AverageTrueRange(14)
        
        # Price history for volatility calculation
        self.price_history = []

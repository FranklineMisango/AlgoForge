# region imports
from AlgorithmImports import *
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
# endregion

class CryptoMomentum(QCAlgorithm):
    """
    Cryptocurrency Momentum Strategy
    
    This strategy implements momentum trading for cryptocurrencies:
    - Uses multiple momentum indicators (MACD, RSI, Rate of Change)
    - Incorporates volume analysis for signal confirmation
    - Applies dynamic position sizing based on volatility
    - Includes market regime detection for crypto markets
    - Features comprehensive risk management with trailing stops
    """
    
    def Initialize(self):
        self.SetStartDate(2021, 1, 1)
        self.SetEndDate(2024, 12, 31)
        self.SetCash(100000)
        
        # Cryptocurrency universe
        self.crypto_symbols = ["BTCUSD", "ETHUSD", "ADAUSD", "SOLUSD", "DOTUSD", "LINKUSD", "LTCUSD", "BCHUSD"]
        
        # Strategy parameters
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9
        self.rsi_period = 14
        self.roc_period = 10
        self.volume_period = 20
        self.volatility_period = 20
        self.max_position_size = 0.15  # 15% max position size for crypto
        self.momentum_threshold = 0.6  # Momentum score threshold
        self.trailing_stop_pct = 0.08  # 8% trailing stop
        self.max_crypto_exposure = 0.8  # Maximum 80% in crypto
        
        # Data storage
        self.symbol_data = {}
        self.momentum_scores = {}
        self.trailing_stops = {}
        self.market_regime = "neutral"
        
        # Add cryptocurrencies
        for ticker in self.crypto_symbols:
            try:
                symbol = self.AddCrypto(ticker, Resolution.Daily, Market.Coinbase).Symbol
                
                # Create symbol data container
                symbol_data = CryptoSymbolData(symbol, self.macd_fast, self.macd_slow, self.macd_signal,
                                             self.rsi_period, self.roc_period, self.volume_period)
                self.symbol_data[symbol] = symbol_data
                
                # Initialize momentum score
                self.momentum_scores[symbol] = 0.0
                self.trailing_stops[symbol] = None
                
            except Exception as e:
                self.Log(f"Failed to add {ticker}: {str(e)}")
        
        # Add benchmark (Bitcoin)
        try:
            self.benchmark_symbol = self.AddCrypto("BTCUSD", Resolution.Daily, Market.Coinbase).Symbol
            self.SetBenchmark(self.benchmark_symbol)
        except:
            self.Log("Failed to set benchmark")
        
        # Schedule analysis and rebalancing
        self.Schedule.On(self.DateRules.EveryDay(), 
                        self.TimeRules.At(1, 0),  # 1 AM UTC (crypto markets are 24/7)
                        self.AnalyzeAndRebalance)
        
        # Risk management
        self.Schedule.On(self.DateRules.EveryDay(), 
                        self.TimeRules.At(6, 0),  # 6 AM UTC
                        self.ManageRisk)
        
        self.Log("Crypto Momentum Strategy Initialized")
    
    def OnData(self, data):
        """Process new data and update indicators"""
        for symbol in self.symbol_data:
            if symbol in data and data[symbol] is not None:
                symbol_data = self.symbol_data[symbol]
                price = data[symbol].Close
                
                # Update price history
                symbol_data.price_history.append(price)
                if len(symbol_data.price_history) > 100:
                    symbol_data.price_history.pop(0)
                
                # Update volume history if available
                if hasattr(data[symbol], 'Volume'):
                    symbol_data.volume_history.append(data[symbol].Volume)
                    if len(symbol_data.volume_history) > 50:
                        symbol_data.volume_history.pop(0)
    
    def AnalyzeAndRebalance(self):
        """Analyze momentum and rebalance portfolio"""
        # Detect market regime
        self.market_regime = self.DetectMarketRegime()
        
        # Calculate momentum scores
        self.CalculateMomentumScores()
        
        # Rank cryptocurrencies by momentum
        ranked_cryptos = self.RankCryptosByMomentum()
        
        # Determine position sizes
        allocations = self.DetermineAllocations(ranked_cryptos)
        
        # Execute trades
        self.ExecuteAllocations(allocations)
        
        self.LogPortfolioStatus()
    
    def DetectMarketRegime(self):
        """Detect crypto market regime based on Bitcoin behavior"""
        if self.benchmark_symbol not in self.symbol_data:
            return "neutral"
        
        btc_data = self.symbol_data[self.benchmark_symbol]
        
        if not btc_data.macd.IsReady or not btc_data.rsi.IsReady:
            return "neutral"
        
        macd_value = btc_data.macd.Current.Value
        macd_signal = btc_data.macd.Signal.Current.Value
        rsi_value = btc_data.rsi.Current.Value
        
        # Bull market: MACD above signal, RSI not overbought
        if macd_value > macd_signal and rsi_value < 70:
            return "bull"
        # Bear market: MACD below signal, RSI not oversold
        elif macd_value < macd_signal and rsi_value > 30:
            return "bear"
        else:
            return "neutral"
    
    def CalculateMomentumScores(self):
        """Calculate momentum scores for each cryptocurrency"""
        for symbol, symbol_data in self.symbol_data.items():
            if not self.IsDataReady(symbol_data):
                self.momentum_scores[symbol] = 0.0
                continue
            
            score = 0.0
            
            # MACD component (40% weight)
            macd_score = self.GetMACDScore(symbol_data)
            score += macd_score * 0.4
            
            # RSI component (25% weight)
            rsi_score = self.GetRSIScore(symbol_data)
            score += rsi_score * 0.25
            
            # Rate of Change component (25% weight)
            roc_score = self.GetROCScore(symbol_data)
            score += roc_score * 0.25
            
            # Volume component (10% weight)
            volume_score = self.GetVolumeScore(symbol_data)
            score += volume_score * 0.1
            
            self.momentum_scores[symbol] = score
    
    def GetMACDScore(self, symbol_data):
        """Calculate MACD momentum score"""
        if not symbol_data.macd.IsReady:
            return 0.0
        
        macd_value = symbol_data.macd.Current.Value
        macd_signal = symbol_data.macd.Signal.Current.Value
        macd_histogram = symbol_data.macd.Histogram.Current.Value
        
        score = 0.0
        
        # MACD above signal line
        if macd_value > macd_signal:
            score += 0.5
        
        # Histogram increasing (momentum accelerating)
        if macd_histogram > 0:
            score += 0.5
        
        return score
    
    def GetRSIScore(self, symbol_data):
        """Calculate RSI momentum score"""
        if not symbol_data.rsi.IsReady:
            return 0.0
        
        rsi_value = symbol_data.rsi.Current.Value
        
        # Optimal RSI range for momentum (45-75)
        if 45 <= rsi_value <= 75:
            return 1.0
        elif rsi_value > 75:  # Overbought but still bullish
            return 0.3
        elif rsi_value < 30:  # Oversold, potential reversal
            return 0.2
        else:
            return 0.0
    
    def GetROCScore(self, symbol_data):
        """Calculate Rate of Change momentum score"""
        if not symbol_data.roc.IsReady:
            return 0.0
        
        roc_value = symbol_data.roc.Current.Value
        
        # Normalize ROC value
        if roc_value > 10:  # Strong positive momentum
            return 1.0
        elif roc_value > 5:  # Moderate positive momentum
            return 0.7
        elif roc_value > 0:  # Weak positive momentum
            return 0.4
        else:  # Negative momentum
            return 0.0
    
    def GetVolumeScore(self, symbol_data):
        """Calculate volume confirmation score"""
        if len(symbol_data.volume_history) < 10:
            return 0.5  # Neutral if insufficient data
        
        recent_volume = np.mean(symbol_data.volume_history[-5:])  # Last 5 days
        historical_volume = np.mean(symbol_data.volume_history[-20:-5])  # Previous 15 days
        
        if recent_volume > historical_volume * 1.2:  # 20% above average
            return 1.0
        elif recent_volume > historical_volume:
            return 0.7
        else:
            return 0.3
    
    def RankCryptosByMomentum(self):
        """Rank cryptocurrencies by momentum score"""
        return sorted(self.momentum_scores.items(), key=lambda x: x[1], reverse=True)
    
    def DetermineAllocations(self, ranked_cryptos):
        """Determine position allocations based on momentum and market regime"""
        allocations = {}
        
        # Filter cryptos above momentum threshold
        qualified_cryptos = [(symbol, score) for symbol, score in ranked_cryptos 
                           if score >= self.momentum_threshold]
        
        if not qualified_cryptos:
            return allocations
        
        # Adjust strategy based on market regime
        if self.market_regime == "bull":
            # Aggressive allocation in bull market
            top_cryptos = qualified_cryptos[:4]  # Top 4 cryptos
            total_allocation = min(self.max_crypto_exposure, 0.9)
        elif self.market_regime == "bear":
            # Conservative allocation in bear market
            top_cryptos = qualified_cryptos[:2]  # Top 2 cryptos only
            total_allocation = min(self.max_crypto_exposure, 0.4)
        else:  # neutral
            # Balanced allocation
            top_cryptos = qualified_cryptos[:3]  # Top 3 cryptos
            total_allocation = min(self.max_crypto_exposure, 0.6)
        
        # Calculate individual allocations
        if top_cryptos:
            total_score = sum([score for _, score in top_cryptos])
            
            for symbol, score in top_cryptos:
                # Weight by momentum score
                base_allocation = (score / total_score) * total_allocation
                
                # Apply volatility adjustment
                volatility_adjustment = self.GetVolatilityAdjustment(symbol)
                final_allocation = base_allocation * volatility_adjustment
                
                # Cap individual position size
                final_allocation = min(final_allocation, self.max_position_size)
                
                allocations[symbol] = final_allocation
        
        return allocations
    
    def GetVolatilityAdjustment(self, symbol):
        """Adjust position size based on volatility"""
        symbol_data = self.symbol_data[symbol]
        
        if len(symbol_data.price_history) < 20:
            return 0.5  # Conservative if insufficient data
        
        # Calculate daily returns
        returns = []
        for i in range(1, min(21, len(symbol_data.price_history))):
            ret = (symbol_data.price_history[i] - symbol_data.price_history[i-1]) / symbol_data.price_history[i-1]
            returns.append(ret)
        
        if len(returns) > 0:
            volatility = np.std(returns)
            
            # Inverse relationship with volatility
            if volatility > 0.08:  # Very high volatility (>8%)
                return 0.3
            elif volatility > 0.05:  # High volatility (>5%)
                return 0.6
            elif volatility > 0.03:  # Medium volatility (>3%)
                return 0.8
            else:  # Low volatility
                return 1.0
        
        return 0.5
    
    def ExecuteAllocations(self, allocations):
        """Execute the determined allocations"""
        # Liquidate positions not in new allocation
        for symbol in self.Portfolio.Keys:
            if self.Portfolio[symbol].Invested and symbol not in allocations:
                self.Liquidate(symbol)
                self.trailing_stops[symbol] = None
                self.Log(f"Liquidated {symbol}")
        
        # Set new positions
        for symbol, allocation in allocations.items():
            if allocation > 0:
                self.SetHoldings(symbol, allocation)
                
                # Set trailing stop
                current_price = self.Securities[symbol].Price
                self.trailing_stops[symbol] = current_price * (1 - self.trailing_stop_pct)
                
                self.Log(f"Set {symbol} to {allocation:.2%} allocation")
    
    def ManageRisk(self):
        """Manage risk for existing positions"""
        for symbol in list(self.Portfolio.Keys):
            if self.Portfolio[symbol].Invested:
                self.UpdateTrailingStop(symbol)
                self.CheckTrailingStop(symbol)
    
    def UpdateTrailingStop(self, symbol):
        """Update trailing stop for profitable positions"""
        if symbol not in self.trailing_stops or self.trailing_stops[symbol] is None:
            return
        
        current_price = self.Securities[symbol].Price
        quantity = self.Portfolio[symbol].Quantity
        
        if quantity > 0:  # Long position
            new_stop = current_price * (1 - self.trailing_stop_pct)
            if new_stop > self.trailing_stops[symbol]:
                self.trailing_stops[symbol] = new_stop
        
    def CheckTrailingStop(self, symbol):
        """Check if trailing stop should be triggered"""
        if symbol not in self.trailing_stops or self.trailing_stops[symbol] is None:
            return
        
        current_price = self.Securities[symbol].Price
        quantity = self.Portfolio[symbol].Quantity
        
        if quantity > 0 and current_price <= self.trailing_stops[symbol]:
            self.Liquidate(symbol)
            self.trailing_stops[symbol] = None
            self.Log(f"Trailing stop triggered for {symbol} at {current_price}")
    
    def IsDataReady(self, symbol_data):
        """Check if symbol data is ready for analysis"""
        return (symbol_data.macd.IsReady and 
                symbol_data.rsi.IsReady and 
                symbol_data.roc.IsReady)
    
    def LogPortfolioStatus(self):
        """Log current portfolio status"""
        self.Log(f"Market Regime: {self.market_regime}")
        self.Log(f"Portfolio Value: ${self.Portfolio.TotalPortfolioValue:,.2f}")
        
        invested_symbols = [symbol for symbol in self.Portfolio.Keys if self.Portfolio[symbol].Invested]
        if invested_symbols:
            self.Log("Current Positions:")
            for symbol in invested_symbols:
                holding = self.Portfolio[symbol]
                momentum = self.momentum_scores.get(symbol, 0)
                self.Log(f"  {symbol}: {holding.HoldingsValue/self.Portfolio.TotalPortfolioValue:.1%} "
                        f"(Momentum: {momentum:.2f})")


class CryptoSymbolData:
    """Container for cryptocurrency-specific data and indicators"""
    
    def __init__(self, symbol, macd_fast, macd_slow, macd_signal, rsi_period, roc_period, volume_period):
        self.symbol = symbol
        
        # Technical indicators
        self.macd = MovingAverageConvergenceDivergence(macd_fast, macd_slow, macd_signal)
        self.rsi = RelativeStrengthIndex(rsi_period, MovingAverageType.Wilders)
        self.roc = RateOfChange(roc_period)
        
        # Data storage
        self.price_history = []
        self.volume_history = []

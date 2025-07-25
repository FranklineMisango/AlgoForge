#region imports
    using System;
    using System.Collections;
    using System.Collections.Generic;
    using System.Linq;
    using System.Globalization;
    using System.Drawing;
    using QuantConnect;
    using QuantConnect.Algorithm.Framework;
    using QuantConnect.Algorithm.Framework.Selection;
    using QuantConnect.Algorithm.Framework.Alphas;
    using QuantConnect.Algorithm.Framework.Portfolio;
    using QuantConnect.Algorithm.Framework.Portfolio.SignalExports;
    using QuantConnect.Algorithm.Framework.Execution;
    using QuantConnect.Algorithm.Framework.Risk;
    using QuantConnect.Algorithm.Selection;
    using QuantConnect.Api;
    using QuantConnect.Parameters;
    using QuantConnect.Benchmarks;
    using QuantConnect.Brokerages;
    using QuantConnect.Commands;
    using QuantConnect.Configuration;
    using QuantConnect.Util;
    using QuantConnect.Interfaces;
    using QuantConnect.Algorithm;
    using QuantConnect.Indicators;
    using QuantConnect.Data;
    using QuantConnect.Data.Auxiliary;
    using QuantConnect.Data.Consolidators;
    using QuantConnect.Data.Custom;
    using QuantConnect.Data.Custom.IconicTypes;
    using QuantConnect.DataSource;
    using QuantConnect.Data.Fundamental;
    using QuantConnect.Data.Market;
    using QuantConnect.Data.Shortable;
    using QuantConnect.Data.UniverseSelection;
    using QuantConnect.Notifications;
    using QuantConnect.Orders;
    using QuantConnect.Orders.Fees;
    using QuantConnect.Orders.Fills;
    using QuantConnect.Orders.OptionExercise;
    using QuantConnect.Orders.Slippage;
    using QuantConnect.Orders.TimeInForces;
    using QuantConnect.Python;
    using QuantConnect.Scheduling;
    using QuantConnect.Securities;
    using QuantConnect.Securities.Equity;
    using QuantConnect.Securities.Future;
    using QuantConnect.Securities.Option;
    using QuantConnect.Securities.Positions;
    using QuantConnect.Securities.Forex;
    using QuantConnect.Securities.Crypto;
    using QuantConnect.Securities.CryptoFuture;
    using QuantConnect.Securities.IndexOption;
    using QuantConnect.Securities.Interfaces;
    using QuantConnect.Securities.Volatility;
    using QuantConnect.Storage;
    using QuantConnect.Statistics;
    using QCAlgorithmFramework = QuantConnect.Algorithm.QCAlgorithm;
    using QCAlgorithmFrameworkBridge = QuantConnect.Algorithm.QCAlgorithm;
    using Calendar = QuantConnect.Data.Consolidators.Calendar;
#endregion

namespace QuantConnect.Algorithm.CSharp
{
    /// <summary>
    /// Momentum Mean Reversion Strategy
    /// 
    /// This strategy combines momentum and mean reversion signals:
    /// - Uses RSI for mean reversion signals (oversold/overbought conditions)
    /// - Uses moving average crossovers for momentum signals
    /// - Applies position sizing based on volatility (ATR)
    /// - Includes stop-loss and take-profit mechanisms
    /// </summary>
    public class MomentumMeanReversion : QCAlgorithm
    {
        // Strategy Parameters
        private readonly List<string> _symbols = new List<string> { "SPY", "QQQ", "IWM", "EFA", "EEM", "TLT", "GLD", "XLE", "XLF", "XLK" };
        private readonly Dictionary<Symbol, SymbolData> _symbolData = new Dictionary<Symbol, SymbolData>();
        
        // Risk Management
        private decimal _maxPositionSize = 0.10m; // 10% max position size
        private decimal _stopLossPercentage = 0.05m; // 5% stop loss
        private decimal _takeProfitPercentage = 0.15m; // 15% take profit
        private decimal _volatilityLookback = 20; // Days for volatility calculation
        
        // Technical Analysis Parameters
        private int _rsiPeriod = 14;
        private int _fastMaPeriod = 10;
        private int _slowMaPeriod = 30;
        private int _atrPeriod = 14;
        
        public override void Initialize()
        {
            SetStartDate(2020, 1, 1);
            SetEndDate(2024, 12, 31);
            SetCash(100000);
            
            // Add securities and create indicators
            foreach (var ticker in _symbols)
            {
                var symbol = AddEquity(ticker, Resolution.Daily).Symbol;
                
                var symbolData = new SymbolData
                {
                    Symbol = symbol,
                    RSI = RSI(symbol, _rsiPeriod, MovingAverageType.Wilders),
                    FastMA = SMA(symbol, _fastMaPeriod),
                    SlowMA = SMA(symbol, _slowMaPeriod),
                    ATR = ATR(symbol, _atrPeriod),
                    RollingWindow = new RollingWindow<decimal>(21) // For volatility calculation
                };
                
                _symbolData[symbol] = symbolData;
            }
            
            // Set benchmark
            SetBenchmark("SPY");
            
            // Schedule portfolio rebalancing
            Schedule.On(DateRules.WeekStart(), TimeRules.AfterMarketOpen("SPY", 30), Rebalance);
            
            Log("Momentum Mean Reversion Strategy Initialized");
        }
        
        public override void OnData(Slice data)
        {
            // Update rolling windows for volatility calculation
            foreach (var kvp in _symbolData)
            {
                var symbol = kvp.Key;
                var symbolData = kvp.Value;
                
                if (data.Bars.ContainsKey(symbol))
                {
                    var price = data.Bars[symbol].Close;
                    symbolData.RollingWindow.Add(price);
                }
            }
            
            // Check stop loss and take profit for existing positions
            ManageRiskForExistingPositions();
        }
        
        private void Rebalance()
        {
            var insights = GenerateInsights();
            
            foreach (var insight in insights)
            {
                var symbol = insight.Symbol;
                var direction = insight.Direction;
                var confidence = insight.Confidence;
                
                // Calculate position size based on volatility and confidence
                var positionSize = CalculatePositionSize(symbol, confidence);
                
                if (direction == InsightDirection.Up && positionSize > 0)
                {
                    SetHoldings(symbol, positionSize);
                    
                    // Set stop loss and take profit orders
                    var currentPrice = Securities[symbol].Price;
                    var stopPrice = currentPrice * (1 - _stopLossPercentage);
                    var limitPrice = currentPrice * (1 + _takeProfitPercentage);
                    
                    Log($"Long {symbol} at ${currentPrice:F2}, Stop: ${stopPrice:F2}, Target: ${limitPrice:F2}");
                }
                else if (direction == InsightDirection.Down && positionSize > 0)
                {
                    SetHoldings(symbol, -positionSize);
                    
                    // Set stop loss and take profit orders for short position
                    var currentPrice = Securities[symbol].Price;
                    var stopPrice = currentPrice * (1 + _stopLossPercentage);
                    var limitPrice = currentPrice * (1 - _takeProfitPercentage);
                    
                    Log($"Short {symbol} at ${currentPrice:F2}, Stop: ${stopPrice:F2}, Target: ${limitPrice:F2}");
                }
                else if (direction == InsightDirection.Flat)
                {
                    Liquidate(symbol);
                    Log($"Liquidated {symbol}");
                }
            }
        }
        
        private List<Insight> GenerateInsights()
        {
            var insights = new List<Insight>();
            
            foreach (var kvp in _symbolData)
            {
                var symbol = kvp.Key;
                var symbolData = kvp.Value;
                
                // Skip if indicators are not ready
                if (!symbolData.RSI.IsReady || !symbolData.FastMA.IsReady || !symbolData.SlowMA.IsReady)
                    continue;
                
                var rsi = symbolData.RSI.Current.Value;
                var fastMA = symbolData.FastMA.Current.Value;
                var slowMA = symbolData.SlowMA.Current.Value;
                var currentPrice = Securities[symbol].Price;
                
                // Generate signals
                var momentumSignal = GetMomentumSignal(fastMA, slowMA);
                var meanReversionSignal = GetMeanReversionSignal(rsi);
                
                // Combine signals
                var combinedSignal = CombineSignals(momentumSignal, meanReversionSignal);
                
                if (combinedSignal.Direction != InsightDirection.Flat)
                {
                    insights.Add(new Insight(symbol, TimeSpan.FromDays(5), combinedSignal.Direction, 
                                           combinedSignal.Magnitude, combinedSignal.Confidence));
                }
            }
            
            return insights;
        }
        
        private (InsightDirection Direction, double Magnitude, double Confidence) GetMomentumSignal(decimal fastMA, decimal slowMA)
        {
            var maRatio = (double)(fastMA / slowMA);
            
            if (maRatio > 1.02) // Fast MA 2% above slow MA
                return (InsightDirection.Up, Math.Min((maRatio - 1) * 10, 1.0), 0.6);
            else if (maRatio < 0.98) // Fast MA 2% below slow MA
                return (InsightDirection.Down, Math.Min((1 - maRatio) * 10, 1.0), 0.6);
            else
                return (InsightDirection.Flat, 0, 0);
        }
        
        private (InsightDirection Direction, double Magnitude, double Confidence) GetMeanReversionSignal(decimal rsi)
        {
            if (rsi < 30) // Oversold
                return (InsightDirection.Up, (double)(30 - rsi) / 30, 0.7);
            else if (rsi > 70) // Overbought
                return (InsightDirection.Down, (double)(rsi - 70) / 30, 0.7);
            else
                return (InsightDirection.Flat, 0, 0);
        }
        
        private (InsightDirection Direction, double Magnitude, double Confidence) CombineSignals(
            (InsightDirection Direction, double Magnitude, double Confidence) momentum,
            (InsightDirection Direction, double Magnitude, double Confidence) meanReversion)
        {
            // If both signals agree, increase confidence
            if (momentum.Direction == meanReversion.Direction && momentum.Direction != InsightDirection.Flat)
            {
                var combinedMagnitude = (momentum.Magnitude + meanReversion.Magnitude) / 2;
                var combinedConfidence = Math.Min(momentum.Confidence + meanReversion.Confidence, 1.0);
                return (momentum.Direction, combinedMagnitude, combinedConfidence);
            }
            
            // If signals disagree, use the stronger signal with reduced confidence
            if (momentum.Magnitude > meanReversion.Magnitude)
                return (momentum.Direction, momentum.Magnitude, momentum.Confidence * 0.5);
            else if (meanReversion.Magnitude > momentum.Magnitude)
                return (meanReversion.Direction, meanReversion.Magnitude, meanReversion.Confidence * 0.5);
            
            return (InsightDirection.Flat, 0, 0);
        }
        
        private decimal CalculatePositionSize(Symbol symbol, double confidence)
        {
            // Base position size adjusted by confidence and volatility
            var baseSize = _maxPositionSize * (decimal)confidence;
            
            // Adjust for volatility using ATR
            var symbolData = _symbolData[symbol];
            if (symbolData.ATR.IsReady && symbolData.RollingWindow.IsReady)
            {
                var atr = symbolData.ATR.Current.Value;
                var currentPrice = Securities[symbol].Price;
                var volatilityAdjustment = Math.Min(0.02m / (atr / currentPrice), 2.0m); // Inverse volatility scaling
                
                baseSize *= volatilityAdjustment;
            }
            
            return Math.Min(baseSize, _maxPositionSize);
        }
        
        private void ManageRiskForExistingPositions()
        {
            foreach (var holding in Portfolio.Values.Where(x => x.Invested))
            {
                var symbol = holding.Symbol;
                var currentPrice = Securities[symbol].Price;
                var avgPrice = holding.AveragePrice;
                var quantity = holding.Quantity;
                
                if (quantity > 0) // Long position
                {
                    var returnPct = (currentPrice - avgPrice) / avgPrice;
                    
                    if (returnPct <= -_stopLossPercentage || returnPct >= _takeProfitPercentage)
                    {
                        Liquidate(symbol);
                        var action = returnPct <= -_stopLossPercentage ? "Stop Loss" : "Take Profit";
                        Log($"{action} triggered for {symbol}: {returnPct:P2} return");
                    }
                }
                else if (quantity < 0) // Short position
                {
                    var returnPct = (avgPrice - currentPrice) / avgPrice;
                    
                    if (returnPct <= -_stopLossPercentage || returnPct >= _takeProfitPercentage)
                    {
                        Liquidate(symbol);
                        var action = returnPct <= -_stopLossPercentage ? "Stop Loss" : "Take Profit";
                        Log($"{action} triggered for {symbol}: {returnPct:P2} return");
                    }
                }
            }
        }
    }
    
    /// <summary>
    /// Container class for symbol-specific data and indicators
    /// </summary>
    public class SymbolData
    {
        public Symbol Symbol { get; set; }
        public RelativeStrengthIndex RSI { get; set; }
        public SimpleMovingAverage FastMA { get; set; }
        public SimpleMovingAverage SlowMA { get; set; }
        public AverageTrueRange ATR { get; set; }
        public RollingWindow<decimal> RollingWindow { get; set; }
    }
}

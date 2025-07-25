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
    /// Pairs Trading Strategy
    /// 
    /// This strategy implements statistical arbitrage by trading correlated pairs:
    /// - Identifies highly correlated pairs from a universe of stocks
    /// - Monitors the spread between pairs using z-score analysis
    /// - Opens positions when spreads deviate significantly from historical mean
    /// - Closes positions when spreads revert to the mean
    /// - Includes risk management and position sizing based on correlation strength
    /// </summary>
    public class PairsTrading : QCAlgorithm
    {
        // Strategy Parameters
        private readonly List<string> _universe = new List<string> 
        { 
            "XLF", "XLK", "XLE", "XLI", "XLV", "XLY", "XLP", "XLU", "XLB", "XLRE",
            "SPY", "QQQ", "IWM", "EFA", "VTI", "EEM", "TLT", "GLD", "UUP", "VIX"
        };
        
        private readonly Dictionary<string, PairData> _pairs = new Dictionary<string, PairData>();
        private readonly int _lookbackPeriod = 252; // 1 year of trading days
        private readonly int _correlationPeriod = 60; // 60 days for correlation calculation
        private readonly decimal _entryThreshold = 2.0m; // Z-score threshold for entry
        private readonly decimal _exitThreshold = 0.5m; // Z-score threshold for exit
        private readonly decimal _stopLossThreshold = 3.0m; // Z-score stop loss
        private readonly decimal _minCorrelation = 0.8m; // Minimum correlation for pair selection
        private readonly decimal _maxPositionSize = 0.05m; // 5% max position size per leg
        
        private DateTime _lastRebalanceTime;
        private readonly int _rebalancePeriod = 5; // Rebalance every 5 days
        
        public override void Initialize()
        {
            SetStartDate(2020, 1, 1);
            SetEndDate(2024, 12, 31);
            SetCash(100000);
            
            // Add securities
            foreach (var ticker in _universe)
            {
                AddEquity(ticker, Resolution.Daily);
            }
            
            SetBenchmark("SPY");
            
            // Schedule pair identification and rebalancing
            Schedule.On(DateRules.WeekStart(), TimeRules.AfterMarketOpen("SPY", 30), IdentifyAndRebalancePairs);
            
            _lastRebalanceTime = DateTime.MinValue;
            
            Log("Pairs Trading Strategy Initialized");
        }
        
        public override void OnData(Slice data)
        {
            // Update pair data with new prices
            foreach (var kvp in _pairs)
            {
                var pairData = kvp.Value;
                var symbol1 = pairData.Symbol1;
                var symbol2 = pairData.Symbol2;
                
                if (data.Bars.ContainsKey(symbol1) && data.Bars.ContainsKey(symbol2))
                {
                    var price1 = data.Bars[symbol1].Close;
                    var price2 = data.Bars[symbol2].Close;
                    
                    pairData.AddPrices(price1, price2);
                    
                    // Check for trading signals
                    CheckPairSignals(pairData);
                }
            }
        }
        
        private void IdentifyAndRebalancePairs()
        {
            if (Time.Subtract(_lastRebalanceTime).TotalDays < _rebalancePeriod)
                return;
                
            Log("Identifying and rebalancing pairs...");
            
            // Close existing positions
            Liquidate();
            _pairs.Clear();
            
            // Identify new pairs
            var correlationMatrix = CalculateCorrelationMatrix();
            var newPairs = SelectBestPairs(correlationMatrix);
            
            foreach (var pair in newPairs)
            {
                _pairs[pair.Key] = pair.Value;
            }
            
            _lastRebalanceTime = Time;
            
            Log($"Identified {_pairs.Count} pairs for trading");
        }
        
        private Dictionary<string, decimal[,]> CalculateCorrelationMatrix()
        {
            var priceHistory = new Dictionary<string, List<decimal>>();
            
            // Get price history for all symbols
            foreach (var ticker in _universe)
            {
                var symbol = QuantConnect.Symbol.Create(ticker, SecurityType.Equity, Market.USA);
                var history = History(symbol, _correlationPeriod, Resolution.Daily);
                
                if (history.Any())
                {
                    priceHistory[ticker] = history.Select(bar => bar.Close).ToList();
                }
            }
            
            // Calculate returns and correlations
            var correlations = new Dictionary<string, decimal[,]>();
            
            foreach (var ticker1 in priceHistory.Keys)
            {
                foreach (var ticker2 in priceHistory.Keys)
                {
                    if (ticker1 != ticker2)
                    {
                        var correlation = CalculateCorrelation(priceHistory[ticker1], priceHistory[ticker2]);
                        var key = $"{ticker1}_{ticker2}";
                        
                        if (!correlations.ContainsKey(key) && !correlations.ContainsKey($"{ticker2}_{ticker1}"))
                        {
                            correlations[key] = new decimal[,] { { correlation } };
                        }
                    }
                }
            }
            
            return correlations;
        }
        
        private decimal CalculateCorrelation(List<decimal> prices1, List<decimal> prices2)
        {
            if (prices1.Count != prices2.Count || prices1.Count < 2)
                return 0;
            
            // Calculate returns
            var returns1 = new List<decimal>();
            var returns2 = new List<decimal>();
            
            for (int i = 1; i < prices1.Count; i++)
            {
                if (prices1[i - 1] != 0 && prices2[i - 1] != 0)
                {
                    returns1.Add((prices1[i] - prices1[i - 1]) / prices1[i - 1]);
                    returns2.Add((prices2[i] - prices2[i - 1]) / prices2[i - 1]);
                }
            }
            
            if (returns1.Count < 2)
                return 0;
            
            // Calculate correlation coefficient
            var mean1 = returns1.Average();
            var mean2 = returns2.Average();
            
            var numerator = 0m;
            var sumSq1 = 0m;
            var sumSq2 = 0m;
            
            for (int i = 0; i < returns1.Count; i++)
            {
                var dev1 = returns1[i] - mean1;
                var dev2 = returns2[i] - mean2;
                
                numerator += dev1 * dev2;
                sumSq1 += dev1 * dev1;
                sumSq2 += dev2 * dev2;
            }
            
            var denominator = (decimal)Math.Sqrt((double)(sumSq1 * sumSq2));
            
            return denominator == 0 ? 0 : numerator / denominator;
        }
        
        private Dictionary<string, PairData> SelectBestPairs(Dictionary<string, decimal[,]> correlationMatrix)
        {
            var bestPairs = new Dictionary<string, PairData>();
            
            foreach (var kvp in correlationMatrix)
            {
                var correlation = kvp.Value[0, 0];
                
                if (Math.Abs(correlation) >= _minCorrelation)
                {
                    var symbols = kvp.Key.Split('_');
                    var symbol1 = QuantConnect.Symbol.Create(symbols[0], SecurityType.Equity, Market.USA);
                    var symbol2 = QuantConnect.Symbol.Create(symbols[1], SecurityType.Equity, Market.USA);
                    
                    var pairData = new PairData(symbol1, symbol2, _lookbackPeriod);
                    pairData.Correlation = correlation;
                    
                    bestPairs[kvp.Key] = pairData;
                    
                    if (bestPairs.Count >= 5) // Limit to top 5 pairs
                        break;
                }
            }
            
            return bestPairs;
        }
        
        private void CheckPairSignals(PairData pairData)
        {
            if (!pairData.IsReady())
                return;
                
            var zScore = pairData.GetCurrentZScore();
            var isLong = Portfolio[pairData.Symbol1].IsLong;
            var isShort = Portfolio[pairData.Symbol1].IsShort;
            
            // Entry signals
            if (!isLong && !isShort)
            {
                if (zScore > _entryThreshold)
                {
                    // Short the spread (short symbol1, long symbol2)
                    SetHoldings(pairData.Symbol1, -_maxPositionSize);
                    SetHoldings(pairData.Symbol2, _maxPositionSize);
                    
                    Log($"Entered short spread for {pairData.Symbol1}/{pairData.Symbol2} at z-score: {zScore:F2}");
                }
                else if (zScore < -_entryThreshold)
                {
                    // Long the spread (long symbol1, short symbol2)
                    SetHoldings(pairData.Symbol1, _maxPositionSize);
                    SetHoldings(pairData.Symbol2, -_maxPositionSize);
                    
                    Log($"Entered long spread for {pairData.Symbol1}/{pairData.Symbol2} at z-score: {zScore:F2}");
                }
            }
            // Exit signals
            else
            {
                var shouldExit = Math.Abs(zScore) < _exitThreshold || Math.Abs(zScore) > _stopLossThreshold;
                
                if (shouldExit)
                {
                    Liquidate(pairData.Symbol1);
                    Liquidate(pairData.Symbol2);
                    
                    var reason = Math.Abs(zScore) > _stopLossThreshold ? "Stop Loss" : "Mean Reversion";
                    Log($"Exited {pairData.Symbol1}/{pairData.Symbol2} - {reason} at z-score: {zScore:F2}");
                }
            }
        }
    }
    
    /// <summary>
    /// Container class for pair trading data and calculations
    /// </summary>
    public class PairData
    {
        public Symbol Symbol1 { get; }
        public Symbol Symbol2 { get; }
        public decimal Correlation { get; set; }
        
        private readonly RollingWindow<decimal> _spreadWindow;
        private readonly RollingWindow<decimal> _ratio1Window;
        private readonly RollingWindow<decimal> _ratio2Window;
        private readonly int _lookbackPeriod;
        
        public PairData(Symbol symbol1, Symbol symbol2, int lookbackPeriod)
        {
            Symbol1 = symbol1;
            Symbol2 = symbol2;
            _lookbackPeriod = lookbackPeriod;
            
            _spreadWindow = new RollingWindow<decimal>(lookbackPeriod);
            _ratio1Window = new RollingWindow<decimal>(lookbackPeriod);
            _ratio2Window = new RollingWindow<decimal>(lookbackPeriod);
        }
        
        public void AddPrices(decimal price1, decimal price2)
        {
            if (price2 != 0)
            {
                var ratio = price1 / price2;
                var logRatio = (decimal)Math.Log((double)ratio);
                
                _spreadWindow.Add(logRatio);
                _ratio1Window.Add(price1);
                _ratio2Window.Add(price2);
            }
        }
        
        public bool IsReady()
        {
            return _spreadWindow.IsReady;
        }
        
        public decimal GetCurrentZScore()
        {
            if (!IsReady())
                return 0;
                
            var currentSpread = _spreadWindow[0];
            var mean = _spreadWindow.Average();
            var variance = _spreadWindow.Select(x => (x - mean) * (x - mean)).Average();
            var stdDev = (decimal)Math.Sqrt((double)variance);
            
            return stdDev == 0 ? 0 : (currentSpread - mean) / stdDev;
        }
    }
}

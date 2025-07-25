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
    /// Sector Rotation Strategy
    /// 
    /// This strategy implements tactical asset allocation by rotating between sector ETFs:
    /// - Ranks sectors based on momentum, relative strength, and fundamental factors
    /// - Allocates capital to top-performing sectors dynamically
    /// - Uses multiple timeframes for trend analysis
    /// - Includes risk management through volatility monitoring and position sizing
    /// - Incorporates market regime detection for adaptive positioning
    /// </summary>
    public class SectorRotation : QCAlgorithm
    {
        // Sector ETFs Universe
        private readonly Dictionary<string, string> _sectorETFs = new Dictionary<string, string>
        {
            {"XLK", "Technology"},
            {"XLF", "Financial"},
            {"XLV", "Healthcare"},
            {"XLE", "Energy"},
            {"XLI", "Industrial"},
            {"XLY", "Consumer Discretionary"},
            {"XLP", "Consumer Staples"},
            {"XLU", "Utilities"},
            {"XLB", "Materials"},
            {"XLRE", "Real Estate"}
        };
        
        // Benchmark and Safe Haven Assets
        private readonly string _benchmark = "SPY";
        private readonly string _safeHaven = "TLT"; // Treasury bonds
        private readonly string _cash = "SHY"; // Short-term treasuries
        
        // Strategy Parameters
        private readonly int _topSectorsCount = 3; // Number of top sectors to hold
        private readonly int _rebalancePeriod = 21; // Rebalance every 21 days
        private readonly int _momentumPeriod = 126; // 6 months momentum
        private readonly int _relativeStrengthPeriod = 63; // 3 months relative strength
        private readonly int _volatilityPeriod = 21; // 1 month volatility
        private readonly decimal _maxSectorWeight = 0.4m; // Maximum weight per sector
        private readonly decimal _minCashWeight = 0.1m; // Minimum cash allocation
        private readonly decimal _volatilityThreshold = 0.25m; // High volatility threshold
        
        // Data Storage
        private readonly Dictionary<Symbol, SectorData> _sectorData = new Dictionary<Symbol, SectorData>();
        private Symbol _benchmarkSymbol;
        private Symbol _safeHavenSymbol;
        private Symbol _cashSymbol;
        private DateTime _lastRebalanceTime;
        
        // Market Regime Indicators
        private SimpleMovingAverage _benchmarkMA50;
        private SimpleMovingAverage _benchmarkMA200;
        private RelativeStrengthIndex _benchmarkRSI;
        private AverageTrueRange _benchmarkATR;
        
        public override void Initialize()
        {
            SetStartDate(2018, 1, 1);
            SetEndDate(2024, 12, 31);
            SetCash(100000);
            
            // Add benchmark and safe haven assets
            _benchmarkSymbol = AddEquity(_benchmark, Resolution.Daily).Symbol;
            _safeHavenSymbol = AddEquity(_safeHaven, Resolution.Daily).Symbol;
            _cashSymbol = AddEquity(_cash, Resolution.Daily).Symbol;
            
            // Initialize benchmark indicators for market regime detection
            _benchmarkMA50 = SMA(_benchmarkSymbol, 50);
            _benchmarkMA200 = SMA(_benchmarkSymbol, 200);
            _benchmarkRSI = RSI(_benchmarkSymbol, 14, MovingAverageType.Wilders);
            _benchmarkATR = ATR(_benchmarkSymbol, 20);
            
            // Add sector ETFs and initialize indicators
            foreach (var kvp in _sectorETFs)
            {
                var symbol = AddEquity(kvp.Key, Resolution.Daily).Symbol;
                
                var sectorData = new SectorData
                {
                    Symbol = symbol,
                    SectorName = kvp.Value,
                    Momentum = MOMP(symbol, _momentumPeriod),
                    RelativeStrength = new RelativeStrengthIndex(symbol, _benchmarkSymbol, _relativeStrengthPeriod),
                    Volatility = StandardDeviation(symbol, _volatilityPeriod),
                    MA20 = SMA(symbol, 20),
                    MA50 = SMA(symbol, 50),
                    PriceHistory = new RollingWindow<decimal>(252)
                };
                
                _sectorData[symbol] = sectorData;
            }
            
            SetBenchmark(_benchmark);
            
            // Schedule monthly rebalancing
            Schedule.On(DateRules.MonthStart(), TimeRules.AfterMarketOpen(_benchmark, 30), Rebalance);
            
            _lastRebalanceTime = DateTime.MinValue;
            
            Log("Sector Rotation Strategy Initialized");
        }
        
        public override void OnData(Slice data)
        {
            // Update sector data
            foreach (var kvp in _sectorData)
            {
                var symbol = kvp.Key;
                var sectorData = kvp.Value;
                
                if (data.Bars.ContainsKey(symbol))
                {
                    var price = data.Bars[symbol].Close;
                    sectorData.PriceHistory.Add(price);
                }
            }
            
            // Check for rebalancing
            if (Time.Subtract(_lastRebalanceTime).TotalDays >= _rebalancePeriod)
            {
                Rebalance();
            }
        }
        
        private void Rebalance()
        {
            Log("Starting sector rotation rebalancing...");
            
            // Assess market regime
            var marketRegime = AssessMarketRegime();
            Log($"Market Regime: {marketRegime}");
            
            // Rank sectors
            var sectorRankings = RankSectors();
            
            // Determine allocation based on market regime
            var allocation = DetermineAllocation(sectorRankings, marketRegime);
            
            // Execute trades
            ExecuteAllocation(allocation);
            
            _lastRebalanceTime = Time;
            
            LogPortfolioStatus(allocation);
        }
        
        private MarketRegime AssessMarketRegime()
        {
            if (!_benchmarkMA50.IsReady || !_benchmarkMA200.IsReady || !_benchmarkRSI.IsReady)
                return MarketRegime.Neutral;
            
            var currentPrice = Securities[_benchmarkSymbol].Price;
            var ma50 = _benchmarkMA50.Current.Value;
            var ma200 = _benchmarkMA200.Current.Value;
            var rsi = _benchmarkRSI.Current.Value;
            
            // Bull market: Price above both MAs, RSI not oversold
            if (currentPrice > ma50 && ma50 > ma200 && rsi > 30)
                return MarketRegime.Bullish;
            
            // Bear market: Price below both MAs, RSI not overbought
            if (currentPrice < ma50 && ma50 < ma200 && rsi < 70)
                return MarketRegime.Bearish;
            
            // High volatility: Based on ATR
            if (_benchmarkATR.IsReady)
            {
                var volatility = _benchmarkATR.Current.Value / currentPrice;
                if (volatility > _volatilityThreshold)
                    return MarketRegime.HighVolatility;
            }
            
            return MarketRegime.Neutral;
        }
        
        private List<(Symbol Symbol, decimal Score)> RankSectors()
        {
            var rankings = new List<(Symbol Symbol, decimal Score)>();
            
            foreach (var kvp in _sectorData)
            {
                var symbol = kvp.Key;
                var sectorData = kvp.Value;
                
                // Skip if indicators are not ready
                if (!sectorData.Momentum.IsReady || !sectorData.Volatility.IsReady || !sectorData.MA20.IsReady)
                    continue;
                
                var score = CalculateSectorScore(sectorData);
                rankings.Add((symbol, score));
            }
            
            return rankings.OrderByDescending(x => x.Score).ToList();
        }
        
        private decimal CalculateSectorScore(SectorData sectorData)
        {
            decimal score = 0;
            
            // Momentum component (40% weight)
            if (sectorData.Momentum.IsReady)
            {
                var momentum = sectorData.Momentum.Current.Value;
                score += momentum * 0.4m;
            }
            
            // Relative strength component (30% weight)
            if (sectorData.RelativeStrength.IsReady)
            {
                var relativeStrength = sectorData.RelativeStrength.Current.Value;
                score += (relativeStrength - 50) / 50 * 0.3m; // Normalize RSI to -1 to 1
            }
            
            // Trend component (20% weight)
            if (sectorData.MA20.IsReady && sectorData.MA50.IsReady)
            {
                var currentPrice = Securities[sectorData.Symbol].Price;
                var trendScore = 0m;
                
                if (currentPrice > sectorData.MA20.Current.Value) trendScore += 0.5m;
                if (sectorData.MA20.Current.Value > sectorData.MA50.Current.Value) trendScore += 0.5m;
                
                score += trendScore * 0.2m;
            }
            
            // Volatility penalty (10% weight) - prefer lower volatility
            if (sectorData.Volatility.IsReady)
            {
                var volatility = sectorData.Volatility.Current.Value;
                var volatilityScore = Math.Max(0, 1 - volatility); // Inverse relationship
                score += volatilityScore * 0.1m;
            }
            
            return score;
        }
        
        private Dictionary<Symbol, decimal> DetermineAllocation(List<(Symbol Symbol, decimal Score)> rankings, MarketRegime regime)
        {
            var allocation = new Dictionary<Symbol, decimal>();
            
            switch (regime)
            {
                case MarketRegime.Bullish:
                    // Aggressive allocation to top sectors
                    AllocateToTopSectors(allocation, rankings, 0.9m, _topSectorsCount);
                    allocation[_cashSymbol] = 0.1m;
                    break;
                    
                case MarketRegime.Bearish:
                    // Defensive allocation
                    AllocateToTopSectors(allocation, rankings, 0.4m, 2);
                    allocation[_safeHavenSymbol] = 0.3m;
                    allocation[_cashSymbol] = 0.3m;
                    break;
                    
                case MarketRegime.HighVolatility:
                    // Conservative allocation
                    AllocateToTopSectors(allocation, rankings, 0.5m, 2);
                    allocation[_safeHavenSymbol] = 0.25m;
                    allocation[_cashSymbol] = 0.25m;
                    break;
                    
                default: // Neutral
                    // Balanced allocation
                    AllocateToTopSectors(allocation, rankings, 0.7m, _topSectorsCount);
                    allocation[_safeHavenSymbol] = 0.15m;
                    allocation[_cashSymbol] = 0.15m;
                    break;
            }
            
            return allocation;
        }
        
        private void AllocateToTopSectors(Dictionary<Symbol, decimal> allocation, 
            List<(Symbol Symbol, decimal Score)> rankings, decimal totalSectorWeight, int sectorCount)
        {
            var topSectors = rankings.Take(sectorCount).ToList();
            
            if (topSectors.Any())
            {
                var totalScore = topSectors.Sum(x => Math.Max(x.Score, 0.1m)); // Ensure positive scores
                
                foreach (var sector in topSectors)
                {
                    var weight = Math.Max(sector.Score, 0.1m) / totalScore * totalSectorWeight;
                    weight = Math.Min(weight, _maxSectorWeight); // Apply maximum weight constraint
                    allocation[sector.Symbol] = weight;
                }
            }
        }
        
        private void ExecuteAllocation(Dictionary<Symbol, decimal> targetAllocation)
        {
            foreach (var kvp in targetAllocation)
            {
                var symbol = kvp.Key;
                var targetWeight = kvp.Value;
                
                SetHoldings(symbol, targetWeight);
            }
        }
        
        private void LogPortfolioStatus(Dictionary<Symbol, decimal> allocation)
        {
            Log("Current Portfolio Allocation:");
            foreach (var kvp in allocation)
            {
                var sectorName = _sectorETFs.ContainsKey(kvp.Key.Value) ? 
                    _sectorETFs[kvp.Key.Value] : kvp.Key.Value;
                Log($"  {sectorName}: {kvp.Value:P2}");
            }
            
            Log($"Total Portfolio Value: ${Portfolio.TotalPortfolioValue:F2}");
        }
    }
    
    /// <summary>
    /// Market regime enumeration
    /// </summary>
    public enum MarketRegime
    {
        Bullish,
        Bearish,
        Neutral,
        HighVolatility
    }
    
    /// <summary>
    /// Container for sector-specific data and indicators
    /// </summary>
    public class SectorData
    {
        public Symbol Symbol { get; set; }
        public string SectorName { get; set; }
        public MomentumPercent Momentum { get; set; }
        public RelativeStrengthIndex RelativeStrength { get; set; }
        public StandardDeviation Volatility { get; set; }
        public SimpleMovingAverage MA20 { get; set; }
        public SimpleMovingAverage MA50 { get; set; }
        public RollingWindow<decimal> PriceHistory { get; set; }
    }
    
    /// <summary>
    /// Custom relative strength indicator comparing sector to benchmark
    /// </summary>
    public class RelativeStrengthIndex : IndicatorBase<IndicatorDataPoint>
    {
        private readonly Symbol _sectorSymbol;
        private readonly Symbol _benchmarkSymbol;
        private readonly RollingWindow<decimal> _sectorReturns;
        private readonly RollingWindow<decimal> _benchmarkReturns;
        private readonly int _period;
        
        public RelativeStrengthIndex(Symbol sectorSymbol, Symbol benchmarkSymbol, int period)
            : base($"RS_{sectorSymbol}_{benchmarkSymbol}_{period}")
        {
            _sectorSymbol = sectorSymbol;
            _benchmarkSymbol = benchmarkSymbol;
            _period = period;
            _sectorReturns = new RollingWindow<decimal>(period);
            _benchmarkReturns = new RollingWindow<decimal>(period);
        }
        
        public override bool IsReady => _sectorReturns.IsReady && _benchmarkReturns.IsReady;
        
        protected override decimal ComputeNextValue(IndicatorDataPoint input)
        {
            // This is a simplified implementation - in practice, you'd need to feed both sector and benchmark data
            return 50; // Placeholder - would implement proper relative strength calculation
        }
    }
}

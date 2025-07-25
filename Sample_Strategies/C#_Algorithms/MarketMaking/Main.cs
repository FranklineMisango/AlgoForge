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
    /// Market Making Strategy
    /// 
    /// This strategy implements a market making approach that provides liquidity:
    /// - Places simultaneous buy and sell limit orders around the current market price
    /// - Captures the bid-ask spread as profit
    /// - Uses dynamic spread calculation based on volatility and market conditions
    /// - Implements inventory management to avoid excessive exposure
    /// - Features adaptive position sizing and risk management
    /// - Includes market microstructure analysis for optimal placement
    /// </summary>
    public class MarketMaking : QCAlgorithm
    {
        // Trading Universe - Focus on high-volume, liquid ETFs
        private readonly List<string> _universe = new List<string>
        {
            "SPY", "QQQ", "IWM", "EFA", "VTI", "EEM", "TLT", "GLD", "XLF", "XLK"
        };
        
        // Strategy Parameters
        private readonly decimal _targetSpreadBps = 5m; // Target spread in basis points
        private readonly decimal _maxInventoryPct = 0.02m; // Maximum inventory per symbol (2%)
        private readonly decimal _quoteRefreshSeconds = 30; // How often to refresh quotes
        private readonly decimal _maxOrderSizePct = 0.005m; // Maximum order size (0.5% of portfolio)
        private readonly decimal _minSpreadBps = 2m; // Minimum spread to maintain profitability
        private readonly decimal _maxSpreadBps = 20m; // Maximum spread to maintain competitiveness
        private readonly decimal _volatilityLookback = 20; // Days for volatility calculation
        private readonly decimal _profitTargetBps = 3m; // Profit target per trade in basis points
        
        // Data Storage
        private readonly Dictionary<Symbol, MarketMakingData> _symbolData = new Dictionary<Symbol, MarketMakingData>();
        private readonly Dictionary<Symbol, List<OrderTicket>> _activeOrders = new Dictionary<Symbol, List<OrderTicket>>();
        private readonly Dictionary<Symbol, decimal> _inventory = new Dictionary<Symbol, decimal>();
        private readonly Dictionary<Symbol, DateTime> _lastQuoteTime = new Dictionary<Symbol, DateTime>();
        
        // Market Regime Detection
        private SimpleMovingAverage _marketMA;
        private AverageTrueRange _marketATR;
        private Symbol _marketSymbol;
        
        // Performance Tracking
        private decimal _totalSpreadCapture = 0;
        private int _successfulRoundTrips = 0;
        private int _totalQuotes = 0;
        
        public override void Initialize()
        {
            SetStartDate(2022, 1, 1);
            SetEndDate(2024, 12, 31);
            SetCash(500000); // Larger capital for market making
            
            // Market regime indicators
            _marketSymbol = AddEquity("SPY", Resolution.Minute).Symbol;
            _marketMA = SMA(_marketSymbol, 50);
            _marketATR = ATR(_marketSymbol, 20);
            
            // Add securities and initialize data
            foreach (var ticker in _universe)
            {
                var symbol = AddEquity(ticker, Resolution.Minute).Symbol;
                
                // Set up market making data
                var marketData = new MarketMakingData
                {
                    Symbol = symbol,
                    ATR = ATR(symbol, 14),
                    SMA = SMA(symbol, 20),
                    Volume = SMA(symbol, 20, Field.Volume),
                    PriceHistory = new RollingWindow<decimal>(100),
                    VolumeHistory = new RollingWindow<decimal>(50),
                    LastMidPrice = 0,
                    LastSpread = 0
                };
                
                _symbolData[symbol] = marketData;
                _activeOrders[symbol] = new List<OrderTicket>();
                _inventory[symbol] = 0;
                _lastQuoteTime[symbol] = DateTime.MinValue;
                
                // Set custom fee model for market making (lower fees)
                Securities[symbol].FeeModel = new ConstantFeeModel(0.001m); // $0.001 per share
            }
            
            SetBenchmark("SPY");
            
            // Schedule market making activities
            Schedule.On(DateRules.EveryDay(), TimeRules.Every(TimeSpan.FromSeconds(30)), UpdateQuotes);
            Schedule.On(DateRules.EveryDay(), TimeRules.Every(TimeSpan.FromMinutes(5)), ManageInventory);
            Schedule.On(DateRules.EveryDay(), TimeRules.At(9, 35), OnMarketOpen);
            Schedule.On(DateRules.EveryDay(), TimeRules.BeforeMarketClose("SPY", 15), OnMarketClose);
            
            Log("Market Making Strategy Initialized");
        }
        
        public override void OnData(Slice data)
        {
            // Update symbol data with new market information
            foreach (var kvp in _symbolData)
            {
                var symbol = kvp.Key;
                var symbolData = kvp.Value;
                
                if (data.Bars.ContainsKey(symbol))
                {
                    var bar = data.Bars[symbol];
                    symbolData.PriceHistory.Add(bar.Close);
                    symbolData.VolumeHistory.Add(bar.Volume);
                    symbolData.LastMidPrice = bar.Close;
                }
                
                // Update bid-ask spread from ticks if available
                if (data.Ticks.ContainsKey(symbol))
                {
                    UpdateBidAskData(symbol, data.Ticks[symbol]);
                }
            }
        }
        
        private void UpdateBidAskData(Symbol symbol, List<Tick> ticks)
        {
            var symbolData = _symbolData[symbol];
            
            foreach (var tick in ticks)
            {
                if (tick.TickType == TickType.Quote)
                {
                    var bid = tick.BidPrice;
                    var ask = tick.AskPrice;
                    
                    if (bid > 0 && ask > 0 && ask > bid)
                    {
                        symbolData.LastBid = bid;
                        symbolData.LastAsk = ask;
                        symbolData.LastSpread = ask - bid;
                        symbolData.LastMidPrice = (bid + ask) / 2;
                    }
                }
            }
        }
        
        private void UpdateQuotes()
        {
            if (!IsMarketOpen(_marketSymbol))
                return;
            
            foreach (var kvp in _symbolData)
            {
                var symbol = kvp.Key;
                var symbolData = kvp.Value;
                
                // Skip if not enough data or too recent quote
                if (!ShouldUpdateQuotes(symbol, symbolData))
                    continue;
                
                // Cancel existing orders
                CancelActiveOrders(symbol);
                
                // Calculate optimal spread and size
                var quoteParams = CalculateOptimalQuote(symbol, symbolData);
                
                if (quoteParams != null)
                {
                    PlaceMarketMakingOrders(symbol, quoteParams);
                    _lastQuoteTime[symbol] = Time;
                    _totalQuotes++;
                }
            }
        }
        
        private bool ShouldUpdateQuotes(Symbol symbol, MarketMakingData symbolData)
        {
            // Check if enough time has passed since last quote
            if (Time.Subtract(_lastQuoteTime[symbol]).TotalSeconds < _quoteRefreshSeconds)
                return false;
            
            // Check if we have sufficient data
            if (!symbolData.ATR.IsReady || !symbolData.SMA.IsReady || !symbolData.Volume.IsReady)
                return false;
            
            // Check if market is liquid enough
            if (symbolData.VolumeHistory.IsReady)
            {
                var avgVolume = symbolData.VolumeHistory.Average();
                if (avgVolume < 100000) // Minimum average volume threshold
                    return false;
            }
            
            // Check if price is stable enough for market making
            var currentPrice = Securities[symbol].Price;
            if (currentPrice < 10) // Avoid low-priced stocks
                return false;
            
            return true;
        }
        
        private QuoteParameters CalculateOptimalQuote(Symbol symbol, MarketMakingData symbolData)
        {
            var currentPrice = symbolData.LastMidPrice > 0 ? symbolData.LastMidPrice : Securities[symbol].Price;
            
            if (currentPrice <= 0)
                return null;
            
            // Calculate volatility-adjusted spread
            var baseSpread = CalculateDynamicSpread(symbol, symbolData, currentPrice);
            
            // Adjust spread based on inventory
            var inventoryAdjustment = CalculateInventoryAdjustment(symbol);
            var adjustedSpread = baseSpread * (1 + inventoryAdjustment);
            
            // Ensure spread is within bounds
            var spreadBps = Math.Max(_minSpreadBps, Math.Min(_maxSpreadBps, adjustedSpread));
            var spreadAmount = currentPrice * spreadBps / 10000m;
            
            // Calculate order size
            var orderSize = CalculateOrderSize(symbol, currentPrice);
            
            if (orderSize <= 0)
                return null;
            
            return new QuoteParameters
            {
                MidPrice = currentPrice,
                Spread = spreadAmount,
                OrderSize = orderSize,
                BidPrice = currentPrice - spreadAmount / 2,
                AskPrice = currentPrice + spreadAmount / 2
            };
        }
        
        private decimal CalculateDynamicSpread(Symbol symbol, MarketMakingData symbolData, decimal currentPrice)
        {
            var baseSpread = _targetSpreadBps;
            
            // Volatility adjustment
            if (symbolData.ATR.IsReady)
            {
                var atrPct = symbolData.ATR.Current.Value / currentPrice;
                var volatilityMultiplier = Math.Max(0.5m, Math.Min(3.0m, atrPct * 100)); // Scale ATR percentage
                baseSpread *= volatilityMultiplier;
            }
            
            // Market regime adjustment
            if (_marketMA.IsReady && _marketATR.IsReady)
            {
                var marketPrice = Securities[_marketSymbol].Price;
                var marketMA = _marketMA.Current.Value;
                var marketVolatility = _marketATR.Current.Value / marketPrice;
                
                // Increase spread during high volatility periods
                if (marketVolatility > 0.02m) // 2% daily volatility
                {
                    baseSpread *= 1.5m;
                }
                
                // Increase spread when market is trending strongly
                var trendStrength = Math.Abs(marketPrice - marketMA) / marketMA;
                if (trendStrength > 0.03m) // 3% deviation from MA
                {
                    baseSpread *= 1.2m;
                }
            }
            
            // Time of day adjustment
            var timeOfDay = Time.TimeOfDay;
            if (timeOfDay < TimeSpan.FromHours(10) || timeOfDay > TimeSpan.FromHours(15))
            {
                baseSpread *= 1.3m; // Wider spreads during less liquid hours
            }
            
            return baseSpread;
        }
        
        private decimal CalculateInventoryAdjustment(Symbol symbol)
        {
            var currentInventory = _inventory[symbol];
            var maxInventory = Portfolio.TotalPortfolioValue * _maxInventoryPct;
            var currentValue = Math.Abs(currentInventory * Securities[symbol].Price);
            
            if (maxInventory == 0)
                return 0;
            
            var inventoryRatio = currentValue / maxInventory;
            
            // Skew quotes away from inventory position
            if (currentInventory > 0) // Long inventory, encourage selling
            {
                return inventoryRatio * 0.5m; // Widen ask more than bid
            }
            else if (currentInventory < 0) // Short inventory, encourage buying
            {
                return inventoryRatio * 0.5m; // Widen bid more than ask
            }
            
            return 0;
        }
        
        private decimal CalculateOrderSize(Symbol symbol, decimal currentPrice)
        {
            var maxOrderValue = Portfolio.TotalPortfolioValue * _maxOrderSizePct;
            var maxShares = (int)(maxOrderValue / currentPrice);
            
            // Adjust for current inventory
            var currentInventory = Math.Abs(_inventory[symbol]);
            var maxInventoryShares = (int)(Portfolio.TotalPortfolioValue * _maxInventoryPct / currentPrice);
            
            // Reduce order size if approaching inventory limits
            var availableInventorySpace = Math.Max(0, maxInventoryShares - (int)currentInventory);
            var orderSize = Math.Min(maxShares, availableInventorySpace);
            
            // Minimum order size
            return Math.Max(orderSize, 100);
        }
        
        private void PlaceMarketMakingOrders(Symbol symbol, QuoteParameters quoteParams)
        {
            var bidSize = (int)quoteParams.OrderSize;
            var askSize = (int)quoteParams.OrderSize;
            
            // Adjust order sizes based on inventory bias
            var currentInventory = _inventory[symbol];
            if (currentInventory > 0) // Long inventory, favor selling
            {
                askSize = (int)(askSize * 1.5m);
                bidSize = (int)(bidSize * 0.7m);
            }
            else if (currentInventory < 0) // Short inventory, favor buying
            {
                bidSize = (int)(bidSize * 1.5m);
                askSize = (int)(askSize * 0.7m);
            }
            
            // Place bid order
            if (bidSize > 0)
            {
                var bidOrder = LimitOrder(symbol, bidSize, quoteParams.BidPrice);
                if (bidOrder != null)
                {
                    _activeOrders[symbol].Add(bidOrder);
                }
            }
            
            // Place ask order
            if (askSize > 0)
            {
                var askOrder = LimitOrder(symbol, -askSize, quoteParams.AskPrice);
                if (askOrder != null)
                {
                    _activeOrders[symbol].Add(askOrder);
                }
            }
            
            Log($"Market Making {symbol}: Bid {bidSize}@{quoteParams.BidPrice:F2}, Ask {askSize}@{quoteParams.AskPrice:F2}");
        }
        
        private void CancelActiveOrders(Symbol symbol)
        {
            var orders = _activeOrders[symbol].ToList();
            foreach (var order in orders)
            {
                if (order.Status == OrderStatus.Submitted || order.Status == OrderStatus.PartiallyFilled)
                {
                    order.Cancel();
                }
            }
            _activeOrders[symbol].Clear();
        }
        
        private void ManageInventory()
        {
            foreach (var kvp in _inventory.ToList())
            {
                var symbol = kvp.Key;
                var position = kvp.Value;
                var maxInventory = Portfolio.TotalPortfolioValue * _maxInventoryPct / Securities[symbol].Price;
                
                // Force inventory reduction if exceeding limits
                if (Math.Abs(position) > maxInventory)
                {
                    var excessPosition = Math.Abs(position) - maxInventory;
                    var liquidationSize = (int)(excessPosition * 0.5m); // Liquidate 50% of excess
                    
                    if (position > 0)
                    {
                        MarketOrder(symbol, -liquidationSize);
                        Log($"Inventory liquidation: Selling {liquidationSize} shares of {symbol}");
                    }
                    else
                    {
                        MarketOrder(symbol, liquidationSize);
                        Log($"Inventory liquidation: Buying {liquidationSize} shares of {symbol}");
                    }
                }
            }
        }
        
        private void OnMarketOpen()
        {
            Log("Market opened - Initializing market making activities");
            
            // Cancel all orders from previous session
            foreach (var symbol in _activeOrders.Keys.ToList())
            {
                CancelActiveOrders(symbol);
            }
        }
        
        private void OnMarketClose()
        {
            Log("Market closing - Winding down market making activities");
            
            // Cancel all active orders
            foreach (var symbol in _activeOrders.Keys.ToList())
            {
                CancelActiveOrders(symbol);
            }
            
            // Log daily performance
            LogDailyPerformance();
        }
        
        public override void OnOrderEvent(OrderEvent orderEvent)
        {
            var symbol = orderEvent.Symbol;
            
            if (orderEvent.Status == OrderStatus.Filled)
            {
                // Update inventory
                _inventory[symbol] = _inventory.GetValueOrDefault(symbol, 0) + orderEvent.FillQuantity;
                
                // Calculate spread capture
                var symbolData = _symbolData[symbol];
                if (symbolData.LastMidPrice > 0)
                {
                    var expectedSpread = Math.Abs(orderEvent.FillPrice - symbolData.LastMidPrice);
                    _totalSpreadCapture += expectedSpread * Math.Abs(orderEvent.FillQuantity);
                }
                
                // Check for completed round trips
                CheckForRoundTrips(symbol);
                
                Log($"Order filled: {orderEvent.Symbol} {orderEvent.FillQuantity}@{orderEvent.FillPrice:F2}");
            }
            else if (orderEvent.Status == OrderStatus.Canceled)
            {
                // Remove from active orders
                var activeOrders = _activeOrders[symbol];
                var orderToRemove = activeOrders.FirstOrDefault(o => o.OrderId == orderEvent.OrderId);
                if (orderToRemove != null)
                {
                    activeOrders.Remove(orderToRemove);
                }
            }
        }
        
        private void CheckForRoundTrips(Symbol symbol)
        {
            var currentPosition = _inventory[symbol];
            var transactions = Transactions.GetOrderTickets(t => t.Symbol == symbol && t.Status == OrderStatus.Filled);
            
            // Simple round trip detection - look for position returning to zero
            if (Math.Abs(currentPosition) < 100 && transactions.Count() >= 2)
            {
                _successfulRoundTrips++;
            }
        }
        
        private void LogDailyPerformance()
        {
            var totalPnL = Portfolio.TotalUnrealizedProfit + Portfolio.TotalRealizedProfit;
            var totalValue = Portfolio.TotalPortfolioValue;
            
            Log("=== Daily Market Making Performance ===");
            Log($"Total Portfolio Value: ${totalValue:F2}");
            Log($"Total PnL: ${totalPnL:F2}");
            Log($"Total Quotes: {_totalQuotes}");
            Log($"Successful Round Trips: {_successfulRoundTrips}");
            Log($"Total Spread Capture: ${_totalSpreadCapture:F2}");
            
            // Log current inventory
            Log("Current Inventory:");
            foreach (var kvp in _inventory)
            {
                if (Math.Abs(kvp.Value) > 0)
                {
                    var value = kvp.Value * Securities[kvp.Key].Price;
                    Log($"  {kvp.Key}: {kvp.Value:F0} shares (${value:F2})");
                }
            }
        }
    }
    
    /// <summary>
    /// Container for market making data and indicators
    /// </summary>
    public class MarketMakingData
    {
        public Symbol Symbol { get; set; }
        public AverageTrueRange ATR { get; set; }
        public SimpleMovingAverage SMA { get; set; }
        public SimpleMovingAverage Volume { get; set; }
        public RollingWindow<decimal> PriceHistory { get; set; }
        public RollingWindow<decimal> VolumeHistory { get; set; }
        public decimal LastBid { get; set; }
        public decimal LastAsk { get; set; }
        public decimal LastMidPrice { get; set; }
        public decimal LastSpread { get; set; }
    }
    
    /// <summary>
    /// Parameters for optimal quote calculation
    /// </summary>
    public class QuoteParameters
    {
        public decimal MidPrice { get; set; }
        public decimal Spread { get; set; }
        public decimal OrderSize { get; set; }
        public decimal BidPrice { get; set; }
        public decimal AskPrice { get; set; }
    }
}

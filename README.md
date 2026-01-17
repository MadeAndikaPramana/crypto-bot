# Crypto Futures Trading Bot - Backtest System

Comprehensive backtesting framework for cryptocurrency futures trading strategies with focus on BTC and SOL.

## 📊 Strategies Implemented

### 1. BTC Funding Rate Divergence
**Concept**: Exploit crowded positioning through funding rate extremes

**Entry Signals**:
- **LONG**: Negative funding (<-0.01%) + Price above EMA200 (short squeeze potential)
- **SHORT**: Positive funding (>0.05%) + Price below EMA200 (long squeeze potential)

**Exit Rules**:
- TP: 2x ATR from entry
- SL: 1.5x ATR from entry
- Time stop: 7 days maximum hold

**Target**: 45-55% win rate, 1:1.3 risk:reward

### 2. SOL Volatility Squeeze Breakout
**Concept**: Bollinger Band squeeze followed by expansion with volume confirmation

**Entry Signals**:
- **LONG**: BB Width <0.04 for 6+ candles → Breakout above upper BB + RSI >50 + Volume >1.5x avg
- **SHORT**: BB Width <0.04 for 6+ candles → Breakout below lower BB + RSI <50 + Volume >1.5x avg

**Exit Rules**:
- TP1: 1.5x ATR (take 50% profit)
- TP2: 2.5x ATR (take remaining 50%)
- SL: Middle BB or 1x ATR (whichever tighter)
- After TP1: Move SL to breakeven

**Target**: 40-50% win rate, 1:1.5 risk:reward

## 🚀 Quick Start

### Installation

```bash
# Clone/create project directory
mkdir crypto_bot_backtest
cd crypto_bot_backtest

# Install dependencies
pip install -r requirements.txt
```

### Basic Usage

```bash
# Run backtest for all strategies
python run_backtest.py --strategy all

# Run BTC strategy only
python run_backtest.py --strategy btc

# Run SOL strategy only
python run_backtest.py --strategy sol

# Force download new data
python run_backtest.py --strategy all --download

# Custom date range
python run_backtest.py --strategy all --start-date 2024-06-01 --end-date 2024-12-31
```

## 📁 Project Structure

```
crypto_bot_backtest/
├── config.py              # Configuration parameters
├── data_downloader.py     # Historical data fetching
├── indicators.py          # Technical indicators
├── strategies/
│   ├── btc_funding.py    # BTC funding rate strategy
│   └── sol_squeeze.py    # SOL squeeze breakout strategy
├── backtest_engine.py     # Core backtesting logic
├── performance.py         # Performance metrics
├── visualize.py          # Visualization tools
├── run_backtest.py       # Main entry point
├── requirements.txt      # Dependencies
└── data_cache/           # Cached historical data (auto-created)
```

## 🎯 Configuration

Edit `config.py` to customize:

### Risk Management
```python
INITIAL_CAPITAL = 10000.0    # Starting capital
RISK_PER_TRADE = 0.01        # 1% risk per trade
MAX_OPEN_POSITIONS = 2       # Max concurrent trades
```

### Strategy Parameters
```python
# BTC
BTC_FUNDING_LONG_THRESHOLD = -0.0001   # -0.01%
BTC_FUNDING_SHORT_THRESHOLD = 0.0005   # 0.05%
BTC_ATR_SL_MULTIPLIER = 1.5
BTC_ATR_TP_MULTIPLIER = 2.0
BTC_MAX_HOLD_DAYS = 7

# SOL
SOL_SQUEEZE_THRESHOLD = 0.04
SOL_SQUEEZE_MIN_CANDLES = 6
SOL_VOLUME_MULTIPLIER = 1.5
SOL_ATR_TP1_MULTIPLIER = 1.5  # 50% exit
SOL_ATR_TP2_MULTIPLIER = 2.5  # Remaining 50%
```

### Backtest Period
```python
START_DATE = "2024-01-01"
END_DATE = "2025-01-13"
```

## 📈 Output

### Console Report
```
BACKTEST PERFORMANCE REPORT
====================================================
--- RETURNS ---
Initial Capital:     $10,000.00
Final Equity:        $11,234.56
Total Return:        $1,234.56
Total Return %:      12.35%

--- TRADE STATISTICS ---
Total Trades:        45
Winning Trades:      23
Losing Trades:       22
Win Rate:            51.11%

--- P&L ANALYSIS ---
Avg Win:             $87.50  (1.85%)
Avg Loss:            $-52.30  (-1.10%)
Profit Factor:       1.67
Expectancy:          $27.43  (0.58%)

--- RISK METRICS ---
Max Drawdown:        $-456.78
Max Drawdown %:      -4.57%
Sharpe Ratio:        1.23
Calmar Ratio:        2.70
```

### Visual Reports (saved to `results/`)
1. **Equity Curve**: Shows capital growth over time with drawdown visualization
2. **Trade Distribution**: P&L histogram and cumulative returns
3. **Monthly Returns**: Heatmap of monthly performance
4. **Strategy Comparison**: Side-by-side comparison of all strategies

## 🔧 Advanced Features

### Data Caching
- First run downloads data from Binance (can take a few minutes)
- Subsequent runs use cached data (instant)
- Use `--download` flag to refresh data

### Realistic Simulation
- **Fees**: 0.02% maker, 0.04% taker (Binance Futures rates)
- **Slippage**: 0.05% average market impact
- **Position Sizing**: Risk-based (1% account risk per trade)
- **Leverage**: Simulated (3x BTC, 5x SOL)

### Exit Management
- **Stop Loss**: Exchange-managed (survives bot crash)
- **Take Profit**: Single TP for BTC, split TP for SOL (50% + 50%)
- **Trailing**: SOL moves SL to breakeven after TP1
- **Time Stop**: BTC has 7-day maximum hold period

## 📊 Performance Metrics Explained

### Return Metrics
- **Total Return**: Absolute profit/loss in USDT
- **Total Return %**: Percentage gain on initial capital

### Trade Statistics
- **Win Rate**: % of profitable trades
- **Profit Factor**: Gross profit / Gross loss (>1 is profitable)
- **Expectancy**: Average profit per trade

### Risk Metrics
- **Max Drawdown**: Largest peak-to-trough decline
- **Sharpe Ratio**: Risk-adjusted return (>1 is good, >2 is excellent)
- **Sortino Ratio**: Like Sharpe but only counts downside volatility
- **Calmar Ratio**: Annual return / Max drawdown (higher is better)

## 🐛 Troubleshooting

### Rate Limit Errors
```python
# Binance has rate limits. If you get errors:
# 1. Data is cached, so subsequent runs won't hit API
# 2. Downloads are already rate-limited
# 3. Wait a few minutes and retry
```

### Missing Data
```python
# Some markets may not have full funding rate or OI history
# The system handles this gracefully by using zeros
# This mainly affects BTC OI filter (optional anyway)
```

### Memory Issues
```python
# If testing long periods (>1 year):
# 1. Reduce date range
# 2. Use higher timeframes (4h instead of 1h)
# 3. Test strategies separately instead of 'all'
```

## 🎮 Next Steps After Backtesting

Once you're satisfied with backtest results:

1. **Paper Trading** (Testnet):
   - Use the live trading code (from original prompt)
   - Set up Binance Testnet account
   - Run with test funds to validate execution

2. **Live Trading** (Small Capital):
   - Start with minimum capital ($100-500)
   - Monitor closely for 1-2 weeks
   - Verify real-world behavior matches backtest

3. **Scale Up**:
   - Gradually increase capital
   - Monitor for slippage impact
   - Consider splitting orders for larger sizes

## ⚠️ Important Notes

### Backtest Limitations
- Past performance ≠ future results
- Market conditions change
- Real trading has additional factors:
  - Network latency
  - Order execution delay
  - Exchange outages
  - Emotional factors

### Risk Management
- Never risk more than you can afford to lose
- Futures trading is highly leveraged and risky
- Use stop losses religiously
- Start small and scale gradually

## 📝 Customization Ideas

### Add New Strategies
```python
# 1. Create new file in strategies/
# 2. Implement evaluate() method
# 3. Add to run_backtest.py
# 4. Test!
```

### Optimize Parameters
```python
# Use parameter grid search:
# - Test different ATR multipliers
# - Test different thresholds
# - Find optimal combinations
# Note: Beware of overfitting!
```

### Add Filters
```python
# Common additions:
# - Market regime filters (trending vs ranging)
# - Volatility filters
# - Time-of-day filters
# - Correlation filters
```

## 📚 References

- [Binance Futures API](https://binance-docs.github.io/apidocs/futures/en/)
- [CCXT Library](https://github.com/ccxt/ccxt)
- [Funding Rate Explained](https://www.binance.com/en/support/faq/funding-rate-explained)
- [Bollinger Bands Strategy](https://www.investopedia.com/articles/trading/07/bollinger.asp)

## 🤝 Contributing

Feel free to:
- Report bugs
- Suggest improvements
- Share your own strategies
- Optimize existing code

## ⚖️ License

This is for educational purposes. Trade at your own risk.

---

**Happy Backtesting! 🚀**

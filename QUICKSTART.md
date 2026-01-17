# 🚀 QUICK START GUIDE

## Installation (Local - MacOS/Linux/Windows)

```bash
# 1. Navigate to project directory
cd /path/to/crypto_bot_backtest

# 2. Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

## Your First Backtest

### Option 1: Quick Demo (No Data Download)
```bash
# Test with synthetic data - super fast!
python demo.py
```
This will:
- Generate test data
- Run both strategies
- Create performance reports
- Generate charts in `results/` folder

**Expected output:**
- BTC and SOL equity curves
- Performance metrics
- Strategy comparison chart

### Option 2: Real Historical Data
```bash
# Download real data and backtest (takes 2-5 minutes on first run)
python run_backtest.py --strategy all

# Subsequent runs are instant (uses cached data)
python run_backtest.py --strategy all
```

## Understanding the Output

### Console Output
```
BACKTEST PERFORMANCE REPORT
====================================================
--- RETURNS ---
Initial Capital:     $10,000.00
Final Equity:        $11,234.56    ← Your profit!
Total Return %:      12.35%         ← Your ROI

--- TRADE STATISTICS ---
Win Rate:            51.11%         ← % winning trades
Profit Factor:       1.67           ← >1 means profitable

--- RISK METRICS ---
Max Drawdown %:      -4.57%         ← Worst decline
Sharpe Ratio:        1.23           ← Risk-adjusted return
```

### Files Generated
```
results/
├── BTC_Funding_Divergence_equity_curve.png    ← Capital growth chart
├── BTC_Funding_Divergence_trade_dist.png      ← Trade distribution
├── SOL_Squeeze_Breakout_equity_curve.png      ← Capital growth chart
├── SOL_Squeeze_Breakout_trade_dist.png        ← Trade distribution
├── strategy_comparison.png                     ← Side-by-side comparison
└── strategy_comparison.csv                     ← Metrics table
```

## Customizing Parameters

Edit `config.py` to adjust:

### Test Different Time Periods
```python
START_DATE = "2024-06-01"  # Earlier = more data, longer test
END_DATE = "2024-12-31"
```

### Adjust Risk
```python
RISK_PER_TRADE = 0.01      # 1% risk per trade (conservative)
RISK_PER_TRADE = 0.02      # 2% risk per trade (aggressive)
MAX_OPEN_POSITIONS = 2     # Max concurrent trades
```

### Tune Strategy Parameters

**BTC Funding Strategy:**
```python
BTC_FUNDING_LONG_THRESHOLD = -0.0001   # More negative = fewer longs
BTC_FUNDING_SHORT_THRESHOLD = 0.0005   # More positive = fewer shorts
BTC_ATR_SL_MULTIPLIER = 1.5            # Larger = wider stops
BTC_ATR_TP_MULTIPLIER = 2.0            # Larger = bigger targets
```

**SOL Squeeze Strategy:**
```python
SOL_SQUEEZE_THRESHOLD = 0.04           # Lower = tighter squeeze required
SOL_VOLUME_MULTIPLIER = 1.5            # Higher = more volume needed
SOL_ATR_TP1_MULTIPLIER = 1.5           # First target
SOL_ATR_TP2_MULTIPLIER = 2.5           # Second target
```

## Advanced Usage

### Test Different Date Ranges
```bash
# Test Q4 2024 only
python run_backtest.py --start-date 2024-10-01 --end-date 2024-12-31

# Test 2024 only
python run_backtest.py --start-date 2024-01-01 --end-date 2024-12-31
```

### Test Single Strategy
```bash
# BTC only
python run_backtest.py --strategy btc

# SOL only
python run_backtest.py --strategy sol
```

### Force Fresh Data Download
```bash
# Re-download all data (if market conditions changed)
python run_backtest.py --strategy all --download
```

## Interpreting Results

### Good Performance Indicators
✅ Total Return > 10% per year
✅ Win Rate > 40%
✅ Profit Factor > 1.5
✅ Max Drawdown < 20%
✅ Sharpe Ratio > 1.0

### Warning Signs
⚠️ Win Rate < 30% (strategy too aggressive)
⚠️ Max Drawdown > 30% (too risky)
⚠️ Profit Factor < 1.0 (losing money)
⚠️ Very few trades (< 10) - not enough data

### What If Results Are Bad?

1. **Check Data Quality**
   - Is the test period too short?
   - Was it an unusually choppy market?

2. **Adjust Parameters**
   - Tighten entry filters
   - Adjust SL/TP multipliers
   - Try different thresholds

3. **Test Different Periods**
   - Bull market vs bear market
   - High volatility vs low volatility

## Common Issues

### "No trades executed"
- Strategy filters too strict
- Test period doesn't have the right market conditions
- Try adjusting thresholds in config.py

### "Rate limit error"
- Binance API has limits
- Wait a few minutes
- Data gets cached, so just retry

### "Import errors"
- Dependencies not installed
- Run: `pip install -r requirements.txt`

### Charts not showing
- Make sure you're not running on a headless server
- Charts save to results/ folder automatically
- Use `plt.show()` to display them

## Next Steps

### 1. Optimize Parameters
Try different parameter combinations to find what works best:
```python
# Test multiple values
for sl_multiplier in [1.0, 1.5, 2.0]:
    for tp_multiplier in [1.5, 2.0, 2.5]:
        # Run backtest with these params
        # Compare results
```

### 2. Walk-Forward Testing
Test on one period, optimize, then validate on another:
```bash
# Optimize on H1 2024
python run_backtest.py --start-date 2024-01-01 --end-date 2024-06-30

# Validate on H2 2024
python run_backtest.py --start-date 2024-07-01 --end-date 2024-12-31
```

### 3. Paper Trading
Once satisfied with backtest:
1. Set up Binance Testnet account
2. Use the live trading code
3. Monitor for 1-2 weeks
4. Compare real results to backtest

### 4. Live Trading (CAREFUL!)
Only after successful paper trading:
1. Start with SMALL capital ($100-500)
2. Use lower leverage (1-2x instead of 3-5x)
3. Monitor closely for first week
4. Scale up gradually

## Tips for Success

1. **Don't Overfit**: If you test 100 parameter combinations, you'll find one that works by chance. Test on out-of-sample data!

2. **Market Conditions Matter**: A strategy that works in trending markets may fail in choppy markets.

3. **Start Conservative**: Better to miss opportunities than lose capital. You can always increase risk later.

4. **Keep a Journal**: Track what parameters you tested and why. Future you will thank you.

5. **Respect Drawdowns**: If live trading hits max backtest drawdown, pause and reassess.

## Resources

- **README.md**: Full documentation
- **config.py**: All adjustable parameters
- **strategies/**: Strategy implementations
- **demo.py**: Quick test with synthetic data

## Getting Help

If something isn't working:
1. Check error messages carefully
2. Review README.md
3. Test with demo.py first
4. Check that all dependencies are installed

---

**Remember**: Past performance does not guarantee future results. Trade responsibly! 🎯

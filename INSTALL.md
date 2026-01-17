# 🚀 Installation Guide

## Step-by-Step Setup

### 1. Download All Files

Make sure you have these 13 files:

```
✓ config.py
✓ data_downloader.py  
✓ demo.py
✓ indicators.py
✓ backtest_engine.py
✓ performance.py
✓ visualize.py
✓ run_backtest.py
✓ requirements.txt
✓ README.md
✓ QUICKSTART.md
✓ strategies/btc_funding.py
✓ strategies/sol_squeeze.py
```

### 2. Create Project Structure

```bash
# Create folder
mkdir crypto_bot_backtest
cd crypto_bot_backtest

# Place all files here
# Make sure strategies/ folder contains the 2 strategy files
```

### 3. Create Virtual Environment (Recommended)

```bash
# Create venv
python3 -m venv venv

# Activate it
source venv/bin/activate          # Mac/Linux
# OR
venv\Scripts\activate              # Windows
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

Expected output:
```
Installing ccxt>=4.0.0
Installing pandas>=2.0.0
Installing numpy>=1.24.0
Installing matplotlib>=3.7.0
Installing seaborn>=0.12.0
...
Successfully installed ccxt-4.x.x pandas-2.x.x ...
```

### 5. Verify Setup

```bash
python verify_setup.py
```

Expected output:
```
🎉 ALL CHECKS PASSED! 🎉

You're ready to run:
  python demo.py
  python run_backtest.py --strategy all
```

### 6. Run Demo

```bash
python demo.py
```

This will:
- Generate synthetic data
- Run both strategies
- Create charts in `results/` folder
- Takes ~10 seconds

Expected output:
```
CRYPTO BOT BACKTEST - QUICK DEMO
Step 1: Generating synthetic data...
✓ BTC data: 500 candles
✓ SOL data: 500 candles
...
✅ Demo Complete!
```

### 7. Run Real Backtest

```bash
python run_backtest.py --strategy all
```

This will:
- Download real data from Binance (first time: 2-5 min)
- Run backtests on both strategies
- Generate comprehensive reports
- Save charts to `results/` folder

Expected output:
```
RUNNING BACKTEST: BTC_Funding_Divergence
Step 1: Loading data...
Downloaded 2000 candles for BTC/USDT 4h
...
BACKTEST PERFORMANCE REPORT
Total Return: $1,234.56 (12.35%)
Win Rate: 51.11%
...
```

## Troubleshooting

### "Module not found" errors

```bash
# Make sure dependencies are installed
pip install -r requirements.txt

# Make sure you're in the right directory
ls -la  # Should see all .py files

# Make sure virtual environment is activated
which python  # Should show path to venv
```

### "No module named 'strategies'"

```bash
# Make sure strategies folder exists
ls strategies/
# Should show: btc_funding.py  sol_squeeze.py
```

### Rate limit errors on first run

```bash
# Normal - Binance has API limits
# Just wait 1-2 minutes and retry
# Data gets cached, so subsequent runs are instant
```

### Charts not showing

```bash
# Charts auto-save to results/ folder
ls results/

# If plt.show() doesn't work, just check the saved images
```

## Quick Reference

### Test with synthetic data (fast):
```bash
python demo.py
```

### Run full backtest (downloads data):
```bash
python run_backtest.py --strategy all
```

### Run single strategy:
```bash
python run_backtest.py --strategy btc
python run_backtest.py --strategy sol
```

### Custom date range:
```bash
python run_backtest.py --start-date 2024-06-01 --end-date 2024-12-31
```

### Force fresh data:
```bash
python run_backtest.py --strategy all --download
```

## File Organization

After running, your folder will look like:
```
crypto_bot_backtest/
├── config.py
├── data_downloader.py
├── demo.py
├── indicators.py
├── backtest_engine.py
├── performance.py
├── visualize.py
├── run_backtest.py
├── requirements.txt
├── verify_setup.py
├── README.md
├── QUICKSTART.md
├── PROJECT_FILES.md
├── INSTALL.md (this file)
├── strategies/
│   ├── btc_funding.py
│   └── sol_squeeze.py
├── data_cache/              ← Auto-created on first run
│   └── *.pkl                ← Cached historical data
├── results/                 ← Auto-created when generating charts
│   ├── *_equity_curve.png
│   ├── *_trade_dist.png
│   └── strategy_comparison.csv
└── venv/                    ← Virtual environment (if created)
```

## What to Read

1. **This file (INSTALL.md)** - Setup instructions
2. **QUICKSTART.md** - Usage guide  
3. **README.md** - Full documentation
4. **PROJECT_FILES.md** - File descriptions

## Next Steps

After installation:

1. ✅ Run `python verify_setup.py`
2. ✅ Run `python demo.py` 
3. ✅ Check charts in `results/` folder
4. ✅ Run `python run_backtest.py --strategy all`
5. ✅ Analyze results
6. ✅ Adjust parameters in `config.py`
7. ✅ Re-run and compare

---

**Need help?** Check README.md or QUICKSTART.md for detailed guides.

#!/usr/bin/env python3
"""
Data Diagnostic Tool
Analyze actual market data to calibrate strategy parameters
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from config import config
from data_downloader import prepare_backtest_data
from indicators import add_all_indicators, merge_funding_rate, merge_open_interest
import pandas as pd
import numpy as np

def diagnose_btc_data():
    """Analyze BTC data to find optimal thresholds"""
    
    print("\n" + "="*70)
    print("BTC/USDT DATA DIAGNOSTIC")
    print("="*70)
    
    # Load data
    print("\n📊 Loading BTC data...")
    data = prepare_backtest_data(
        symbol=config.BTC_SYMBOL,
        timeframe=config.BTC_TIMEFRAME,
        start_date=config.START_DATE,
        end_date=config.END_DATE,
        download_funding=True,
        download_oi=False
    )
    
    df = data['ohlcv']
    df = add_all_indicators(df, config)
    
    if 'funding' in data and not data['funding'].empty:
        df = merge_funding_rate(df, data['funding'])
    
    print(f"✓ Loaded {len(df)} candles")
    print(f"  Period: {df['timestamp'].min()} to {df['timestamp'].max()}")
    
    # === FUNDING RATE ANALYSIS ===
    print("\n" + "="*70)
    print("FUNDING RATE DISTRIBUTION")
    print("="*70)
    
    funding = df['funding_rate'].dropna()
    
    print(f"\nBasic Stats:")
    print(f"  Min:    {funding.min():.6f} ({funding.min()*100:.4f}%)")
    print(f"  Max:    {funding.max():.6f} ({funding.max()*100:.4f}%)")
    print(f"  Mean:   {funding.mean():.6f} ({funding.mean()*100:.4f}%)")
    print(f"  Median: {funding.median():.6f} ({funding.median()*100:.4f}%)")
    print(f"  Std:    {funding.std():.6f}")
    
    print(f"\nPercentiles:")
    percentiles = [1, 5, 10, 20, 25, 50, 75, 80, 90, 95, 99]
    for p in percentiles:
        val = funding.quantile(p/100)
        print(f"  {p:>2}th: {val:.6f} ({val*100:.4f}%)")
    
    # Count extreme values
    print(f"\nExtreme Values:")
    print(f"  Funding < -0.01%:  {(funding < -0.0001).sum():>4} candles ({(funding < -0.0001).sum()/len(funding)*100:.1f}%)")
    print(f"  Funding < -0.005%: {(funding < -0.00005).sum():>4} candles ({(funding < -0.00005).sum()/len(funding)*100:.1f}%)")
    print(f"  Funding > +0.05%:  {(funding > 0.0005).sum():>4} candles ({(funding > 0.0005).sum()/len(funding)*100:.1f}%)")
    print(f"  Funding > +0.03%:  {(funding > 0.0003).sum():>4} candles ({(funding > 0.0003).sum()/len(funding)*100:.1f}%)")
    
    # === PRICE vs EMA ANALYSIS ===
    print("\n" + "="*70)
    print("PRICE vs EMA200 TREND")
    print("="*70)
    
    df_clean = df.dropna(subset=['ema_200', 'close'])
    above_ema = (df_clean['close'] > df_clean['ema_200']).sum()
    below_ema = (df_clean['close'] < df_clean['ema_200']).sum()
    
    print(f"\nTrend Distribution:")
    print(f"  Price > EMA200: {above_ema:>4} candles ({above_ema/len(df_clean)*100:.1f}%)")
    print(f"  Price < EMA200: {below_ema:>4} candles ({below_ema/len(df_clean)*100:.1f}%)")
    
    # === COMBINED CONDITIONS ===
    print("\n" + "="*70)
    print("STRATEGY SIGNAL ANALYSIS")
    print("="*70)
    
    df_signals = df.dropna(subset=['funding_rate', 'ema_200', 'close'])
    
    # Current thresholds
    print(f"\nCurrent Thresholds (from config.py):")
    print(f"  LONG:  funding < {config.BTC_FUNDING_LONG_THRESHOLD:.6f} ({config.BTC_FUNDING_LONG_THRESHOLD*100:.4f}%)")
    print(f"  SHORT: funding > {config.BTC_FUNDING_SHORT_THRESHOLD:.6f} ({config.BTC_FUNDING_SHORT_THRESHOLD*100:.4f}%)")
    
    long_funding = df_signals['funding_rate'] < config.BTC_FUNDING_LONG_THRESHOLD
    long_trend = df_signals['close'] > df_signals['ema_200']
    long_signals = long_funding & long_trend
    
    short_funding = df_signals['funding_rate'] > config.BTC_FUNDING_SHORT_THRESHOLD
    short_trend = df_signals['close'] < df_signals['ema_200']
    short_signals = short_funding & short_trend
    
    print(f"\nSignals with CURRENT thresholds:")
    print(f"  Funding meets LONG:   {long_funding.sum():>4} candles")
    print(f"  Trend meets LONG:     {long_trend.sum():>4} candles")
    print(f"  ► LONG signals:       {long_signals.sum():>4} candles ◄")
    print(f"")
    print(f"  Funding meets SHORT:  {short_funding.sum():>4} candles")
    print(f"  Trend meets SHORT:    {short_trend.sum():>4} candles")
    print(f"  ► SHORT signals:      {short_signals.sum():>4} candles ◄")
    
    # === RECOMMENDED THRESHOLDS ===
    print("\n" + "="*70)
    print("RECOMMENDED THRESHOLDS")
    print("="*70)
    
    # Calculate percentile-based thresholds
    p20 = funding.quantile(0.20)
    p30 = funding.quantile(0.30)
    p70 = funding.quantile(0.70)
    p80 = funding.quantile(0.80)
    
    print(f"\nOption 1: Percentile-based (Recommended)")
    print(f"  LONG:  funding < {p20:.6f} (20th percentile = {p20*100:.4f}%)")
    print(f"  SHORT: funding > {p80:.6f} (80th percentile = {p80*100:.4f}%)")
    
    # Test with recommended thresholds
    long_funding_new = df_signals['funding_rate'] < p20
    short_funding_new = df_signals['funding_rate'] > p80
    long_signals_new = long_funding_new & long_trend
    short_signals_new = short_funding_new & short_trend
    
    print(f"\nExpected signals with percentile thresholds:")
    print(f"  LONG signals:  {long_signals_new.sum():>4} candles ({long_signals_new.sum()/len(df_signals)*100:.1f}%)")
    print(f"  SHORT signals: {short_signals_new.sum():>4} candles ({short_signals_new.sum()/len(df_signals)*100:.1f}%)")
    
    # Less aggressive option
    print(f"\nOption 2: Moderate thresholds")
    print(f"  LONG:  funding < {p30:.6f} (30th percentile = {p30*100:.4f}%)")
    print(f"  SHORT: funding > {p70:.6f} (70th percentile = {p70*100:.4f}%)")
    
    long_signals_mod = (df_signals['funding_rate'] < p30) & long_trend
    short_signals_mod = (df_signals['funding_rate'] > p70) & short_trend
    
    print(f"\nExpected signals with moderate thresholds:")
    print(f"  LONG signals:  {long_signals_mod.sum():>4} candles ({long_signals_mod.sum()/len(df_signals)*100:.1f}%)")
    print(f"  SHORT signals: {short_signals_mod.sum():>4} candles ({short_signals_mod.sum()/len(df_signals)*100:.1f}%)")
    
    # === CONFIGURATION RECOMMENDATIONS ===
    print("\n" + "="*70)
    print("COPY THIS TO config.py")
    print("="*70)
    
    print(f"""
# === CALIBRATED THRESHOLDS (based on 2024 data) ===

# Option 1: Percentile-based (More trades)
BTC_FUNDING_LONG_THRESHOLD: float = {p20:.6f}   # 20th percentile
BTC_FUNDING_SHORT_THRESHOLD: float = {p80:.6f}  # 80th percentile

# Option 2: Moderate (Balanced)  
# BTC_FUNDING_LONG_THRESHOLD: float = {p30:.6f}   # 30th percentile
# BTC_FUNDING_SHORT_THRESHOLD: float = {p70:.6f}  # 70th percentile

# Expected trades per year with Option 1:
# LONG:  ~{int(long_signals_new.sum() / len(df_signals) * 365 / 4)} trades
# SHORT: ~{int(short_signals_new.sum() / len(df_signals) * 365 / 4)} trades
""")
    
    print("\n" + "="*70)
    print("✓ Diagnostic Complete!")
    print("="*70)
    print("\nNext steps:")
    print("1. Copy recommended thresholds to config.py")
    print("2. Run: python run_backtest.py --strategy btc")
    print("3. Check if trade count is reasonable (20-50 trades/year)")
    print("\n")

def diagnose_sol_data():
    """Analyze SOL data"""
    
    print("\n" + "="*70)
    print("SOL/USDT DATA DIAGNOSTIC")
    print("="*70)
    
    print("\n📊 Loading SOL data...")
    data = prepare_backtest_data(
        symbol=config.SOL_SYMBOL,
        timeframe=config.SOL_TIMEFRAME,
        start_date=config.START_DATE,
        end_date=config.END_DATE,
        download_funding=False,
        download_oi=False
    )
    
    df = data['ohlcv']
    df = add_all_indicators(df, config)
    
    print(f"✓ Loaded {len(df)} candles")
    
    # BB Width analysis
    print("\n" + "="*70)
    print("BOLLINGER BAND WIDTH ANALYSIS")
    print("="*70)
    
    bb_width = df['bb_width'].dropna()
    
    print(f"\nBB Width Stats:")
    print(f"  Min:    {bb_width.min():.6f}")
    print(f"  Max:    {bb_width.max():.6f}")
    print(f"  Mean:   {bb_width.mean():.6f}")
    print(f"  Median: {bb_width.median():.6f}")
    
    print(f"\nSqueeze Detection:")
    print(f"  Current threshold: {config.SOL_SQUEEZE_THRESHOLD:.6f}")
    squeeze_candles = (bb_width < config.SOL_SQUEEZE_THRESHOLD).sum()
    print(f"  Candles < threshold: {squeeze_candles} ({squeeze_candles/len(bb_width)*100:.1f}%)")
    
    # Recommended threshold
    p30 = bb_width.quantile(0.30)
    print(f"\nRecommended threshold (30th percentile): {p30:.6f}")
    print(f"  Expected squeeze candles: {(bb_width < p30).sum()} ({(bb_width < p30).sum()/len(bb_width)*100:.1f}%)")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', choices=['btc', 'sol', 'all'], default='btc')
    args = parser.parse_args()
    
    try:
        if args.symbol in ['btc', 'all']:
            diagnose_btc_data()
        
        if args.symbol in ['sol', 'all']:
            diagnose_sol_data()
            
    except KeyboardInterrupt:
        print("\n\nDiagnostic interrupted by user")
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()
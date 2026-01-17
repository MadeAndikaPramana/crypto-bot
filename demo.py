#!/usr/bin/env python3
# ============================================
# QUICK DEMO - Test Your Setup
# ============================================
"""
Run this script to verify everything is set up correctly.
It will test all components without downloading large amounts of data.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add project to path
sys.path.append(str(Path(__file__).parent))

from config import config
from indicators import add_all_indicators
from strategies.btc_funding import BTCFundingStrategy
from strategies.sol_squeeze import SOLSqueezeStrategy
from backtest_engine import BacktestEngine
from performance import PerformanceAnalyzer
from visualize import BacktestVisualizer

def generate_sample_data(symbol: str, timeframe: str, num_candles: int = 500):
    """Generate synthetic data for testing"""
    
    print(f"Generating {num_candles} candles of sample data for {symbol}...")
    
    # Base price
    if 'BTC' in symbol:
        base_price = 95000
        volatility = 2000
    else:  # SOL
        base_price = 140
        volatility = 8
    
    # Generate price series with trend
    price_trend = np.linspace(0, 5000 if 'BTC' in symbol else 20, num_candles)
    price_random = np.random.randn(num_candles).cumsum() * volatility
    close_prices = base_price + price_trend + price_random
    
    # OHLCV
    opens = close_prices + np.random.randn(num_candles) * (volatility * 0.5)
    highs = np.maximum(opens, close_prices) + abs(np.random.randn(num_candles) * (volatility * 0.3))
    lows = np.minimum(opens, close_prices) - abs(np.random.randn(num_candles) * (volatility * 0.3))
    volumes = np.random.uniform(1000000, 5000000, num_candles)
    
    # Generate timestamps
    if timeframe == '4h':
        freq = '4h'
    else:  # 1h
        freq = '1h'
    
    start_date = datetime(2024, 10, 1)
    timestamps = pd.date_range(start=start_date, periods=num_candles, freq=freq)
    
    df = pd.DataFrame({
        'timestamp': timestamps,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': close_prices,
        'volume': volumes
    })
    
    # Add funding rate (for BTC)
    # Create some extreme values occasionally
    funding_base = np.random.uniform(-0.0003, 0.0003, num_candles)
    # Add some spikes
    spike_indices = np.random.choice(num_candles, size=int(num_candles * 0.1), replace=False)
    funding_base[spike_indices] = np.random.choice(
        [-0.0015, 0.0015],  # Extreme funding
        size=len(spike_indices)
    )
    df['funding_rate'] = funding_base
    
    # Add OI change
    df['oi_change_pct'] = np.random.uniform(-0.03, 0.03, num_candles)
    
    return df

def run_demo():
    """Run a quick demo of the entire system"""
    
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║                                                            ║
    ║           CRYPTO BOT BACKTEST - QUICK DEMO                ║
    ║                                                            ║
    ║  This will test all components with synthetic data        ║
    ║  No real data download required!                          ║
    ║                                                            ║
    ╚════════════════════════════════════════════════════════════╝
    """)
    
    # Create results directory
    Path('results').mkdir(exist_ok=True)
    
    print("\n📝 Step 1: Generating synthetic data...")
    
    # Generate BTC data
    btc_df = generate_sample_data('BTC/USDT', '4h', 500)
    print(f"✓ BTC data: {len(btc_df)} candles")
    
    # Generate SOL data
    sol_df = generate_sample_data('SOL/USDT', '1h', 500)
    print(f"✓ SOL data: {len(sol_df)} candles")
    
    print("\n📊 Step 2: Calculating indicators...")
    
    # Add indicators
    btc_df = add_all_indicators(btc_df, config)
    sol_df = add_all_indicators(sol_df, config)
    
    print(f"✓ BTC indicators calculated")
    print(f"✓ SOL indicators calculated")
    
    print("\n🎯 Step 3: Testing BTC Strategy...")
    
    # Test BTC strategy
    btc_strategy = BTCFundingStrategy(config)
    btc_engine = BacktestEngine(config)
    
    btc_results = btc_engine.run(btc_df, btc_strategy, "BTC_Demo")
    
    print(f"✓ BTC backtest complete: {len(btc_results['trades'])} trades")
    
    print("\n🎯 Step 4: Testing SOL Strategy...")
    
    # Test SOL strategy
    sol_strategy = SOLSqueezeStrategy(config)
    sol_engine = BacktestEngine(config)
    
    sol_results = sol_engine.run(sol_df, sol_strategy, "SOL_Demo")
    
    print(f"✓ SOL backtest complete: {len(sol_results['trades'])} trades")
    
    print("\n📈 Step 5: Analyzing performance...")
    
    # Analyze BTC
    btc_analyzer = PerformanceAnalyzer(config.INITIAL_CAPITAL)
    btc_metrics = btc_analyzer.analyze(btc_results['trades'], btc_results['equity_curve'])
    
    print("\n=== BTC Strategy Results ===")
    print(f"Total Return: ${btc_metrics['total_return']:,.2f} ({btc_metrics['total_return_pct']:.2f}%)")
    print(f"Total Trades: {btc_metrics['total_trades']}")
    print(f"Win Rate: {btc_metrics['win_rate']:.1f}%")
    print(f"Profit Factor: {btc_metrics['profit_factor']:.2f}")
    print(f"Max Drawdown: {btc_metrics['max_drawdown_pct']:.2f}%")
    
    # Analyze SOL
    sol_analyzer = PerformanceAnalyzer(config.INITIAL_CAPITAL)
    sol_metrics = sol_analyzer.analyze(sol_results['trades'], sol_results['equity_curve'])
    
    print("\n=== SOL Strategy Results ===")
    print(f"Total Return: ${sol_metrics['total_return']:,.2f} ({sol_metrics['total_return_pct']:.2f}%)")
    print(f"Total Trades: {sol_metrics['total_trades']}")
    print(f"Win Rate: {sol_metrics['win_rate']:.1f}%")
    print(f"Profit Factor: {sol_metrics['profit_factor']:.2f}")
    print(f"Max Drawdown: {sol_metrics['max_drawdown_pct']:.2f}%")
    
    print("\n📊 Step 6: Creating visualizations...")
    
    visualizer = BacktestVisualizer()
    
    # BTC equity curve
    visualizer.plot_equity_curve(
        btc_results['equity_curve'],
        config.INITIAL_CAPITAL,
        title="BTC Demo - Equity Curve",
        save_path="results/demo_btc_equity.png"
    )
    
    # SOL equity curve
    visualizer.plot_equity_curve(
        sol_results['equity_curve'],
        config.INITIAL_CAPITAL,
        title="SOL Demo - Equity Curve",
        save_path="results/demo_sol_equity.png"
    )
    
    # Comparison
    all_results = {
        'BTC_Demo': {
            'equity_curve': btc_results['equity_curve'],
            'metrics': btc_metrics
        },
        'SOL_Demo': {
            'equity_curve': sol_results['equity_curve'],
            'metrics': sol_metrics
        }
    }
    
    visualizer.plot_strategy_comparison(
        all_results,
        save_path="results/demo_comparison.png"
    )
    
    print("\n✅ Demo Complete!")
    print("\nResults saved to ./results/")
    print("\nWhat to do next:")
    print("  1. Check the charts in results/ folder")
    print("  2. Review the performance metrics above")
    print("  3. Run real backtest: python run_backtest.py --strategy all")
    print("\n" + "="*60 + "\n")
    
    return {
        'btc': {'results': btc_results, 'metrics': btc_metrics},
        'sol': {'results': sol_results, 'metrics': sol_metrics}
    }

if __name__ == "__main__":
    try:
        demo_results = run_demo()
    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()
        print("\nIf you see import errors, make sure you've installed dependencies:")
        print("  pip install -r requirements.txt")

# ============================================
# MAIN BACKTEST RUNNER
# ============================================
import sys
from pathlib import Path
import json

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from config import config
from data_downloader import prepare_backtest_data
from indicators import add_all_indicators, merge_funding_rate, merge_open_interest
from strategies.btc_funding import BTCFundingStrategy
from strategies.sol_squeeze import SOLSqueezeStrategy
from strategies.btc_mean_reversion import BTCMeanReversionStrategy
from backtest_engine import BacktestEngine
from performance import PerformanceAnalyzer
from visualize import BacktestVisualizer

def run_single_backtest(symbol: str, timeframe: str, strategy_class, 
                       strategy_name: str, download_new_data: bool = False):
    """
    Run backtest for a single strategy
    """
    print(f"\n{'='*70}")
    print(f"RUNNING BACKTEST: {strategy_name}")
    print(f"Symbol: {symbol}, Timeframe: {timeframe}")
    print(f"Period: {config.START_DATE} to {config.END_DATE}")
    print(f"{'='*70}\n")

    # Instantiate strategy to check required data
    strategy = strategy_class(config)
    
    download_funding = hasattr(strategy, 'required_data') and 'funding' in strategy.required_data
    download_oi = hasattr(strategy, 'required_data') and 'oi' in strategy.required_data

    # Step 1: Download/Load data
    print("Step 1: Loading data...")
    
    if download_new_data or not Path('data_cache').exists():
        data = prepare_backtest_data(
            symbol=symbol,
            timeframe=timeframe,
            start_date=config.START_DATE,
            end_date=config.END_DATE,
            download_funding=download_funding,
            download_oi=download_oi
        )
    else:
        from data_downloader import DataDownloader
        downloader = DataDownloader()
        
        # Load from cache
        ohlcv = downloader.download_ohlcv(symbol, timeframe, config.START_DATE, config.END_DATE)
        data = {'ohlcv': ohlcv}
        if download_funding:
            data['funding'] = downloader.download_funding_rate(symbol, config.START_DATE, config.END_DATE)
        if download_oi:
            data['oi'] = downloader.download_open_interest(symbol, timeframe, config.START_DATE, config.END_DATE)
    
    df = data['ohlcv']
    
    # Step 2: Add indicators
    print("Step 2: Calculating indicators...")
    df = add_all_indicators(df, config)
    
    # Merge funding rate
    if 'funding' in data and data.get('funding') is not None and not data['funding'].empty:
        df = merge_funding_rate(df, data['funding'])
    else:
        df['funding_rate'] = 0.0
    
    # Merge OI
    if 'oi' in data and data.get('oi') is not None and not data['oi'].empty:
        df = merge_open_interest(df, data['oi'])
    else:
        df['open_interest'] = 0.0
        df['oi_change_pct'] = 0.0
    
    df = df.reset_index(drop=True)
    
    print(f"Data loaded: {len(df)} candles")
    print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    
    # Step 3: Initialize strategy and engine
    print("\nStep 3: Initializing backtest engine...")
    engine = BacktestEngine(config)
    
    # Step 4: Run backtest
    print("Step 4: Running backtest...")
    results = engine.run(df, strategy, strategy_name)
    
    # Step 5: Analyze performance
    print("\nStep 5: Analyzing performance...")
    analyzer = PerformanceAnalyzer(config.INITIAL_CAPITAL)
    metrics = analyzer.analyze(results['trades'], results['equity_curve'])
    
    # Step 6: Print report
    analyzer.print_report(metrics)
    
    # Step 7: Create visualizations
    print("Step 6: Creating visualizations...")
    visualizer = BacktestVisualizer()
    
    # Equity curve
    visualizer.plot_equity_curve(
        results['equity_curve'], 
        config.INITIAL_CAPITAL,
        title=f"{strategy_name} - Equity Curve",
        save_path=f"results/{strategy_name}_equity_curve.png"
    )
    
    # Trade distribution (if trades exist)
    if results['trades']:
        visualizer.plot_trade_distribution(
            results['trades'],
            save_path=f"results/{strategy_name}_trade_dist.png"
        )
        
        visualizer.plot_monthly_returns(
            results['equity_curve'],
            save_path=f"results/{strategy_name}_monthly.png"
        )
    
    return {
        'results': results,
        'metrics': metrics,
        'df': df
    }

def run_multi_strategy_backtest(download_new_data: bool = False):
    """
    Run backtest for all strategies and compare
    """
    # Create results directory
    Path('results').mkdir(exist_ok=True)
    
    strategies_to_test = [
        {
            'symbol': config.MR_SYMBOL,
            'timeframe': config.MR_TIMEFRAME,
            'strategy_class': BTCMeanReversionStrategy,
            'name': 'BTC_Mean_Reversion'
        },
        {
            'symbol': config.SOL_SYMBOL,
            'timeframe': config.SOL_TIMEFRAME,
            'strategy_class': SOLSqueezeStrategy,
            'name': 'SOL_Squeeze_Breakout'
        }
    ]
    
    all_results = {}
    
    for strategy_config in strategies_to_test:
        result = run_single_backtest(
            symbol=strategy_config['symbol'],
            timeframe=strategy_config['timeframe'],
            strategy_class=strategy_config['strategy_class'],
            strategy_name=strategy_config['name'],
            download_new_data=download_new_data
        )
        
        all_results[strategy_config['name']] = {
            'equity_curve': result['results']['equity_curve'],
            'metrics': result['metrics']
        }
    
    # Compare strategies
    print(f"\n{'='*70}")
    print("STRATEGY COMPARISON")
    print(f"{'='*70}\n")
    
    # Create a serializable copy for JSON output
    serializable_results = {}
    for name, data in all_results.items():
        serializable_results[name] = {
            'metrics': data['metrics'],
            'equity_curve': [[timestamp.isoformat(), value] for timestamp, value in data['equity_curve'].items()]
        }

    # Save detailed metrics to JSON
    json_path = Path('results') / 'all_metrics.json'
    with open(json_path, 'w') as f:
        json.dump(serializable_results, f, indent=4)
    print(f"Detailed metrics saved to {json_path}")

    analyzer = PerformanceAnalyzer(config.INITIAL_CAPITAL)
    comparison_df = analyzer.compare_strategies({
        name: data['metrics'] for name, data in all_results.items()
    })
    
    print(comparison_df.to_string())
    comparison_df.to_csv('results/strategy_comparison.csv')
    print("\nComparison saved to results/strategy_comparison.csv")
    
    # Visualization comparison
    visualizer = BacktestVisualizer()
    visualizer.plot_strategy_comparison(
        all_results,
        save_path='results/strategy_comparison.png'
    )
    
    return all_results

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Crypto Futures Trading Bot Backtest')
    parser.add_argument('--strategy', type=str, choices=['btc', 'sol', 'mr', 'all'], 
                       default='all', help='Which strategy to backtest (btc=funding, sol=squeeze, mr=mean reversion)')
    parser.add_argument('--download', action='store_true', 
                       help='Force download new data')
    parser.add_argument('--start-date', type=str, 
                       help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, 
                       help='End date (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    # Override dates if provided
    if args.start_date:
        config.START_DATE = args.start_date
    if args.end_date:
        config.END_DATE = args.end_date
    
    print(f"""
    ╔════════════════════════════════════════════════════════════╗
    ║                                                            ║
    ║      CRYPTO FUTURES TRADING BOT - BACKTEST SYSTEM         ║
    ║                                                            ║
    ║  Strategy Testing Period: {config.START_DATE} to {config.END_DATE}    ║
    ║  Initial Capital: ${config.INITIAL_CAPITAL:,.2f}                            ║
    ║                                                            ║
    ╚════════════════════════════════════════════════════════════╝
    """)
    
    try:
        if args.strategy == 'all':
            # Run all strategies
            results = run_multi_strategy_backtest(download_new_data=args.download)
        elif args.strategy == 'btc':
            # Run BTC only
            result = run_single_backtest(
                symbol=config.BTC_SYMBOL,
                timeframe=config.BTC_TIMEFRAME,
                strategy_class=BTCFundingStrategy,
                strategy_name='BTC_Funding_Divergence',
                download_new_data=args.download
            )
        elif args.strategy == 'sol':
            # Run SOL only
            result = run_single_backtest(
                symbol=config.SOL_SYMBOL,
                timeframe=config.SOL_TIMEFRAME,
                strategy_class=SOLSqueezeStrategy,
                strategy_name='SOL_Squeeze_Breakout',
                download_new_data=args.download
            )
        elif args.strategy == 'mr':
            # Run Mean Reversion only
            result = run_single_backtest(
                symbol=config.MR_SYMBOL,
                timeframe=config.MR_TIMEFRAME,
                strategy_class=BTCMeanReversionStrategy,
                strategy_name='BTC_Mean_Reversion',
                download_new_data=args.download
            )
        
        print(f"\n{'='*70}")
        print("BACKTEST COMPLETE!")
        print(f"{'='*70}\n")
        print("Results saved to ./results/")
        
    except KeyboardInterrupt:
        print("\n\nBacktest interrupted by user")
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
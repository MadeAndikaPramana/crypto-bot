# ============================================ 
# VISUALIZATION DATA EXPORTER
# ============================================ 
import pandas as pd
import numpy as np
from typing import List, Dict
from dataclasses import asdict
import json
from pathlib import Path

class BacktestVisualizer:
    """
    Exports backtest results data to JSON files.
    """
    
    def __init__(self, figsize=(15, 10)):
        self.figsize = figsize

    def _save_json(self, data, save_path):
        if save_path:
            json_path = Path(save_path).with_suffix('.json')
            json_path.parent.mkdir(parents=True, exist_ok=True)
            with open(json_path, 'w') as f:
                # Use pandas to handle numpy types
                pd.Series([data]).to_json(f, orient='records', indent=4)
            print(f"Data saved to {json_path}")

    def plot_equity_curve(self, equity_curve: pd.DataFrame, initial_capital: float, 
                         title: str = "Equity Curve", save_path: str = None):
        """Saves equity curve data to JSON."""
        equity_curve['peak'] = equity_curve['equity'].cummax()
        equity_curve['drawdown_pct'] = ((equity_curve['equity'] - equity_curve['peak']) 
                                       / equity_curve['peak']) * 100
        
        # Convert timestamp to string for JSON
        equity_curve_serializable = equity_curve.copy()
        equity_curve_serializable['timestamp'] = equity_curve_serializable['timestamp'].apply(lambda x: x.isoformat())
        
        data_to_save = {
            'title': title,
            'initial_capital': initial_capital,
            'equity_curve': equity_curve_serializable.to_dict(orient='records')
        }
        self._save_json(data_to_save, save_path)
    
    def plot_trade_distribution(self, trades: List, save_path: str = None):
        """Saves trade distribution data to JSON."""
        if not trades:
            print("No trades to analyze")
            return
        
        trades_df = pd.DataFrame([asdict(t) for t in trades])
        # Convert timestamp to string for JSON
        for col in ['entry_time', 'exit_time']:
            if col in trades_df.columns:
                trades_df[col] = pd.to_datetime(trades_df[col]).apply(lambda x: x.isoformat())

        self._save_json(trades_df.to_dict(orient='records'), save_path)
    
    def plot_monthly_returns(self, equity_curve: pd.DataFrame, save_path: str = None):
        """Saves monthly returns data to JSON."""
        if equity_curve.empty:
            print("Equity curve is empty, cannot calculate monthly returns.")
            return

        ec = equity_curve.copy()
        ec['date'] = pd.to_datetime(ec['timestamp'])
        ec = ec.set_index('date')
        
        monthly_equity = ec['equity'].resample('ME').last()
        monthly_returns = monthly_equity.pct_change() * 100
        
        monthly_returns_df = pd.DataFrame({
            'year': monthly_returns.index.year,
            'month': monthly_returns.index.month,
            'return': monthly_returns.values
        })
        
        pivot = monthly_returns_df.pivot(index='month', columns='year', values='return').fillna(0)
        
        self._save_json(pivot.to_dict(), save_path)
    
    def plot_strategy_comparison(self, results_dict: Dict[str, Dict], 
                                save_path: str = None):
        """Saves strategy comparison data to JSON."""
        
        serializable_results = {}
        for name, data in results_dict.items():
            equity_curve_df = data['equity_curve'].copy()
            equity_curve_df['timestamp'] = equity_curve_df['timestamp'].apply(lambda x: x.isoformat())
            
            serializable_results[name] = {
                'metrics': data['metrics'],
                'equity_curve': equity_curve_df.to_dict(orient='records')
            }
        
        self._save_json(serializable_results, save_path)

if __name__ == "__main__":
    print("Testing Visualizer Data Exporter...")
    
    # Create sample data
    dates = pd.to_datetime(pd.date_range('2024-01-01', periods=100, freq='1h'))
    equity_values = 10000 + np.random.randn(100).cumsum() * 100
    
    equity_curve_sample = pd.DataFrame({
        'timestamp': dates,
        'equity': equity_values,
        'balance': equity_values,
        'num_positions': np.random.randint(0, 2, 100)
    })
    
    visualizer = BacktestVisualizer()
    
    # Test equity curve export
    visualizer.plot_equity_curve(equity_curve_sample.copy(), 10000, 
                                title="Test Equity Curve", save_path="results/test_equity.png")

    # Test monthly returns
    visualizer.plot_monthly_returns(equity_curve_sample.copy(), "results/test_monthly_returns.png")
    
    # Test trade distribution
    from backtest_engine import Trade
    trades_sample = [
        Trade(entry_time=pd.to_datetime('2024-01-01 10:00'), exit_time=pd.to_datetime('2024-01-01 15:00'), entry_price=50000, exit_price=50500, size=1, pnl=500, pnl_pct=0.01, trade_type='long', hold_time_hours=5),
        Trade(entry_time=pd.to_datetime('2024-01-02 11:00'), exit_time=pd.to_datetime('2024-01-02 12:00'), entry_price=51000, exit_price=50900, size=1, pnl=-100, pnl_pct=-0.002, trade_type='short', hold_time_hours=1)
    ]
    visualizer.plot_trade_distribution(trades_sample, "results/test_trades.png")

    # Test strategy comparison
    results_dict_sample = {
        "Strategy_A": {
            "metrics": {"total_return_pct": 10.5, "sharpe_ratio": 1.2, "win_rate": 65.0},
            "equity_curve": equity_curve_sample.copy()
        },
        "Strategy_B": {
            "metrics": {"total_return_pct": -5.2, "sharpe_ratio": -0.4, "win_rate": 45.0},
            "equity_curve": equity_curve_sample.copy()
        }
    }
    visualizer.plot_strategy_comparison(results_dict_sample, "results/test_comparison.png")

    print("\nVisualization data export tests complete!")
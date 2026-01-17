# ============================================
# PERFORMANCE METRICS & ANALYSIS
# ============================================
import pandas as pd
import numpy as np
from typing import List, Dict
from dataclasses import asdict

class PerformanceAnalyzer:
    """
    Calculate comprehensive performance metrics for backtest results
    """
    
    def __init__(self, initial_capital: float):
        self.initial_capital = initial_capital
    
    def analyze(self, trades: List, equity_curve: pd.DataFrame) -> Dict:
        """
        Generate complete performance report
        """
        if not trades:
            return {
                'error': 'No trades executed',
                'total_trades': 0
            }
        
        # Convert trades to DataFrame for analysis
        trades_df = pd.DataFrame([asdict(t) for t in trades])
        
        # Basic metrics
        metrics = {}
        
        # === RETURN METRICS ===
        final_equity = equity_curve['equity'].iloc[-1]
        total_return = final_equity - self.initial_capital
        total_return_pct = (total_return / self.initial_capital) * 100
        
        metrics['initial_capital'] = self.initial_capital
        metrics['final_equity'] = final_equity
        metrics['total_return'] = total_return
        metrics['total_return_pct'] = total_return_pct
        
        # === TRADE STATISTICS ===
        metrics['total_trades'] = len(trades)
        metrics['winning_trades'] = len(trades_df[trades_df['pnl'] > 0])
        metrics['losing_trades'] = len(trades_df[trades_df['pnl'] < 0])
        metrics['breakeven_trades'] = len(trades_df[trades_df['pnl'] == 0])
        
        if metrics['total_trades'] > 0:
            metrics['win_rate'] = (metrics['winning_trades'] / metrics['total_trades']) * 100
        else:
            metrics['win_rate'] = 0
        
        # === P&L ANALYSIS ===
        winning_trades = trades_df[trades_df['pnl'] > 0]
        losing_trades = trades_df[trades_df['pnl'] < 0]
        
        if len(winning_trades) > 0:
            metrics['avg_win'] = winning_trades['pnl'].mean()
            metrics['avg_win_pct'] = winning_trades['pnl_pct'].mean()
            metrics['largest_win'] = winning_trades['pnl'].max()
            metrics['largest_win_pct'] = winning_trades['pnl_pct'].max()
        else:
            metrics['avg_win'] = 0
            metrics['avg_win_pct'] = 0
            metrics['largest_win'] = 0
            metrics['largest_win_pct'] = 0
        
        if len(losing_trades) > 0:
            metrics['avg_loss'] = losing_trades['pnl'].mean()
            metrics['avg_loss_pct'] = losing_trades['pnl_pct'].mean()
            metrics['largest_loss'] = losing_trades['pnl'].min()
            metrics['largest_loss_pct'] = losing_trades['pnl_pct'].min()
        else:
            metrics['avg_loss'] = 0
            metrics['avg_loss_pct'] = 0
            metrics['largest_loss'] = 0
            metrics['largest_loss_pct'] = 0
        
        # Profit Factor
        gross_profit = winning_trades['pnl'].sum() if len(winning_trades) > 0 else 0
        gross_loss = abs(losing_trades['pnl'].sum()) if len(losing_trades) > 0 else 0
        
        if gross_loss > 0:
            metrics['profit_factor'] = gross_profit / gross_loss
        else:
            metrics['profit_factor'] = float('inf') if gross_profit > 0 else 0
        
        # Expectancy
        metrics['expectancy'] = trades_df['pnl'].mean()
        metrics['expectancy_pct'] = trades_df['pnl_pct'].mean()
        
        # === RISK METRICS ===
        # Drawdown analysis
        equity_curve['peak'] = equity_curve['equity'].cummax()
        equity_curve['drawdown'] = equity_curve['equity'] - equity_curve['peak']
        equity_curve['drawdown_pct'] = (equity_curve['drawdown'] / equity_curve['peak']) * 100
        
        metrics['max_drawdown'] = equity_curve['drawdown'].min()
        metrics['max_drawdown_pct'] = equity_curve['drawdown_pct'].min()
        
        # Find max drawdown period
        dd_start_idx = equity_curve['drawdown'].idxmin()
        dd_peak = equity_curve.loc[:dd_start_idx, 'peak'].max()
        dd_peak_idx = equity_curve[equity_curve['equity'] == dd_peak].index[0]
        
        # Recovery (if recovered)
        recovery_idx = equity_curve[
            (equity_curve.index > dd_start_idx) & 
            (equity_curve['equity'] >= dd_peak)
        ].index
        
        if len(recovery_idx) > 0:
            recovery_time = equity_curve.loc[recovery_idx[0], 'timestamp'] - \
                          equity_curve.loc[dd_peak_idx, 'timestamp']
            metrics['max_dd_recovery_days'] = recovery_time.days
        else:
            metrics['max_dd_recovery_days'] = None  # Not recovered yet
        
        # Sharpe Ratio (assuming daily returns)
        equity_curve['returns'] = equity_curve['equity'].pct_change()
        daily_returns = equity_curve.set_index('timestamp')['returns'].resample('D').sum()
        
        if len(daily_returns) > 1 and daily_returns.std() > 0:
            metrics['sharpe_ratio'] = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)
        else:
            metrics['sharpe_ratio'] = 0
        
        # Sortino Ratio (downside deviation)
        downside_returns = daily_returns[daily_returns < 0]
        if len(downside_returns) > 1 and downside_returns.std() > 0:
            metrics['sortino_ratio'] = (daily_returns.mean() / downside_returns.std()) * np.sqrt(252)
        else:
            metrics['sortino_ratio'] = 0
        
        # Calmar Ratio
        if metrics['max_drawdown_pct'] != 0:
            annual_return = (final_equity / self.initial_capital) ** (365 / len(equity_curve)) - 1
            metrics['calmar_ratio'] = (annual_return * 100) / abs(metrics['max_drawdown_pct'])
        else:
            metrics['calmar_ratio'] = 0
        
        # === TRADE DURATION ===
        metrics['avg_hold_time_hours'] = trades_df['hold_time_hours'].mean()
        metrics['median_hold_time_hours'] = trades_df['hold_time_hours'].median()
        metrics['max_hold_time_hours'] = trades_df['hold_time_hours'].max()
        
        # === FEES ===
        metrics['total_fees_paid'] = trades_df['fees_paid'].sum()
        metrics['fees_as_pct_of_returns'] = (metrics['total_fees_paid'] / abs(total_return)) * 100 if total_return != 0 else 0
        
        # === CONSISTENCY ===
        # Consecutive wins/losses
        trades_df['result'] = trades_df['pnl'].apply(lambda x: 'W' if x > 0 else 'L')
        streaks = trades_df['result'].ne(trades_df['result'].shift()).cumsum()
        streak_lengths = trades_df.groupby([streaks, 'result']).size()
        
        win_streaks = streak_lengths[streak_lengths.index.get_level_values(1) == 'W']
        loss_streaks = streak_lengths[streak_lengths.index.get_level_values(1) == 'L']
        
        metrics['max_consecutive_wins'] = win_streaks.max() if len(win_streaks) > 0 else 0
        metrics['max_consecutive_losses'] = loss_streaks.max() if len(loss_streaks) > 0 else 0
        
        # === EXIT REASON BREAKDOWN ===
        exit_reasons = trades_df['exit_reason'].value_counts()
        metrics['exit_reasons'] = exit_reasons.to_dict()
        
        return metrics
    
    def print_report(self, metrics: Dict):
        """Print formatted performance report"""
        
        if 'error' in metrics:
            print(f"\n{'='*60}")
            print(f"ERROR: {metrics['error']}")
            print(f"{'='*60}")
            return
        
        print(f"\n{'='*60}")
        print(f"BACKTEST PERFORMANCE REPORT")
        print(f"{'='*60}")
        
        print(f"\n--- RETURNS ---")
        print(f"Initial Capital:     ${metrics['initial_capital']:>12,.2f}")
        print(f"Final Equity:        ${metrics['final_equity']:>12,.2f}")
        print(f"Total Return:        ${metrics['total_return']:>12,.2f}")
        print(f"Total Return %:      {metrics['total_return_pct']:>12.2f}%")
        
        print(f"\n--- TRADE STATISTICS ---")
        print(f"Total Trades:        {metrics['total_trades']:>12}")
        print(f"Winning Trades:      {metrics['winning_trades']:>12}")
        print(f"Losing Trades:       {metrics['losing_trades']:>12}")
        print(f"Win Rate:            {metrics['win_rate']:>12.2f}%")
        
        print(f"\n--- P&L ANALYSIS ---")
        print(f"Avg Win:             ${metrics['avg_win']:>12,.2f}  ({metrics['avg_win_pct']:.2f}%)")
        print(f"Avg Loss:            ${metrics['avg_loss']:>12,.2f}  ({metrics['avg_loss_pct']:.2f}%)")
        print(f"Largest Win:         ${metrics['largest_win']:>12,.2f}  ({metrics['largest_win_pct']:.2f}%)")
        print(f"Largest Loss:        ${metrics['largest_loss']:>12,.2f}  ({metrics['largest_loss_pct']:.2f}%)")
        print(f"Profit Factor:       {metrics['profit_factor']:>12.2f}")
        print(f"Expectancy:          ${metrics['expectancy']:>12,.2f}  ({metrics['expectancy_pct']:.2f}%)")
        
        print(f"\n--- RISK METRICS ---")
        print(f"Max Drawdown:        ${metrics['max_drawdown']:>12,.2f}")
        print(f"Max Drawdown %:      {metrics['max_drawdown_pct']:>12.2f}%")
        if metrics['max_dd_recovery_days']:
            print(f"DD Recovery:         {metrics['max_dd_recovery_days']:>12} days")
        else:
            print(f"DD Recovery:         {'Not recovered':>12}")
        print(f"Sharpe Ratio:        {metrics['sharpe_ratio']:>12.2f}")
        print(f"Sortino Ratio:       {metrics['sortino_ratio']:>12.2f}")
        print(f"Calmar Ratio:        {metrics['calmar_ratio']:>12.2f}")
        
        print(f"\n--- TRADE DURATION ---")
        print(f"Avg Hold Time:       {metrics['avg_hold_time_hours']:>12.1f} hours")
        print(f"Median Hold Time:    {metrics['median_hold_time_hours']:>12.1f} hours")
        print(f"Max Hold Time:       {metrics['max_hold_time_hours']:>12.1f} hours")
        
        print(f"\n--- FEES ---")
        print(f"Total Fees Paid:     ${metrics['total_fees_paid']:>12,.2f}")
        print(f"Fees % of Returns:   {metrics['fees_as_pct_of_returns']:>12.2f}%")
        
        print(f"\n--- CONSISTENCY ---")
        print(f"Max Consecutive Wins:   {metrics['max_consecutive_wins']:>9}")
        print(f"Max Consecutive Losses: {metrics['max_consecutive_losses']:>9}")
        
        print(f"\n--- EXIT REASONS ---")
        for reason, count in metrics['exit_reasons'].items():
            pct = (count / metrics['total_trades']) * 100
            print(f"{reason:.<30} {count:>5} ({pct:.1f}%)")
        
        print(f"\n{'='*60}\n")
    
    def compare_strategies(self, results_dict: Dict[str, Dict]) -> pd.DataFrame:
        """
        Compare multiple strategy results side-by-side
        
        Args:
            results_dict: Dict of {strategy_name: metrics_dict}
        
        Returns:
            DataFrame with comparison
        """
        comparison_metrics = [
            'total_return_pct',
            'total_trades',
            'win_rate',
            'profit_factor',
            'expectancy_pct',
            'max_drawdown_pct',
            'sharpe_ratio',
            'calmar_ratio',
            'avg_hold_time_hours'
        ]
        
        comparison_data = {}
        for strategy_name, metrics in results_dict.items():
            comparison_data[strategy_name] = {
                metric: metrics.get(metric, 0) 
                for metric in comparison_metrics
            }
        
        df = pd.DataFrame(comparison_data).T
        df.columns = [
            'Return %',
            'Trades',
            'Win Rate %',
            'Profit Factor',
            'Expectancy %',
            'Max DD %',
            'Sharpe',
            'Calmar',
            'Avg Hold (hrs)'
        ]
        
        return df


if __name__ == "__main__":
    # Test performance analyzer
    from backtest_engine import Trade
    from datetime import datetime, timedelta
    
    print("Testing Performance Analyzer...")
    
    # Create sample trades
    sample_trades = [
        Trade('BTC/USDT', 'LONG', 95000, 97000, datetime(2024,1,1), datetime(2024,1,2), 
              0.1, 200, 2.1, 'TP', 'BTC_Test', 3, 10, 24),
        Trade('BTC/USDT', 'SHORT', 96000, 95000, datetime(2024,1,3), datetime(2024,1,4),
              0.1, 100, 1.04, 'TP', 'BTC_Test', 3, 10, 24),
        Trade('BTC/USDT', 'LONG', 94000, 93000, datetime(2024,1,5), datetime(2024,1,6),
              0.1, -100, -1.06, 'SL', 'BTC_Test', 3, 10, 24),
    ]
    
    # Create sample equity curve
    dates = pd.date_range('2024-01-01', periods=100, freq='1h')
    equity_values = 10000 + np.random.randn(100).cumsum() * 100
    equity_curve = pd.DataFrame({
        'timestamp': dates,
        'equity': equity_values,
        'balance': equity_values,
        'num_positions': np.random.randint(0, 2, 100)
    })
    
    analyzer = PerformanceAnalyzer(initial_capital=10000)
    metrics = analyzer.analyze(sample_trades, equity_curve)
    analyzer.print_report(metrics)

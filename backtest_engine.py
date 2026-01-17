# ============================================
# BACKTEST ENGINE
# ============================================
import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from datetime import timedelta

@dataclass
class Position:
    """Open position tracking"""
    symbol: str
    side: str  # 'LONG' or 'SHORT'
    entry_price: float
    entry_time: pd.Timestamp
    size: float  # Full position size
    remaining_size: float  # Size still open (for partial exits)
    leverage: int
    sl_price: float
    tp_price: float  # For BTC (single TP)
    tp1_price: Optional[float] = None  # For SOL
    tp2_price: Optional[float] = None  # For SOL
    tp1_hit: bool = False
    sl_moved_to_entry: bool = False
    entry_reason: str = ""
    
    # Metadata
    strategy_name: str = ""
    entry_idx: int = 0

@dataclass
class Trade:
    """Closed trade record"""
    symbol: str
    side: str
    entry_price: float
    exit_price: float
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    size: float
    pnl: float
    pnl_pct: float
    exit_reason: str
    strategy_name: str
    leverage: int
    fees_paid: float
    hold_time_hours: float

class BacktestEngine:
    """
    Core backtesting engine
    Simulates order execution with realistic fees and slippage
    """
    
    def __init__(self, config):
        self.config = config
        self.initial_capital = config.INITIAL_CAPITAL
        self.reset()
    
    def reset(self):
        """Reset backtest state"""
        self.balance = self.initial_capital
        self.equity = self.initial_capital
        self.positions: List[Position] = []
        self.trades: List[Trade] = []
        self.equity_curve = []
        self.current_idx = 0
    
    def get_available_balance(self) -> float:
        """Get balance available for new trades (excluding margin in use)"""
        margin_in_use = sum(
            (p.size * p.entry_price) / p.leverage 
            for p in self.positions
        )
        return self.balance - margin_in_use
    
    def calculate_fees(self, value: float, is_maker: bool = False) -> float:
        """Calculate trading fees"""
        fee_rate = self.config.MAKER_FEE if is_maker else self.config.TAKER_FEE
        return value * fee_rate
    
    def apply_slippage(self, price: float, side: str) -> float:
        """Apply slippage to execution price"""
        slippage = price * self.config.SLIPPAGE_PCT
        if side in ['LONG', 'buy']:
            return price + slippage  # Pay more when buying
        else:
            return price - slippage  # Receive less when selling
    
    def open_position(self, signal, strategy_name: str, idx: int) -> bool:
        """
        Open a new position based on signal
        Returns True if successful
        """
        # Check if we have enough balance
        required_margin = (signal.size * signal.entry_price) / signal.leverage
        entry_value = signal.size * signal.entry_price
        entry_fees = self.calculate_fees(entry_value, is_maker=False)
        
        if required_margin + entry_fees > self.get_available_balance():
            return False
        
        # Apply slippage to entry
        actual_entry = self.apply_slippage(signal.entry_price, signal.action)
        
        # Deduct fees AND margin from balance
        self.balance -= entry_fees
        
        # Lock margin for this position
        required_margin = (signal.size * actual_entry) / signal.leverage
        self.balance -= required_margin
        
        # Create position
        position = Position(
            symbol=self.config.BTC_SYMBOL if 'BTC' in strategy_name else self.config.SOL_SYMBOL,
            side=signal.action,
            entry_price=actual_entry,
            entry_time=signal.timestamp,
            size=signal.size,
            remaining_size=signal.size,
            leverage=signal.leverage,
            sl_price=signal.sl_price,
            tp_price=getattr(signal, 'tp_price', None),
            tp1_price=getattr(signal, 'tp1_price', None),
            tp2_price=getattr(signal, 'tp2_price', None),
            entry_reason=signal.reason,
            strategy_name=strategy_name,
            entry_idx=idx
        )
        
        self.positions.append(position)
        return True
    
    def close_position(self, position: Position, exit_price: float, 
                      exit_time: pd.Timestamp, reason: str, 
                      size_to_close: Optional[float] = None):
        """
        Close position (full or partial)
        """
        if size_to_close is None:
            size_to_close = position.remaining_size
        
        # Apply slippage
        actual_exit = self.apply_slippage(
            exit_price, 
            'SHORT' if position.side == 'LONG' else 'LONG'
        )
        
        # Calculate P&L
        if position.side == 'LONG':
            pnl_per_unit = actual_exit - position.entry_price
        else:  # SHORT
            pnl_per_unit = position.entry_price - actual_exit
        
        gross_pnl = pnl_per_unit * size_to_close
        
        # P&L is already leveraged (calculated from full notional)
        # DO NOT multiply by leverage again - that would be double counting!
        
        # Calculate fees
        exit_value = size_to_close * actual_exit
        exit_fees = self.calculate_fees(exit_value, is_maker=False)
        
        # Net P&L
        net_pnl = gross_pnl - exit_fees
        
        # Update balance
        self.balance += net_pnl
        
        # Return margin
        margin_returned = (size_to_close * position.entry_price) / position.leverage
        self.balance += margin_returned
        
        # Calculate hold time
        hold_time = (exit_time - position.entry_time).total_seconds() / 3600
        
        # Record trade
        pnl_pct = (net_pnl / margin_returned) * 100 if margin_returned > 0 else 0
        
        trade = Trade(
            symbol=position.symbol,
            side=position.side,
            entry_price=position.entry_price,
            exit_price=actual_exit,
            entry_time=position.entry_time,
            exit_time=exit_time,
            size=size_to_close,
            pnl=net_pnl,
            pnl_pct=pnl_pct,
            exit_reason=reason,
            strategy_name=position.strategy_name,
            leverage=position.leverage,
            fees_paid=exit_fees,
            hold_time_hours=hold_time
        )
        
        self.trades.append(trade)
        
        # Update position
        position.remaining_size -= size_to_close
        
        # Remove if fully closed
        if position.remaining_size <= 0:
            self.positions.remove(position)
    
    def update_position_exits(self, df: pd.DataFrame, idx: int):
        """
        Check and execute SL/TP exits for all open positions
        """
        current_high = df.loc[idx, 'high']
        current_low = df.loc[idx, 'low']
        current_close = df.loc[idx, 'close']
        current_time = df.loc[idx, 'timestamp']
        
        positions_to_check = self.positions.copy()
        
        for position in positions_to_check:
            # Check Stop Loss
            sl_hit = False
            if position.side == 'LONG':
                sl_hit = current_low <= position.sl_price
                exit_price = position.sl_price if sl_hit else None
            else:  # SHORT
                sl_hit = current_high >= position.sl_price
                exit_price = position.sl_price if sl_hit else None
            
            if sl_hit:
                self.close_position(position, exit_price, current_time, "Stop Loss")
                continue
            
            # Check Take Profit(s)
            # For SOL with partial TPs
            if position.tp1_price is not None and not position.tp1_hit:
                tp1_hit = False
                if position.side == 'LONG':
                    tp1_hit = current_high >= position.tp1_price
                    tp_exit_price = position.tp1_price
                else:
                    tp1_hit = current_low <= position.tp1_price
                    tp_exit_price = position.tp1_price
                
                if tp1_hit:
                    # Close 50% at TP1
                    self.close_position(
                        position, 
                        tp_exit_price, 
                        current_time, 
                        "TP1 (50%)",
                        size_to_close=position.size * 0.5
                    )
                    position.tp1_hit = True
                    
                    # Move SL to entry (breakeven)
                    position.sl_price = position.entry_price
                    position.sl_moved_to_entry = True
                    continue
            
            # Check TP2 (remaining 50%)
            if position.tp2_price is not None and position.tp1_hit:
                tp2_hit = False
                if position.side == 'LONG':
                    tp2_hit = current_high >= position.tp2_price
                    tp_exit_price = position.tp2_price
                else:
                    tp2_hit = current_low <= position.tp2_price
                    tp_exit_price = position.tp2_price
                
                if tp2_hit:
                    # Close remaining position
                    self.close_position(position, tp_exit_price, current_time, "TP2 (50%)")
                    continue
            
            # Single TP (for BTC)
            if position.tp_price is not None and position.tp1_price is None:
                tp_hit = False
                if position.side == 'LONG':
                    tp_hit = current_high >= position.tp_price
                    tp_exit_price = position.tp_price
                else:
                    tp_hit = current_low <= position.tp_price
                    tp_exit_price = position.tp_price
                
                if tp_hit:
                    self.close_position(position, tp_exit_price, current_time, "Take Profit")
                    continue
    
    def update_equity(self, current_prices: Dict[str, float]):
        """
        Update current equity based on open positions
        """
        # Start with cash balance
        equity = self.balance
        
        # Add unrealized P&L from open positions
        for position in self.positions:
            current_price = current_prices.get(position.symbol, position.entry_price)
            
            if position.side == 'LONG':
                unrealized_pnl = (current_price - position.entry_price) * position.remaining_size
            else:
                unrealized_pnl = (position.entry_price - current_price) * position.remaining_size
            
            # Apply leverage
            unrealized_pnl *= position.leverage
            
            equity += unrealized_pnl
        
        self.equity = equity
    
    def run(self, df: pd.DataFrame, strategy, strategy_name: str) -> Dict:
        """
        Run backtest for a single strategy
        
        Args:
            df: DataFrame with OHLCV + indicators
            strategy: Strategy instance with evaluate() method
            strategy_name: Name for tracking
        
        Returns:
            Dictionary with results
        """
        print(f"\nRunning backtest for {strategy_name}...")
        
        self.reset()
        
        # Main backtest loop
        for idx in df.index:
            self.current_idx = idx
            current_time = df.loc[idx, 'timestamp']
            current_close = df.loc[idx, 'close']
            
            # Update position exits first (SL/TP checks)
            self.update_position_exits(df, idx)
            
            # Check strategy-specific exits (time stops, etc)
            if hasattr(strategy, 'check_exit'):
                for position in self.positions.copy():
                    if position.strategy_name == strategy_name:
                        should_exit, reason = strategy.check_exit(
                            asdict(position), df, idx
                        )
                        if should_exit:
                            self.close_position(
                                position, current_close, current_time, reason
                            )
            
            # Generate new signals
            signal = strategy.evaluate(
                df, idx, self.get_available_balance(), self.positions
            )
            
            if signal and signal.action != 'WAIT':
                self.open_position(signal, strategy_name, idx)
            
            # Update equity curve
            current_prices = {
                self.config.BTC_SYMBOL: df.loc[idx, 'close'],
                self.config.SOL_SYMBOL: df.loc[idx, 'close']
            }
            self.update_equity(current_prices)
            
            self.equity_curve.append({
                'timestamp': current_time,
                'equity': self.equity,
                'balance': self.balance,
                'num_positions': len(self.positions)
            })
        
        # Close any remaining positions at final price
        for position in self.positions.copy():
            final_price = df.loc[df.index[-1], 'close']
            final_time = df.loc[df.index[-1], 'timestamp']
            self.close_position(position, final_price, final_time, "Backtest End")
        
        print(f"Backtest complete: {len(self.trades)} trades executed")
        
        return {
            'trades': self.trades,
            'equity_curve': pd.DataFrame(self.equity_curve),
            'final_equity': self.equity,
            'final_balance': self.balance
        }


if __name__ == "__main__":
    # Test backtest engine
    from config import config
    from strategies.btc_funding import BTCFundingStrategy
    import numpy as np
    
    print("Testing Backtest Engine...")
    
    # Create sample data
    dates = pd.date_range('2024-01-01', periods=1000, freq='4h')
    sample_df = pd.DataFrame({
        'timestamp': dates,
        'open': np.random.randn(1000).cumsum() + 95000,
        'high': np.random.randn(1000).cumsum() + 95500,
        'low': np.random.randn(1000).cumsum() + 94500,
        'close': np.random.randn(1000).cumsum() + 95000,
        'volume': np.random.uniform(1000000, 5000000, 1000),
        'ema_200': np.random.randn(1000).cumsum() + 94000,
        'atr_14': np.random.uniform(2000, 3000, 1000),
        'funding_rate': np.random.uniform(-0.001, 0.001, 1000),
        'oi_change_pct': np.random.uniform(-0.02, 0.02, 1000)
    })
    
    # Initialize
    engine = BacktestEngine(config)
    strategy = BTCFundingStrategy(config)
    
    # Run backtest
    results = engine.run(sample_df, strategy, "BTC_Test")
    
    print(f"\nResults:")
    print(f"  Initial Capital: ${config.INITIAL_CAPITAL:,.2f}")
    print(f"  Final Equity: ${results['final_equity']:,.2f}")
    print(f"  Total Trades: {len(results['trades'])}")
    print(f"  P&L: ${results['final_equity'] - config.INITIAL_CAPITAL:,.2f}")
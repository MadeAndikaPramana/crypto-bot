# ============================================
# SOL VOLATILITY SQUEEZE BREAKOUT STRATEGY
# ============================================
from dataclasses import dataclass
from typing import Optional, Literal
import pandas as pd

@dataclass
class Signal:
    """Trading signal with all required information"""
    action: Literal['LONG', 'SHORT', 'WAIT']
    entry_price: float
    sl_price: float
    tp1_price: float  # First target (50% position)
    tp2_price: float  # Second target (remaining 50%)
    size: float
    leverage: int
    reason: str
    timestamp: pd.Timestamp
    
    # Additional metadata
    atr: float = 0.0
    rsi: float = 0.0
    bb_width: float = 0.0
    volume_ratio: float = 0.0

class SOLSqueezeStrategy:
    """
    SOL Volatility Squeeze Breakout Strategy
    
    Concept: Bollinger Band squeeze followed by breakout
    - Low volatility (BB width) creates tension
    - Breakout direction confirmed by volume + RSI
    - Partial profit taking (50% at TP1, 50% at TP2)
    - Trailing SL after TP1 hit
    
    Key filters:
    - BB width must be compressed for min N candles
    - Volume must be > 1.5x average (real participation)
    - RSI confirms direction (>50 for longs, <50 for shorts)
    - Price must close beyond BB (not just wick)
    """
    
    def __init__(self, config):
        self.config = config
        self.name = "SOL_Squeeze_Breakout"
        self.required_data = ['ohlcv']
    
    def _calculate_position_size(self, current_balance: float, entry_price: float, 
                                  sl_price: float) -> float:
        """
        Calculate position size with safety caps
        
        Returns position size in base currency (SOL)
        """
        risk_amount = current_balance * self.config.RISK_PER_TRADE
        sl_distance_pct = abs(entry_price - sl_price) / entry_price
        position_value = risk_amount / sl_distance_pct
        
        # SAFETY CAP 1: Max 50% of balance as position value (notional)
        max_position_value = current_balance * 0.5
        if position_value > max_position_value:
            position_value = max_position_value
        
        position_size = position_value / entry_price
        
        # SAFETY CAP 2: Verify max loss doesn't exceed 2% of balance
        max_loss = position_size * abs(entry_price - sl_price)
        max_loss_pct = max_loss / current_balance
        
        if max_loss_pct > 0.02:  # 2% hard limit
            position_size = position_size * (0.02 / max_loss_pct)
        
        return position_size
    
    def evaluate(self, df: pd.DataFrame, idx: int, current_balance: float,
                 open_positions: list) -> Optional[Signal]:
        """
        Evaluate strategy at given candle index
        """
        # Skip if we already have max positions
        if len(open_positions) >= self.config.MAX_OPEN_POSITIONS:
            return None
        
        # Need enough history
        if idx < self.config.SOL_BB_PERIOD + self.config.SOL_SQUEEZE_MIN_CANDLES:
            return None
        
        # Check if we already have SOL position
        if any(p.symbol == self.config.SOL_SYMBOL for p in open_positions):
            return None
        
        # Get current values
        current_price = df.loc[idx, 'close']
        current_upper = df.loc[idx, 'bb_upper']
        current_lower = df.loc[idx, 'bb_lower']
        current_middle = df.loc[idx, 'bb_middle']
        current_width = df.loc[idx, 'bb_width']
        current_rsi = df.loc[idx, 'rsi_14']
        current_atr = df.loc[idx, 'atr_14']
        current_volume = df.loc[idx, 'volume']
        avg_volume = df.loc[idx, 'volume_ma_20']
        timestamp = df.loc[idx, 'timestamp']
        current_adx = df.loc[idx, 'adx_14']

        # Saring: Hanya masuk jika tren cukup kuat (ADX > 20)
        if current_adx < 20:
            return None
        
        # Skip if key values are NaN
        if any(pd.isna(x) for x in [current_atr, current_rsi, current_width, avg_volume]):
            return None
        
        if current_atr == 0 or avg_volume == 0:
            return None
        
        # === CHECK SQUEEZE CONDITION ===
        # BB Width must be compressed for recent N candles
        start_idx = idx - self.config.SOL_SQUEEZE_MIN_CANDLES
        recent_widths = df.loc[start_idx:idx, 'bb_width']
        
        is_squeeze = (recent_widths < self.config.SOL_SQUEEZE_THRESHOLD).all()
        
        if not is_squeeze:
            return None
        
        # === CHECK VOLUME CONFIRMATION ===
        volume_ratio = current_volume / avg_volume
        volume_confirmed = volume_ratio > self.config.SOL_VOLUME_MULTIPLIER
        
        if not volume_confirmed:
            return None
        
        signal = None
        
        # === LONG SETUP ===
        # Breakout above upper BB + RSI > 50 + high volume
        prev_price = df.loc[idx-1, 'close']
        prev_upper = df.loc[idx-1, 'bb_upper']

        if current_price > current_upper and prev_price > prev_upper and current_rsi > 50:
            
            # Confirm it's a close above BB (not just a wick)
            # This is already true since we're using close price
            
            # Check RSI momentum (rising)
            if idx > 0:
                prev_rsi = df.loc[idx - 1, 'rsi_14']
                if not pd.isna(prev_rsi) and current_rsi < prev_rsi:
                    # RSI not rising, weaker signal
                    pass  # Still allow but log this
            
            # Calculate SL (use middle BB or ATR-based, whichever is tighter)
            atr_sl = current_price - (current_atr * self.config.SOL_ATR_SL_MULTIPLIER)
            bb_sl = current_middle
            sl_price = max(atr_sl, bb_sl)  # Tighter stop
            
            # Calculate TPs
            tp1_price = current_price + (current_atr * self.config.SOL_ATR_TP1_MULTIPLIER)
            tp2_price = current_price + (current_atr * self.config.SOL_ATR_TP2_MULTIPLIER)
            
            # Position sizing with safety caps
            position_size = self._calculate_position_size(current_balance, current_price, sl_price)
            
            signal = Signal(
                action='LONG',
                entry_price=current_price,
                sl_price=sl_price,
                tp1_price=tp1_price,
                tp2_price=tp2_price,
                size=position_size,
                leverage=self.config.MAX_LEVERAGE_SOL,
                reason=f"Squeeze breakout UP: RSI={current_rsi:.1f}, Vol={volume_ratio:.1f}x",
                timestamp=timestamp,
                atr=current_atr,
                rsi=current_rsi,
                bb_width=current_width,
                volume_ratio=volume_ratio
            )
        
        # === SHORT SETUP ===
        # Breakout below lower BB + RSI < 50 + high volume
        elif current_price < current_lower and current_rsi < 50:
            
            # Check RSI momentum (falling)
            if idx > 0:
                prev_rsi = df.loc[idx - 1, 'rsi_14']
                if not pd.isna(prev_rsi) and current_rsi > prev_rsi:
                    pass  # Still allow but weaker
            
            # Calculate SL
            atr_sl = current_price + (current_atr * self.config.SOL_ATR_SL_MULTIPLIER)
            bb_sl = current_middle
            sl_price = min(atr_sl, bb_sl)  # Tighter stop
            
            # Calculate TPs
            tp1_price = current_price - (current_atr * self.config.SOL_ATR_TP1_MULTIPLIER)
            tp2_price = current_price - (current_atr * self.config.SOL_ATR_TP2_MULTIPLIER)
            
            # Position sizing with safety caps
            position_size = self._calculate_position_size(current_balance, current_price, sl_price)
            
            signal = Signal(
                action='SHORT',
                entry_price=current_price,
                sl_price=sl_price,
                tp1_price=tp1_price,
                tp2_price=tp2_price,
                size=position_size,
                leverage=self.config.MAX_LEVERAGE_SOL,
                reason=f"Squeeze breakout DOWN: RSI={current_rsi:.1f}, Vol={volume_ratio:.1f}x",
                timestamp=timestamp,
                atr=current_atr,
                rsi=current_rsi,
                bb_width=current_width,
                volume_ratio=volume_ratio
            )
        
        return signal
    
    def check_partial_exit(self, position: dict, current_price: float) -> tuple[bool, str]:
        """
        Check if TP1 has been hit (for partial profit taking)
        
        Returns: (should_take_partial, reason)
        """
        if position.get('tp1_hit', False):
            return False, ""  # Already took partial profit
        
        if position['side'] == 'LONG':
            if current_price >= position['tp1_price']:
                return True, "TP1 reached"
        else:  # SHORT
            if current_price <= position['tp1_price']:
                return True, "TP1 reached"
        
        return False, ""
    
    def update_trailing_sl(self, position: dict, current_price: float) -> Optional[float]:
        """
        Update stop loss to entry after TP1 is hit (breakeven + trailing)
        
        Returns: New SL price or None if no update needed
        """
        if not position.get('tp1_hit', False):
            return None
        
        # After TP1 hit, move SL to breakeven (entry price)
        if position.get('sl_moved_to_entry', False):
            return None  # Already moved
        
        return position['entry_price']


if __name__ == "__main__":
    # Test strategy
    from config import config
    import numpy as np
    
    print("Testing SOL Squeeze Strategy...")
    
    # Create sample data with squeeze scenario
    dates = pd.date_range('2024-01-01', periods=100, freq='1h')
    
    # Simulate squeeze: low volatility then expansion
    bb_widths = np.concatenate([
        np.random.uniform(0.03, 0.039, 50),  # Squeeze period
        np.random.uniform(0.05, 0.10, 50)    # Expansion
    ])
    
    sample_df = pd.DataFrame({
        'timestamp': dates,
        'close': np.random.randn(100).cumsum() + 140,
        'volume': np.random.uniform(800000, 1200000, 100),
        'bb_upper': np.random.randn(100).cumsum() + 142,
        'bb_middle': np.random.randn(100).cumsum() + 140,
        'bb_lower': np.random.randn(100).cumsum() + 138,
        'bb_width': bb_widths,
        'rsi_14': np.random.uniform(40, 60, 100),
        'atr_14': np.random.uniform(6, 9, 100),
        'volume_ma_20': np.random.uniform(700000, 900000, 100)
    })
    
    # Force a breakout signal at idx 55
    sample_df.loc[55, 'close'] = sample_df.loc[55, 'bb_upper'] + 2
    sample_df.loc[55, 'rsi_14'] = 58
    sample_df.loc[55, 'volume'] = sample_df.loc[55, 'volume_ma_20'] * 2
    
    strategy = SOLSqueezeStrategy(config)
    
    # Test evaluation
    signal = strategy.evaluate(sample_df, 55, 10000, [])
    
    if signal:
        print(f"\nSignal generated:")
        print(f"  Action: {signal.action}")
        print(f"  Entry: ${signal.entry_price:.2f}")
        print(f"  SL: ${signal.sl_price:.2f}")
        print(f"  TP1: ${signal.tp1_price:.2f} (50% exit)")
        print(f"  TP2: ${signal.tp2_price:.2f} (50% exit)")
        print(f"  Size: {signal.size:.2f} SOL")
        print(f"  Reason: {signal.reason}")
    else:
        print("\nNo signal generated")
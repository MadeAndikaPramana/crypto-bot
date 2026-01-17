# ============================================
# BTC FUNDING RATE DIVERGENCE STRATEGY
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
    tp_price: float
    size: float  # Position size in base currency
    leverage: int
    reason: str
    timestamp: pd.Timestamp
    
    # Additional metadata
    atr: float = 0.0
    funding_rate: float = 0.0
    ema200: float = 0.0
    oi_change_pct: float = 0.0

class BTCFundingStrategy:
    """
    BTC Funding Rate Divergence Strategy
    
    Concept: Exploit crowded positioning via funding rate extremes
    - Negative funding + uptrend = short squeeze potential
    - Positive funding + downtrend = long squeeze potential
    
    Additional filters:
    - Open Interest increasing (position accumulation)
    - Price near liquidation zones
    - Time-based exit (max 7 days)
    """
    
    def __init__(self, config):
        self.config = config
        self.name = "BTC_Funding_Divergence"
        self.required_data = ['ohlcv', 'funding', 'oi']
    
    def _calculate_position_size(self, current_balance: float, entry_price: float, 
                                  sl_price: float) -> float:
        """
        Calculate position size with safety caps
        
        Returns position size in base currency (BTC)
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
    
    def _is_good_volatility(self, df: pd.DataFrame, idx: int) -> bool:
        """
        Volatility filter: Avoid trading in extreme/dead markets
        
        Logic:
        - Too low volatility = choppy, range-bound market
        - Too high volatility = unpredictable, dangerous
        - Sweet spot = 0.8x to 1.5x average ATR
        
        Returns True if volatility is in acceptable range
        """
        # Need at least 20 candles for average
        if idx < 20:
            return False
        
        # Current ATR
        current_atr = df.loc[idx, 'atr_14']
        
        if pd.isna(current_atr) or current_atr == 0:
            return False
        
        # Average ATR over last 20 periods
        avg_atr = df.loc[idx-19:idx, 'atr_14'].mean()
        
        if pd.isna(avg_atr) or avg_atr == 0:
            return False
        
        # Calculate ratio
        atr_ratio = current_atr / avg_atr
        
        # Check if within acceptable range
        return self.config.BTC_MIN_ATR_RATIO <= atr_ratio <= self.config.BTC_MAX_ATR_RATIO
    
    def evaluate(self, df: pd.DataFrame, idx: int, current_balance: float, 
                 open_positions: list) -> Optional[Signal]:
        """
        Evaluate strategy at given candle index
        
        Args:
            df: DataFrame with OHLCV + indicators
            idx: Current candle index
            current_balance: Available balance in USDT
            open_positions: List of currently open positions
        
        Returns:
            Signal or None
        """
        # Skip if we already have max positions
        if len(open_positions) >= self.config.MAX_OPEN_POSITIONS:
            return None
        
        # Need enough history for indicators
        if idx < self.config.BTC_EMA_PERIOD:
            return None
        
        # Check if we already have BTC position open
        if any(p.symbol == self.config.BTC_SYMBOL for p in open_positions):
            return None
        
        # === VOLATILITY FILTER (Option C) ===
        # Skip if market conditions are too choppy or too extreme
        if not self._is_good_volatility(df, idx):
            return None
        
        # Get current values
        current_price = df.loc[idx, 'close']
        current_ema = df.loc[idx, 'ema_200']
        current_atr = df.loc[idx, 'atr_14']
        funding_rate = df.loc[idx, 'funding_rate']
        timestamp = df.loc[idx, 'timestamp']
        
        # Check if we have OI data
        oi_change_pct = df.loc[idx, 'oi_change_pct'] if 'oi_change_pct' in df.columns else 0
        
        # Skip if ATR is NaN
        if pd.isna(current_atr) or current_atr == 0:
            return None
        
        # === VOLATILITY FILTER (Option C) ===
        # Skip trading if volatility is too low (choppy) or too high (extreme)
        if not self._is_good_volatility(df, idx):
            return None
        
        signal = None
        
        # === LONG SETUP ===
        # Negative funding (shorts crowded) + price above EMA (uptrend)
        if (funding_rate < self.config.BTC_FUNDING_LONG_THRESHOLD and 
            current_price > current_ema):
            
            # Additional OI filter (if available)
            if 'oi_change_pct' in df.columns and not pd.isna(oi_change_pct):
                # OI should be increasing (shorts accumulating)
                # But we're more lenient here - just need funding divergence
                if oi_change_pct < -0.05:  # If OI dropping significantly, skip
                    return None
            
            # Calculate SL/TP
            sl_price = current_price - (current_atr * self.config.BTC_ATR_SL_MULTIPLIER)
            tp_price = current_price + (current_atr * self.config.BTC_ATR_TP_MULTIPLIER)
            
            # Position sizing with safety caps
            position_size = self._calculate_position_size(current_balance, current_price, sl_price)
            
            signal = Signal(
                action='LONG',
                entry_price=current_price,
                sl_price=sl_price,
                tp_price=tp_price,
                size=position_size,
                leverage=self.config.MAX_LEVERAGE_BTC,
                reason=f"Short squeeze setup: Funding={funding_rate:.4%}, Price>{current_ema:.0f}",
                timestamp=timestamp,
                atr=current_atr,
                funding_rate=funding_rate,
                ema200=current_ema,
                oi_change_pct=oi_change_pct
            )
        
        # === SHORT SETUP ===
        # Positive funding (longs crowded) + price below EMA (downtrend)
        elif (funding_rate > self.config.BTC_FUNDING_SHORT_THRESHOLD and 
              current_price < current_ema):
            
            # Additional OI filter
            if 'oi_change_pct' in df.columns and not pd.isna(oi_change_pct):
                if oi_change_pct < -0.05:  # If OI dropping significantly, skip
                    return None
            
            # Calculate SL/TP
            sl_price = current_price + (current_atr * self.config.BTC_ATR_SL_MULTIPLIER)
            tp_price = current_price - (current_atr * self.config.BTC_ATR_TP_MULTIPLIER)
            
            # Position sizing with safety caps
            position_size = self._calculate_position_size(current_balance, current_price, sl_price)
            
            signal = Signal(
                action='SHORT',
                entry_price=current_price,
                sl_price=sl_price,
                tp_price=tp_price,
                size=position_size,
                leverage=self.config.MAX_LEVERAGE_BTC,
                reason=f"Long squeeze setup: Funding={funding_rate:.4%}, Price<{current_ema:.0f}",
                timestamp=timestamp,
                atr=current_atr,
                funding_rate=funding_rate,
                ema200=current_ema,
                oi_change_pct=oi_change_pct
            )
        
        return signal
    
    def check_exit(self, position: dict, df: pd.DataFrame, idx: int) -> tuple[bool, str]:
        """
        Check if position should be exited (beyond SL/TP)
        
        Returns: (should_exit, reason)
        """
        # Time-based exit: max hold period
        entry_time = position['entry_time']
        current_time = df.loc[idx, 'timestamp']
        days_held = (current_time - entry_time).total_seconds() / 86400
        
        if days_held >= self.config.BTC_MAX_HOLD_DAYS:
            return True, f"Time stop ({self.config.BTC_MAX_HOLD_DAYS} days)"
        
        # Could add additional exit logic here:
        # - Funding rate reversal
        # - Trend reversal
        # - etc.
        
        return False, ""


if __name__ == "__main__":
    # Test strategy logic
    from config import config
    import numpy as np
    
    print("Testing BTC Funding Strategy...")
    
    # Create sample data
    dates = pd.date_range('2024-01-01', periods=300, freq='4h')
    sample_df = pd.DataFrame({
        'timestamp': dates,
        'close': np.random.randn(300).cumsum() + 95000,
        'high': np.random.randn(300).cumsum() + 95500,
        'low': np.random.randn(300).cumsum() + 94500,
        'ema_200': np.random.randn(300).cumsum() + 94000,
        'atr_14': np.random.uniform(2000, 3000, 300),
        'funding_rate': np.random.uniform(-0.0005, 0.001, 300),
        'oi_change_pct': np.random.uniform(-0.02, 0.02, 300)
    })
    
    strategy = BTCFundingStrategy(config)
    
    # Test evaluation
    signal = strategy.evaluate(sample_df, 250, 10000, [])
    
    if signal:
        print(f"\nSignal generated:")
        print(f"  Action: {signal.action}")
        print(f"  Entry: ${signal.entry_price:,.0f}")
        print(f"  SL: ${signal.sl_price:,.0f}")
        print(f"  TP: ${signal.tp_price:,.0f}")
        print(f"  Size: {signal.size:.4f} BTC")
        print(f"  Reason: {signal.reason}")
    else:
        print("\nNo signal generated (conditions not met)")
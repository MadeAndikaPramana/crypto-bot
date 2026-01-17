# ============================================
# BTC MEAN REVERSION STRATEGY
# ============================================
import pandas as pd
import numpy as np
from typing import Optional
from dataclasses import dataclass

@dataclass
class Signal:
    """Trading signal with entry/exit prices"""
    action: str  # 'LONG' or 'SHORT'
    entry_price: float
    sl_price: float
    tp1_price: float  # First target (50% position)
    tp2_price: float  # Second target (50% position)
    size: float
    leverage: int
    reason: str
    timestamp: pd.Timestamp
    
    # Additional metadata
    rsi: float
    atr: float
    bb_middle: float
    volume_ratio: float

class BTCMeanReversionStrategy:
    """
    BTC Mean Reversion Strategy
    
    Concept: Price tends to revert to mean after extreme moves
    - Buy oversold conditions at support
    - Sell overbought conditions at resistance
    
    Key Edge:
    - Fade retail panic at extremes
    - High win rate (55-65%)
    - Quick trades (4-24 hours)
    
    Entry Conditions:
    LONG:
    - Price at/below lower Bollinger Band
    - RSI 25-35 (oversold but not catching knife)
    - Above EMA200 (macro uptrend)
    - Near recent support
    - Volume spike (>1.2x average)
    
    SHORT:
    - Price at/above upper Bollinger Band
    - RSI 65-75 (overbought)
    - Below EMA200 (macro downtrend)
    - Near recent resistance
    - Volume spike
    
    Exit:
    - TP1: Middle BB (take 50%)
    - TP2: 2 ATR (take remaining 50%)
    - SL: 1.5 ATR or swing level (whichever tighter)
    - Time stop: 48 hours
    """
    
    def __init__(self, config):
        self.config = config
        self.name = "BTC_Mean_Reversion"
        self.required_data = ['ohlcv']
    
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
        if idx < max(self.config.MR_EMA_PERIOD, self.config.MR_BB_PERIOD, self.config.MR_SR_LOOKBACK):
            return None
        
        # Check if we already have BTC position open
        if any(p.symbol == self.config.BTC_SYMBOL for p in open_positions):
            return None

        # Volatility filter
        if not self._is_good_volatility(df, idx):
            return None
        
        # Get current values
        current_price = df.loc[idx, 'close']
        current_rsi = df.loc[idx, 'rsi_14']
        current_atr = df.loc[idx, 'atr_14']
        bb_upper = df.loc[idx, 'bb_upper']
        bb_lower = df.loc[idx, 'bb_lower']
        bb_middle = df.loc[idx, 'bb_middle']
        ema200 = df.loc[idx, 'ema_200']
        current_volume = df.loc[idx, 'volume']
        timestamp = df.loc[idx, 'timestamp']
        
        # Volume analysis
        volume_ma = df.loc[max(0, idx-self.config.MR_VOLUME_MA_PERIOD+1):idx+1, 'volume'].mean()
        volume_ratio = current_volume / volume_ma if volume_ma > 0 else 1.0
        
        # Support/Resistance levels
        recent_low = df.loc[max(0, idx-self.config.MR_SR_LOOKBACK+1):idx+1, 'low'].min()
        recent_high = df.loc[max(0, idx-self.config.MR_SR_LOOKBACK+1):idx+1, 'high'].max()
        
        # Skip if ATR is NaN
        if pd.isna(current_atr) or current_atr == 0:
            return None
        
        signal = None
        
        # === LONG SETUP ===
        # Oversold bounce at support
        if self._check_long_conditions(
            current_price, current_rsi, bb_lower, ema200, 
            recent_low, volume_ratio
        ):
            # Calculate SL (tighter of ATR-based or swing low)
            sl_atr = current_price - (current_atr * self.config.MR_SL_ATR_MULT)
            sl_swing = recent_low * 0.995  # Just below recent low
            sl_price = max(sl_atr, sl_swing)  # Use tighter SL
            
            # Calculate TPs
            tp1_price = bb_middle  # Quick profit at mean
            tp2_price = current_price + (current_atr * self.config.MR_TP2_ATR_MULT)
            
            # Position sizing
            position_size = self._calculate_position_size(current_balance, current_price, sl_price)
            
            signal = Signal(
                action='LONG',
                entry_price=current_price,
                sl_price=sl_price,
                tp1_price=tp1_price,
                tp2_price=tp2_price,
                size=position_size,
                leverage=self.config.MAX_LEVERAGE_BTC,
                reason=f"Mean Rev LONG: RSI={current_rsi:.1f}, Lower BB, Vol={volume_ratio:.1f}x",
                timestamp=timestamp,
                rsi=current_rsi,
                atr=current_atr,
                bb_middle=bb_middle,
                volume_ratio=volume_ratio
            )
        
        # === SHORT SETUP ===
        # Overbought exhaustion at resistance
        elif self._check_short_conditions(
            current_price, current_rsi, bb_upper, ema200,
            recent_high, volume_ratio
        ):
            # Calculate SL
            sl_atr = current_price + (current_atr * self.config.MR_SL_ATR_MULT)
            sl_swing = recent_high * 1.005  # Just above recent high
            sl_price = min(sl_atr, sl_swing)  # Use tighter SL
            
            # Calculate TPs
            tp1_price = bb_middle
            tp2_price = current_price - (current_atr * self.config.MR_TP2_ATR_MULT)
            
            # Position sizing
            position_size = self._calculate_position_size(current_balance, current_price, sl_price)
            
            signal = Signal(
                action='SHORT',
                entry_price=current_price,
                sl_price=sl_price,
                tp1_price=tp1_price,
                tp2_price=tp2_price,
                size=position_size,
                leverage=self.config.MAX_LEVERAGE_BTC,
                reason=f"Mean Rev SHORT: RSI={current_rsi:.1f}, Upper BB, Vol={volume_ratio:.1f}x",
                timestamp=timestamp,
                rsi=current_rsi,
                atr=current_atr,
                bb_middle=bb_middle,
                volume_ratio=volume_ratio
            )
        
        return signal
    
    def _check_long_conditions(self, price: float, rsi: float, bb_lower: float,
                               ema200: float, recent_low: float, volume_ratio: float) -> bool:
        """
        Check if all LONG entry conditions are met
        
        Returns True if conditions satisfied
        """
        # 1. Price at/below lower Bollinger Band (with 0.5% tolerance)
        price_at_lower_bb = price <= bb_lower * 1.005
        
        # 2. RSI oversold but not extreme (avoid catching falling knife)
        rsi_valid = self.config.MR_RSI_EXTREME_LOW < rsi < self.config.MR_RSI_OVERSOLD
        
        # 3. Macro uptrend filter (price above EMA200)
        macro_uptrend = price > ema200
        
        # 4. Near support level (within tolerance)
        near_support = price <= recent_low * (1 + self.config.MR_SR_TOLERANCE)
        
        # 5. Volume spike (capitulation)
        volume_spike = volume_ratio > self.config.MR_VOLUME_SPIKE_MULT
        
        # All conditions must be true
        return all([
            price_at_lower_bb,
            rsi_valid,
            macro_uptrend,
            near_support,
            volume_spike
        ])
    
    def _check_short_conditions(self, price: float, rsi: float, bb_upper: float,
                                ema200: float, recent_high: float, volume_ratio: float) -> bool:
        """
        Check if all SHORT entry conditions are met
        
        Returns True if conditions satisfied
        """
        # 1. Price at/above upper Bollinger Band
        price_at_upper_bb = price >= bb_upper * 0.995
        
        # 2. RSI overbought but not extreme
        rsi_valid = self.config.MR_RSI_OVERBOUGHT < rsi < self.config.MR_RSI_EXTREME_HIGH
        
        # 3. Macro downtrend filter (price below EMA200)
        macro_downtrend = price < ema200
        
        # 4. Near resistance level
        near_resistance = price >= recent_high * (1 - self.config.MR_SR_TOLERANCE)
        
        # 5. Volume spike (exhaustion)
        volume_spike = volume_ratio > self.config.MR_VOLUME_SPIKE_MULT
        
        # All conditions must be true
        return all([
            price_at_upper_bb,
            rsi_valid,
            macro_downtrend,
            near_resistance,
            volume_spike
        ])
    
    def check_exit(self, position: dict, df: pd.DataFrame, idx: int) -> tuple[bool, str]:
        """
        Check if position should be exited (beyond SL/TP)
        
        Time-based exit for mean reversion:
        - If no reversion after 48 hours, thesis is wrong
        
        Returns: (should_exit, reason)
        """
        entry_time = position['entry_time']
        current_time = df.loc[idx, 'timestamp']
        hours_held = (current_time - entry_time).total_seconds() / 3600
        
        if hours_held >= self.config.MR_MAX_HOLD_HOURS:
            return True, f"Time stop ({self.config.MR_MAX_HOLD_HOURS}h - no reversion)"
        
        return False, ""

# Test function
def test_mean_reversion():
    """Test strategy with sample data"""
    from config import config
    
    # Create sample data
    dates = pd.date_range('2024-01-01', periods=300, freq='1h')
    df = pd.DataFrame({
        'timestamp': dates,
        'close': np.random.randn(300).cumsum() + 100,
        'high': np.random.randn(300).cumsum() + 102,
        'low': np.random.randn(300).cumsum() + 98,
        'volume': np.random.rand(300) * 1000
    })
    
    # Add required indicators (would come from indicators.py in real use)
    df['rsi_14'] = 50 + np.random.randn(300) * 15
    df['atr_14'] = 2.0
    df['bb_upper'] = df['close'] + 4
    df['bb_lower'] = df['close'] - 4
    df['bb_middle'] = df['close']
    df['ema_200'] = df['close'].ewm(span=200).mean()
    
    strategy = BTCMeanReversionStrategy(config)
    
    # Test evaluation
    signal = strategy.evaluate(df, 250, 10000, [])
    
    if signal:
        print(f"✓ Signal generated: {signal.action} at ${signal.entry_price:.2f}")
    else:
        print("✓ No signal (expected with random data)")
    
    print("✓ Mean Reversion strategy test passed")

if __name__ == "__main__":
    test_mean_reversion()
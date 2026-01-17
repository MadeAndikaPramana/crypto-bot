# ============================================
# BACKTEST CONFIGURATION
# ============================================
from dataclasses import dataclass
from datetime import datetime

@dataclass
class BacktestConfig:
    # Account Settings
    INITIAL_CAPITAL: float = 50.0  # Starting capital in USDT
    
    # Risk Management
    RISK_PER_TRADE: float = 0.01  # 1% risk per trade
    MAX_LEVERAGE_BTC: int = 3
    MAX_LEVERAGE_SOL: int = 5
    MAX_OPEN_POSITIONS: int = 2
    
    # BTC Strategy Parameters - OPTIMIZED
    BTC_SYMBOL: str = "BTC/USDT"
    BTC_TIMEFRAME: str = "4h"
    BTC_EMA_PERIOD: int = 200
    BTC_FUNDING_LONG_THRESHOLD: float = 0.000038   # 20th percentile (0.0038%)
    BTC_FUNDING_SHORT_THRESHOLD: float = 0.000100  # 80th percentile (0.0100%)
    BTC_ATR_PERIOD: int = 14
    BTC_ATR_SL_MULTIPLIER: float = 3.0   # Wider SL (Option A)
    BTC_ATR_TP_MULTIPLIER: float = 4.0   # Higher TP (Option A)
    BTC_MAX_HOLD_DAYS: int = 7  # Time stop
    BTC_OI_INCREASE_THRESHOLD: float = 0.02  # 2% increase in OI required
    
    # Volatility Filter (Option C) - Avoid choppy & extreme vol conditions
    BTC_MIN_ATR_RATIO: float = 0.8   # Min 80% of avg ATR (avoid dead markets)
    BTC_MAX_ATR_RATIO: float = 1.5   # Max 150% of avg ATR (avoid extreme vol)
    
    # SOL Strategy Parameters
    SOL_SYMBOL: str = "SOL/USDT"
    SOL_TIMEFRAME: str = "1h"
    SOL_BB_PERIOD: int = 20
    SOL_BB_STD: float = 2.0
    SOL_SQUEEZE_THRESHOLD: float = 0.03
    SOL_SQUEEZE_MIN_CANDLES: int = 12
    SOL_VOLUME_MULTIPLIER: float = 1.5
    SOL_ATR_PERIOD: int = 14
    SOL_ATR_SL_MULTIPLIER: float = 2.0
    SOL_ATR_TP1_MULTIPLIER: float = 2.0  # First target (50% position)
    SOL_ATR_TP2_MULTIPLIER: float = 4.0  # Second target (50% position)
    SOL_ADX_THRESHOLD: float = 20.0
    
    # Mean Reversion Strategy Parameters (H1 BTC)
    MR_SYMBOL: str = "BTC/USDT"
    MR_TIMEFRAME: str = "1h"
    MR_BB_PERIOD: int = 20
    MR_BB_STD: float = 2.0
    MR_RSI_PERIOD: int = 14
    MR_RSI_OVERSOLD: float = 45.0   # Long entry threshold
    MR_RSI_OVERBOUGHT: float = 55.0  # Short entry threshold
    MR_RSI_EXTREME_LOW: float = 25   # Don't catch falling knife
    MR_RSI_EXTREME_HIGH: float = 75  # Don't short parabolic moves
    MR_EMA_PERIOD: int = 200  # Trend filter
    MR_SR_LOOKBACK: int = 20  # Support/Resistance lookback
    MR_SR_TOLERANCE: float = 0.01  # 1% tolerance for S/R
    MR_VOLUME_MA_PERIOD: int = 20
    MR_VOLUME_SPIKE_MULT: float = 1.2  # Volume must be 1.2x average
    MR_ATR_PERIOD: int = 14
    MR_SL_ATR_MULT: float = 2.5
    MR_TP2_ATR_MULT: float = 3.0
    MR_MAX_HOLD_HOURS: int = 48  # Time stop (mean reversion should be quick)
    
    # Backtest Period
    START_DATE: str = "2024-01-01"  # Format: YYYY-MM-DD
    END_DATE: str = "2025-01-13"    # Format: YYYY-MM-DD
    
    # Fees
    MAKER_FEE: float = 0.0002  # 0.02% (Binance Futures maker fee)
    TAKER_FEE: float = 0.0004  # 0.04% (Binance Futures taker fee)
    
    # Slippage (realistic market impact)
    SLIPPAGE_PCT: float = 0.0005  # 0.05% average slippage

    # Optional: Proxy for network access
    PROXY: str = None  # e.g., 'http://user:pass@host:port'

config = BacktestConfig()
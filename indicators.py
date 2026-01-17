# ============================================
# TECHNICAL INDICATORS
# ============================================
import pandas as pd
import numpy as np
from typing import Tuple

def calc_ema(df: pd.DataFrame, period: int, column: str = 'close') -> pd.Series:
    """Calculate Exponential Moving Average"""
    return df[column].ewm(span=period, adjust=False).mean()

def calc_sma(df: pd.DataFrame, period: int, column: str = 'close') -> pd.Series:
    """Calculate Simple Moving Average"""
    return df[column].rolling(window=period).mean()

def calc_atr(df: pd.DataFrame, period: int) -> pd.Series:
    """
    Calculate Average True Range (ATR)
    ATR is used for volatility-based position sizing and stop placement
    """
    high = df['high']
    low = df['low']
    close = df['close']
    
    # True Range components
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    
    # True Range is the max of the three
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # ATR is the moving average of True Range
    atr = tr.rolling(window=period).mean()
    
    return atr

def calc_bollinger_bands(df: pd.DataFrame, period: int, std: float) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """
    Calculate Bollinger Bands
    Returns: (upper_band, middle_band, lower_band, width)
    
    Width is normalized by middle band for comparability across price levels
    """
    middle = df['close'].rolling(window=period).mean()
    std_dev = df['close'].rolling(window=period).std()
    
    upper = middle + (std_dev * std)
    lower = middle - (std_dev * std)
    
    # Normalized width (for comparing squeeze across different price levels)
    width = (upper - lower) / middle
    
    return upper, middle, lower, width

def calc_rsi(df: pd.DataFrame, period: int = 14, column: str = 'close') -> pd.Series:
    """
    Calculate Relative Strength Index (RSI)
    RSI oscillates between 0-100, typically overbought >70, oversold <30
    """
    delta = df[column].diff()
    
    # Separate gains and losses
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    # Relative Strength
    rs = gain / loss
    
    # RSI calculation
    rsi = 100 - (100 / (1 + rs))
    
    return rsi

def calc_volume_ma(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Calculate Volume Moving Average"""
    return df['volume'].rolling(window=period).mean()

def calc_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Average Directional Index (ADX) untuk filter kekuatan tren"""
    plus_dm = df['high'].diff()
    minus_dm = df['low'].diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm > 0] = 0
    
    tr = pd.concat([df['high'] - df['low'], 
                    abs(df['high'] - df['close'].shift(1)), 
                    abs(df['low'] - df['close'].shift(1))], axis=1).max(axis=1)
    
    atr = tr.rolling(window=period).mean()
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
    minus_di = 100 * (abs(minus_dm).rolling(window=period).mean() / atr)
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    return dx.rolling(window=period).mean()

def merge_funding_rate(ohlcv_df: pd.DataFrame, funding_df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge funding rate data with OHLCV data
    Uses forward fill to propagate funding rate until next update
    """
    # Ensure both have timestamp as index
    if 'timestamp' in ohlcv_df.columns:
        ohlcv_df = ohlcv_df.set_index('timestamp')
    if 'timestamp' in funding_df.columns:
        funding_df = funding_df.set_index('timestamp')
    
    # Merge and forward fill
    merged = ohlcv_df.join(funding_df, how='left')
    merged['funding_rate'] = merged['funding_rate'].fillna(method='ffill')
    
    return merged.reset_index()

def merge_open_interest(ohlcv_df: pd.DataFrame, oi_df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge Open Interest data with OHLCV data
    Uses forward fill for missing values
    """
    # Ensure both have timestamp as index
    if 'timestamp' in ohlcv_df.columns:
        ohlcv_df = ohlcv_df.set_index('timestamp')
    if 'timestamp' in oi_df.columns:
        oi_df = oi_df.set_index('timestamp')
    
    # Merge and forward fill
    merged = ohlcv_df.join(oi_df, how='left')
    merged['open_interest'] = merged['open_interest'].fillna(method='ffill')
    
    # Calculate OI change percentage
    merged['oi_change_pct'] = merged['open_interest'].pct_change()
    
    return merged.reset_index()

def add_all_indicators(df: pd.DataFrame, config) -> pd.DataFrame:
    """
    Add all required indicators to dataframe based on config
    This is a convenience function for backtesting
    """
    df = df.copy()
    
    # Common indicators
    df['atr_14'] = calc_atr(df, 14)
    df['rsi_14'] = calc_rsi(df, 14)
    df['volume_ma_20'] = calc_volume_ma(df, 20)
    
    # EMA for trend identification
    df['ema_200'] = calc_ema(df, 200)
    
    # Bollinger Bands
    upper, middle, lower, width = calc_bollinger_bands(df, 20, 2.0)
    df['bb_upper'] = upper
    df['bb_middle'] = middle
    df['bb_lower'] = lower
    df['bb_width'] = width

    df['adx_14'] = calc_adx(df, 14)
    
    return df

def check_rsi_momentum(df: pd.DataFrame, idx: int, direction: str = 'up') -> bool:
    """
    Check if RSI is rising/falling (momentum confirmation)
    """
    if idx < 2:
        return False
    
    rsi_current = df.loc[idx, 'rsi_14']
    rsi_prev = df.loc[idx - 1, 'rsi_14']
    
    if direction == 'up':
        return rsi_current > rsi_prev
    else:
        return rsi_current < rsi_prev


if __name__ == "__main__":
    # Test indicators
    print("Testing indicators...")
    
    # Create sample data
    dates = pd.date_range('2024-01-01', periods=200, freq='1h')
    sample_data = pd.DataFrame({
        'timestamp': dates,
        'open': np.random.randn(200).cumsum() + 100,
        'high': np.random.randn(200).cumsum() + 102,
        'low': np.random.randn(200).cumsum() + 98,
        'close': np.random.randn(200).cumsum() + 100,
        'volume': np.random.randint(1000, 10000, 200)
    })
    
    # Add indicators
    sample_data = add_all_indicators(sample_data, None)
    
    print("\nDataFrame with indicators:")
    print(sample_data[['timestamp', 'close', 'ema_200', 'rsi_14', 'atr_14', 'bb_width']].tail())
    
    print("\nIndicators calculated successfully!")

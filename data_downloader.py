# ============================================
# HISTORICAL DATA DOWNLOADER
# ============================================
import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
from pathlib import Path
import pickle

from config import config
import pickle
from pathlib import Path
import time
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import ccxt


class DataDownloader:
    def __init__(self, cache_dir: str = "data_cache"):
        try:
            self.exchange = ccxt.binance({
                'enableRateLimit': True,
                'options': {'defaultType': 'future'},
                'proxy': config.PROXY if hasattr(config, 'PROXY') and config.PROXY else None,
            })
            self.exchange.load_markets()
        except ccxt.errors.ExchangeError as e:
            print(f"Error loading markets from Binance: {e}")
            print("This might be due to a network issue or geographical restrictions.")
            print("If you are in a restricted region, you can try setting a proxy in your config.py file.")
            print("Example: PROXY = 'http://user:pass@host:port'")
            raise e

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
    
    def download_ohlcv(self, symbol: str, timeframe: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Download OHLCV data for given period
        Uses cache to avoid repeated API calls
        """
        cache_file = self.cache_dir / f"{symbol.replace('/', '_')}_{timeframe}_{start_date}_{end_date}.pkl"
        
        # Check cache
        if cache_file.exists():
            print(f"Loading {symbol} {timeframe} from cache...")
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
        
        print(f"Downloading {symbol} {timeframe} data...")
        
        # Convert dates to timestamps
        start_ts = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp() * 1000)
        end_ts = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp() * 1000)
        
        all_candles = []
        current_ts = start_ts
        
        # Download in chunks (max 1000 candles per request)
        while current_ts < end_ts:
            try:
                candles = self.exchange.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    since=current_ts,
                    limit=1000
                )
                
                if not candles:
                    break
                
                all_candles.extend(candles)
                current_ts = candles[-1][0] + 1
                
                print(f"  Downloaded {len(all_candles)} candles...", end='\r')
                time.sleep(self.exchange.rateLimit / 1000)
                
            except Exception as e:
                print(f"\nError downloading data: {e}")
                time.sleep(5)
                continue
        
        # Convert to DataFrame
        df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df[(df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)]
        
        print(f"\nDownloaded {len(df)} candles for {symbol} {timeframe}")
        
        # Cache the data
        with open(cache_file, 'wb') as f:
            pickle.dump(df, f)
        
        return df
    
    def download_funding_rate(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Download funding rate history
        Binance funding rate updates every 8 hours (00:00, 08:00, 16:00 UTC)
        """
        cache_file = self.cache_dir / f"{symbol.replace('/', '_')}_funding_{start_date}_{end_date}.pkl"
        
        if cache_file.exists():
            print(f"Loading {symbol} funding rates from cache...")
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
        
        print(f"Downloading {symbol} funding rate history...")
        
        start_ts = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp() * 1000)
        end_ts = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp() * 1000)
        
        all_rates = []
        current_ts = start_ts
        
        while current_ts < end_ts:
            try:
                # Binance-specific endpoint for funding rate history
                rates = self.exchange.fapiPublicGetFundingRate({
                    'symbol': symbol.replace('/', ''),
                    'startTime': current_ts,
                    'limit': 1000
                })
                
                if not rates:
                    break
                
                all_rates.extend(rates)
                current_ts = int(rates[-1]['fundingTime']) + 1
                
                print(f"  Downloaded {len(all_rates)} funding rates...", end='\r')
                time.sleep(self.exchange.rateLimit / 1000)
                
            except Exception as e:
                print(f"\nError downloading funding rates: {e}")
                time.sleep(5)
                continue
        
        # Convert to DataFrame
        df = pd.DataFrame(all_rates)
        df['fundingTime'] = pd.to_datetime(df['fundingTime'], unit='ms')
        df['fundingRate'] = df['fundingRate'].astype(float)
        df = df[['fundingTime', 'fundingRate']]
        df.columns = ['timestamp', 'funding_rate']
        
        print(f"\nDownloaded {len(df)} funding rate entries for {symbol}")
        
        with open(cache_file, 'wb') as f:
            pickle.dump(df, f)
        
        return df
    
    def download_open_interest(self, symbol: str, timeframe: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Download Open Interest history
        Note: OI data availability might be limited on free tier
        """
        cache_file = self.cache_dir / f"{symbol.replace('/', '_')}_oi_{timeframe}_{start_date}_{end_date}.pkl"
        
        if cache_file.exists():
            print(f"Loading {symbol} OI from cache...")
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
        
        print(f"Downloading {symbol} Open Interest history...")
        
        start_ts = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp() * 1000)
        end_ts = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp() * 1000)
        
        # Map timeframe to period
        period_map = {'5m': '5m', '15m': '15m', '30m': '30m', '1h': '1h', '2h': '2h', '4h': '4h', '1d': '1d'}
        period = period_map.get(timeframe, '4h')
        
        all_oi = []
        current_ts = start_ts
        
        while current_ts < end_ts:
            try:
                oi_data = self.exchange.fapiPublicGetOpenInterestHist({
                    'symbol': symbol.replace('/', ''),
                    'period': period,
                    'startTime': current_ts,
                    'limit': 500
                })
                
                if not oi_data:
                    break
                
                all_oi.extend(oi_data)
                current_ts = int(oi_data[-1]['timestamp']) + 1
                
                print(f"  Downloaded {len(all_oi)} OI datapoints...", end='\r')
                time.sleep(self.exchange.rateLimit / 1000)
                
            except Exception as e:
                print(f"\nWarning: Could not download OI data: {e}")
                # OI data might not be available, return empty DataFrame
                return pd.DataFrame(columns=['timestamp', 'open_interest'])
        
        # Convert to DataFrame
        df = pd.DataFrame(all_oi)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['sumOpenInterest'] = df['sumOpenInterest'].astype(float)
        df = df[['timestamp', 'sumOpenInterest']]
        df.columns = ['timestamp', 'open_interest']
        
        print(f"\nDownloaded {len(df)} OI entries for {symbol}")
        
        with open(cache_file, 'wb') as f:
            pickle.dump(df, f)
        
        return df


def prepare_backtest_data(symbol: str, timeframe: str, start_date: str, end_date: str, 
                          download_funding: bool = True, download_oi: bool = True):
    """
    Convenience function to download all required data for backtesting
    """
    downloader = DataDownloader()
    
    # Download OHLCV
    ohlcv_df = downloader.download_ohlcv(symbol, timeframe, start_date, end_date)
    
    result = {'ohlcv': ohlcv_df}
    
    # Download funding rate if requested
    if download_funding:
        funding_df = downloader.download_funding_rate(symbol, start_date, end_date)
        result['funding'] = funding_df
    
    # Download OI if requested
    if download_oi:
        oi_df = downloader.download_open_interest(symbol, timeframe, start_date, end_date)
        result['oi'] = oi_df
    
    return result


if __name__ == "__main__":
    # Test download
    print("Testing data download...")
    
    # Download BTC 4h data for last 3 months
    btc_data = prepare_backtest_data(
        symbol="BTC/USDT",
        timeframe="4h",
        start_date="2024-10-01",
        end_date="2025-01-13",
        download_funding=True,
        download_oi=True
    )
    
    print(f"\nBTC OHLCV shape: {btc_data['ohlcv'].shape}")
    print(f"BTC Funding shape: {btc_data['funding'].shape}")
    print(f"BTC OI shape: {btc_data['oi'].shape}")
    
    print("\nSample OHLCV:")
    print(btc_data['ohlcv'].head())
    
    print("\nSample Funding:")
    print(btc_data['funding'].head())

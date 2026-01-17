# run_sol_squeeze.py
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from config import config
from strategies.sol_squeeze import SOLSqueezeStrategy
from run_backtest import run_single_backtest

if __name__ == "__main__":
    run_single_backtest(
        symbol=config.SOL_SYMBOL,
        timeframe=config.SOL_TIMEFRAME,
        strategy_class=SOLSqueezeStrategy,
        strategy_name='SOL_Squeeze_Breakout'
    )

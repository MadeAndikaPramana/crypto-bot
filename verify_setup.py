#!/usr/bin/env python3
"""
Setup Verification Script
Run this to verify all components are working correctly
"""

import sys
from pathlib import Path

def check_files():
    """Check if all required files exist"""
    print("📁 Checking files...")
    
    required_files = [
        'config.py',
        'data_downloader.py',
        'indicators.py',
        'backtest_engine.py',
        'performance.py',
        'visualize.py',
        'run_backtest.py',
        'demo.py',
        'requirements.txt',
        'strategies/btc_funding.py',
        'strategies/sol_squeeze.py'
    ]
    
    missing = []
    for file in required_files:
        if not Path(file).exists():
            missing.append(file)
            print(f"  ❌ Missing: {file}")
        else:
            print(f"  ✓ Found: {file}")
    
    if missing:
        print(f"\n❌ {len(missing)} files missing!")
        return False
    
    print(f"\n✅ All {len(required_files)} files present!")
    return True

def check_imports():
    """Check if all modules can be imported"""
    print("\n📦 Checking imports...")
    
    tests = [
        ('config', 'from config import config'),
        ('indicators', 'from indicators import calc_ema'),
        ('strategies', 'from strategies.btc_funding import BTCFundingStrategy'),
        ('backtest_engine', 'from backtest_engine import BacktestEngine'),
        ('performance', 'from performance import PerformanceAnalyzer'),
        ('visualize', 'from visualize import BacktestVisualizer'),
    ]
    
    failed = []
    for name, code in tests:
        try:
            exec(code)
            print(f"  ✓ {name} OK")
        except Exception as e:
            print(f"  ❌ {name} FAILED: {e}")
            failed.append(name)
    
    if failed:
        print(f"\n❌ {len(failed)} imports failed!")
        return False
    
    print(f"\n✅ All imports successful!")
    return True

def check_dependencies():
    """Check if required packages are installed"""
    print("\n📚 Checking dependencies...")
    
    packages = [
        ('ccxt', 'ccxt'),
        ('pandas', 'pandas'),
        ('numpy', 'numpy'),
        ('matplotlib', 'matplotlib.pyplot'),
    ]
    
    missing = []
    for name, import_name in packages:
        try:
            __import__(import_name)
            print(f"  ✓ {name} installed")
        except ImportError:
            print(f"  ❌ {name} NOT installed")
            missing.append(name)
    
    if missing:
        print(f"\n❌ {len(missing)} packages missing!")
        print("\nInstall with: pip install -r requirements.txt")
        return False
    
    print(f"\n✅ All dependencies installed!")
    return True

def run_quick_test():
    """Run a quick functionality test"""
    print("\n🧪 Running quick test...")
    
    try:
        from config import config
        from indicators import calc_ema
        import pandas as pd
        import numpy as np
        
        # Create test data
        df = pd.DataFrame({
            'close': np.random.randn(100).cumsum() + 100
        })
        
        # Test indicator
        ema = calc_ema(df, 20)
        
        if len(ema) == len(df):
            print("  ✓ Indicator calculation works")
        else:
            print("  ❌ Indicator calculation failed")
            return False
        
        # Test config
        if config.INITIAL_CAPITAL > 0:
            print("  ✓ Config loaded correctly")
        else:
            print("  ❌ Config has invalid values")
            return False
        
        print("\n✅ Quick test passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Quick test failed: {e}")
        return False

def main():
    """Run all checks"""
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║                                                            ║
    ║         CRYPTO BOT BACKTEST - SETUP VERIFICATION          ║
    ║                                                            ║
    ╚════════════════════════════════════════════════════════════╝
    """)
    
    checks = [
        check_files,
        check_dependencies,
        check_imports,
        run_quick_test
    ]
    
    all_passed = True
    for check in checks:
        if not check():
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("🎉 ALL CHECKS PASSED! 🎉")
        print("\nYou're ready to run:")
        print("  python demo.py                        # Quick test")
        print("  python run_backtest.py --strategy all # Full backtest")
    else:
        print("❌ SOME CHECKS FAILED")
        print("\nPlease fix the issues above before proceeding.")
        print("\nCommon fixes:")
        print("  pip install -r requirements.txt  # Install dependencies")
        print("  ls -la                           # Check files are present")
    print("="*60 + "\n")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())

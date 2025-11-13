"""
Quick test to verify simulation setup is ready.
"""

def test_imports():
    """Test that all required imports are available."""
    print("Testing imports...")

    errors = []

    # Core dependencies
    try:
        import pandas
        print("  [OK] pandas")
    except ImportError as e:
        errors.append(("pandas", str(e)))
        print("  [FAIL] pandas - NOT FOUND")

    try:
        import numpy
        print("  [OK] numpy")
    except ImportError as e:
        errors.append(("numpy", str(e)))
        print("  [FAIL] numpy - NOT FOUND")

    try:
        import plotly
        print("  [OK] plotly")
    except ImportError as e:
        errors.append(("plotly", str(e)))
        print("  [FAIL] plotly - NOT FOUND")

    try:
        import streamlit
        print("  [OK] streamlit")
    except ImportError as e:
        errors.append(("streamlit", str(e)))
        print("  [FAIL] streamlit - NOT FOUND")

    # Project imports
    try:
        from gambler_ai.analysis.stock_scanner import StockScanner
        print("  [OK] gambler_ai.analysis.stock_scanner")
    except ImportError as e:
        errors.append(("stock_scanner", str(e)))
        print("  [FAIL] gambler_ai.analysis.stock_scanner - NOT FOUND")

    try:
        from gambler_ai.analysis.momentum_detector import MomentumDetector
        print("  [OK] gambler_ai.analysis.momentum_detector")
    except ImportError as e:
        errors.append(("momentum_detector", str(e)))
        print("  [FAIL] gambler_ai.analysis.momentum_detector - NOT FOUND")

    if errors:
        print("\n" + "="*80)
        print("[X] SETUP INCOMPLETE")
        print("="*80)
        print("\nMissing dependencies. Please install them:")
        print("\n  pip install -r requirements.txt\n")
        return False
    else:
        print("\n" + "="*80)
        print("[SUCCESS] ALL TESTS PASSED - Ready to run simulation!")
        print("="*80)
        print("\nNext steps:")
        print("  1. Run simulation: python scripts/run_simulation_race.py simulation")
        print("  2. View results:   python scripts/run_simulation_race.py ui")
        print()
        return True


if __name__ == "__main__":
    test_imports()

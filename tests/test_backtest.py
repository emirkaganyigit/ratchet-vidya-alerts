import pandas as pd

from src.analysis.backtest import backtest_next_open


def test_backtest_next_open_position_shift():
    # 5 bars, open increases
    idx = pd.date_range("2025-01-01", periods=5, freq="h", tz="UTC")
    candles = pd.DataFrame({"open": [100, 101, 102, 103, 104]}, index=idx)

    signals = pd.DataFrame(
        {
            "long_signal": [False, True, False, False, False],  # signal at t=1
            "short_signal": [False, False, False, False, False],
        },
        index=idx,
    )

    bt = backtest_next_open(candles, signals, fee_bps=0.0)

    # LONG signal at t=1 => position should be +1 starting t=2
    assert bt["position"].iloc[0] == 0.0
    assert bt["position"].iloc[1] == 0.0
    assert bt["position"].iloc[2] == 1.0


def test_backtest_applies_fee_on_change():
    idx = pd.date_range("2025-01-01", periods=4, freq="h", tz="UTC")
    candles = pd.DataFrame({"open": [100, 100, 100, 100]}, index=idx)

    signals = pd.DataFrame(
        {
            "long_signal": [False, True, False, False],  # enter at t=2 open
            "short_signal": [False, False, False, False],
        },
        index=idx,
    )

    bt = backtest_next_open(candles, signals, fee_bps=10.0)  # 10 bps = 0.1%
    # Position change occurs at t=2 open => cost should appear there
    assert bt["trade_cost"].iloc[2] > 0.0

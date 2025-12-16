import numpy as np
import pandas as pd

from src.indicators.ratchet_t import ratcheted_tracking_line


def test_long_regime_T_never_decreases():
    vma = pd.Series([1, 2, 3, 2.5, 2.0, 2.2, 2.1, 2.8, 2.6])
    out = ratcheted_tracking_line(vma, offset_pct=10.0, initial_dir="LONG")
    T = out["T"].dropna().values
    # check monotonic non-decreasing
    assert np.all(np.diff(T) >= -1e-12)


def test_short_regime_T_never_increases():
    vma = pd.Series([5, 4, 3, 3.5, 4.0, 3.8, 3.9, 3.0, 3.2])
    out = ratcheted_tracking_line(vma, offset_pct=10.0, initial_dir="SHORT")
    T = out["T"].dropna().values
    # check monotonic non-increasing
    assert np.all(np.diff(T) <= 1e-12)


def test_initialization_is_deterministic():
    vma = pd.Series([10.0] * 30)
    out1 = ratcheted_tracking_line(vma, offset_pct=1.0, initial_dir="LONG")["T"]
    out2 = ratcheted_tracking_line(vma, offset_pct=1.0, initial_dir="LONG")["T"]
    assert out1.equals(out2)

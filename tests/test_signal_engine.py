import numpy as np
import pandas as pd

from src.signals.vma_t_crossover import compute_t_and_signals_from_vma


def test_short_signal_reanchors_T_above_vma():
    # Construct VMA that rises then drops below a flat long-ratcheted T -> should trigger SHORT
    vma = pd.Series([100, 110, 120, 119, 118, 117, 116])
    out = compute_t_and_signals_from_vma(vma, offset_pct=1.0, initial_dir="LONG")

    # Find first short signal
    short_idx = out.index[out["short_signal"]].tolist()
    assert len(short_idx) >= 1

    i = short_idx[0]
    v = float(out.loc[i, "vma"])
    d = float(out.loc[i, "delta"])

    # After SHORT, dir must be SHORT and T must be vma + delta on that bar
    assert out.loc[i, "dir"] == "SHORT"
    assert np.isclose(float(out.loc[i, "T"]), v + d, atol=1e-12)


def test_long_signal_reanchors_T_below_vma():
    # Start SHORT, then make VMA drop and later rise above flat short-ratcheted T -> should trigger LONG
    vma = pd.Series([120, 110, 100, 101, 102, 103, 104, 105])
    out = compute_t_and_signals_from_vma(vma, offset_pct=1.0, initial_dir="SHORT")

    long_idx = out.index[out["long_signal"]].tolist()
    assert len(long_idx) >= 1

    i = long_idx[0]
    v = float(out.loc[i, "vma"])
    d = float(out.loc[i, "delta"])

    assert out.loc[i, "dir"] == "LONG"
    assert np.isclose(float(out.loc[i, "T"]), v - d, atol=1e-12)


def test_T_monotonic_within_regimes():
    # Check that within each contiguous dir segment:
    # LONG: T never decreases, SHORT: T never increases
    vma = pd.Series([100, 110, 120, 118, 116, 114, 113, 112, 113, 114, 115, 116])
    out = compute_t_and_signals_from_vma(vma, offset_pct=1.0, initial_dir="LONG")

    T = out["T"].values
    dirs = out["dir"].ffill().values

    # scan contiguous blocks
    start = 0
    for k in range(1, len(dirs) + 1):
        if k == len(dirs) or dirs[k] != dirs[start]:
            block_T = T[start:k]
            block_T = block_T[~np.isnan(block_T)]
            if len(block_T) > 1:
                diffs = np.diff(block_T)
                if dirs[start] == "LONG":
                    assert np.all(diffs >= -1e-12)
                else:
                    assert np.all(diffs <= 1e-12)
            start = k

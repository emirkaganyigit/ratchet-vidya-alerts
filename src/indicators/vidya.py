import numpy as np
import pandas as pd


def vidya(source: pd.Series, vma_length: int = 20, momentum_length: int = 9) -> pd.Series:
    """
    VMA implemented as VIDYA (CMO-based).

    source: price series (e.g., Close)
    vma_length: smoothing length
    momentum_length: CMO window length

    Output: VIDYA series aligned with source index.
    Deterministic initialization: first available VIDYA value equals source at that index.
    """

    if vma_length <= 0:
        raise ValueError("vma_length must be positive")
    if momentum_length <= 0:
        raise ValueError("momentum_length must be positive")

    # Compute price changes
    diff = source.diff()

    # Positive and negative changes
    up = diff.clip(lower=0.0)
    down = (-diff).clip(lower=0.0)

    # Rolling sums for CMO
    sum_up = up.rolling(momentum_length).sum()
    sum_down = down.rolling(momentum_length).sum()
    denom = sum_up + sum_down

    # CMO in [-100, 100], define 0 when denom is 0
    cmo = pd.Series(0.0, index=source.index, dtype="float64")
    mask = denom != 0
    cmo.loc[mask] = 100.0 * (sum_up.loc[mask] - sum_down.loc[mask]) / denom.loc[mask]

    # Adaptive alpha
    base_alpha = 2.0 / (vma_length + 1.0)
    alpha = base_alpha * (cmo.abs() / 100.0)

    out = pd.Series(np.nan, index=source.index, dtype="float64")

    # First index where alpha is valid (after momentum window)
    first_idx = alpha.first_valid_index()
    if first_idx is None:
        return out

    # Deterministic init: start VIDYA at the source value
    out.loc[first_idx] = float(source.loc[first_idx])
    prev = out.loc[first_idx]

    started = False
    for idx in source.index:
        if idx == first_idx:
            started = True
            continue
        if not started:
            continue

        a = float(alpha.loc[idx]) if pd.notna(alpha.loc[idx]) else 0.0
        s = float(source.loc[idx])
        prev = a * s + (1.0 - a) * prev
        out.loc[idx] = prev

    return out

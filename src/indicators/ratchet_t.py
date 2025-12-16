import numpy as np
import pandas as pd


def ratcheted_tracking_line(
    vma: pd.Series,
    offset_pct: float = 1.0,
    initial_dir: str = "LONG",
) -> pd.DataFrame:
    """
    Compute the single ratcheted tracking line T around VMA (VIDYA).

    Rules (customer spec):
      delta_t = VMA_t * offset_pct / 100

      If dir = LONG:
        candidate = VMA_t - delta_t
        T_t = max(T_{t-1}, candidate)   # never decreases

      If dir = SHORT:
        candidate = VMA_t + delta_t
        T_t = min(T_{t-1}, candidate)   # never increases

    Initialization:
      On first bar where VMA is available:
        dir = initial_dir (deterministic default LONG)
        T_0 = VMA_0 - delta_0 (if LONG) else VMA_0 + delta_0

    Returns DataFrame with columns:
      - T (tracking line)
      - dir (LONG/SHORT regime at each bar, based only on initialization here)
      - delta (offset per bar)
      - candidate (pre-ratchet candidate per bar)
    NOTE: dir flipping on crossover will be implemented in signal engine (next step).
    """
    if offset_pct <= 0:
        raise ValueError("offset_pct must be positive")

    init = initial_dir.upper()
    if init not in ("LONG", "SHORT"):
        raise ValueError("initial_dir must be 'LONG' or 'SHORT'")

    df = pd.DataFrame(index=vma.index)
    df["vma"] = vma.astype("float64")

    delta = df["vma"] * (offset_pct / 100.0)
    df["delta"] = delta

    # Prepare outputs
    T = pd.Series(np.nan, index=vma.index, dtype="float64")
    dir_series = pd.Series(pd.NA, index=vma.index, dtype="object")
    candidate_series = pd.Series(np.nan, index=vma.index, dtype="float64")

    first_idx = df["vma"].first_valid_index()
    if first_idx is None:
        df["T"] = T
        df["dir"] = dir_series
        df["candidate"] = candidate_series
        return df[["T", "dir", "delta", "candidate"]]

    # Initialize
    current_dir = init
    v0 = float(df.loc[first_idx, "vma"])
    d0 = float(df.loc[first_idx, "delta"])
    if current_dir == "LONG":
        T.loc[first_idx] = v0 - d0
        candidate_series.loc[first_idx] = v0 - d0
    else:
        T.loc[first_idx] = v0 + d0
        candidate_series.loc[first_idx] = v0 + d0
    dir_series.loc[first_idx] = current_dir

    prev_T = float(T.loc[first_idx])
    started = False

    for idx in df.index:
        if idx == first_idx:
            started = True
            continue
        if not started:
            continue

        v = float(df.loc[idx, "vma"])
        d = float(df.loc[idx, "delta"])

        if current_dir == "LONG":
            cand = v - d
            candidate_series.loc[idx] = cand
            prev_T = max(prev_T, cand)
        else:
            cand = v + d
            candidate_series.loc[idx] = cand
            prev_T = min(prev_T, cand)

        T.loc[idx] = prev_T
        dir_series.loc[idx] = current_dir

    out = pd.DataFrame({
        "T": T,
        "dir": dir_series,
        "delta": delta,
        "candidate": candidate_series
    }, index=vma.index)

    return out

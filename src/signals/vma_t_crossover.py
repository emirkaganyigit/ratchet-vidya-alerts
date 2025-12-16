import numpy as np
import pandas as pd


def compute_t_and_signals_from_vma(
    vma: pd.Series,
    offset_pct: float = 1.0,
    initial_dir: str = "LONG",
) -> pd.DataFrame:
    """
    Core engine (customer spec):
    - Input: VMA series (VIDYA)
    - Output: single T line + dir + LONG/SHORT signals
    - Signals ONLY from VMA–T crossover
    - T ratchets by dir, and re-anchors immediately on signal bar

    delta_t = VMA_t * offset_pct / 100

    Update (provisional):
      if dir=LONG:  candidate = VMA_t - delta;  T = max(prev_T, candidate)
      if dir=SHORT: candidate = VMA_t + delta;  T = min(prev_T, candidate)

    Signals (using prev values and provisional current values):
      LONG  if prev_vma <= prev_T and vma > T
      SHORT if prev_vma >= prev_T and vma < T

    On signal:
      set dir accordingly
      re-anchor immediately:
        LONG:  T = vma - delta
        SHORT: T = vma + delta
    """
    if offset_pct <= 0:
        raise ValueError("offset_pct must be positive")

    init = initial_dir.upper()
    if init not in ("LONG", "SHORT"):
        raise ValueError("initial_dir must be 'LONG' or 'SHORT'")

    idx = vma.index
    out = pd.DataFrame(index=idx)
    out["vma"] = vma.astype("float64")
    out["delta"] = out["vma"] * (offset_pct / 100.0)

    T = pd.Series(np.nan, index=idx, dtype="float64")
    dir_series = pd.Series(pd.NA, index=idx, dtype="object")
    long_sig = pd.Series(False, index=idx)
    short_sig = pd.Series(False, index=idx)

    first = out["vma"].first_valid_index()
    if first is None:
        out["T"] = T
        out["dir"] = dir_series
        out["long_signal"] = long_sig
        out["short_signal"] = short_sig
        return out[["vma", "T", "dir", "delta", "long_signal", "short_signal"]]

    # Initialize deterministically
    current_dir = init
    v0 = float(out.loc[first, "vma"])
    d0 = float(out.loc[first, "delta"])
    T0 = (v0 - d0) if current_dir == "LONG" else (v0 + d0)

    T.loc[first] = T0
    dir_series.loc[first] = current_dir

    prev_vma = v0
    prev_T = float(T0)

    started = False
    for t in idx:
        if t == first:
            started = True
            continue
        if not started:
            continue

        v = float(out.loc[t, "vma"])
        d = float(out.loc[t, "delta"])

        # Provisional ratchet update (based on current_dir)
        if current_dir == "LONG":
            provisional_T = max(prev_T, v - d)
        else:
            provisional_T = min(prev_T, v + d)

        # Signal detection uses prev_vma/prev_T and current v/provisional_T
        is_long = (prev_vma <= prev_T) and (v > provisional_T)
        is_short = (prev_vma >= prev_T) and (v < provisional_T)

        if is_long and not is_short:
            long_sig.loc[t] = True
            current_dir = "LONG"
            final_T = v - d  # re-anchor
        elif is_short and not is_long:
            short_sig.loc[t] = True
            current_dir = "SHORT"
            final_T = v + d  # re-anchor
        else:
            final_T = provisional_T

        T.loc[t] = final_T
        dir_series.loc[t] = current_dir

        prev_vma = v
        prev_T = float(final_T)

    out["T"] = T
    out["dir"] = dir_series
    out["long_signal"] = long_sig
    out["short_signal"] = short_sig
    return out[["vma", "T", "dir", "delta", "long_signal", "short_signal"]]

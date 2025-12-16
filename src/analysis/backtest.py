from __future__ import annotations

import pandas as pd
import numpy as np


def backtest_next_open(
    candles: pd.DataFrame,
    signals: pd.DataFrame,
    fee_bps: float = 0.0,
) -> pd.DataFrame:
    """
    Simple backtest using next-open execution.

    candles: DataFrame indexed by open_dt (UTC), must include column 'open'
    signals: output of compute_t_and_signals_from_vma indexed the same way, includes:
             'long_signal', 'short_signal'

    Execution model (close-confirmed -> next open):
      - If long_signal at t -> position becomes +1 starting at t+1 open
      - If short_signal at t -> position becomes -1 starting at t+1 open
      - Default position is 0 (flat) until first signal

    Returns DataFrame with:
      - open, open_ret
      - position (at each bar open)
      - strategy_ret
      - equity (starting at 1.0)
      - trade_cost
    """
    if "open" not in candles.columns:
        raise ValueError("candles must include 'open' column")
    if not candles.index.equals(signals.index):
        raise ValueError("candles and signals must have identical index")

    df = pd.DataFrame(index=candles.index)
    df["open"] = candles["open"].astype("float64")
    df["open_ret"] = df["open"].pct_change().fillna(0.0)

    # Position series: position held starting at each bar open
    pos = pd.Series(0.0, index=df.index)

    long_idx = signals.index[signals["long_signal"]].tolist()
    short_idx = signals.index[signals["short_signal"]].tolist()

    # Set target positions at next bar open
    for t in long_idx:
        loc = df.index.get_loc(t)
        if loc + 1 < len(df.index):
            pos.iloc[loc + 1] = 1.0
    for t in short_idx:
        loc = df.index.get_loc(t)
        if loc + 1 < len(df.index):
            pos.iloc[loc + 1] = -1.0

    # Forward-fill positions (hold until next signal changes it)
    pos = pos.replace(0.0, np.nan).ffill().fillna(0.0)
    df["position"] = pos

    # Transaction cost applied when position changes at a bar open
    fee_rate = fee_bps / 10_000.0
    pos_change = df["position"].diff().fillna(df["position"])
    trade_cost = pos_change.abs() * fee_rate  # flip +1 to -1 -> abs change = 2
    df["trade_cost"] = trade_cost

    # Strategy returns: earned by position at open[t-1] over open[t-1]->open[t]
    df["strategy_ret"] = df["position"].shift(1).fillna(0.0) * df["open_ret"] - df["trade_cost"]
    df["equity"] = (1.0 + df["strategy_ret"]).cumprod()

    return df


def summary_stats(bt: pd.DataFrame) -> dict:
    """
    Minimal stats from backtest output.
    """
    eq = bt["equity"]
    total_return = float(eq.iloc[-1] - 1.0)

    peak = eq.cummax()
    drawdown = (eq / peak) - 1.0
    max_dd = float(drawdown.min())

    # Trades proxy: count when position changes
    pos = bt["position"]
    changes = pos.diff().fillna(pos).ne(0)
    n_changes = int(changes.sum())

    return {
        "total_return": total_return,
        "max_drawdown": max_dd,
        "position_changes": n_changes,
    }

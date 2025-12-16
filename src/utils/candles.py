from __future__ import annotations

import time
import pandas as pd


def drop_unclosed_last_candle(
    df: pd.DataFrame,
    now_ms: int | None = None,
    safety_ms: int = 2000,
) -> pd.DataFrame:
    """
    Drops the last candle if it is not closed yet.

    - df must have a 'close_time' column in milliseconds (Binance kline closeTime).
    - now_ms: current time in ms (UTC). If None, uses system time.
    - safety_ms: small buffer to avoid edge timing issues.

    Returns a new DataFrame if a row is dropped; otherwise returns df unchanged.
    """
    if df is None or df.empty:
        return df

    if "close_time" not in df.columns:
        raise ValueError("Expected 'close_time' column in candles DataFrame.")

    if now_ms is None:
        now_ms = int(time.time() * 1000)
    else:
        now_ms = int(now_ms)

    last_close = int(df["close_time"].iloc[-1])

    # If last candle close time is in the future (or too close), it's not closed yet.
    if last_close > (now_ms - safety_ms):
        return df.iloc[:-1].copy()

    return df

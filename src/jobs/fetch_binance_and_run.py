from __future__ import annotations

import time
import pandas as pd

from src.ingestion.binance_spot import fetch_klines_range
from src.storage.sqlite_store import connect, init_schema, upsert_candles, read_candles, insert_signals
from src.indicators.vidya import vidya
from src.signals.vma_t_crossover import compute_t_and_signals_from_vma


def now_ms() -> int:
    return int(time.time() * 1000)


def run(
    symbol: str = "BTCUSDT",
    interval: str = "1h",
    lookback_days: int = 30,
    vma_length: int = 20,
    momentum_length: int = 9,
    offset_pct: float = 1.0,
    initial_dir: str = "LONG",
    db_path: str = "data.db",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    end = now_ms()
    start = end - int(lookback_days * 24 * 60 * 60 * 1000)

    candles_raw = fetch_klines_range(symbol, interval, start_time_ms=start, end_time_ms=end)

    con = connect(db_path)
    init_schema(con)
    upsert_candles(con, symbol, interval, candles_raw)

    candles = read_candles(con, symbol, interval, limit=5000)
    con.close()

    if candles.empty:
        return pd.DataFrame(), pd.DataFrame()

    source = candles["close"]  # Price used ONLY for VIDYA computation
    vma = vidya(source, vma_length=vma_length, momentum_length=momentum_length).rename("vma")
    out = compute_t_and_signals_from_vma(vma, offset_pct=offset_pct, initial_dir=initial_dir)

    return candles, out


def persist_signals(
    candles: pd.DataFrame,
    out: pd.DataFrame,
    symbol: str,
    interval: str,
    db_path: str = "data.db",
) -> int:
    """
    Persist ONLY signal bars into SQLite, return number of newly inserted signals.
    """
    if candles.empty or out.empty:
        return 0

    sig_mask = out["long_signal"] | out["short_signal"]
    if not sig_mask.any():
        return 0

    sig = pd.DataFrame(index=out.index[sig_mask]).copy()

    # open_time from candles (same index)
    sig["open_time"] = candles.loc[sig.index, "open_time"].astype("int64")

    sig["signal_type"] = ["LONG" if x else "SHORT" for x in out.loc[sig.index, "long_signal"].tolist()]
    sig["vma"] = out.loc[sig.index, "vma"].astype("float64")
    sig["t"] = out.loc[sig.index, "T"].astype("float64")
    sig["dir"] = out.loc[sig.index, "dir"].astype("object")

    con = connect(db_path)
    init_schema(con)
    inserted = insert_signals(con, symbol, interval, sig.reset_index(drop=True))
    con.close()
    return inserted


if __name__ == "__main__":
    candles, out = run()
    print(f"rows={len(out)} longs={int(out['long_signal'].sum())} shorts={int(out['short_signal'].sum())}")

from __future__ import annotations

import time
import pandas as pd

from src.ingestion.binance_spot import fetch_klines_range
from src.storage.sqlite_store import connect, init_schema, upsert_candles, read_candles
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
) -> pd.DataFrame:
    end = now_ms()
    start = end - int(lookback_days * 24 * 60 * 60 * 1000)

    candles = fetch_klines_range(symbol, interval, start_time_ms=start, end_time_ms=end)
    con = connect(db_path)
    init_schema(con)
    upsert_candles(con, symbol, interval, candles)

    df = read_candles(con, symbol, interval, limit=5000)
    con.close()

    if df.empty:
        return pd.DataFrame()

    source = df["close"]  # Price is used ONLY to compute VMA
    vma = vidya(source, vma_length=vma_length, momentum_length=momentum_length).rename("vma")
    out = compute_t_and_signals_from_vma(vma, offset_pct=offset_pct, initial_dir=initial_dir)
    return out


if __name__ == "__main__":
    out = run()
    n_long = int(out["long_signal"].sum()) if not out.empty else 0
    n_short = int(out["short_signal"].sum()) if not out.empty else 0
    print(f"Done. LONG signals: {n_long}, SHORT signals: {n_short}, rows: {len(out)}")

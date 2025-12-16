from __future__ import annotations

import os

from src.jobs.fetch_binance_and_run import run, persist_signals
from src.alerts.telegram import send_telegram_message


def main():
    symbol = os.getenv("SYMBOL", "BTCUSDT")
    interval = os.getenv("INTERVAL", "1h")
    lookback_days = int(os.getenv("LOOKBACK_DAYS", "30"))
    vma_length = int(os.getenv("VMA_LENGTH", "20"))
    momentum_length = int(os.getenv("MOMENTUM_LENGTH", "9"))
    offset_pct = float(os.getenv("OFFSET_PCT", "1.0"))
    initial_dir = os.getenv("INITIAL_DIR", "LONG")
    db_path = os.getenv("DB_PATH", "data.db")

    candles, out = run(
        symbol=symbol,
        interval=interval,
        lookback_days=lookback_days,
        vma_length=vma_length,
        momentum_length=momentum_length,
        offset_pct=offset_pct,
        initial_dir=initial_dir,
        db_path=db_path,
    )

    inserted = persist_signals(candles, out, symbol=symbol, interval=interval, db_path=db_path)

    # Eğer yeni sinyal eklendiyse telegram gönder (INSERT OR IGNORE sayesinde spam olmaz)
    if inserted > 0:
        # son sinyali bul
        last = out.loc[out["long_signal"] | out["short_signal"]].tail(1)
        t = last.index[0]
        is_long = bool(last["long_signal"].iloc[0])
        sig_type = "LONG" if is_long else "SHORT"
        vma = float(last["vma"].iloc[0])
        T = float(last["T"].iloc[0])
        msg = f"[{symbol} {interval}] New signal: {sig_type}\nTime(UTC): {t}\nVMA={vma:.6f}\nT={T:.6f}"
        send_telegram_message(msg)

    print(f"Done. New signals inserted: {inserted}")


if __name__ == "__main__":
    main()

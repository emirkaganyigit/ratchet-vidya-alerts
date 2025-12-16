from __future__ import annotations

import os

from dotenv import load_dotenv

from src.jobs.fetch_binance_and_run import run
from src.alerts.telegram import send_telegram_message
from src.storage.state_file import load_state, save_state, get_last_sent, set_last_sent


STATE_PATH_DEFAULT = "state/alerts_state.json"


def main():
    # Allow .env locally; harmless in GitHub Actions (env already present)
    load_dotenv()

    symbol = os.getenv("SYMBOL", "BTCUSDT")
    interval = os.getenv("INTERVAL", "1h")
    lookback_days = int(os.getenv("LOOKBACK_DAYS", "30"))
    vma_length = int(os.getenv("VMA_LENGTH", "20"))
    momentum_length = int(os.getenv("MOMENTUM_LENGTH", "9"))
    offset_pct = float(os.getenv("OFFSET_PCT", "1.0"))
    initial_dir = os.getenv("INITIAL_DIR", "LONG")
    state_path = os.getenv("STATE_PATH", STATE_PATH_DEFAULT)

    candles, out = run(
        symbol=symbol,
        interval=interval,
        lookback_days=lookback_days,
        vma_length=vma_length,
        momentum_length=momentum_length,
        offset_pct=offset_pct,
        initial_dir=initial_dir,
        db_path=os.getenv("DB_PATH", "data.db"),
    )

    if candles.empty or out.empty:
        print("No data / no output. Exiting.")
        return

    sig_mask = out["long_signal"] | out["short_signal"]
    if not sig_mask.any():
        print("No signals in the selected window. Exiting.")
        return

    last = out.loc[sig_mask].tail(1)
    t = last.index[0]
    is_long = bool(last["long_signal"].iloc[0])
    sig_type = "LONG" if is_long else "SHORT"

    # Use open_time as stable bar identifier
    open_time = int(candles.loc[t, "open_time"])
    vma = float(last["vma"].iloc[0])
    T = float(last["T"].iloc[0])
    dir_after = str(last["dir"].iloc[0])

    # Load persistent state
    state = load_state(state_path)
    prev = get_last_sent(state, symbol, interval)

    current_payload = {
        "open_time": open_time,
        "signal_type": sig_type,
    }

    if prev == current_payload:
        print(f"No new alert. Last sent already: {prev}")
        return

    # Send alert (optional—only if env vars exist)
    msg = (
        f"[{symbol.upper()} {interval}] New signal: {sig_type}\n"
        f"Time(UTC): {t}\n"
        f"open_time(ms): {open_time}\n"
        f"VMA={vma:.6f}\n"
        f"T={T:.6f}\n"
        f"dir(after)={dir_after}"
    )
    send_telegram_message(msg)

    # Update state
    set_last_sent(state, symbol, interval, current_payload)
    save_state(state_path, state)

    print(f"Alert sent and state updated: {current_payload}")


if __name__ == "__main__":
    main()

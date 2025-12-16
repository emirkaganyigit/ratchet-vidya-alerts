from __future__ import annotations

import os
from typing import List

from dotenv import load_dotenv

from src.alerts.telegram import send_telegram_message
from src.jobs.fetch_binance_and_run import run
from src.storage.state_file import get_last_sent, load_state, save_state, set_last_sent
from src.utils.logging import get_logger


STATE_PATH_DEFAULT = "state/alerts_state.json"
logger = get_logger("run_and_alert")


def _parse_symbols() -> List[str]:
    """
    SYMBOLS="BTCUSDT,ETHUSDT,SOLUSDT" gibi bir liste bekler.
    Eğer SYMBOLS yoksa, SYMBOL tek sembol olarak kullanılır.
    """
    symbols_env = (os.getenv("SYMBOLS") or "").strip()
    if symbols_env:
        parts = [s.strip().upper() for s in symbols_env.replace(" ", "").split(",") if s.strip()]
        # uniq + preserve order
        uniq = []
        for s in parts:
            if s not in uniq:
                uniq.append(s)
        return uniq

    return [(os.getenv("SYMBOL", "BTCUSDT") or "BTCUSDT").strip().upper()]


def main():
    load_dotenv()  # local dev için; Actions'ta da zararsız

    symbols = _parse_symbols()
    interval = os.getenv("INTERVAL", "1h")
    lookback_days = int(os.getenv("LOOKBACK_DAYS", "30"))
    vma_length = int(os.getenv("VMA_LENGTH", "20"))
    momentum_length = int(os.getenv("MOMENTUM_LENGTH", "9"))
    offset_pct = float(os.getenv("OFFSET_PCT", "1.0"))
    initial_dir = os.getenv("INITIAL_DIR", "LONG")
    state_path = os.getenv("STATE_PATH", STATE_PATH_DEFAULT)
    db_path = os.getenv("DB_PATH", "data.db")

    state = load_state(state_path)
    state_dirty = False
    any_alert_sent = False

    logger.info("Starting alert job for symbols=%s interval=%s", symbols, interval)

    for symbol in symbols:
        try:
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

            if candles.empty or out.empty:
                logger.info("[%s %s] No data / no output. Skipping.", symbol, interval)
                continue

            sig_mask = out["long_signal"] | out["short_signal"]
            if not sig_mask.any():
                logger.info("[%s %s] No signals in the selected window. Skipping.", symbol, interval)
                continue

            last = out.loc[sig_mask].tail(1)
            t = last.index[0]
            sig_type = "LONG" if bool(last["long_signal"].iloc[0]) else "SHORT"

            open_time = int(candles.loc[t, "open_time"])
            vma = float(last["vma"].iloc[0])
            T = float(last["T"].iloc[0])
            dir_after = str(last["dir"].iloc[0])

            prev = get_last_sent(state, symbol, interval)
            current_payload = {"open_time": open_time, "signal_type": sig_type}

            if prev == current_payload:
                logger.info("[%s %s] No new alert. Last sent already: %s", symbol, interval, prev)
                continue

            msg = (
                f"[{symbol} {interval}] New signal: {sig_type}\n"
                f"Time(UTC): {t}\n"
                f"open_time(ms): {open_time}\n"
                f"VMA={vma:.6f}\n"
                f"T={T:.6f}\n"
                f"dir(after)={dir_after}"
            )

            send_telegram_message(msg)

            set_last_sent(state, symbol, interval, current_payload)
            state_dirty = True
            any_alert_sent = True

            logger.info("[%s %s] Alert sent and state updated: %s", symbol, interval, current_payload)

        except Exception as e:
            # Bir sembolde hata olursa diğerlerini etkilemesin
            logger.exception("[%s %s] Error while processing symbol: %s", symbol, interval, e)
            continue

    if state_dirty:
        save_state(state_path, state)
        logger.info("State saved to %s", state_path)

    if not any_alert_sent:
        logger.info("No alerts sent in this run.")


if __name__ == "__main__":
    main()

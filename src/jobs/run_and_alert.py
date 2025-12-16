from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Dict, List, Tuple

from dotenv import load_dotenv

from src.alerts.telegram import send_telegram_message
from src.jobs.fetch_binance_and_run import run
from src.storage.state_file import get_last_sent, load_state, save_state, set_last_sent
from src.utils.logging import get_logger

try:
    from zoneinfo import ZoneInfo  # py>=3.9
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore


STATE_PATH_DEFAULT = "state/alerts_state.json"
logger = get_logger("run_and_alert")


def _parse_symbols() -> List[str]:
    """
    SYMBOLS="BTCUSDT,ETHUSDT,SOLUSDT" gibi bir liste bekler.
    Eğer SYMBOLS yoksa, SYMBOL tek sembol olarak kullanılır.
    """
    symbols_env = (os.getenv("SYMBOLS") or "").strip()
    if symbols_env:
        parts = [s.strip().upper() for s in symbols_env.split(",") if s.strip()]
        uniq: List[str] = []
        for s in parts:
            if s not in uniq:
                uniq.append(s)
        return uniq

    return [(os.getenv("SYMBOL", "BTCUSDT") or "BTCUSDT").strip().upper()]


def _truthy(s: str | None, default: bool = False) -> bool:
    if s is None:
        return default
    return s.strip().lower() in {"1", "true", "yes", "y", "on"}


def _format_times(open_time_ms: int, local_tz: str = "Europe/Istanbul") -> Tuple[str, str]:
    dt_utc = datetime.fromtimestamp(open_time_ms / 1000, tz=timezone.utc)
    utc_str = dt_utc.strftime("%Y-%m-%d %H:%M:%S UTC")

    if ZoneInfo is None:
        return utc_str, utc_str

    try:
        dt_local = dt_utc.astimezone(ZoneInfo(local_tz))
        local_str = dt_local.strftime(f"%Y-%m-%d %H:%M:%S {local_tz}")
        return utc_str, local_str
    except Exception:
        return utc_str, utc_str


def _tradingview_link(symbol: str) -> str:
    """
    TradingView sembol formatı genelde: EXCHANGE:SYMBOL
    Varsayılan EXCHANGE=BINANCE (env: TV_EXCHANGE ile değiştirilebilir)
    """
    exch = (os.getenv("TV_EXCHANGE", "BINANCE") or "BINANCE").strip().upper()
    return f"https://www.tradingview.com/chart/?symbol={exch}:{symbol}"


def _build_alert_message(
    symbol: str,
    interval: str,
    sig_type: str,
    open_time_ms: int,
    vma: float,
    T: float,
    dir_after: str,
    vma_length: int,
    momentum_length: int,
    offset_pct: float,
    initial_dir: str,
) -> str:
    utc_str, local_str = _format_times(open_time_ms, local_tz=os.getenv("LOCAL_TZ", "Europe/Istanbul"))

    return (
        f"ALERT — {symbol} {interval} — {sig_type}\n"
        f"Time: {utc_str} | {local_str}\n"
        f"open_time(ms): {open_time_ms}\n"
        f"VMA={vma:.6f} | T={T:.6f} | dir(after)={dir_after}\n"
        f"Params: vma_length={vma_length}, momentum_length={momentum_length}, offset_pct={offset_pct}, initial_dir={initial_dir}\n"
        f"Chart: {_tradingview_link(symbol)}"
    )


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

    # Batching (tek mesajda birden çok alert)
    batch_alerts = _truthy(os.getenv("BATCH_ALERTS"), default=True)
    max_alerts_per_run = int(os.getenv("MAX_ALERTS_PER_RUN", "20"))

    state: Dict = load_state(state_path)

    logger.info("Starting alert job for symbols=%s interval=%s batch=%s", symbols, interval, batch_alerts)

    pending_messages: List[str] = []
    pending_state_updates: List[Tuple[str, str, Dict]] = []  # (symbol, interval, payload)
    alerts_found = 0

    for symbol in symbols:
        if alerts_found >= max_alerts_per_run:
            logger.warning("MAX_ALERTS_PER_RUN reached (%s). Stopping early.", max_alerts_per_run)
            break

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

            # bar kimliği olarak open_time(ms)
            open_time = int(candles.loc[t, "open_time"])
            vma = float(last["vma"].iloc[0])
            T = float(last["T"].iloc[0])
            dir_after = str(last["dir"].iloc[0])

            prev = get_last_sent(state, symbol, interval)
            current_payload = {"open_time": open_time, "signal_type": sig_type}

            if prev == current_payload:
                logger.info("[%s %s] No new alert. Last sent already: %s", symbol, interval, prev)
                continue

            msg = _build_alert_message(
                symbol=symbol,
                interval=interval,
                sig_type=sig_type,
                open_time_ms=open_time,
                vma=vma,
                T=T,
                dir_after=dir_after,
                vma_length=vma_length,
                momentum_length=momentum_length,
                offset_pct=offset_pct,
                initial_dir=initial_dir,
            )

            pending_messages.append(msg)
            pending_state_updates.append((symbol, interval, current_payload))
            alerts_found += 1

            logger.info("[%s %s] New alert queued: %s", symbol, interval, current_payload)

        except Exception as e:
            # Bir sembolde hata olursa diğerlerini etkilemesin
            logger.exception("[%s %s] Error while processing symbol: %s", symbol, interval, e)
            continue

    if not pending_messages:
        logger.info("No alerts sent in this run.")
        return

    # Gönderim: batch veya tek tek
    if batch_alerts:
        combined = "\n\n" + ("-" * 30) + "\n\n"
        final_msg = combined.join(pending_messages)
        send_telegram_message(final_msg)
        logger.info("Batch alert sent (%d alerts).", len(pending_messages))

        # Başarılı gönderimden sonra state güncelle
        for sym, itv, payload in pending_state_updates:
            set_last_sent(state, sym, itv, payload)

        save_state(state_path, state)
        logger.info("State saved to %s", state_path)

    else:
        # Tek tek gönder
        any_state_dirty = False
        for (sym, itv, payload), msg in zip(pending_state_updates, pending_messages):
            send_telegram_message(msg)
            set_last_sent(state, sym, itv, payload)
            any_state_dirty = True
            logger.info("[%s %s] Alert sent and state updated: %s", sym, itv, payload)

        if any_state_dirty:
            save_state(state_path, state)
            logger.info("State saved to %s", state_path)


if __name__ == "__main__":
    main()

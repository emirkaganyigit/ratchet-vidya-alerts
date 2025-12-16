from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Optional

import pandas as pd
import requests

from src.utils.logging import get_logger

logger = get_logger("binance_spot")

BINANCE_MAIN_API = "https://api.binance.com"
BINANCE_MARKET_DATA_API = "https://data-api.binance.vision"  # Actions için daha stabil


def get_base_url() -> str:
    """
    Env override:
      BINANCE_BASE_URL=https://data-api.binance.vision (recommended)
      BINANCE_BASE_URL=https://api.binance.com         (optional local)

    Default: market-data endpoint
    """
    return (os.getenv("BINANCE_BASE_URL", BINANCE_MARKET_DATA_API) or BINANCE_MARKET_DATA_API).strip()


@dataclass(frozen=True)
class KlineRequest:
    symbol: str
    interval: str
    start_time_ms: Optional[int] = None
    end_time_ms: Optional[int] = None
    limit: int = 1000


def _parse_klines(raw: list[list]) -> pd.DataFrame:
    if not raw:
        return pd.DataFrame(
            columns=["open_time", "open", "high", "low", "close", "volume", "close_time"]
        )

    df = pd.DataFrame(
        raw,
        columns=[
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_asset_volume",
            "num_trades",
            "taker_buy_base_volume",
            "taker_buy_quote_volume",
            "ignore",
        ],
    )

    df = df[["open_time", "open", "high", "low", "close", "volume", "close_time"]]

    df["open_time"] = df["open_time"].astype("int64")
    df["close_time"] = df["close_time"].astype("int64")
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = df[c].astype("float64")

    df["open_dt"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df = df.set_index("open_dt").sort_index()
    return df


def fetch_klines(req: KlineRequest, session: Optional[requests.Session] = None) -> pd.DataFrame:
    """
    Fetch one page of klines (<=1000) and return as DataFrame.
    Retries once with market-data endpoint if a 451 is returned.
    """
    s = session or requests.Session()

    base_url = get_base_url().rstrip("/")
    url = f"{base_url}/api/v3/klines"

    params = {
        "symbol": req.symbol.upper(),
        "interval": req.interval,
        "limit": int(req.limit),
    }
    if req.start_time_ms is not None:
        params["startTime"] = int(req.start_time_ms)
    if req.end_time_ms is not None:
        params["endTime"] = int(req.end_time_ms)

    logger.debug("GET %s params=%s", url, params)
    r = s.get(url, params=params, timeout=20)

    # Eğer biri yanlışlıkla BINANCE_BASE_URL=api.binance.com verdiyse bile,
    # 451 gördüğümüzde market-data endpoint'e 1 kez fallback yap.
    if r.status_code == 451 and base_url != BINANCE_MARKET_DATA_API.rstrip("/"):
        fallback_url = f"{BINANCE_MARKET_DATA_API}/api/v3/klines"
        logger.warning("451 from %s. Retrying with %s", base_url, BINANCE_MARKET_DATA_API)
        r = s.get(fallback_url, params=params, timeout=20)

    r.raise_for_status()
    raw = r.json()
    return _parse_klines(raw)


def fetch_klines_range(
    symbol: str,
    interval: str,
    start_time_ms: int,
    end_time_ms: Optional[int] = None,
    limit: int = 1000,
    polite_sleep_s: float = 0.2,
) -> pd.DataFrame:
    """
    Fetch klines by paginating with startTime until endTime (or until no data).
    Returns DataFrame indexed by open_dt (UTC).
    """
    sess = requests.Session()
    all_parts: list[pd.DataFrame] = []

    cur = int(start_time_ms)
    end = int(end_time_ms) if end_time_ms is not None else None

    while True:
        df = fetch_klines(KlineRequest(symbol, interval, cur, end, limit=limit), session=sess)

        if df.empty:
            break

        all_parts.append(df)

        last_open_time = int(df["open_time"].iloc[-1])
        next_cur = last_open_time + 1

        if next_cur == cur:
            break

        cur = next_cur

        if end is not None and last_open_time >= end:
            break

        if len(df) < limit:
            break

        time.sleep(polite_sleep_s)

    if not all_parts:
        return _parse_klines([])

    out = pd.concat(all_parts, axis=0)
    out = out[~out["open_time"].duplicated()].sort_index()
    return out

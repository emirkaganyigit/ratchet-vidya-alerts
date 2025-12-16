from __future__ import annotations

import sqlite3
from pathlib import Path
import pandas as pd


def connect(db_path: str = "data.db") -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA synchronous=NORMAL;")
    return con


def init_schema(con: sqlite3.Connection) -> None:
    # OHLCV
    con.execute("""
    CREATE TABLE IF NOT EXISTS candles (
        symbol TEXT NOT NULL,
        interval TEXT NOT NULL,
        open_time INTEGER NOT NULL,
        open REAL NOT NULL,
        high REAL NOT NULL,
        low REAL NOT NULL,
        close REAL NOT NULL,
        volume REAL NOT NULL,
        close_time INTEGER NOT NULL,
        PRIMARY KEY (symbol, interval, open_time)
    );
    """)

    # Signals (dedup by bar)
    con.execute("""
    CREATE TABLE IF NOT EXISTS signals (
        symbol TEXT NOT NULL,
        interval TEXT NOT NULL,
        open_time INTEGER NOT NULL,
        signal_type TEXT NOT NULL,   -- LONG or SHORT
        vma REAL NOT NULL,
        t REAL NOT NULL,
        dir TEXT NOT NULL,           -- LONG or SHORT (regime after signal)
        PRIMARY KEY (symbol, interval, open_time)
    );
    """)
    con.commit()


def upsert_candles(con: sqlite3.Connection, symbol: str, interval: str, df: pd.DataFrame) -> int:
    if df.empty:
        return 0

    rows = []
    for _, r in df.iterrows():
        rows.append((
            symbol.upper(), interval,
            int(r["open_time"]),
            float(r["open"]), float(r["high"]), float(r["low"]),
            float(r["close"]), float(r["volume"]),
            int(r["close_time"])
        ))

    cur = con.cursor()
    cur.executemany("""
    INSERT OR REPLACE INTO candles
    (symbol, interval, open_time, open, high, low, close, volume, close_time)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, rows)
    con.commit()
    return cur.rowcount


def read_candles(con: sqlite3.Connection, symbol: str, interval: str, limit: int = 2000) -> pd.DataFrame:
    q = """
    SELECT open_time, open, high, low, close, volume, close_time
    FROM candles
    WHERE symbol = ? AND interval = ?
    ORDER BY open_time ASC
    LIMIT ?;
    """
    df = pd.read_sql_query(q, con, params=(symbol.upper(), interval, int(limit)))
    if df.empty:
        return df

    df["open_time"] = df["open_time"].astype("int64")
    df["close_time"] = df["close_time"].astype("int64")
    df["open_dt"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df = df.set_index("open_dt").sort_index()
    return df


def insert_signals(con: sqlite3.Connection, symbol: str, interval: str, sig_df: pd.DataFrame) -> int:
    """
    Insert only NEW signals (INSERT OR IGNORE). Returns number of inserted signals.
    sig_df columns required: open_time, signal_type, vma, t, dir
    """
    if sig_df.empty:
        return 0

    rows = []
    for _, r in sig_df.iterrows():
        rows.append((
            symbol.upper(),
            interval,
            int(r["open_time"]),
            str(r["signal_type"]),
            float(r["vma"]),
            float(r["t"]),
            str(r["dir"]),
        ))

    cur = con.cursor()
    cur.executemany("""
    INSERT OR IGNORE INTO signals
    (symbol, interval, open_time, signal_type, vma, t, dir)
    VALUES (?, ?, ?, ?, ?, ?, ?);
    """, rows)
    con.commit()
    return cur.rowcount


def read_latest_signal(con: sqlite3.Connection, symbol: str, interval: str) -> pd.DataFrame:
    q = """
    SELECT symbol, interval, open_time, signal_type, vma, t, dir
    FROM signals
    WHERE symbol = ? AND interval = ?
    ORDER BY open_time DESC
    LIMIT 1;
    """
    df = pd.read_sql_query(q, con, params=(symbol.upper(), interval))
    return df

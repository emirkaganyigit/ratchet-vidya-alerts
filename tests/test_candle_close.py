import pandas as pd
from src.utils.candles import drop_unclosed_last_candle


def test_drop_unclosed_last_candle_drops_when_not_closed():
    # now_ms = 10000, last close_time = 12000 -> not closed
    df = pd.DataFrame(
        {
            "close_time": [8000, 12000],
            "open_time": [0, 6000],
            "close": [1.0, 2.0],
        }
    )
    out = drop_unclosed_last_candle(df, now_ms=10000, safety_ms=0)
    assert len(out) == 1
    assert int(out["close_time"].iloc[-1]) == 8000


def test_drop_unclosed_last_candle_keeps_when_closed():
    # now_ms = 10000, last close_time = 9000 -> closed
    df = pd.DataFrame(
        {
            "close_time": [8000, 9000],
            "open_time": [0, 6000],
            "close": [1.0, 2.0],
        }
    )
    out = drop_unclosed_last_candle(df, now_ms=10000, safety_ms=0)
    assert len(out) == 2

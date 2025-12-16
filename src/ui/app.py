import numpy as np
import streamlit as st
import plotly.graph_objects as go

from src.jobs.fetch_binance_and_run import run
from src.analysis.backtest import backtest_next_open, summary_stats


st.set_page_config(page_title="ratchet-vidya-alerts", layout="wide")
st.title("ratchet-vidya-alerts — Real Market Data (Binance)")

col1, col2, col3 = st.columns(3)
with col1:
    symbol = st.text_input("symbol (Binance)", value="BTCUSDT")
    interval = st.selectbox("interval", ["1m", "5m", "15m", "1h", "4h", "1d"], index=3)
with col2:
    lookback_days = st.slider("lookback_days", 1, 180, 30)
    offset_pct = st.slider("offset_pct (%)", 0.1, 10.0, 1.0)
with col3:
    vma_length = st.slider("vma_length", 5, 80, 20)
    momentum_length = st.slider("momentum_length", 2, 40, 9)
    initial_dir = st.selectbox("initial_dir", ["LONG", "SHORT"], index=0)

fee_bps = st.slider("fee_bps (transaction cost)", 0.0, 50.0, 10.0)

if st.button("Fetch & Compute (Binance)"):
    with st.spinner("Fetching OHLCV and computing signals..."):
        candles, out = run(
            symbol=symbol,
            interval=interval,
            lookback_days=lookback_days,
            vma_length=vma_length,
            momentum_length=momentum_length,
            offset_pct=offset_pct,
            initial_dir=initial_dir,
        )

    if out.empty or candles.empty:
        st.warning("No data returned.")
        st.stop()

    # ---------- Indicator Plot (exactly two lines: VMA and T) ----------
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=out.index, y=out["vma"],
        mode="lines",
        name="VMA (VIDYA)"
    ))
    fig.add_trace(go.Scatter(
        x=out.index, y=out["T"],
        mode="lines",
        name="T (ratcheted)"
    ))

    # Signal markers (not lines)
    long_mask = out["long_signal"]
    short_mask = out["short_signal"]

    fig.add_trace(go.Scatter(
        x=out.index[long_mask],
        y=out.loc[long_mask, "vma"],
        mode="markers",
        name="LONG signal"
    ))
    fig.add_trace(go.Scatter(
        x=out.index[short_mask],
        y=out.loc[short_mask, "vma"],
        mode="markers",
        name="SHORT signal"
    ))

    fig.update_layout(height=520, margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, use_container_width=True)

    # ---------- Signals Table ----------
    st.subheader("Last signals")
    sig_mask = long_mask | short_mask
    signals = out.loc[sig_mask, ["vma", "T", "dir"]].copy()
    signals["type"] = np.where(out.loc[sig_mask, "long_signal"], "LONG", "SHORT")
    st.dataframe(signals.tail(30), use_container_width=True)

    # ---------- Backtest (analysis) ----------
    bt = backtest_next_open(candles, out, fee_bps=fee_bps)
    stats = summary_stats(bt)

    st.subheader("Backtest Summary (next-open)")
    st.write(stats)

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=bt.index, y=bt["equity"],
        mode="lines",
        name="Equity"
    ))
    fig2.update_layout(height=300, margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig2, use_container_width=True)

    st.caption("Signals use only VMA–T crossover. Price is used only to compute VIDYA (VMA).")

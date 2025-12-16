import streamlit as st
import plotly.graph_objects as go

from src.jobs.fetch_binance_and_run import run


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

if st.button("Fetch & Compute (Binance)"):
    with st.spinner("Fetching OHLCV and computing signals..."):
        out = run(
            symbol=symbol,
            interval=interval,
            lookback_days=lookback_days,
            vma_length=vma_length,
            momentum_length=momentum_length,
            offset_pct=offset_pct,
            initial_dir=initial_dir,
        )

    if out.empty:
        st.warning("No data returned.")
        st.stop()

    # Plot exactly TWO LINES: VMA and T (+ markers)
    fig = go.Figure()
    fig.add_trace(go.Scatter(y=out["vma"], mode="lines", name="VMA (VIDYA)"))
    fig.add_trace(go.Scatter(y=out["T"], mode="lines", name="T (ratcheted)"))

    long_y = out["vma"].where(out["long_signal"])
    short_y = out["vma"].where(out["short_signal"])

    fig.add_trace(go.Scatter(y=long_y, mode="markers", name="LONG signal"))
    fig.add_trace(go.Scatter(y=short_y, mode="markers", name="SHORT signal"))

    fig.update_layout(height=520, margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Last signals")
    signals = out.loc[out["long_signal"] | out["short_signal"], ["vma", "T", "dir"]].copy()
    signals["type"] = ["LONG" if x else "SHORT" for x in out.loc[out["long_signal"] | out["short_signal"], "long_signal"].tolist()]
    st.dataframe(signals.tail(30), use_container_width=True)

    st.caption("Signals use only VMA–T crossover. Price is used only to compute VIDYA (VMA).")

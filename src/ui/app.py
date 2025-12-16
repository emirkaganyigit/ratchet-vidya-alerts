import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from src.indicators.vidya import vidya
from src.signals.vma_t_crossover import compute_t_and_signals_from_vma


st.set_page_config(page_title="ratchet-vidya-alerts", layout="wide")
st.title("ratchet-vidya-alerts — VMA (VIDYA) + Ratcheted T + Crossover Signals")

# Parameters
vma_length = st.slider("vma_length (VIDYA length)", 5, 80, 20)
momentum_length = st.slider("momentum_length (CMO window)", 2, 40, 9)
offset_pct = st.slider("offset_pct (%)", 0.1, 10.0, 1.0)
initial_dir = st.selectbox("initial_dir", ["LONG", "SHORT"])
seed = st.number_input("synthetic seed (for reproducibility)", value=42, step=1)

# Synthetic source (price) only for computing VIDYA
rng = np.random.default_rng(int(seed))
n = 350
x = np.arange(n)
source = 100 + 0.05 * x + rng.normal(0, 0.8, size=n)
source = pd.Series(source, name="source")

vma = vidya(source, vma_length=vma_length, momentum_length=momentum_length).rename("vma")
out = compute_t_and_signals_from_vma(vma, offset_pct=offset_pct, initial_dir=initial_dir)

# Build plot: exactly TWO LINES (VMA and T), plus marker points for signals
fig = go.Figure()

fig.add_trace(go.Scatter(
    y=out["vma"],
    mode="lines",
    name="VMA (VIDYA)"
))
fig.add_trace(go.Scatter(
    y=out["T"],
    mode="lines",
    name="T (ratcheted)"
))

# Signal markers (not lines)
long_y = out["vma"].where(out["long_signal"])
short_y = out["vma"].where(out["short_signal"])

fig.add_trace(go.Scatter(
    y=long_y,
    mode="markers",
    name="LONG signal"
))
fig.add_trace(go.Scatter(
    y=short_y,
    mode="markers",
    name="SHORT signal"
))

fig.update_layout(
    height=520,
    legend_title_text="Series",
    margin=dict(l=10, r=10, t=40, b=10)
)

st.plotly_chart(fig, use_container_width=True)

st.subheader("Signals (table)")
signals = out.loc[out["long_signal"] | out["short_signal"], ["vma", "T", "dir"]].copy()
signals["type"] = np.where(out["long_signal"], "LONG", np.where(out["short_signal"], "SHORT", ""))
st.dataframe(signals.tail(20), use_container_width=True)

st.caption("Signals are generated only from VMA–T crossover. Source is used only to compute VMA (VIDYA).")

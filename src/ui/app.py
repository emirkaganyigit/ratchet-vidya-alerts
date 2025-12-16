import numpy as np
import pandas as pd
import streamlit as st

from src.indicators.vidya import vidya
from src.indicators.ratchet_t import ratcheted_tracking_line

st.set_page_config(page_title="ratchet-vidya-alerts", layout="wide")
st.title("ratchet-vidya-alerts — VIDYA + Ratcheted T (Demo)")

vma_length = st.slider("vma_length (VIDYA length)", 5, 80, 20)
momentum_length = st.slider("momentum_length (CMO window)", 2, 40, 9)
offset_pct = st.slider("offset_pct (%)", 0.1, 10.0, 1.0)
initial_dir = st.selectbox("initial_dir", ["LONG", "SHORT"])

# Synthetic series for validation
n = 300
x = np.arange(n)
price = 100 + 0.05 * x + np.random.normal(0, 0.8, size=n)
s = pd.Series(price, name="price")

v = vidya(s, vma_length=vma_length, momentum_length=momentum_length).rename("vidya")
t_df = ratcheted_tracking_line(v, offset_pct=offset_pct, initial_dir=initial_dir)
t = t_df["T"].rename("T")

df = pd.concat([s, v, t], axis=1)
st.line_chart(df)

st.caption("This demo uses synthetic data. Next step: dir flips + crossover signals based only on VIDYA and T.")

# Ratchet VIDYA Alerts

A simple, production-oriented alerting service that generates **LONG/SHORT** signals **only** from the crossover between:
- **VMA / VIDYA** (Variable Moving Average) line, and
- A **ratcheted tracking line (T)** that follows VMA with a percent offset and only ratchets in the regime direction.

Notifications are sent to **Telegram**, and the system is designed to run **consistently** via **GitHub Actions scheduled workflow**.

---

## What this project does

- Fetches market data (candles) from Binance market data endpoint
- Computes **VIDYA/VMA** and the **Ratcheted Tracking Line (T)**
- Generates signals **only** when VMA crosses T (no price crossover logic)
- Sends Telegram alerts with a clean message format + TradingView chart link
- Prevents duplicate alerts via a persistent **state file** (`state/alerts_state.json`)
- Supports **multiple symbols** via `SYMBOLS=BTCUSDT,ETHUSDT,...`
- Avoids overlapping scheduled runs via **GitHub Actions concurrency**

Key Terms:
- **VIDYA/VMA (Variable/Adaptive Moving Average):** Adaptive MA, typically using CMO-based adaptivity.
- **Ratchet (Ratcheting):** A line that moves only in one direction depending on regime (LONG => never decreases, SHORT => never increases).
- **Deduplication / Idempotency:** The same signal is not alerted twice.

---

## Repo structure (high level)

- `src/ingestion/` : Market data ingestion (Binance klines)
- `src/indicators/` : VIDYA/VMA and indicator computations
- `src/signal_engine/` : Tracking line (T), regimes, and crossover signals
- `src/alerts/` : Telegram integration
- `src/jobs/` : Scheduled job entrypoints (run + alert)
- `state/alerts_state.json` : Persistent alert state (tracked in git)

---

## Quickstart (local / Codespaces)

### 1) Install dependencies
```bash
pip install -r requirements.txt

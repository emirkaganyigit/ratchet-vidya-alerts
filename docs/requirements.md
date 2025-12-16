# Requirements — Ratcheted Offset Line Around VMA (VIDYA)

## Objective
Implement an indicator that generates LONG/SHORT signals based **only** on the crossover between:
1) VMA (implemented as VIDYA)
2) A single ratcheted tracking line T

The indicator must plot **exactly two lines**: VMA and T.
No bands, no ATR, no price-cross signals, no extra thresholds.

## Inputs (Parameters)
### A) VMA (VIDYA) parameters
- source: price series (default: Close)
- vma_length: int (e.g., 20)
- momentum_length: int (e.g., 9)
- Method: standard VIDYA/VMA approach (CMO-based VIDYA is acceptable)

### B) Offset parameters
Preferred mode:
- offset_pct: float (e.g., 1.0 means 1%)
- delta_t = VMA_t * offset_pct / 100

Only one mode active. (Fixed multiplier mode optional but not required for MVP.)

## Core Series
### 1) VMA (Main Line)
Compute VMA_t using VIDYA (VMA) from the selected source.
Price is used **only** as input to compute VMA.

### 2) T (Ratcheted Tracking Line)
T_t is a single line that tracks VMA with offset delta_t, using internal state:
- dir = LONG
- dir = SHORT

dir is required only for updating T.

## Update Rules for T
Let delta_t be computed per bar.

### If dir = LONG
- Candidate: candidate = VMA_t - delta_t
- Ratchet update: T_t = max(T_{t-1}, candidate)
- Constraint: T never decreases.

### If dir = SHORT
- Candidate: candidate = VMA_t + delta_t
- Ratchet update: T_t = min(T_{t-1}, candidate)
- Constraint: T never increases.

## Signal Generation (VMA–T crossover only)
Signals use **only** VMA and T.

### LONG Signal
Trigger:
- Previous: VMA_{t-1} <= T_{t-1}
- Current:  VMA_t >  T_t

On LONG signal:
- dir = LONG
- Re-anchor immediately: T_t = VMA_t - delta_t

### SHORT Signal
Trigger:
- Previous: VMA_{t-1} >= T_{t-1}
- Current:  VMA_t <  T_t

On SHORT signal:
- dir = SHORT
- Re-anchor immediately: T_t = VMA_t + delta_t

No other filters or confirmations.

## Initialization
On first bar where VMA is available:
- deterministic initial dir (default: LONG)
- if LONG: T_0 = VMA_0 - delta_0
- if SHORT: T_0 = VMA_0 + delta_0

## Output / Visualization
- Plot exactly two lines: VMA and T
- Plot discrete markers for LONG and SHORT signals
- Do NOT plot bands, ATR lines, or additional series

## Acceptance Criteria
1) Exactly two plotted lines exist: VMA and T
2) Signals are generated only from VMA–T crossover (not price)
3) Ratcheting:
   - In LONG regime, T never decreases
   - In SHORT regime, T never increases
4) After a signal:
   - dir flips appropriately
   - T is immediately placed on correct side of VMA by offset
5) Offset is percent-based and scales across instruments

## Out of Scope (Explicit)
- ATR-based logic
- Price-based signals (price crossing VMA/T)
- Extra thresholds, confirmations, regime filters, quality scoring
- Upper/lower bands

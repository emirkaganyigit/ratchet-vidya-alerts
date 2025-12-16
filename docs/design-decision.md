# Design Decisions

## DD-001 — VMA implementation uses VIDYA (CMO-based)
- Requirement: "standard VIDYA/VMA approach"
- Decision: implement VMA as VIDYA using CMO-based adaptivity
- Rationale: common, deterministic, widely recognized VMA variant
- Impact: VMA method can be swapped later if customer requests a different VMA variant

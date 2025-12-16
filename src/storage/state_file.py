from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional


def load_state(path: str) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_state(path: str, data: Dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def state_key(symbol: str, interval: str) -> str:
    return f"{symbol.upper()}__{interval}"


def get_last_sent(state: Dict[str, Any], symbol: str, interval: str) -> Optional[Dict[str, Any]]:
    return state.get(state_key(symbol, interval))


def set_last_sent(state: Dict[str, Any], symbol: str, interval: str, payload: Dict[str, Any]) -> None:
    state[state_key(symbol, interval)] = payload

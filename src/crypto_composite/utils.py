from __future__ import annotations
import json
import time
from pathlib import Path
from dataclasses import asdict, is_dataclass
from typing import Any

def now_ms() -> int:
    return int(time.time() * 1000)

def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))

def quote_volume(price: float, base_volume: float) -> float:
    if price <= 0 or base_volume < 0:
        raise ValueError("invalid price/base volume")
    return price * base_volume

def dataclass_to_dict(obj: Any) -> Any:
    if is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj)
    if isinstance(obj, list):
        return [dataclass_to_dict(x) for x in obj]
    if isinstance(obj, dict):
        return {k: dataclass_to_dict(v) for k, v in obj.items()}
    return obj

def write_json(path: str | Path, obj: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(dataclass_to_dict(obj), ensure_ascii=False, indent=2), encoding="utf-8")

def read_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))

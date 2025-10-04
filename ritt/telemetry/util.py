# ritt/telemetry/util.py
from __future__ import annotations
from typing import Any, Mapping, Iterable

def dig(data: Mapping[str, Any] | None, path: str) -> Any | None:
    """
    Bezpieczne pobieranie zagnieżdżonych kluczy po kropkach, np. "truck.engineOn".
    Zwraca None jeśli ścieżka nie istnieje.
    """
    if data is None:
        return None
    cur: Any = data
    for part in path.split("."):
        if isinstance(cur, Mapping) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur

def coerce_bool(v: Any) -> bool:
    """
    Konwersja różnych typów na bool (obsługa '1', 'true', 'yes', itp.).
    """
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    if isinstance(v, (int, float)):
        return v != 0
    if isinstance(v, str):
        return v.strip().lower() in {"1", "true", "t", "yes", "y", "on"}
    return bool(v)

def first_present(data: Mapping[str, Any] | None, candidates: Iterable[str], default: Any = None) -> Any:
    """
    Zwróć pierwszą istniejącą wartość dla listy ścieżek (po kropkach).
    """
    for p in candidates:
        val = dig(data, p)
        if val is not None:
            return val
    return default

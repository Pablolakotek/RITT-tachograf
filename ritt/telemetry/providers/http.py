# ritt/telemetry/providers/http.py
from __future__ import annotations
import json
from typing import Any, Dict, Optional
from datetime import datetime

try:
    import requests  # type: ignore
    _HAS_REQUESTS = True
except Exception:
    import urllib.request  # type: ignore
    _HAS_REQUESTS = False

try:
    from ritt.config import CFG  # type: ignore
except Exception:
    CFG = {}  # type: ignore[assignment]

from ritt.telemetry.util import first_present, coerce_bool

# --- Klucze kandydaci ---
PARK_BRAKE_KEYS = [
    "truck.parkBrakeOn",
    "parkBrakeOn",
    "truck.brakes.parking",
    "gameplay.parkBrakeOn",
    "game.parkBrakeOn",
    "truck.park_brake",
]

ENGINE_ON_KEYS = [
    "truck.engineOn",
    "engineOn",
    "engine.enabled",
    "gameplay.engineOn",
    "game.engineOn",
    "truck.engine.enabled",
    "engine_on",
]

SPEED_KEYS = ["truck.speed", "speed"]
TIME_KEYS  = ["game.time", "time"]

def _cfg_get(key: str, default: Any = None) -> Any:
    try:
        if isinstance(CFG, dict):
            return CFG.get(key, default)  # type: ignore[union-attr]
        return getattr(CFG, key, default)  # type: ignore[arg-type]
    except Exception:
        return default

def _parse_iso_z(iso_str: str | None) -> Optional[datetime]:
    """Parsuje ISO z 'Z' na końcu, zwraca naive UTC (dla UI wystarczy)."""
    if not iso_str or not isinstance(iso_str, str):
        return None
    s = iso_str.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
        # Uproszczenie: zwracamy 'naive' (bez tzinfo), UI tylko wyświetla HH:MM/weekday
        return dt.replace(tzinfo=None)
    except Exception:
        return None

class TelemetryHTTP:
    """
    Provider HTTP:
    - pobiera surowy JSON,
    - normalizuje engine/parking brake (bool),
    - skaluje prędkość (speed_scaled),
    - SPŁASZCZA czas gry do top-level 'time' + daje gotowe pola do UI.
    """

    def __init__(
        self,
        url: Optional[str] = None,
        timeout: Optional[float] = None,
        speed_scale: float = 1.0,
    ) -> None:
        self.url = url or _cfg_get("http_url", "http://127.0.0.1:25555/api/ets2/telemetry")
        self.timeout = float(timeout if timeout is not None else _cfg_get("http_timeout", 0.5))
        self.speed_scale = float(speed_scale)

    def _fetch_json(self) -> Dict[str, Any]:
        if _HAS_REQUESTS:
            r = requests.get(self.url, timeout=self.timeout)
            r.raise_for_status()
            txt = r.text
        else:
            with urllib.request.urlopen(self.url, timeout=self.timeout) as resp:  # type: ignore[attr-defined]
                txt = resp.read().decode("utf-8", "replace")
        return json.loads(txt)

    def poll(self) -> Dict[str, Any]:
        data = self._fetch_json()

        # --- Normalizacja flag ---
        engine_on_raw = first_present(data, ENGINE_ON_KEYS, default=None)
        park_brake_raw = first_present(data, PARK_BRAKE_KEYS, default=None)
        engine_on = coerce_bool(engine_on_raw)
        parking_brake = coerce_bool(park_brake_raw)

        # --- Skalowanie prędkości ---
        raw_speed = first_present(data, SPEED_KEYS, default=0.0)
        try:
            raw_speed_f = float(raw_speed or 0.0)
        except Exception:
            raw_speed_f = 0.0
        speed_scaled = raw_speed_f * self.speed_scale

        # --- Czas gry: spłaszczenie + pola dla UI ---
        time_iso = first_present(data, TIME_KEYS, default=None)
        if isinstance(time_iso, (int, float)):  # na wszelki wypadek
            time_iso = str(time_iso)
        dt = _parse_iso_z(time_iso) if isinstance(time_iso, str) else None
        game_time_hhmm = dt.strftime("%H:%M") if dt else None
        game_weekday = dt.strftime("%a") if dt else None

        # Budujemy wynik: surowe dane + normalizacje (nie nadpisujemy oryginalnych gałęzi)
        result = dict(data)

        # truck.speed_scaled jako wygoda
        if isinstance(result.get("truck"), dict):
            t = dict(result["truck"])
            t["speed_scaled"] = speed_scaled
            result["truck"] = t

        # top-level dodatki używane przez UI
        result["engine_on"] = engine_on
        result["parking_brake"] = parking_brake
        result["speed_scaled"] = speed_scaled

        # >>> PRZYWRÓCONY ZEGAR <<<
        # mirror 'game.time' -> top-level 'time' (tak jak oczekiwał UI)
        if time_iso is not None:
            result["time"] = time_iso
        result["game_time_iso"] = time_iso
        if game_time_hhmm is not None:
            result["game_time_hhmm"] = game_time_hhmm
        if game_weekday is not None:
            result["game_weekday"] = game_weekday

        # print(f"[HTTP] time={result.get('time')} hhmm={result.get('game_time_hhmm')} wkday={result.get('game_weekday')}")

        return result

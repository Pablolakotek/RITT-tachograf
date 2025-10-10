# ritt/telemetry/providers/http.py
# -*- coding: utf-8 -*-
from __future__ import annotations
import json
from typing import Any, Dict, Optional

try:
    import requests  # typowy sposób komunikacji z Funbit Telemetry Server
    _HAS_REQUESTS = True
except Exception:
    import urllib.request  # fallback, jeśli requests nie jest zainstalowany
    _HAS_REQUESTS = False

try:
    from ritt.config import CFG  # globalna konfiguracja systemu
except Exception:
    CFG = {}  # fallback, jeśli config nie został załadowany

from ritt.telemetry.util import first_present, coerce_bool

# Możliwe nazwy pól w JSON z Funbit Telemetry Server (różne wersje modów)
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

def _cfg_get(key: str, default: Any = None) -> Any:
    """Bezpieczny odczyt z CFG (obsługuje dict lub obiekt)."""
    try:
        if isinstance(CFG, dict):
            return CFG.get(key, default)
        return getattr(CFG, key, default)
    except Exception:
        return default


class TelemetryHTTP:
    """Provider danych telemetrii ETS2/ATS przez HTTP (Funbit Telemetry Server)."""

    def __init__(
        self,
        url: Optional[str] = None,
        timeout: Optional[float] = None,
        speed_scale: float = 1.0,
    ) -> None:
        # adres serwera (domyślnie Funbit)
        self.url = url or _cfg_get("http_url", "http://127.0.0.1:25555/api/ets2/telemetry")
        self.timeout = float(timeout if timeout is not None else _cfg_get("http_timeout", 0.5))
        self.speed_scale = float(speed_scale)

    # ---------------------------------------------------------------
    # Niskopoziomowe pobranie danych z HTTP
    # ---------------------------------------------------------------
    def _fetch_json(self) -> Dict[str, Any]:
        """Pobiera surowy JSON z serwera Funbit."""
        if _HAS_REQUESTS:
            r = requests.get(self.url, timeout=self.timeout)
            r.raise_for_status()
            txt = r.text
        else:
            with urllib.request.urlopen(self.url, timeout=self.timeout) as resp:  # type: ignore[attr-defined]
                txt = resp.read().decode("utf-8", "replace")
        return json.loads(txt)

    # ---------------------------------------------------------------
    # Główna metoda pobierania danych
    # ---------------------------------------------------------------
    def poll(self) -> Dict[str, Any]:
        """Pobiera i normalizuje dane telemetryczne z gry."""
        data = self._fetch_json()

        # odczyt kluczowych informacji o stanie pojazdu
        engine_on_raw = first_present(data, ENGINE_ON_KEYS, default=None)
        park_brake_raw = first_present(data, PARK_BRAKE_KEYS, default=None)
        engine_on = coerce_bool(engine_on_raw)
        parking_brake = coerce_bool(park_brake_raw)

        # prędkość z ewentualnym skalowaniem
        raw_speed = first_present(data, SPEED_KEYS, default=0.0)
        try:
            raw_speed_f = float(raw_speed or 0.0)
        except Exception:
            raw_speed_f = 0.0
        speed_scaled = raw_speed_f * self.speed_scale

        # tworzymy wynikowy słownik
        result = dict(data)
        if isinstance(result.get("truck"), dict):
            t = dict(result["truck"])
            t["speed_scaled"] = speed_scaled
            result["truck"] = t

        result["engine_on"] = engine_on
        result["parking_brake"] = parking_brake
        result["speed_scaled"] = speed_scaled
        return result

    # ---------------------------------------------------------------
    # Alias dla kompatybilności z resztą aplikacji
    # ---------------------------------------------------------------
    fetch = poll  # ✅ dzięki temu działa p.fetch() w całym systemie

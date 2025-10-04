# ritt/telemetry/service.py
from __future__ import annotations
from typing import Dict, Any, Callable, Optional
from .model import TelemetryFrame, GameInfo, TruckInfo, TrailerInfo, JobInfo, NavigationInfo, Vec3
from .store import TelemetryDB

def _to_bool(v) -> bool:
    if isinstance(v, bool): return v
    if v is None: return False
    if isinstance(v, (int, float)): return v != 0
    if isinstance(v, str):
        s = v.strip().lower()
        return s in ("1","true","t","yes","y","on")
    return bool(v)

def _from_legacy_flat(raw: Dict[str, Any]) -> TelemetryFrame:
    """
    Adapter dla 'starego' providera (jak w TACHO1), który zwraca płaskie pola:
      speed_kmh, engine_on, parking_brake, paused, game_time_iso, game_minutes, game_time_unix
    """
    tf = TelemetryFrame(
        paused = _to_bool(raw.get("paused")),
        speed_kmh = float(raw.get("speed_kmh") or 0.0),
        engine_on = _to_bool(raw.get("engine_on")),
        parking_brake = _to_bool(raw.get("parking_brake")),
        game_time_iso = raw.get("game_time_iso"),
        game_time_unix = int(raw.get("game_time_unix") or 0),
        game_minutes = raw.get("game_minutes"),
        game = GameInfo(time_iso=raw.get("game_time_iso")),
        truck = TruckInfo(speed_kmh=float(raw.get("speed_kmh") or 0.0)),
        trailer = TrailerInfo(),
        job = JobInfo(),
        navigation = NavigationInfo(),
        raw = raw,
    )
    return tf

class TelemetryService:
    """
    Odbiera surowe ramki z providera (build_provider().poll()).
    Obsługuje dwa formaty:
      1) SUROWY Funbit (ma klucze 'game'/'truck'...) → używa mappera -> TelemetryFrame
      2) 'Legacy flat' (jak TACHO1: speed_kmh/engine_on/...) → adapter _from_legacy_flat
    Opcjonalnie zapisuje do DB, a UI zawsze dostaje płaski dict.
    """
    def __init__(self,
                 provider,
                 mapper: Callable[[Dict[str, Any]], TelemetryFrame],
                 db: Optional[TelemetryDB] = None):
        self.provider = provider
        self.mapper = mapper
        self.db = db

    def poll_normalized(self) -> Dict[str, Any]:
        raw = self.provider.poll() or {}

        # Wykryj format
        is_raw_funbit = isinstance(raw, dict) and (
            ("game" in raw) or ("truck" in raw) or ("navigation" in raw)
        )
        try:
            if is_raw_funbit:
                tf: TelemetryFrame = self.mapper(raw)
            else:
                # legacy flat (TACHO1)
                tf: TelemetryFrame = _from_legacy_flat(raw)
        except Exception:
            # w razie błędu mappera – spróbuj legacy jako fallback
            tf = _from_legacy_flat(raw)

        # Zapis do DB (bezpiecznie)
        if self.db:
            try:
                self.db.insert(tf)
            except Exception:
                pass

        # Płaski interfejs dla UI (zawsze!)
        out = {
            "game_time_iso": tf.game_time_iso,
            "game_time_unix": tf.game_time_unix,
            "game_minutes": tf.game_minutes,
            "paused": bool(tf.paused),
            "speed_kmh": float(tf.speed_kmh),
            "engine_on": bool(tf.engine_on),
            "parking_brake": bool(tf.parking_brake),
            # snapshoty – dostępne na przyszłość; jeśli legacy, będą w większości puste
            "game": tf.game.__dict__,
            "truck": {
                **tf.truck.__dict__,
                "placement": tf.truck.placement.__dict__,
                "acceleration": tf.truck.acceleration.__dict__,
                "head": tf.truck.head.__dict__,
                "cabin": tf.truck.cabin.__dict__,
                "hook": tf.truck.hook.__dict__,
            },
            "trailer": {**tf.trailer.__dict__, "placement": tf.trailer.placement.__dict__},
            "job": tf.job.__dict__,
            "navigation": tf.navigation.__dict__,
        }
        return out

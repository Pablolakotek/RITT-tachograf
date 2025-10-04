# ritt/telemetry/mappers/funbit_v9.py
from __future__ import annotations
from typing import Dict, Any
from ..model import TelemetryFrame, GameInfo, TruckInfo, TrailerInfo, JobInfo, NavigationInfo, Vec3

SPEED_SCALE = 3.6  # m/s -> km/h

def to_bool(v) -> bool:
    if isinstance(v, bool): return v
    if v is None: return False
    if isinstance(v, (int, float)): return v != 0
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("1","true","t","yes","y","on"): return True
        if s in ("0","false","f","no","n","off",""): return False
    return bool(v)

def get_first(d: dict, *keys, default=None):
    for k in keys:
        if k in d: return d.get(k)
    return default

def _vec3(d: Dict[str, Any] | None) -> Vec3:
    if not isinstance(d, dict): return Vec3()
    return Vec3(float(d.get("x") or 0.0), float(d.get("y") or 0.0), float(d.get("z") or 0.0))

def normalize_funbit_v9(raw: Dict[str, Any]) -> TelemetryFrame:
    """
    AUTO mapper:
    - jeśli 'raw' jest już spłaszczony (speed_kmh/engine_on/parking_brake), użyj bezpośrednio,
    - w przeciwnym wypadku zmapuj pełny JSON Funbita (game/truck/trailer/...).
    """

    # --- FAST-PATH: spłaszczony słownik jak z TelemetryHTTP (TACHO1) ---
    if any(k in raw for k in ("speed_kmh", "engine_on", "parking_brake", "game_time_iso", "paused")):
        # wartości domyślne + bezpieczne konwersje
        speed_kmh = float(raw.get("speed_kmh") or 0.0)
        engine_on = to_bool(raw.get("engine_on"))
        parking_brake = to_bool(raw.get("parking_brake"))
        paused = to_bool(raw.get("paused"))
        game_time_iso = raw.get("game_time_iso")
        game_time_unix = raw.get("game_time_unix")
        game_minutes = raw.get("game_minutes")

        # Minimalne snapshoty (żeby UI/dev mógł sięgnąć po truck/placement w przyszłości)
        truck = TruckInfo(
            speed_kmh=speed_kmh,
            speed_ms=speed_kmh / SPEED_SCALE if speed_kmh else 0.0,
            engine_on=engine_on,
            park_brake_on=parking_brake,
        )
        tf = TelemetryFrame(
            paused=paused,
            speed_kmh=speed_kmh,
            engine_on=engine_on,
            parking_brake=parking_brake,
            game_time_iso=game_time_iso,
            game_time_unix=int(game_time_unix or 0),
            game_minutes= int(game_minutes) if (game_minutes is not None and str(game_minutes).isdigit()) else None,
            truck=truck,
            raw=raw,
        )
        return tf

    # --- STANDARDOWA ŚCIEŻKA: surowy JSON Funbita ---
    g = raw.get("game", {}) or {}
    t = raw.get("truck", {}) or {}
    tr = raw.get("trailer", {}) or {}
    j = raw.get("job", {}) or {}
    n = raw.get("navigation", {}) or {}

    speed_ms = float(t.get("speed") or 0.0)
    speed_kmh = speed_ms * SPEED_SCALE

    engine_on = to_bool(get_first(t, "engineOn", "engine_on", "engine", default=False))
    parking_brake = to_bool(get_first(t, "parkBrakeOn", "parkingBrake", "parking_brake", default=False))

    game = GameInfo(
        connected = to_bool(get_first(g, "connected")),
        game_name = g.get("gameName"),
        paused = to_bool(get_first(g, "paused")),
        time_iso = g.get("time"),
        time_scale = g.get("timeScale"),
        next_rest_iso = g.get("nextRestStopTime"),
        version = g.get("version"),
        plugin_version = (str(get_first(g, "telemetryPluginVersion")) if get_first(g, "telemetryPluginVersion") is not None else None),
    )

    truck = TruckInfo(
        id = t.get("id"),
        make = t.get("make"),
        model = t.get("model"),
        speed_ms = speed_ms,
        speed_kmh = speed_kmh,
        engine_on = engine_on,
        park_brake_on = parking_brake,
        cruise_on = to_bool(get_first(t, "cruiseControlOn")),
        cruise_speed_kmh = float(get_first(t, "cruiseControlSpeed") or 0.0),
        odometer_km = float(get_first(t, "odometer") or 0.0),
        gear = get_first(t, "gear"),
        rpm = float(get_first(t, "engineRpm") or 0.0),
        battery_v = float(get_first(t, "batteryVoltage") or 0.0),
        lights_beam_low = to_bool(get_first(t, "lightsBeamLowOn")),
        lights_parking = to_bool(get_first(t, "lightsParkingOn")),
        placement = _vec3(get_first(t, "placement")),
        heading = float((get_first(t, "placement") or {}).get("heading") or 0.0),
        pitch = float((get_first(t, "placement") or {}).get("pitch") or 0.0),
        roll = float((get_first(t, "placement") or {}).get("roll") or 0.0),
        acceleration = _vec3(get_first(t, "acceleration")),
        head = _vec3(get_first(t, "head")),
        cabin = _vec3(get_first(t, "cabin")),
        hook = _vec3(get_first(t, "hook")),
    )

    trailer = TrailerInfo(
        attached = to_bool(get_first(tr, "attached")),
        id = tr.get("id"),
        name = tr.get("name"),
        mass_kg = float(get_first(tr, "mass") or 0.0),
        wear = float(get_first(tr, "wear") or 0.0),
        placement = _vec3(get_first(tr, "placement")),
        heading = float((get_first(tr, "placement") or {}).get("heading") or 0.0),
        pitch = float((get_first(tr, "placement") or {}).get("pitch") or 0.0),
        roll = float((get_first(tr, "placement") or {}).get("roll") or 0.0),
    )

    job = JobInfo(
        income = int(get_first(j, "income") or 0),
        deadline_iso = get_first(j, "deadlineTime"),
        remaining_iso = get_first(j, "remainingTime"),
        source_city = get_first(j, "sourceCity"),
        source_company = get_first(j, "sourceCompany"),
        dest_city = get_first(j, "destinationCity"),
        dest_company = get_first(j, "destinationCompany"),
    )

    nav = NavigationInfo(
        eta_iso = get_first(n, "estimatedTime"),
        distance_m = int(get_first(n, "estimatedDistance") or 0),
        speed_limit_kmh = int(get_first(n, "speedLimit") or 0),
    )

    tf = TelemetryFrame(
        paused = to_bool(get_first(g, "paused", default=False)),
        speed_kmh = speed_kmh,
        engine_on = engine_on,
        parking_brake = parking_brake,
        game_time_iso = get_first(g, "time"),
        game = game,
        truck = truck,
        trailer = trailer,
        job = job,
        navigation = nav,
        raw = raw,
    )
    return tf

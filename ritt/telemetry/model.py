# ritt/telemetry/model.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

@dataclass
class GameInfo:
    connected: Optional[bool] = None
    game_name: Optional[str] = None
    paused: Optional[bool] = None
    time_iso: Optional[str] = None
    time_unix: Optional[int] = None
    minutes: Optional[int] = None
    time_scale: Optional[int] = None
    next_rest_iso: Optional[str] = None
    version: Optional[str] = None
    plugin_version: Optional[str] = None

@dataclass
class Vec3:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

@dataclass
class TruckInfo:
    id: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    speed_ms: float = 0.0
    speed_kmh: float = 0.0
    engine_on: Optional[bool] = None
    park_brake_on: Optional[bool] = None
    cruise_on: Optional[bool] = None
    cruise_speed_kmh: Optional[float] = None
    odometer_km: Optional[float] = None
    gear: Optional[int] = None
    rpm: Optional[float] = None
    battery_v: Optional[float] = None
    lights_beam_low: Optional[bool] = None
    lights_parking: Optional[bool] = None
    placement: Vec3 = field(default_factory=Vec3)
    heading: Optional[float] = None
    pitch: Optional[float] = None
    roll: Optional[float] = None
    acceleration: Vec3 = field(default_factory=Vec3)
    head: Vec3 = field(default_factory=Vec3)
    cabin: Vec3 = field(default_factory=Vec3)
    hook: Vec3 = field(default_factory=Vec3)

@dataclass
class TrailerInfo:
    attached: Optional[bool] = None
    id: Optional[str] = None
    name: Optional[str] = None
    mass_kg: Optional[float] = None
    wear: Optional[float] = None
    placement: Vec3 = field(default_factory=Vec3)
    heading: Optional[float] = None
    pitch: Optional[float] = None
    roll: Optional[float] = None

@dataclass
class JobInfo:
    income: Optional[int] = None
    deadline_iso: Optional[str] = None
    remaining_iso: Optional[str] = None
    source_city: Optional[str] = None
    source_company: Optional[str] = None
    dest_city: Optional[str] = None
    dest_company: Optional[str] = None

@dataclass
class NavigationInfo:
    eta_iso: Optional[str] = None
    distance_m: Optional[int] = None
    speed_limit_kmh: Optional[int] = None

@dataclass
class TelemetryFrame:
    # 1) płaski zestaw dla tachografu
    paused: bool = False
    speed_kmh: float = 0.0
    engine_on: bool = False
    parking_brake: bool = False
    game_time_iso: Optional[str] = None
    game_time_unix: Optional[int] = None
    game_minutes: Optional[int] = None

    # 2) snapshoty tematyczne
    game: GameInfo = field(default_factory=GameInfo)
    truck: TruckInfo = field(default_factory=TruckInfo)
    trailer: TrailerInfo = field(default_factory=TrailerInfo)
    job: JobInfo = field(default_factory=JobInfo)
    navigation: NavigationInfo = field(default_factory=NavigationInfo)

    # 3) surowy JSON
    raw: Dict[str, Any] = field(default_factory=dict)

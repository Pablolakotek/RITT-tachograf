# ritt/telemetry/store.py
from __future__ import annotations
import json, sqlite3, time
from typing import Optional, List, Dict, Any
from .model import TelemetryFrame

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS telemetry_frames (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts_utc REAL NOT NULL,
  game_time_iso TEXT,
  paused INTEGER,
  speed_kmh REAL,
  engine_on INTEGER,
  parking_brake INTEGER,
  odometer_km REAL,
  truck_x REAL, truck_y REAL, truck_z REAL,
  heading REAL, pitch REAL, roll REAL,
  trailer_attached INTEGER,
  job_income INTEGER,
  nav_distance_m INTEGER,
  raw_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tf_ts ON telemetry_frames(ts_utc);
CREATE INDEX IF NOT EXISTS idx_tf_flags ON telemetry_frames(paused, engine_on, parking_brake);
"""

class TelemetryDB:
    def __init__(self, path: str = "telemetry.sqlite"):
        self.path = path
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.execute("PRAGMA foreign_keys=ON;")
        for stmt in SCHEMA.strip().split(";\n"):
            if stmt.strip():
                self._conn.execute(stmt)
        self._conn.commit()

    def insert(self, tf: TelemetryFrame) -> int:
        js = json.dumps(tf.raw, ensure_ascii=False)
        truck = tf.truck
        cur = self._conn.cursor()
        cur.execute("""
        INSERT INTO telemetry_frames
        (ts_utc, game_time_iso, paused, speed_kmh, engine_on, parking_brake,
         odometer_km, truck_x, truck_y, truck_z, heading, pitch, roll,
         trailer_attached, job_income, nav_distance_m, raw_json)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            time.time(), tf.game_time_iso, int(tf.paused), float(tf.speed_kmh),
            int(tf.engine_on), int(tf.parking_brake),
            float(truck.odometer_km or 0.0),
            float(truck.placement.x), float(truck.placement.y), float(truck.placement.z),
            float(truck.heading or 0.0), float(truck.pitch or 0.0), float(truck.roll or 0.0),
            int(tf.trailer.attached or 0), int(tf.job.income or 0), int(tf.navigation.distance_m or 0),
            js
        ))
        self._conn.commit()
        return int(cur.lastrowid)

    def latest(self) -> Optional[Dict[str, Any]]:
        row = self._conn.execute(
            "SELECT id, ts_utc, game_time_iso, paused, speed_kmh, engine_on, parking_brake, raw_json "
            "FROM telemetry_frames ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if not row:
            return None
        import json as _json
        return {
            "id": row[0], "ts_utc": row[1], "game_time_iso": row[2],
            "paused": bool(row[3]), "speed_kmh": float(row[4]),
            "engine_on": bool(row[5]), "parking_brake": bool(row[6]),
            "raw": _json.loads(row[7])
        }

    def last_n(self, n: int = 100) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT ts_utc, speed_kmh, engine_on, parking_brake, truck_x, truck_y, truck_z "
            "FROM telemetry_frames ORDER BY id DESC LIMIT ?", (int(n),)
        ).fetchall()
        return [
            {"ts_utc": r[0], "speed_kmh": r[1], "engine_on": bool(r[2]),
             "parking_brake": bool(r[3]), "x": r[4], "y": r[5], "z": r[6]}
            for r in rows
        ]

    def between(self, ts_from: float, ts_to: float) -> List[Dict[str, Any]]:
        cur = self._conn.execute(
            "SELECT ts_utc, speed_kmh, engine_on, parking_brake, nav_distance_m "
            "FROM telemetry_frames WHERE ts_utc BETWEEN ? AND ? ORDER BY ts_utc ASC",
            (float(ts_from), float(ts_to))
        )
        return [{"ts_utc": r[0], "speed_kmh": r[1], "engine_on": bool(r[2]), "parking_brake": bool(r[3]),
                 "nav_distance_m": r[4]} for r in cur.fetchall()]

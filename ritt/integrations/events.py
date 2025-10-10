# -*- coding: utf-8 -*-
"""
RITT Event Core — system zdarzeń telemetrycznych wysyłanych do n8n.
Autor: Pawel / RITT
"""

import threading, datetime, uuid


def send_event_to_n8n(self, event_type: str, description: str = "", extra: dict | None = None):
    """Wysyła zdarzenie do n8n (asynchronicznie)."""
    try:
        odometer = 0.0
        if hasattr(self, "telemetry_service") and hasattr(self.telemetry_service, "db"):
            get_odo = getattr(self.telemetry_service.db, "get_last_odometer", None)
            if callable(get_odo):
                odometer = float(get_odo())

        data = {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "driver_id": getattr(self, "logged_user", "DRV_UNKNOWN"),
            "vehicle_id": getattr(self, "vehicle_id", "TRUCK_01"),
            "event_type": event_type,
            "description": description,
            "odometer_km": round(odometer, 2),
            "job_status": getattr(self, "current_job_status", "unknown"),
            "engine_on": getattr(self, "engine_on", False),
            "speed_kmh": getattr(self, "speed_kmh", 0.0),
            "parking_brake": getattr(self, "parking_brake", False),
        }

        if extra:
            data.update(extra)

        print(f"[EVENT] {event_type} → {description}")

        def _worker():
            try:
                if hasattr(self, "net") and self.net:
                    self.net.post_json("/ritt/event", data)
                    print(f"[EVENT] Wysłano do n8n ({event_type})")
                else:
                    print("[EVENT] Brak połączenia z n8n.")
            except Exception as e:
                print(f"[EVENT] Błąd wysyłania: {e}")

        threading.Thread(target=_worker, daemon=True).start()

    except Exception as e:
        print(f"[EVENT] Unexpected error: {e}")

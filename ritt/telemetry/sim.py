import time
from .base import TelemetryBase

class TelemetrySIM(TelemetryBase):
    def __init__(self, v=60.0):
        self.game_time=int(time.time()); self.v=v
        self.engine_on=True; self.parking=False; self.paused=False
    def poll(self):
        self.game_time+=1
        return {"game_time_unix":self.game_time, "speed_kmh": self.v if not (self.paused or self.parking) else 0.0,
                "engine_on":self.engine_on,"parking_brake":self.parking,"paused":self.paused}

import os, ctypes
from .base import TelemetryBase

class TelemetryDLL(TelemetryBase):
    """Oczekiwane (jeśli to nie Funbit): get_game_time_minutes() albo get_game_time_unix() itd."""
    def __init__(self, dll_path, speed_scale=3.6):
        self.scale = speed_scale
        self.dll = None
        self.has_minutes = False
        self.has_unix = False
        if dll_path and os.path.exists(dll_path):
            try:
                self.dll = ctypes.CDLL(dll_path)
                try:
                    self.dll.get_game_time_minutes.restype = ctypes.c_int
                    self.has_minutes = True
                except Exception:
                    self.has_minutes = False
                try:
                    self.dll.get_game_time_unix.restype = ctypes.c_int
                    self.has_unix = True
                except Exception:
                    self.has_unix = False
                try: self.dll.get_speed_ms.restype = ctypes.c_float
                except Exception: pass
                try: self.dll.get_engine_on.restype = ctypes.c_int
                except Exception: pass
                try: self.dll.get_parking_brake.restype = ctypes.c_int
                except Exception: pass
                try: self.dll.get_paused.restype = ctypes.c_int
                except Exception: pass
            except Exception as e:
                print("DLL load error:", e); self.dll=None

    def poll(self):
        if not self.dll:
            return {"game_minutes": None,"game_time_unix":0,"speed_kmh":0.0,"engine_on":True,"parking_brake":False,"paused":False,"time_source":"dll:none"}
        gm=None; gt=0; sp=0.0; eng=1; park=0; paused=0
        try:
            if self.has_minutes:
                gm = int(self.dll.get_game_time_minutes())
        except Exception: gm=None
        try:
            if self.has_unix:
                gt = int(self.dll.get_game_time_unix())
        except Exception: gt=0
        try: sp=float(self.dll.get_speed_ms())
        except Exception: sp=0.0
        try: eng=int(self.dll.get_engine_on())
        except Exception: eng=1
        try: park=int(self.dll.get_parking_brake())
        except Exception: park=0
        try: paused=int(self.dll.get_paused())
        except Exception: paused=0

        src = "dll:minutes" if gm is not None else ("dll:unix" if gt>0 else "dll:none")
        return {
            "game_minutes": gm,
            "game_time_unix": gt,
            "speed_kmh": max(0.0, sp*self.scale),
            "engine_on": bool(eng),
            "parking_brake": bool(park),
            "paused": bool(paused),
            "time_source": src,
        }

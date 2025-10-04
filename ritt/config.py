import os, configparser

DEFAULTS = {
    "api_base": "http://127.0.0.1:8000",
    "driver_id": "DRV001",
    "lang": "pl",
    # telemetry
    "mode": "sim",  # dll | http | sim
    "dll_path": "",
    "http_url": "http://127.0.0.1:25555/api/telemetry",
    "speed_scale": "3.6",       # m/s -> km/h
    "fallback_game_speed": "0", # sek gry / sek real (0=wyłącz)
}

def _read_ini():
    cfg_path = os.path.join(os.path.dirname(__file__), "..", "ritt.ini")
    cfg_path = os.path.abspath(cfg_path)
    cp = configparser.ConfigParser()
    cp.read_dict({"ritt": {}, "telemetry": {}})
    if os.path.exists(cfg_path):
        cp.read(cfg_path, encoding="utf-8")
    return {
        "api_base": cp.get("ritt", "api_base", fallback=DEFAULTS["api_base"]),
        "driver_id": cp.get("ritt", "driver_id", fallback=DEFAULTS["driver_id"]),
        "lang": cp.get("ritt", "lang", fallback=DEFAULTS["lang"]).lower(),
        "mode": cp.get("telemetry", "mode", fallback=DEFAULTS["mode"]).lower(),
        "dll_path": cp.get("telemetry", "dll_path", fallback=DEFAULTS["dll_path"]),
        "http_url": cp.get("telemetry", "http_url", fallback=DEFAULTS["http_url"]),
        "speed_scale": float(cp.get("telemetry", "speed_scale", fallback=DEFAULTS["speed_scale"])),
        "fallback_game_speed": int(cp.get("telemetry", "fallback_game_speed", fallback=DEFAULTS["fallback_game_speed"])),
    }

CFG = _read_ini()

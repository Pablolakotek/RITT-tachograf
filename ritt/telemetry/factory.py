# ritt/telemetry/factory.py
from __future__ import annotations
from typing import Any
import importlib

try:
    from ritt.config import CFG  # type: ignore
except Exception:
    CFG = {}  # type: ignore[assignment]

def _cfg_get(key: str, default: Any = None) -> Any:
    """Bezpieczny odczyt z CFG (obsługuje dict lub obiekt z atrybutami)."""
    try:
        if isinstance(CFG, dict):
            return CFG.get(key, default)  # type: ignore[union-attr]
        return getattr(CFG, key, default)  # type: ignore[arg-type]
    except Exception:
        return default

def _import_provider(module_name: str, class_name: str):
    """
    Próbujemy importować providera na kilka sposobów, żeby uniknąć
    problemów ścieżkowych (np. gdy uruchamiasz z różnego katalogu).
    """
    # 1) absolute: ritt.telemetry.providers.http
    try:
        mod = importlib.import_module(module_name)
        return getattr(mod, class_name)
    except Exception:
        pass

    # 2) relative do pakietu telemetry: .providers.http
    try:
        mod = importlib.import_module("." + module_name.split(".")[-1], package=__package__)
        return getattr(mod, class_name)
    except Exception:
        pass

    # 3) bez prefiksu ritt. — czasem projekt jest uruchamiany z innego sys.path
    try:
        short_name = module_name.split("ritt.", 1)[-1]
        mod = importlib.import_module(short_name)
        return getattr(mod, class_name)
    except Exception as e:
        raise ModuleNotFoundError(f"Cannot import {class_name} from {module_name} (also tried relative/short). Last error: {e}")

def build_provider():
    """
    Buduje provider telemetrii zgodnie z konfiguracją.
    Obsługiwane: 'http', 'dll', 'sim' (domyślnie 'http').
    """
    mode = str(_cfg_get("telemetry_mode", _cfg_get("mode", "http"))).lower()
    speed_scale = float(_cfg_get("speed_scale", 1.0))

    if mode == "dll":
        TelemetryDLL = _import_provider("ritt.telemetry.providers.dll", "TelemetryDLL")
        return TelemetryDLL(dll_path=_cfg_get("dll_path", None), speed_scale=speed_scale)

    if mode == "sim":
        TelemetrySim = _import_provider("ritt.telemetry.providers.sim", "TelemetrySim")
        return TelemetrySim(speed_scale=speed_scale)

    # domyślnie HTTP
    TelemetryHTTP = _import_provider("ritt.telemetry.providers.http", "TelemetryHTTP")
    return TelemetryHTTP(
        url=_cfg_get("http_url", "http://127.0.0.1:25555/api/ets2/telemetry"),
        timeout=_cfg_get("http_timeout", 0.5),
        speed_scale=speed_scale,
    )

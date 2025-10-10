# ritt/telemetry/providers/__init__.py
# Eksport klas providerów, aby były dostępne jako ritt.telemetry.providers.*
try:
    from .http import TelemetryHTTP
except Exception:  # pragma: no cover
    TelemetryHTTP = None  # type: ignore

try:
    from .dll import TelemetryDLL
except Exception:  # pragma: no cover
    TelemetryDLL = None  # type: ignore

try:
    from .sim import TelemetrySim
except Exception:  # pragma: no cover
    TelemetrySim = None  # type: ignore

__all__ = ["TelemetryHTTP", "TelemetryDLL", "TelemetrySim"]

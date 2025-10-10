# ritt/telemetry/__init__.py
# Upewnia się, że podpakiety są widoczne jako pakiety Pythona.
from .factory import build_provider  # wygodny re-export

__all__ = ["build_provider"]

import time, threading, requests
from PySide6.QtCore import QObject, Signal
from .config import CFG

class NetSignals(QObject):
    pointsUpdated = Signal(int)
    eventAck = Signal(str)
    netError = Signal(str)

class NetClient:
    def __init__(self, signals: NetSignals):
        self.s = requests.Session()
        self.s.headers.update({"Content-Type":"application/json"})
        self.signals = signals
        self._lock = threading.Lock()
        self._last_err = 0

    def _guard(self, fn, *a, **kw):
        try:
            with self._lock:
                r = fn(*a, **kw)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            now = time.time()
            if now - self._last_err > 5:
                self._last_err = now
                self.signals.netError.emit(str(e))
            return None

    def post_json(self, path, payload, timeout=1.5):
        return self._guard(self.s.post, f"{CFG['api_base']}{path}", json=payload, timeout=timeout)

    def get_json(self, path, timeout=1.5):
        return self._guard(self.s.get, f"{CFG['api_base']}{path}", timeout=timeout)

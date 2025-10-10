# ritt/n8n.py
from __future__ import annotations
import json, time, hmac, hashlib, uuid, threading, queue
from typing import Callable, Dict, Any, Iterable, Optional, List
from dataclasses import dataclass
import requests
import websocket
from pydantic import BaseModel, Field
from datetime import datetime, timezone

# ===== MODELE =====
def _now_iso_z() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

class Event(BaseModel):
    api_version: str = "1.0"
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sequence_no: int
    session_id: str
    event_type: str
    driver_id: str
    vehicle_id: Optional[str] = None
    ts_utc: str = Field(default_factory=_now_iso_z)
    tz: str = "Europe/London"
    status: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    speed_kph: Optional[float] = None
    odo_km: Optional[float] = None
    source: str = "ets2"
    app_version: str = "1.0.0"
    payload: Dict[str, Any] = {}

class Batch(BaseModel):
    api_version: str = "1.0"
    events: List[Event]

class Ack(BaseModel):
    cmd_id: str
    driver_id: str
    ack_ts: str = Field(default_factory=_now_iso_z)
    status: str
    message: str = ""
    details: Dict[str, Any] = {}

# ===== HMAC =====
def _signed_headers(secret: str, body: bytes) -> Dict[str, str]:
    ts = str(int(time.time() * 1000))
    nonce = str(uuid.uuid4())
    mac = hmac.new(secret.encode("utf-8"), (ts + nonce).encode("utf-8") + body, hashlib.sha256).hexdigest()
    return {
        "X-RITT-Timestamp": ts,
        "X-RITT-Nonce": nonce,
        "X-RITT-Signature": f"sha256={mac}",
        "User-Agent": "RITT-Tachograph/1.0 (python)",
        "Content-Type": "application/json; charset=utf-8",
    }

@dataclass
class N8nEndpoints:
    base_url: str
    ingest_path: str
    commands_path: str
    ack_path: str

    @property
    def ingest_url(self) -> str:
        return self.base_url.rstrip("/") + self.ingest_path

    @property
    def ack_url(self) -> str:
        return self.base_url.rstrip("/") + self.ack_path

    @property
    def ws_url(self) -> str:
        # http[s] -> ws[s]
        if self.base_url.startswith("https://"):
            base_ws = "wss://" + self.base_url[len("https://"):]
        elif self.base_url.startswith("http://"):
            base_ws = "ws://" + self.base_url[len("http://"):]
        else:
            base_ws = self.base_url  # already ws/wss
        return base_ws.rstrip("/") + self.commands_path

class N8nClient:
    def __init__(
        self,
        endpoints: N8nEndpoints,
        hmac_secret: str,
        send_interval_ms: int = 1000,
        batch_size: int = 50,
        retry_max: int = 8,
        dry_run: bool = False,
        timezone: str = "Europe/London",
    ):
        self.endpoints = endpoints
        self.hmac_secret = hmac_secret
        self.send_interval_ms = send_interval_ms
        self.batch_size = batch_size
        self.retry_max = retry_max
        self.dry_run = dry_run
        self.timezone = timezone

        self._q: "queue.Queue[Event]" = queue.Queue(maxsize=10000)
        self._stop = threading.Event()
        self._sender_thread: Optional[threading.Thread] = None
        self._ws: Optional[websocket.WebSocketApp] = None
        self._session_id: str = "unknown"
        self._seq = 0

        self._cmd_handler: Optional[Callable[[Dict[str, Any]], tuple]] = None  # (status, message, details)

    # ===== API (App → n8n) =====
    def enqueue_event(self, **evt):
        self._seq += 1
        evt.setdefault("sequence_no", self._seq)
        evt.setdefault("session_id", self._session_id)
        e = Event(**evt)
        self._q.put(e)

    def _post_batch(self, events: Iterable[Event]) -> bool:
        payload = Batch(events=list(events)).model_dump_json().encode("utf-8")
        headers = _signed_headers(self.hmac_secret, payload)
        resp = requests.post(self.endpoints.ingest_url, data=payload, headers=headers, timeout=15)
        # no-retry for 4xx (except 429), retry for 5xx
        if resp.status_code in (200, 201):
            return True
        if resp.status_code in (400, 401, 403, 409, 422):
            return False
        if resp.status_code == 429:
            time.sleep(int(resp.headers.get("Retry-After", "1")))
            return False
        # 5xx -> throw to backoff
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")

    def _sender_loop(self):
        backoff = 1.0
        buf: List[Event] = []
        while not self._stop.is_set():
            try:
                # fill buffer or wait tick
                try:
                    e = self._q.get(timeout=self.send_interval_ms / 1000)
                    buf.append(e)
                except queue.Empty:
                    pass

                if not buf:
                    continue

                batch = buf[: self.batch_size]
                buf = buf[self.batch_size :] if len(buf) > self.batch_size else []

                if self.dry_run:
                    continue

                ok = self._post_batch(batch)
                if ok:
                    backoff = 1.0
                else:
                    # soft failure (4xx handled) — drop silently
                    pass

            except Exception:
                time.sleep(min(backoff, 60.0))
                backoff = min(backoff * 2, 60.0)

    # ===== API (n8n → App via WS) =====
    def _on_ws_message(self, ws, msg: str):
        try:
            data = json.loads(msg)
        except Exception:
            return

        status, message, details = "ok", "", {}
        try:
            if self._cmd_handler:
                out = self._cmd_handler(data)  # expects (status, message, details)
                if isinstance(out, tuple) and len(out) == 3:
                    status, message, details = out
        except Exception as e:
            status, message = "failed", str(e)
            details = {}

        # ACK
        try:
            ack = Ack(
                cmd_id   = data.get("cmd_id", ""),
                driver_id= (data.get("target") or {}).get("driver_id", "DRV_001"),
                status   = status,
                message  = message,
                details  = details or {},
            )
            body = ack.model_dump_json().encode("utf-8")
            headers = _signed_headers(self.hmac_secret, body)
            requests.post(self.endpoints.ack_url, data=body, headers=headers, timeout=10)
        except Exception:
            pass

    def _on_ws_error(self, ws, err):
        # opcjonalnie: logowanie
        pass

    def _on_ws_close(self, ws, code, reason):
        if not self._stop.is_set():
            time.sleep(2.0)
            self._run_ws_async()

    def _run_ws_async(self):
        self._ws = websocket.WebSocketApp(
            self.endpoints.ws_url,
            on_message=self._on_ws_message,
            on_error=self._on_ws_error,
            on_close=self._on_ws_close,
        )
        threading.Thread(target=self._ws.run_forever, kwargs={"ping_interval": 30}, daemon=True).start()

    # ===== Lifecyle =====
    def set_command_handler(self, fn: Callable[[Dict[str, Any]], tuple]):
        self._cmd_handler = fn

    def start(self, session_id: str):
        self._session_id = session_id
        self._sender_thread = threading.Thread(target=self._sender_loop, daemon=True)
        self._sender_thread.start()
        self._run_ws_async()

    def stop(self):
        self._stop.set()
        try:
            if self._ws:
                self._ws.close()
        except Exception:
            pass

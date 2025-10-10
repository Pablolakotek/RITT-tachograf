# ritt/n8n_config.py
from __future__ import annotations
import configparser
from dataclasses import dataclass

@dataclass
class N8nConfig:
    base_url: str
    ingest_path: str
    commands_path: str
    ack_path: str
    hmac_secret: str

@dataclass
class SaveConfig:
    dir: str
    backup_dir: str

@dataclass
class TachographConfig:
    n8n: N8nConfig
    save: SaveConfig
    send_interval_ms: int
    batch_size: int
    retry_max: int
    dry_run: bool
    timezone: str

def load_from_ini(path: str = "ritt.ini") -> TachographConfig:
    cp = configparser.ConfigParser()
    read_ok = cp.read(path, encoding="utf-8")
    if not read_ok:
        raise FileNotFoundError(f"Config not found: {path}")

    n8n = N8nConfig(
        base_url      = cp.get("n8n", "base_url"),
        ingest_path   = cp.get("n8n", "ingest_path", fallback="/v1/ritt/ingest"),
        commands_path = cp.get("n8n", "commands_path", fallback="/v1/ritt/commands"),
        ack_path      = cp.get("n8n", "ack_path", fallback="/v1/ritt/ack"),
        hmac_secret   = cp.get("n8n", "hmac_secret"),
    )

    save = SaveConfig(
        dir        = cp.get("save", "dir"),
        backup_dir = cp.get("save", "backup_dir"),
    )

    return TachographConfig(
        n8n=n8n,
        save=save,
        send_interval_ms = cp.getint("APP", "SEND_INTERVAL_MS", fallback=1000),
        batch_size       = cp.getint("APP", "BATCH_SIZE", fallback=50),
        retry_max        = cp.getint("APP", "RETRY_MAX", fallback=8),
        dry_run          = cp.getboolean("APP", "DRY_RUN", fallback=False),
        timezone         = cp.get("APP", "TIMEZONE", fallback="Europe/London"),
    )

# ritt/save_ops.py
from __future__ import annotations
import os, shutil, json
from typing import Tuple, Dict, Any
from datetime import datetime

def _ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def backup_file(path: str, backup_dir: str) -> str:
    os.makedirs(backup_dir, exist_ok=True)
    base = os.path.basename(path)
    out = os.path.join(backup_dir, f"{base}.{_ts()}.bak")
    shutil.copy2(path, out)
    return out

def apply_patch(save_file: str, patch: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
    """
    TODO: Zamień na realny parser SII. Na razie 'append' metadanych,
    żeby przetestować przepływ komend i ACK w n8n.
    """
    try:
        with open(save_file, "a", encoding="utf-8") as f:
            f.write(f"\n// RITT PATCH {json.dumps(patch, ensure_ascii=False)}\n")
        return True, "Patched", {"save_file": save_file, "patch": patch}
    except Exception as e:
        return False, str(e), {}

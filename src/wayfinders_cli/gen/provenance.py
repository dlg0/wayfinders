from __future__ import annotations

import datetime as _dt
import hashlib
import json
from pathlib import Path
from typing import Any


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def now_utc_iso() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).isoformat().replace("+00:00", "Z")


def write_sidecar(out_path: Path, payload: dict[str, Any]) -> None:
    sidecar = out_path.with_suffix(out_path.suffix + ".json")
    sidecar.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def append_jsonl(log_path: Path, payload: dict[str, Any]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")

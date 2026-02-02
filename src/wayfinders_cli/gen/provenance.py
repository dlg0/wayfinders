from __future__ import annotations

import datetime as _dt
import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from wayfinders_cli.gen.types import GeneratedAsset, ImageGenRequest


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


def write_asset_sidecar(asset: GeneratedAsset, request: ImageGenRequest) -> Path:
    payload = {
        "cache_key": asset.cache_key,
        "provider_id": asset.provider_id,
        "model_id": asset.model_id,
        "template_name": request.template_name,
        "resolved_prompt": request.resolved_prompt,
        "params": request.params,
        "created_at": now_utc_iso(),
        "output_hash": asset.output_hash,
    }
    write_sidecar(asset.out_path, payload)
    return asset.out_path.with_suffix(asset.out_path.suffix + ".json")


def log_generation_run(
    episode_dir: Path,
    request: ImageGenRequest,
    asset: GeneratedAsset,
    cache_hit: bool,
) -> None:
    log_path = episode_dir / "logs" / "gen_runs.jsonl"
    payload = {
        "timestamp": now_utc_iso(),
        "asset_id": request.asset_id,
        "cache_key": asset.cache_key,
        "cache_hit": cache_hit,
        "provider_id": asset.provider_id,
        "output_path": str(asset.out_path),
    }
    append_jsonl(log_path, payload)

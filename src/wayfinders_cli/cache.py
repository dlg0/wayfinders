from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from wayfinders_cli.gen.types import ImageGenRequest


def stable_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ContentHash:
    algo: str
    value: str

    def short(self, n: int = 12) -> str:
        return self.value[:n]


def hash_dict(d: dict[str, Any]) -> ContentHash:
    return ContentHash("sha256", sha256_text(stable_json(d)))


def compute_cache_key(request: ImageGenRequest) -> str:
    payload = {
        "template_name": request.template_name,
        "resolved_prompt": request.resolved_prompt,
        "params": request.params,
        "width": request.width,
        "height": request.height,
        "provider_id": request.provider_id,
        "model_id": request.model_id,
    }
    return sha256_text(stable_json(payload))


def check_cache(cache_key: str, out_path: Path) -> bool:
    if not out_path.exists():
        return False
    sidecar = out_path.with_suffix(out_path.suffix + ".json")
    if not sidecar.exists():
        return False
    try:
        data = json.loads(sidecar.read_text(encoding="utf-8"))
        return data.get("cache_key") == cache_key
    except (json.JSONDecodeError, OSError):
        return False

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass(frozen=True)
class ImageGenRequest:
    asset_type: str
    asset_id: str
    template_name: str
    resolved_prompt: str
    params: dict[str, Any]
    width: int
    height: int
    out_path: Path
    provider_id: str
    model_id: Optional[str] = None


@dataclass(frozen=True)
class GeneratedAsset:
    out_path: Path
    output_hash: str
    cache_key: str
    provider_id: str
    model_id: Optional[str]

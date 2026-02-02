from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..reproducibility import get_pipeline_version


@dataclass
class Manifest:
    version: str
    pipeline_version: str
    build_timestamp: str
    episode_id: str
    files: list[str] = field(default_factory=list)
    checksums: dict[str, str] = field(default_factory=dict)
    output_path: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


def create_manifest(
    episode_id: str,
    files: list[str],
    checksums: dict[str, str],
    output_path: Optional[Path] = None,
) -> Manifest:
    return Manifest(
        version="1.0",
        pipeline_version=get_pipeline_version(),
        build_timestamp=datetime.now(timezone.utc).isoformat(),
        episode_id=episode_id,
        files=files,
        checksums=checksums,
        output_path=str(output_path) if output_path else None,
    )

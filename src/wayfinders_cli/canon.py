from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .io import read_yaml


@dataclass(frozen=True)
class Canon:
    characters: dict[str, dict[str, Any]]
    biomes: dict[str, dict[str, Any]]
    overlays: dict[str, dict[str, Any]]
    fx: dict[str, dict[str, Any]]


def load_canon(repo_root: Path) -> Canon:
    canon_dir = repo_root / "show" / "canon"

    def by_id(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        for it in items:
            if "id" in it:
                out[it["id"]] = it
        return out

    ch = read_yaml(canon_dir / "characters.yaml").get("characters", [])
    bi = read_yaml(canon_dir / "biomes.yaml").get("biomes", [])
    ov = read_yaml(canon_dir / "overlays.yaml").get("overlays", [])
    fx = read_yaml(canon_dir / "fx.yaml").get("fx", [])

    return Canon(
        characters=by_id(ch),
        biomes=by_id(bi),
        overlays=by_id(ov),
        fx=by_id(fx),
    )

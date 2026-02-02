from __future__ import annotations

from pathlib import Path
from typing import Any

from .io import load_model
from .schema import Episode, ShotList
from .cache import hash_dict


def build_plan(episode_path: Path) -> dict[str, Any]:
    ep = load_model(Episode, episode_path)
    sl = load_model(ShotList, episode_path.parent / "shotlist.yaml")

    assets_dir = episode_path.parent / "assets"
    referenced = {"bgs": [], "chars": []}
    missing = {"bgs": [], "chars": []}

    for sh in sl.shots:
        bg_file = assets_dir / "bgs" / f"{sh.bg}.png"
        referenced["bgs"].append(str(bg_file))
        if not bg_file.exists():
            missing["bgs"].append(str(bg_file))

        for a in sh.actors:
            ch_file = assets_dir / "chars" / a.character / f"{a.pose}_{a.expression}.png"
            referenced["chars"].append(str(ch_file))
            if not ch_file.exists():
                missing["chars"].append(str(ch_file))

    payload = {
        "episode_id": ep.id,
        "episode_title": ep.title,
        "referenced": {k: sorted(set(v)) for k, v in referenced.items()},
        "missing": {k: sorted(set(v)) for k, v in missing.items()},
    }
    payload["hash"] = hash_dict(payload).value
    return payload

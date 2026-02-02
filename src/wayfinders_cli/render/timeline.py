from __future__ import annotations

import json
from pathlib import Path

from ..io import load_model
from ..schema import Episode, ShotList
from .ir import TimelineIR, ShotIR, CameraMoveIR, ActorIR, OverlayIR, AudioIR


def build_timeline_ir(episode_yaml: Path) -> TimelineIR:
    ep = load_model(Episode, episode_yaml)
    sl = load_model(ShotList, episode_yaml.parent / "shotlist.yaml")

    shots_out: list[ShotIR] = []
    for sh in sl.shots:
        frame_count = max(int(round(sh.dur_sec * ep.render.fps)), 1)
        shots_out.append(
            ShotIR(
                id=sh.id,
                dur_sec=sh.dur_sec,
                frame_count=frame_count,
                bg=sh.bg,
                camera=CameraMoveIR(**sh.camera.model_dump()),
                actors=[ActorIR(**a.model_dump()) for a in sh.actors],
                overlays=[OverlayIR(**o.model_dump()) for o in sh.overlays],
                fx=list(sh.fx),
                audio=AudioIR(**sh.audio.model_dump()),
            )
        )

    return TimelineIR(
        episode_id=ep.id,
        fps=ep.render.fps,
        resolution=ep.render.resolution,
        shots=shots_out,
    )


def write_timeline(episode_yaml: Path, out_path: Path | None = None) -> Path:
    ir = build_timeline_ir(episode_yaml)
    if out_path is None:
        out_path = episode_yaml.parent / "logs" / "timeline.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(ir.model_dump(mode="json"), indent=2), encoding="utf-8")
    return out_path


def export_timeline_jsonschema(out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    schema = TimelineIR.model_json_schema()
    out_path.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    return out_path

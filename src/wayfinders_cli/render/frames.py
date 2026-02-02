from __future__ import annotations

import json
from pathlib import Path

from .compositor import Compositor
from .ir import TimelineIR


def render_episode_frames(
    episode_yaml: Path,
    output_dir: Path | None = None,
    timeline_path: Path | None = None,
) -> list[Path]:
    ep_dir = episode_yaml.parent
    
    if timeline_path is None:
        timeline_path = ep_dir / "logs" / "timeline.json"
    
    if not timeline_path.exists():
        raise FileNotFoundError(
            f"Timeline not found: {timeline_path}. Run 'wf build-timeline' first."
        )
    
    timeline_data = json.loads(timeline_path.read_text(encoding="utf-8"))
    timeline = TimelineIR.model_validate(timeline_data)
    
    if output_dir is None:
        output_dir = ep_dir / "renders" / "frames"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    assets_dir = ep_dir / "assets"
    compositor = Compositor(assets_dir, resolution=tuple(timeline.resolution))
    
    frame_paths: list[Path] = []
    frame_num = 1
    
    for shot in timeline.shots:
        for frame_in_shot in range(shot.frame_count):
            frame = compositor.render_frame(shot, frame_in_shot)
            frame_path = output_dir / f"frame_{frame_num:06d}.png"
            frame.save(frame_path)
            frame_paths.append(frame_path)
            frame_num += 1
    
    return frame_paths


def render_frames_from_timeline(
    timeline: TimelineIR,
    assets_dir: Path,
    output_dir: Path,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    compositor = Compositor(assets_dir, resolution=tuple(timeline.resolution))
    
    frame_paths: list[Path] = []
    frame_num = 1
    
    for shot in timeline.shots:
        for frame_in_shot in range(shot.frame_count):
            frame = compositor.render_frame(shot, frame_in_shot)
            frame_path = output_dir / f"frame_{frame_num:06d}.png"
            frame.save(frame_path)
            frame_paths.append(frame_path)
            frame_num += 1
    
    return frame_paths

from __future__ import annotations

from pathlib import Path

from .timeline import build_timeline_ir, write_timeline
from .ffmpeg import frames_to_mp4, ffmpeg_exists

try:
    from PIL import Image, ImageDraw
except Exception:
    Image = None  # type: ignore
    ImageDraw = None  # type: ignore


def _require_pillow():
    if Image is None:
        raise RuntimeError(
            "Pillow required. Install: uv pip install -e '.[placeholders]'"
        )


def build_animatic_from_placeholders(episode_yaml: Path) -> Path:
    """Smoke-test animatic:
    - builds timeline.json
    - repeats BG placeholder per shot for frame_count
    - assembles mp4 if ffmpeg exists
    """
    _require_pillow()
    timeline = build_timeline_ir(episode_yaml)
    payload = timeline.model_dump(mode="json")

    fps = int(payload["fps"])
    w, h = payload["resolution"]
    ep_dir = episode_yaml.parent
    frames_dir = ep_dir / "renders" / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    bgs_dir = ep_dir / "assets" / "bgs"

    frame_idx = 1
    for sh in payload["shots"]:
        bg_path = bgs_dir / f"{sh['bg']}.png"
        if bg_path.exists():
            base = Image.open(bg_path).convert("RGBA")
        else:
            base = Image.new("RGBA", (w, h), (235, 235, 235, 255))

        for i in range(int(sh["frame_count"])):
            img = base.copy()
            d = ImageDraw.Draw(img)
            d.text((30, 30), f"{payload['episode_id']} {sh['id']} {i+1}/{sh['frame_count']}", fill=(0,0,0,255))
            out = frames_dir / f"frame_{frame_idx:06d}.png"
            img.save(out)
            frame_idx += 1

    write_timeline(episode_yaml)

    out_mp4 = ep_dir / "renders" / "animatic.mp4"
    if ffmpeg_exists():
        frames_to_mp4(frames_dir, out_mp4, fps=fps)
        return out_mp4

    note = ep_dir / "renders" / "animatic.NO_FFMPEG.txt"
    note.write_text("ffmpeg not found; frames rendered to renders/frames/", encoding="utf-8")
    return note

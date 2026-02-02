from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def ffmpeg_exists() -> bool:
    return shutil.which("ffmpeg") is not None


def frames_to_mp4(frames_dir: Path, out_mp4: Path, fps: int) -> None:
    if not ffmpeg_exists():
        raise RuntimeError("ffmpeg not found on PATH")

    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-r",
        str(fps),
        "-i",
        str(frames_dir / "frame_%06d.png"),
        "-pix_fmt",
        "yuv420p",
        "-c:v",
        "libx264",
        str(out_mp4),
    ]
    subprocess.check_call(cmd)

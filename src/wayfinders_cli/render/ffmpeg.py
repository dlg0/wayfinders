from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import List


def ffmpeg_exists() -> bool:
    """Check if ffmpeg is available (deprecated, use check_ffmpeg)."""
    return shutil.which("ffmpeg") is not None


def check_ffmpeg() -> bool:
    """Check if ffmpeg is available on PATH."""
    return shutil.which("ffmpeg") is not None


def run_ffmpeg(cmd: List[str]) -> None:
    """Run an ffmpeg command, raising subprocess errors on failure."""
    subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def frames_to_mp4(frames_dir: Path, out_mp4: Path, fps: int) -> None:
    """Legacy function for basic frame-to-MP4 assembly."""
    if not check_ffmpeg():
        raise RuntimeError("ffmpeg not found. Install with: brew install ffmpeg")

    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-framerate",
        str(fps),
        "-i",
        str(frames_dir / "frame_%06d.png"),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-crf",
        "23",
        str(out_mp4),
    ]
    run_ffmpeg(cmd)

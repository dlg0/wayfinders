from __future__ import annotations

from pathlib import Path
from typing import Optional

from .ffmpeg import check_ffmpeg, run_ffmpeg


class FFmpegNotFoundError(RuntimeError):
    """Raised when ffmpeg is not installed."""

    def __init__(self):
        super().__init__(
            "ffmpeg not found. Install with: brew install ffmpeg"
        )


class NoFramesError(RuntimeError):
    """Raised when frames directory is empty or has no frames."""

    def __init__(self, frames_dir: Path):
        super().__init__(f"No frames found in {frames_dir}")


def assemble_video(
    frames_dir: Path,
    output_path: Path,
    fps: int = 24,
    audio_path: Optional[Path] = None,
    crf: int = 23,
    codec: str = "libx264",
) -> Path:
    """Assemble frames into an MP4 video using ffmpeg.

    Args:
        frames_dir: Directory containing frame_NNNNNN.png files
        output_path: Path for the output MP4 file
        fps: Frame rate (default 24)
        audio_path: Optional audio track to add
        crf: Quality setting (0-51, lower = better, default 23)
        codec: Video codec (default libx264)

    Returns:
        Path to the output video file

    Raises:
        FFmpegNotFoundError: If ffmpeg is not installed
        NoFramesError: If no frames are found in frames_dir
    """
    if not check_ffmpeg():
        raise FFmpegNotFoundError()

    frames = sorted(frames_dir.glob("frame_*.png"))
    if not frames:
        raise NoFramesError(frames_dir)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",
        "-framerate", str(fps),
        "-i", str(frames_dir / "frame_%06d.png"),
        "-c:v", codec,
        "-pix_fmt", "yuv420p",
        "-crf", str(crf),
    ]

    if audio_path is not None:
        cmd.extend(["-i", str(audio_path), "-c:a", "aac", "-shortest"])

    cmd.append(str(output_path))

    run_ffmpeg(cmd)

    return output_path

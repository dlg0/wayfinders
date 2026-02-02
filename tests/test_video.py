from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import patch

from wayfinders_cli.render.video import (
    assemble_video,
    FFmpegNotFoundError,
    NoFramesError,
)
from wayfinders_cli.render.ffmpeg import check_ffmpeg, frames_to_mp4


class TestCheckFfmpeg:
    def test_check_ffmpeg_returns_bool(self):
        result = check_ffmpeg()
        assert isinstance(result, bool)


class TestAssembleVideo:
    def test_missing_ffmpeg_raises_helpful_error(self, tmp_path: Path):
        frames_dir = tmp_path / "frames"
        frames_dir.mkdir()
        (frames_dir / "frame_000001.png").write_bytes(b"fake")

        with patch("wayfinders_cli.render.video.check_ffmpeg", return_value=False):
            with pytest.raises(FFmpegNotFoundError) as exc_info:
                assemble_video(frames_dir, tmp_path / "out.mp4")
            assert "ffmpeg not found" in str(exc_info.value)
            assert "brew install ffmpeg" in str(exc_info.value)

    def test_empty_frames_directory_raises_error(self, tmp_path: Path):
        frames_dir = tmp_path / "frames"
        frames_dir.mkdir()

        with patch("wayfinders_cli.render.video.check_ffmpeg", return_value=True):
            with pytest.raises(NoFramesError) as exc_info:
                assemble_video(frames_dir, tmp_path / "out.mp4")
            assert "No frames found" in str(exc_info.value)

    def test_frame_rate_passed_to_ffmpeg(self, tmp_path: Path):
        frames_dir = tmp_path / "frames"
        frames_dir.mkdir()
        (frames_dir / "frame_000001.png").write_bytes(b"fake")

        with patch("wayfinders_cli.render.video.check_ffmpeg", return_value=True):
            with patch("wayfinders_cli.render.video.run_ffmpeg") as mock_run:
                assemble_video(frames_dir, tmp_path / "out.mp4", fps=30)
                mock_run.assert_called_once()
                cmd = mock_run.call_args[0][0]
                fps_idx = cmd.index("-framerate")
                assert cmd[fps_idx + 1] == "30"

    def test_assemble_creates_output_directory(self, tmp_path: Path):
        frames_dir = tmp_path / "frames"
        frames_dir.mkdir()
        (frames_dir / "frame_000001.png").write_bytes(b"fake")
        output_path = tmp_path / "nested" / "dir" / "out.mp4"

        with patch("wayfinders_cli.render.video.check_ffmpeg", return_value=True):
            with patch("wayfinders_cli.render.video.run_ffmpeg"):
                assemble_video(frames_dir, output_path, fps=24)
                assert output_path.parent.exists()

    def test_crf_quality_passed_to_ffmpeg(self, tmp_path: Path):
        frames_dir = tmp_path / "frames"
        frames_dir.mkdir()
        (frames_dir / "frame_000001.png").write_bytes(b"fake")

        with patch("wayfinders_cli.render.video.check_ffmpeg", return_value=True):
            with patch("wayfinders_cli.render.video.run_ffmpeg") as mock_run:
                assemble_video(frames_dir, tmp_path / "out.mp4", crf=18)
                cmd = mock_run.call_args[0][0]
                crf_idx = cmd.index("-crf")
                assert cmd[crf_idx + 1] == "18"

    def test_audio_path_added_when_provided(self, tmp_path: Path):
        frames_dir = tmp_path / "frames"
        frames_dir.mkdir()
        (frames_dir / "frame_000001.png").write_bytes(b"fake")
        audio_path = tmp_path / "audio.mp3"
        audio_path.write_bytes(b"fake audio")

        with patch("wayfinders_cli.render.video.check_ffmpeg", return_value=True):
            with patch("wayfinders_cli.render.video.run_ffmpeg") as mock_run:
                assemble_video(
                    frames_dir, tmp_path / "out.mp4", audio_path=audio_path
                )
                cmd = mock_run.call_args[0][0]
                assert "-c:a" in cmd
                assert "aac" in cmd


class TestFramesToMp4Legacy:
    def test_missing_ffmpeg_raises_error(self, tmp_path: Path):
        with patch("wayfinders_cli.render.ffmpeg.check_ffmpeg", return_value=False):
            with pytest.raises(RuntimeError) as exc_info:
                frames_to_mp4(tmp_path, tmp_path / "out.mp4", fps=24)
            assert "ffmpeg not found" in str(exc_info.value)


@pytest.mark.skipif(not check_ffmpeg(), reason="ffmpeg not installed")
class TestIntegrationWithRealFfmpeg:
    def test_assemble_real_frames(self, tmp_path: Path):
        try:
            from PIL import Image
        except ImportError:
            pytest.skip("Pillow not installed")

        frames_dir = tmp_path / "frames"
        frames_dir.mkdir()

        for i in range(1, 25):
            img = Image.new("RGB", (320, 240), color=(i * 10, 100, 100))
            img.save(frames_dir / f"frame_{i:06d}.png")

        output = tmp_path / "test.mp4"
        result = assemble_video(frames_dir, output, fps=24)

        assert result == output
        assert output.exists()
        assert output.stat().st_size > 0

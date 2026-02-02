from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PIL", reason="Pillow required for compositor tests")

from PIL import Image

from wayfinders_cli.render.compositor import Compositor, MissingAssetError
from wayfinders_cli.render.ir import (
    ShotIR,
    ActorIR,
    CameraMoveIR,
    OverlayIR,
    TimelineIR,
)
from wayfinders_cli.render.frames import render_frames_from_timeline


def _create_test_bg(assets_dir: Path, bg_id: str, resolution: tuple[int, int]) -> Path:
    bg_dir = assets_dir / "bg"
    bg_dir.mkdir(parents=True, exist_ok=True)
    bg_path = bg_dir / f"{bg_id}.png"
    img = Image.new("RGBA", resolution, (100, 150, 200, 255))
    img.save(bg_path)
    return bg_path


def _create_test_cutout(
    assets_dir: Path,
    character: str,
    pose: str,
    size: tuple[int, int] = (200, 400),
    color: tuple[int, int, int, int] = (255, 100, 100, 200),
) -> Path:
    cutouts_dir = assets_dir / "cutouts"
    cutouts_dir.mkdir(parents=True, exist_ok=True)
    cutout_path = cutouts_dir / f"{character}_{pose}.png"
    img = Image.new("RGBA", size, color)
    img.save(cutout_path)
    return cutout_path


class TestCompositorSingleFrame:
    def test_render_bg_only(self, tmp_path: Path) -> None:
        assets_dir = tmp_path / "assets"
        resolution = (1920, 1080)
        _create_test_bg(assets_dir, "bg_test", resolution)

        compositor = Compositor(assets_dir, resolution)
        shot = ShotIR(
            id="S01",
            dur_sec=1.0,
            frame_count=24,
            bg="bg_test",
        )

        frame = compositor.render_frame(shot, frame_in_shot=0)

        assert frame.size == resolution
        assert frame.mode == "RGBA"
        pixel = frame.getpixel((100, 100))
        assert pixel == (100, 150, 200, 255)

    def test_render_bg_with_one_actor(self, tmp_path: Path) -> None:
        assets_dir = tmp_path / "assets"
        resolution = (1920, 1080)
        _create_test_bg(assets_dir, "bg_test", resolution)
        _create_test_cutout(assets_dir, "charlie", "idle", color=(255, 0, 0, 255))

        compositor = Compositor(assets_dir, resolution)
        shot = ShotIR(
            id="S01",
            dur_sec=1.0,
            frame_count=24,
            bg="bg_test",
            actors=[ActorIR(character="charlie", pose="idle", expression="neutral")],
        )

        frame = compositor.render_frame(shot)

        assert frame.size == resolution
        center_x, center_y = resolution[0] // 2, int(resolution[1] * 0.7)
        pixel = frame.getpixel((center_x, center_y - 100))
        assert pixel[0] == 255


class TestCompositorMultipleActors:
    def test_render_two_actors_z_order(self, tmp_path: Path) -> None:
        assets_dir = tmp_path / "assets"
        resolution = (1920, 1080)
        _create_test_bg(assets_dir, "bg_test", resolution)
        _create_test_cutout(assets_dir, "charlie", "idle", color=(255, 0, 0, 255))
        _create_test_cutout(assets_dir, "spencer", "run_loop", color=(0, 255, 0, 255))

        compositor = Compositor(assets_dir, resolution)
        shot = ShotIR(
            id="S01",
            dur_sec=1.0,
            frame_count=24,
            bg="bg_test",
            actors=[
                ActorIR(character="charlie", pose="idle", expression="neutral"),
                ActorIR(character="spencer", pose="run_loop", expression="excited"),
            ],
        )

        frame = compositor.render_frame(shot)
        assert frame.size == resolution


class TestCameraTransforms:
    def test_camera_pan(self, tmp_path: Path) -> None:
        assets_dir = tmp_path / "assets"
        resolution = (1920, 1080)
        _create_test_bg(assets_dir, "bg_test", resolution)

        compositor = Compositor(assets_dir, resolution)
        shot_no_pan = ShotIR(
            id="S01",
            dur_sec=1.0,
            frame_count=24,
            bg="bg_test",
            camera=CameraMoveIR(move="none"),
        )
        shot_with_pan = ShotIR(
            id="S02",
            dur_sec=1.0,
            frame_count=24,
            bg="bg_test",
            camera=CameraMoveIR(move="pan", x0=0.0, x1=0.1, y0=0.0, y1=0.0),
        )

        frame_no_pan = compositor.render_frame(shot_no_pan, frame_in_shot=0)
        frame_with_pan_start = compositor.render_frame(shot_with_pan, frame_in_shot=0)
        frame_with_pan_end = compositor.render_frame(shot_with_pan, frame_in_shot=23)

        assert frame_no_pan.size == resolution
        assert frame_with_pan_start.size == resolution
        assert frame_with_pan_end.size == resolution

    def test_camera_zoom(self, tmp_path: Path) -> None:
        assets_dir = tmp_path / "assets"
        resolution = (1920, 1080)
        _create_test_bg(assets_dir, "bg_test", resolution)

        compositor = Compositor(assets_dir, resolution)
        shot = ShotIR(
            id="S01",
            dur_sec=1.0,
            frame_count=24,
            bg="bg_test",
            camera=CameraMoveIR(move="slowpush", z0=1.0, z1=1.2),
        )

        frame_start = compositor.render_frame(shot, frame_in_shot=0)
        frame_end = compositor.render_frame(shot, frame_in_shot=23)

        assert frame_start.size == resolution
        assert frame_end.size == resolution


class TestMissingAssets:
    def test_missing_bg_produces_error(self, tmp_path: Path) -> None:
        assets_dir = tmp_path / "assets"
        assets_dir.mkdir(parents=True)
        (assets_dir / "bg").mkdir()
        resolution = (1920, 1080)

        compositor = Compositor(assets_dir, resolution)
        shot = ShotIR(
            id="S01",
            dur_sec=1.0,
            frame_count=24,
            bg="bg_nonexistent",
        )

        with pytest.raises(MissingAssetError) as exc_info:
            compositor.render_frame(shot)

        assert "bg_nonexistent" in str(exc_info.value)
        assert exc_info.value.asset_type == "background"

    def test_missing_cutout_produces_error(self, tmp_path: Path) -> None:
        assets_dir = tmp_path / "assets"
        resolution = (1920, 1080)
        _create_test_bg(assets_dir, "bg_test", resolution)
        (assets_dir / "cutouts").mkdir(parents=True)

        compositor = Compositor(assets_dir, resolution)
        shot = ShotIR(
            id="S01",
            dur_sec=1.0,
            frame_count=24,
            bg="bg_test",
            actors=[ActorIR(character="missing", pose="char", expression="neutral")],
        )

        with pytest.raises(MissingAssetError) as exc_info:
            compositor.render_frame(shot)

        assert "missing_char" in str(exc_info.value)
        assert exc_info.value.asset_type == "cutout"


class TestFrameRenderer:
    def test_render_frames_from_timeline(self, tmp_path: Path) -> None:
        assets_dir = tmp_path / "assets"
        output_dir = tmp_path / "renders" / "frames"
        resolution = (1920, 1080)
        _create_test_bg(assets_dir, "bg_test", resolution)
        _create_test_cutout(assets_dir, "charlie", "idle")

        timeline = TimelineIR(
            episode_id="test_ep",
            fps=24,
            resolution=resolution,
            shots=[
                ShotIR(
                    id="S01",
                    dur_sec=0.25,
                    frame_count=6,
                    bg="bg_test",
                    actors=[ActorIR(character="charlie", pose="idle", expression="neutral")],
                ),
                ShotIR(
                    id="S02",
                    dur_sec=0.25,
                    frame_count=6,
                    bg="bg_test",
                ),
            ],
        )

        frame_paths = render_frames_from_timeline(timeline, assets_dir, output_dir)

        assert len(frame_paths) == 12
        assert all(p.exists() for p in frame_paths)
        assert frame_paths[0].name == "frame_000001.png"
        assert frame_paths[-1].name == "frame_000012.png"


class TestActorPositioning:
    def test_explicit_position(self, tmp_path: Path) -> None:
        assets_dir = tmp_path / "assets"
        resolution = (1920, 1080)
        _create_test_bg(assets_dir, "bg_test", resolution)
        _create_test_cutout(assets_dir, "charlie", "idle", color=(255, 0, 0, 255))

        compositor = Compositor(assets_dir, resolution)
        shot = ShotIR(
            id="S01",
            dur_sec=1.0,
            frame_count=24,
            bg="bg_test",
            actors=[
                ActorIR(
                    character="charlie",
                    pose="idle",
                    expression="neutral",
                    x=0.25,
                    y=0.6,
                    scale=0.3,
                )
            ],
        )

        frame = compositor.render_frame(shot)
        assert frame.size == resolution


class TestOverlays:
    def test_text_overlay(self, tmp_path: Path) -> None:
        assets_dir = tmp_path / "assets"
        resolution = (1920, 1080)
        _create_test_bg(assets_dir, "bg_test", resolution)

        compositor = Compositor(assets_dir, resolution)
        shot = ShotIR(
            id="S01",
            dur_sec=1.0,
            frame_count=24,
            bg="bg_test",
            overlays=[OverlayIR(id="title", text="TEST OVERLAY", x=0.5, y=0.5)],
        )

        frame = compositor.render_frame(shot)
        assert frame.size == resolution

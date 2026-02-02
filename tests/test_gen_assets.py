from __future__ import annotations

import json
from pathlib import Path

import pytest

from wayfinders_cli.gen.generate import (
    GenerationResult,
    discover_assets,
    generate_episode_assets,
)


def _create_minimal_episode(tmp_path: Path) -> Path:
    """Create a minimal episode structure for testing."""
    ep_dir = tmp_path / "episodes" / "s01e01_test"
    ep_dir.mkdir(parents=True)
    (ep_dir / "assets").mkdir()
    (ep_dir / "logs").mkdir()
    (ep_dir / "renders").mkdir()

    (ep_dir / "episode.yaml").write_text(
        """
id: "s01e01"
title: "Test Episode"
runtime_target_sec: 780
biome: "windglass_plains"
cast: [charlie, spencer]
style_profile: "comic_low_fps_v1"
render:
  fps: 24
  resolution: [1920, 1080]
assets:
  pose_packs: []
  bg_pack: "test_v1"
  overlay_pack: "overlays_v1"
""".strip(),
        encoding="utf-8",
    )

    (ep_dir / "shotlist.yaml").write_text(
        """
version: 1
shots:
  - id: S01
    dur_sec: 5
    bg: bg_test_forest
    camera: { move: none }
    actors:
      - { character: charlie, pose: idle, expression: neutral }
    overlays: []
    fx: []
    audio: { dialogue: [], sfx: [] }

  - id: S02
    dur_sec: 5
    bg: bg_test_forest
    camera: { move: pan }
    actors:
      - { character: spencer, pose: run_loop, expression: excited }
      - { character: charlie, pose: idle, expression: neutral }
    overlays: []
    fx: []
    audio: { dialogue: [], sfx: [] }

  - id: S03
    dur_sec: 5
    bg: bg_test_mountain
    camera: { move: none }
    actors: []
    overlays: []
    fx: []
    audio: { dialogue: [], sfx: [] }
""".strip(),
        encoding="utf-8",
    )

    return ep_dir / "episode.yaml"


def _create_show_structure(tmp_path: Path) -> Path:
    """Create the show directory with prompts and canon."""
    show_dir = tmp_path / "show"
    show_dir.mkdir()

    (show_dir / "prompts").mkdir()
    (show_dir / "prompts" / "background.j2").write_text(
        """Background prompt for {{ biome_label }} ({{ biome_id }}).
Style: {{ style_profile }}
""",
        encoding="utf-8",
    )
    (show_dir / "prompts" / "cutout.j2").write_text(
        """Cutout prompt for {{ character_label }} ({{ character_id }}).
Pose: {{ pose_id }}
Expression: {{ expression_id }}
Style: {{ style_profile }}
""",
        encoding="utf-8",
    )

    (show_dir / "canon").mkdir()
    (show_dir / "canon" / "characters.yaml").write_text(
        """
version: 1
characters:
  - id: charlie
    label: Charlie
    role: planner_builder
    pose_pack: posepack_charlie_v1
  - id: spencer
    label: Spencer
    role: sprinter_wildcard
    pose_pack: posepack_spencer_v1
""".strip(),
        encoding="utf-8",
    )
    (show_dir / "canon" / "biomes.yaml").write_text(
        """
version: 1
biomes:
  - id: windglass_plains
    label: Windglass Plains
  - id: test_forest
    label: Test Forest
""".strip(),
        encoding="utf-8",
    )

    return show_dir


def _create_config_file(tmp_path: Path, provider: str = "placeholder") -> Path:
    """Create a wf.toml config file."""
    config_path = tmp_path / "wf.toml"
    config_path.write_text(
        f"""
default_provider = "{provider}"

[providers.placeholder]
""".strip(),
        encoding="utf-8",
    )
    return config_path


@pytest.fixture
def setup_episode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Set up a complete episode structure and change to that directory."""
    episode_yaml = _create_minimal_episode(tmp_path)
    _create_show_structure(tmp_path)
    _create_config_file(tmp_path)
    monkeypatch.chdir(tmp_path)
    return episode_yaml


class TestDiscoverAssets:
    def test_discovers_backgrounds_from_shotlist(self, tmp_path: Path) -> None:
        episode_yaml = _create_minimal_episode(tmp_path)
        show_dir = _create_show_structure(tmp_path)

        assets = discover_assets(episode_yaml, show_dir)

        bg_assets = [a for a in assets if a.asset_type == "background"]
        assert len(bg_assets) == 2
        bg_ids = {a.asset_id for a in bg_assets}
        assert bg_ids == {"bg_test_forest", "bg_test_mountain"}

    def test_discovers_cutouts_from_shotlist(self, tmp_path: Path) -> None:
        episode_yaml = _create_minimal_episode(tmp_path)
        show_dir = _create_show_structure(tmp_path)

        assets = discover_assets(episode_yaml, show_dir)

        cutout_assets = [a for a in assets if a.asset_type == "cutout"]
        assert len(cutout_assets) == 2
        cutout_ids = {a.asset_id for a in cutout_assets}
        assert cutout_ids == {"charlie_idle", "spencer_run_loop"}

    def test_deduplicates_assets(self, tmp_path: Path) -> None:
        episode_yaml = _create_minimal_episode(tmp_path)
        show_dir = _create_show_structure(tmp_path)

        assets = discover_assets(episode_yaml, show_dir)

        asset_ids = [a.asset_id for a in assets]
        assert len(asset_ids) == len(set(asset_ids))

    def test_correct_output_paths(self, tmp_path: Path) -> None:
        episode_yaml = _create_minimal_episode(tmp_path)
        show_dir = _create_show_structure(tmp_path)

        assets = discover_assets(episode_yaml, show_dir)

        for asset in assets:
            if asset.asset_type == "background":
                assert "assets/bg" in str(asset.out_path)
                assert asset.out_path.suffix == ".png"
            elif asset.asset_type == "cutout":
                assert "assets/cutouts" in str(asset.out_path)
                assert asset.out_path.suffix == ".png"


class TestGenerateEpisodeAssets:
    def test_generates_all_assets(self, setup_episode: Path) -> None:
        result = generate_episode_assets(setup_episode)

        assert len(result.generated) == 4
        assert len(result.skipped) == 0
        assert len(result.errors) == 0

        ep_dir = setup_episode.parent
        assert (ep_dir / "assets" / "bg" / "bg_test_forest.png").exists()
        assert (ep_dir / "assets" / "bg" / "bg_test_mountain.png").exists()
        assert (ep_dir / "assets" / "cutouts" / "charlie_idle.png").exists()
        assert (ep_dir / "assets" / "cutouts" / "spencer_run_loop.png").exists()

    def test_creates_sidecar_files(self, setup_episode: Path) -> None:
        generate_episode_assets(setup_episode)

        ep_dir = setup_episode.parent
        sidecar_path = ep_dir / "assets" / "bg" / "bg_test_forest.png.json"
        assert sidecar_path.exists()

        sidecar = json.loads(sidecar_path.read_text())
        assert sidecar["asset_id"] == "bg_test_forest"
        assert sidecar["asset_type"] == "background"
        assert "cache_key" in sidecar
        assert "output_hash" in sidecar
        assert "provider_id" in sidecar

    def test_skips_cached_assets(self, setup_episode: Path) -> None:
        result1 = generate_episode_assets(setup_episode)
        assert len(result1.generated) == 4
        assert len(result1.skipped) == 0

        result2 = generate_episode_assets(setup_episode)
        assert len(result2.generated) == 0
        assert len(result2.skipped) == 4

    def test_force_regenerates_all(self, setup_episode: Path) -> None:
        result1 = generate_episode_assets(setup_episode)
        assert len(result1.generated) == 4

        result2 = generate_episode_assets(setup_episode, force=True)
        assert len(result2.generated) == 4
        assert len(result2.skipped) == 0

    def test_logs_generation_events(self, setup_episode: Path) -> None:
        generate_episode_assets(setup_episode)

        ep_dir = setup_episode.parent
        gen_log = ep_dir / "logs" / "gen.jsonl"
        assert gen_log.exists()

        lines = gen_log.read_text().strip().split("\n")
        assert len(lines) == 4

        for line in lines:
            entry = json.loads(line)
            assert entry["event"] == "asset_generated"
            assert "asset_id" in entry
            assert "cache_key" in entry
            assert "timestamp" in entry

    def test_logs_resolved_prompts(self, setup_episode: Path) -> None:
        generate_episode_assets(setup_episode)

        ep_dir = setup_episode.parent
        prompts_dir = ep_dir / "logs" / "prompts"
        assert prompts_dir.exists()

        prompt_files = list(prompts_dir.glob("*.json"))
        assert len(prompt_files) == 4

    def test_invalid_provider_produces_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        episode_yaml = _create_minimal_episode(tmp_path)
        _create_show_structure(tmp_path)
        _create_config_file(tmp_path)
        monkeypatch.chdir(tmp_path)

        result = generate_episode_assets(episode_yaml, provider_override="nonexistent")

        assert len(result.errors) > 0
        assert any("nonexistent" in err[1] for err in result.errors)


class TestGenerationResult:
    def test_dataclass_defaults(self) -> None:
        result = GenerationResult()
        assert result.generated == []
        assert result.skipped == []
        assert result.errors == []

    def test_dataclass_with_values(self) -> None:
        result = GenerationResult(
            generated=["a", "b"],
            skipped=["c"],
            errors=[("d", "error message")],
        )
        assert len(result.generated) == 2
        assert len(result.skipped) == 1
        assert len(result.errors) == 1

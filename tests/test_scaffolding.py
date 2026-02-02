"""Tests for episode scaffolding module."""

from __future__ import annotations

import pytest
from pathlib import Path

from wayfinders_cli.scaffolding import render_episode_scaffold, ScaffoldResult


@pytest.fixture
def sample_params() -> dict:
    """Sample scaffold parameters."""
    return {
        "ep_id": "s01e05",
        "title": "The Lost Compass",
        "biome": "windglass_plains",
        "runtime_target_sec": 780,
        "cast": ["charlie", "spencer", "fletcher", "fold"],
    }


class TestRenderEpisodeScaffold:
    """Tests for render_episode_scaffold function."""

    def test_creates_all_expected_files(self, tmp_path: Path, sample_params: dict):
        """Scaffold generation creates all expected files."""
        ep_dir = tmp_path / "episodes" / "s01e05_the_lost_compass"

        result = render_episode_scaffold(ep_dir=ep_dir, **sample_params)

        assert isinstance(result, ScaffoldResult)
        assert result.ep_dir == ep_dir
        assert "episode.yaml" in result.files_created
        assert "shotlist.yaml" in result.files_created
        assert "README.md" in result.files_created
        assert (ep_dir / "episode.yaml").exists()
        assert (ep_dir / "shotlist.yaml").exists()
        assert (ep_dir / "README.md").exists()

    def test_creates_directory_structure(self, tmp_path: Path, sample_params: dict):
        """Scaffold creates assets, renders, logs directories."""
        ep_dir = tmp_path / "episodes" / "s01e05_test"

        render_episode_scaffold(ep_dir=ep_dir, **sample_params)

        assert (ep_dir / "assets").is_dir()
        assert (ep_dir / "renders").is_dir()
        assert (ep_dir / "logs").is_dir()
        assert (ep_dir / "assets" / ".keep").exists()
        assert (ep_dir / "renders" / ".keep").exists()
        assert (ep_dir / "logs" / ".keep").exists()

    def test_generated_files_pass_schema_validation(self, tmp_path: Path, sample_params: dict):
        """Generated files pass Episode and ShotList schema validation."""
        import yaml
        from wayfinders_cli.schema import Episode, ShotList

        ep_dir = tmp_path / "episodes" / "s01e05_test"

        render_episode_scaffold(ep_dir=ep_dir, **sample_params)

        episode_data = yaml.safe_load((ep_dir / "episode.yaml").read_text())
        episode = Episode(**episode_data)
        assert episode.id == "s01e05"

        shotlist_data = yaml.safe_load((ep_dir / "shotlist.yaml").read_text())
        shotlist = ShotList(**shotlist_data)
        assert shotlist.version == 1

    def test_existing_episode_without_force_raises_error(
        self, tmp_path: Path, sample_params: dict
    ):
        """Existing episode without --force raises FileExistsError."""
        ep_dir = tmp_path / "episodes" / "s01e05_test"
        ep_dir.mkdir(parents=True)

        with pytest.raises(FileExistsError) as exc_info:
            render_episode_scaffold(ep_dir=ep_dir, **sample_params)

        assert "already exists" in str(exc_info.value)

    def test_force_overwrites_existing_episode(self, tmp_path: Path, sample_params: dict):
        """--force overwrites existing episode."""
        ep_dir = tmp_path / "episodes" / "s01e05_test"

        render_episode_scaffold(ep_dir=ep_dir, **sample_params)
        old_content = (ep_dir / "episode.yaml").read_text()

        new_params = {**sample_params, "title": "Updated Title"}
        result = render_episode_scaffold(ep_dir=ep_dir, **new_params, force=True)

        new_content = (ep_dir / "episode.yaml").read_text()
        assert result.ep_dir == ep_dir
        assert "Updated Title" in new_content
        assert old_content != new_content

    def test_episode_yaml_content(self, tmp_path: Path, sample_params: dict):
        """Episode YAML contains correct values."""
        ep_dir = tmp_path / "episodes" / "s01e05_test"

        render_episode_scaffold(ep_dir=ep_dir, **sample_params)

        import yaml

        content = yaml.safe_load((ep_dir / "episode.yaml").read_text())
        assert content["id"] == "s01e05"
        assert content["title"] == "The Lost Compass"
        assert content["biome"] == "windglass_plains"
        assert content["runtime_target_sec"] == 780
        assert content["cast"] == ["charlie", "spencer", "fletcher", "fold"]

    def test_shotlist_yaml_content(self, tmp_path: Path, sample_params: dict):
        """Shotlist YAML contains shots."""
        ep_dir = tmp_path / "episodes" / "s01e05_test"

        render_episode_scaffold(ep_dir=ep_dir, **sample_params)

        import yaml

        content = yaml.safe_load((ep_dir / "shotlist.yaml").read_text())
        assert content["version"] == 1
        assert len(content["shots"]) >= 1

    def test_readme_content(self, tmp_path: Path, sample_params: dict):
        """README.md contains expected content."""
        ep_dir = tmp_path / "episodes" / "s01e05_test"

        render_episode_scaffold(ep_dir=ep_dir, **sample_params)

        content = (ep_dir / "README.md").read_text()
        assert "s01e05 - The Lost Compass" in content
        assert "windglass_plains" in content
        assert "780 seconds" in content
        for char in sample_params["cast"]:
            assert char in content

    def test_custom_style_profile(self, tmp_path: Path, sample_params: dict):
        """Custom style profile is used in generated files."""
        ep_dir = tmp_path / "episodes" / "s01e05_test"

        render_episode_scaffold(
            ep_dir=ep_dir, **sample_params, style_profile="custom_style_v2"
        )

        import yaml

        content = yaml.safe_load((ep_dir / "episode.yaml").read_text())
        assert content["style_profile"] == "custom_style_v2"

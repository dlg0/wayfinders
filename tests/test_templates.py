"""Tests for episode scaffolding Jinja templates."""

from __future__ import annotations

import yaml
from jinja2 import Environment, PackageLoader, StrictUndefined, UndefinedError
import pytest

from wayfinders_cli.schema import Episode, ShotList


@pytest.fixture
def template_env() -> Environment:
    """Create Jinja environment with StrictUndefined."""
    return Environment(
        loader=PackageLoader("wayfinders_cli", "templates"),
        undefined=StrictUndefined,
    )


@pytest.fixture
def sample_params() -> dict:
    """Sample template parameters."""
    return {
        "ep_id": "s01e05",
        "title": "The Lost Compass",
        "biome": "windglass_plains",
        "runtime_target_sec": 780,
        "cast": ["charlie", "spencer", "fletcher", "fold"],
        "style_profile": "comic_low_fps_v1",
    }


class TestEpisodeTemplate:
    """Tests for episode.yaml.j2 template."""

    def test_renders_valid_yaml(self, template_env: Environment, sample_params: dict):
        """Rendered episode.yaml is valid YAML."""
        template = template_env.get_template("episode.yaml.j2")
        content = template.render(**sample_params)
        data = yaml.safe_load(content)
        assert data["id"] == "s01e05"
        assert data["title"] == "The Lost Compass"

    def test_passes_schema_validation(self, template_env: Environment, sample_params: dict):
        """Rendered episode.yaml passes Episode schema validation."""
        template = template_env.get_template("episode.yaml.j2")
        content = template.render(**sample_params)
        data = yaml.safe_load(content)
        episode = Episode(**data)
        assert episode.id == "s01e05"
        assert episode.runtime_target_sec == 780
        assert episode.cast == ["charlie", "spencer", "fletcher", "fold"]

    def test_generates_pose_packs_for_cast(self, template_env: Environment, sample_params: dict):
        """Pose packs are generated for each cast member."""
        template = template_env.get_template("episode.yaml.j2")
        content = template.render(**sample_params)
        data = yaml.safe_load(content)
        assert data["assets"]["pose_packs"] == [
            "posepack_charlie_v1",
            "posepack_spencer_v1",
            "posepack_fletcher_v1",
            "posepack_fold_v1",
        ]

    def test_bg_pack_matches_biome(self, template_env: Environment, sample_params: dict):
        """Background pack is derived from biome."""
        params = {**sample_params, "biome": "crystal_caves"}
        template = template_env.get_template("episode.yaml.j2")
        content = template.render(**params)
        data = yaml.safe_load(content)
        assert data["assets"]["bg_pack"] == "crystal_caves_v1"

    def test_strict_undefined_raises(self, template_env: Environment):
        """Missing parameters raise UndefinedError."""
        template = template_env.get_template("episode.yaml.j2")
        with pytest.raises(UndefinedError):
            template.render(ep_id="s01e01")  # Missing other required params


class TestShotlistTemplate:
    """Tests for shotlist.yaml.j2 template."""

    def test_renders_valid_yaml(self, template_env: Environment, sample_params: dict):
        """Rendered shotlist.yaml is valid YAML."""
        template = template_env.get_template("shotlist.yaml.j2")
        content = template.render(**sample_params)
        data = yaml.safe_load(content)
        assert data["version"] == 1
        assert len(data["shots"]) == 2

    def test_passes_schema_validation(self, template_env: Environment, sample_params: dict):
        """Rendered shotlist.yaml passes ShotList schema validation."""
        template = template_env.get_template("shotlist.yaml.j2")
        content = template.render(**sample_params)
        data = yaml.safe_load(content)
        shotlist = ShotList(**data)
        assert shotlist.version == 1
        assert len(shotlist.shots) == 2

    def test_background_uses_biome(self, template_env: Environment, sample_params: dict):
        """Shot backgrounds use the provided biome."""
        params = {**sample_params, "biome": "misty_forest"}
        template = template_env.get_template("shotlist.yaml.j2")
        content = template.render(**params)
        data = yaml.safe_load(content)
        assert data["shots"][0]["bg"] == "bg_misty_forest_day"

    def test_first_cast_member_in_shot(self, template_env: Environment, sample_params: dict):
        """Second shot features the first cast member."""
        template = template_env.get_template("shotlist.yaml.j2")
        content = template.render(**sample_params)
        data = yaml.safe_load(content)
        assert data["shots"][1]["actors"][0]["character"] == "charlie"


class TestReadmeTemplate:
    """Tests for README.md.j2 template."""

    def test_renders_markdown(self, template_env: Environment, sample_params: dict):
        """Rendered README.md contains expected content."""
        template = template_env.get_template("README.md.j2")
        content = template.render(**sample_params)
        assert "# s01e05 - The Lost Compass" in content
        assert "windglass_plains" in content
        assert "780 seconds" in content

    def test_lists_all_cast(self, template_env: Environment, sample_params: dict):
        """README lists all cast members."""
        template = template_env.get_template("README.md.j2")
        content = template.render(**sample_params)
        for char in sample_params["cast"]:
            assert f"- {char}" in content

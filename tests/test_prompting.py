from __future__ import annotations

import json
from pathlib import Path

import pytest

from wayfinders_cli.gen.prompting import (
    PromptResolutionError,
    PromptResolver,
    ResolvedPrompt,
    log_resolved_prompt,
)


@pytest.fixture
def prompts_dir() -> Path:
    return Path("show/prompts")


@pytest.fixture
def resolver(prompts_dir: Path) -> PromptResolver:
    return PromptResolver(prompts_dir)


class TestPromptResolver:
    def test_resolve_background_prompt_successfully(self, resolver: PromptResolver) -> None:
        params = {
            "biome_label": "Windglass Plains",
            "biome_id": "windglass_plains",
            "style_profile": "cel-shaded adventure",
            "time_of_day": "sunset",
            "mood": "adventurous",
            "camera_desc": "wide establishing shot",
        }
        result = resolver.resolve("background.j2", params)

        assert isinstance(result, ResolvedPrompt)
        assert result.template_name == "background.j2"
        assert result.params == params
        assert "Windglass Plains" in result.resolved_text
        assert "windglass_plains" in result.resolved_text
        assert "cel-shaded adventure" in result.resolved_text
        assert "sunset" in result.resolved_text
        assert "adventurous" in result.resolved_text

    def test_resolve_cutout_prompt_successfully(self, resolver: PromptResolver) -> None:
        params = {
            "character_label": "Charlie",
            "character_id": "charlie",
            "style_profile": "cel-shaded adventure",
            "pose_id": "pose_stand",
            "expression_id": "expr_happy",
            "character_role": "planner_builder",
        }
        result = resolver.resolve("cutout.j2", params)

        assert isinstance(result, ResolvedPrompt)
        assert result.template_name == "cutout.j2"
        assert "Charlie" in result.resolved_text
        assert "charlie" in result.resolved_text
        assert "planner_builder" in result.resolved_text

    def test_missing_variable_raises_clear_error(self, resolver: PromptResolver) -> None:
        params = {
            "biome_label": "Windglass Plains",
            # Missing: biome_id, style_profile (required)
        }
        with pytest.raises(PromptResolutionError) as exc_info:
            resolver.resolve("background.j2", params)

        error_msg = str(exc_info.value)
        assert "Undefined variable" in error_msg
        assert "background.j2" in error_msg

    def test_missing_template_raises_clear_error(self, resolver: PromptResolver) -> None:
        with pytest.raises(PromptResolutionError) as exc_info:
            resolver.resolve("nonexistent.j2", {})

        error_msg = str(exc_info.value)
        assert "not found" in error_msg
        assert "nonexistent.j2" in error_msg

    def test_optional_variables_omitted(self, resolver: PromptResolver) -> None:
        params = {
            "biome_label": "Inkwood",
            "biome_id": "inkwood",
            "style_profile": "painterly",
        }
        result = resolver.resolve("background.j2", params)

        assert "Inkwood" in result.resolved_text
        assert "Time of day:" not in result.resolved_text
        assert "Mood:" not in result.resolved_text


class TestLogResolvedPrompt:
    def test_creates_correct_log_file(self, tmp_path: Path, resolver: PromptResolver) -> None:
        episode_dir = tmp_path / "episodes" / "s01e01_test"
        episode_dir.mkdir(parents=True)

        params = {
            "biome_label": "Saffron Dunes",
            "biome_id": "saffron_dunes",
            "style_profile": "cel-shaded",
        }
        resolved = resolver.resolve("background.j2", params)
        asset_id = "bg_shot01_saffron_dunes"

        log_path = log_resolved_prompt(episode_dir, asset_id, resolved)

        assert log_path.exists()
        assert log_path == episode_dir / "logs" / "prompts" / f"{asset_id}.json"

    def test_logged_prompt_contains_all_required_fields(
        self, tmp_path: Path, resolver: PromptResolver
    ) -> None:
        episode_dir = tmp_path / "episodes" / "s01e01_test"
        episode_dir.mkdir(parents=True)

        params = {
            "character_label": "Spencer",
            "character_id": "spencer",
            "style_profile": "adventure",
            "pose_id": "pose_run",
        }
        resolved = resolver.resolve("cutout.j2", params)
        asset_id = "cutout_spencer_run"

        log_path = log_resolved_prompt(episode_dir, asset_id, resolved)
        logged = json.loads(log_path.read_text())

        assert logged["asset_id"] == asset_id
        assert logged["template_name"] == "cutout.j2"
        assert logged["params"] == params
        assert "Spencer" in logged["resolved_prompt"]
        assert "timestamp" in logged
        assert logged["timestamp"].endswith("Z")

    def test_creates_prompts_directory_if_missing(
        self, tmp_path: Path, resolver: PromptResolver
    ) -> None:
        episode_dir = tmp_path / "episodes" / "s01e02_new"
        episode_dir.mkdir(parents=True)

        params = {
            "biome_label": "Moss-Clock Ruins",
            "biome_id": "moss_clock_ruins",
            "style_profile": "painterly",
        }
        resolved = resolver.resolve("background.j2", params)

        log_path = log_resolved_prompt(episode_dir, "bg_test", resolved)

        assert log_path.exists()
        assert (episode_dir / "logs" / "prompts").is_dir()

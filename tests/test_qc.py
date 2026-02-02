from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from wayfinders_cli.qc.checker import QCChecker, QCResult, QCContext
from wayfinders_cli.qc.rules import (
    Rule,
    RuleResult,
    DialogueLanguageCheck,
    RuntimeBoundsCheck,
    AssetCoverageCheck,
    CharacterConsistencyCheck,
    KidsContentCheck,
    IPChecklistReminder,
)
from wayfinders_cli.qc.report import (
    generate_qc_report,
    generate_cost_report,
    _qc_result_to_dict,
)
from wayfinders_cli.schema import Episode, ShotList, Shot, AudioRef, ActorRef


EXAMPLE_EP = Path("episodes/s01e01_map_forgot_roads/episode.yaml")


@pytest.fixture
def sample_episode() -> Episode:
    return Episode(
        id="s01e01",
        title="Test Episode",
        runtime_target_sec=780,
        biome="windglass_plains",
        cast=["charlie", "spencer", "fletcher", "fold"],
        style_profile="comic_low_fps_v1",
        assets={
            "pose_packs": ["posepack_charlie_v1"],
            "bg_pack": "windglass_v1",
            "overlay_pack": "overlays_v1",
        },
        notes={
            "rule_of_day": "Test rule",
            "logline": "Test logline",
        },
    )


@pytest.fixture
def sample_shotlist() -> ShotList:
    return ShotList(
        version=1,
        shots=[
            Shot(
                id="S01",
                dur_sec=5.0,
                bg="bg_test",
                audio=AudioRef(dialogue=["Spencer: Hello!"], sfx=["wind"]),
                actors=[ActorRef(character="spencer", pose="idle", expression="neutral")],
            ),
            Shot(
                id="S02",
                dur_sec=5.0,
                bg="bg_test2",
                audio=AudioRef(dialogue=["Fletcher: Let's go!"], sfx=[]),
                actors=[ActorRef(character="fletcher", pose="run", expression="excited")],
            ),
        ],
    )


@pytest.fixture
def sample_context(sample_episode, sample_shotlist, tmp_path) -> QCContext:
    return QCContext(
        episode=sample_episode,
        shotlist=sample_shotlist,
        episode_dir=tmp_path,
        canon_characters=["charlie", "spencer", "fletcher", "fold"],
    )


class TestDialogueLanguageCheck:
    def test_passes_clean_dialogue(self, sample_context):
        rule = DialogueLanguageCheck()
        result = rule.check(sample_context)
        assert result.passed is True
        assert len(result.errors) == 0

    def test_catches_inappropriate_words(self, sample_context):
        sample_context.shotlist.shots[0].audio.dialogue = ["Spencer: I hate this!"]
        rule = DialogueLanguageCheck()
        result = rule.check(sample_context)
        assert result.passed is False
        assert any("hate" in e for e in result.errors)

    def test_handles_missing_shotlist(self, sample_context):
        sample_context.shotlist = None
        rule = DialogueLanguageCheck()
        result = rule.check(sample_context)
        assert result.passed is True
        assert any("No shotlist" in w for w in result.warnings)


class TestRuntimeBoundsCheck:
    def test_passes_valid_runtime(self, sample_context):
        rule = RuntimeBoundsCheck()
        result = rule.check(sample_context)
        assert result.passed is True

    def test_fails_too_short_runtime(self, sample_context):
        sample_context.episode.runtime_target_sec = 30
        rule = RuntimeBoundsCheck()
        result = rule.check(sample_context)
        assert result.passed is False
        assert any("below minimum" in e for e in result.errors)

    def test_warns_too_long_runtime(self, sample_context):
        sample_context.episode.runtime_target_sec = 2400
        rule = RuntimeBoundsCheck()
        result = rule.check(sample_context)
        assert result.passed is True
        assert any("exceeds" in w for w in result.warnings)

    def test_warns_runtime_variance(self, sample_context):
        sample_context.episode.runtime_target_sec = 100
        rule = RuntimeBoundsCheck()
        result = rule.check(sample_context)
        assert any("differs from target" in w for w in result.warnings)


class TestAssetCoverageCheck:
    def test_handles_missing_shotlist(self, sample_context):
        sample_context.shotlist = None
        rule = AssetCoverageCheck()
        result = rule.check(sample_context)
        assert result.passed is True
        assert any("No shotlist" in w for w in result.warnings)

    def test_warns_missing_background(self, sample_context):
        rule = AssetCoverageCheck()
        result = rule.check(sample_context)
        assert any("missing background" in w for w in result.warnings)


class TestCharacterConsistencyCheck:
    def test_passes_valid_cast(self, sample_context):
        rule = CharacterConsistencyCheck()
        result = rule.check(sample_context)
        assert result.passed is True

    def test_fails_unknown_character(self, sample_context):
        sample_context.shotlist.shots[0].actors[0].character = "unknown_char"
        rule = CharacterConsistencyCheck()
        result = rule.check(sample_context)
        assert result.passed is False
        assert any("not in episode cast" in e for e in result.errors)

    def test_warns_non_canon_cast(self, sample_context):
        sample_context.episode.cast = ["charlie", "spencer", "new_character"]
        sample_context.canon_characters = ["charlie", "spencer"]
        rule = CharacterConsistencyCheck()
        result = rule.check(sample_context)
        assert any("not in canon" in w for w in result.warnings)


class TestKidsContentCheck:
    def test_passes_clean_content(self, sample_context):
        rule = KidsContentCheck()
        result = rule.check(sample_context)
        assert result.passed is True

    def test_warns_violence_adjacent_words(self, sample_context):
        sample_context.shotlist.shots[0].audio.dialogue = ["Spencer: We must fight for this!"]
        rule = KidsContentCheck()
        result = rule.check(sample_context)
        assert any("fight" in w for w in result.warnings)


class TestIPChecklistReminder:
    def test_always_adds_reminders(self, sample_context):
        rule = IPChecklistReminder()
        result = rule.check(sample_context)
        assert result.passed is True
        assert len(result.warnings) >= 3
        assert any("on-model" in w for w in result.warnings)


class TestQCChecker:
    def test_runs_all_default_rules(self):
        checker = QCChecker()
        assert len(checker.rules) == 6

    def test_run_with_example_episode(self):
        if not EXAMPLE_EP.exists():
            pytest.skip("Example episode not available")
        checker = QCChecker()
        result = checker.run(EXAMPLE_EP)
        assert isinstance(result, QCResult)
        assert len(result.rule_results) > 0

    def test_custom_rules(self, sample_context):
        class CustomRule(Rule):
            @property
            def name(self) -> str:
                return "custom_rule"

            def check(self, ctx: QCContext) -> RuleResult:
                return RuleResult(rule_name=self.name, passed=True)

        checker = QCChecker(rules=[CustomRule()])
        assert len(checker.rules) == 1


class TestQCResult:
    def test_merge_adds_results(self):
        result = QCResult(passed=True)
        rule_result = RuleResult(
            rule_name="test",
            passed=True,
            warnings=["warn1"],
            errors=[],
        )
        result.merge(rule_result)
        assert len(result.rule_results) == 1
        assert "warn1" in result.warnings
        assert result.passed is True

    def test_merge_fails_on_error(self):
        result = QCResult(passed=True)
        rule_result = RuleResult(
            rule_name="test",
            passed=False,
            warnings=[],
            errors=["error1"],
        )
        result.merge(rule_result)
        assert result.passed is False
        assert "error1" in result.errors


class TestReportGeneration:
    def test_generate_qc_report(self, tmp_path):
        result = QCResult(
            passed=True,
            warnings=["test warning"],
            errors=[],
            rule_results=[
                RuleResult(rule_name="test_rule", passed=True, warnings=["warn"], errors=[])
            ],
        )
        json_path, md_path = generate_qc_report(result, tmp_path, "s01e01")
        assert json_path.exists()
        assert md_path.exists()

        data = json.loads(json_path.read_text())
        assert data["passed"] is True
        assert data["episode_id"] == "s01e01"

        md_content = md_path.read_text()
        assert "PASSED" in md_content

    def test_generate_cost_report_empty(self, tmp_path):
        json_path, md_path = generate_cost_report(tmp_path, tmp_path)
        assert json_path.exists()
        assert md_path.exists()

        data = json.loads(json_path.read_text())
        assert data["total_cost_usd"] == 0
        assert data["total_runs"] == 0

    def test_generate_cost_report_with_data(self, tmp_path):
        gen_runs = tmp_path / "gen_runs.jsonl"
        gen_runs.write_text(
            '{"asset_id":"bg1","provider":"flux","model":"flux-v1","cost_usd":0.01,"cached":false,"timestamp":"2024-01-01T00:00:00"}\n'
            '{"asset_id":"bg2","provider":"flux","model":"flux-v1","cost_usd":0.01,"cached":true,"timestamp":"2024-01-01T00:00:01"}\n'
        )

        json_path, md_path = generate_cost_report(tmp_path, tmp_path)
        data = json.loads(json_path.read_text())

        assert data["total_runs"] == 2
        assert data["cached_runs"] == 1
        assert data["reuse_rate"] == 0.5
        assert data["total_cost_usd"] == 0.01

    def test_qc_result_to_dict(self):
        result = QCResult(passed=True, warnings=["w1"], errors=["e1"])
        data = _qc_result_to_dict(result, "s01e01")
        assert data["passed"] is True
        assert "w1" in data["warnings"]
        assert "e1" in data["errors"]


class TestBuildIntegration:
    def test_build_includes_qc_stage(self):
        from wayfinders_cli.build import build_final

        result = build_final(EXAMPLE_EP, dry_run=True)
        assert "qc_check" in result.stages_completed

    def test_build_skip_qc(self):
        from wayfinders_cli.build import build_final

        result = build_final(EXAMPLE_EP, dry_run=True, skip_qc=True)
        assert "qc_check" not in result.stages_completed
        assert any("qc_check: skipped" in w for w in result.warnings)

    def test_qc_stage_writes_reports(self, tmp_path):
        from wayfinders_cli.build import build_final
        from wayfinders_cli.validate import ValidationResult

        with patch("wayfinders_cli.build.validate_episode") as mock_val, \
             patch("wayfinders_cli.build.build_plan") as mock_plan, \
             patch("wayfinders_cli.build.generate_episode_assets") as mock_gen, \
             patch("wayfinders_cli.build.write_timeline") as mock_timeline, \
             patch("wayfinders_cli.build.ffmpeg_exists", return_value=False), \
             patch("wayfinders_cli.build.mix_episode_audio") as mock_audio, \
             patch("wayfinders_cli.build.create_provenance_bundle") as mock_prov:

            mock_val.return_value = ValidationResult(ok=True, errors=[], missing_files=[])
            mock_plan.return_value = {}
            mock_gen.return_value = MagicMock(generated=[], skipped=[], errors=[])
            mock_timeline.return_value = Path("logs/timeline.json")
            mock_audio.return_value = MagicMock(success=True, message="ok", tracks_missing=[])
            mock_prov.return_value = Path("logs/provenance.json")

            result = build_final(EXAMPLE_EP)
            assert "qc_check" in result.stages_completed

            logs_dir = EXAMPLE_EP.parent / "logs"
            qc_report = logs_dir / "qc_report.json"
            assert qc_report.exists()

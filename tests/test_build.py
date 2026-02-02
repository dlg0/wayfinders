from pathlib import Path
from unittest.mock import patch, MagicMock

from wayfinders_cli.build import build_final, BuildResult
from wayfinders_cli.validate import ValidationResult


EXAMPLE_EP = Path("episodes/s01e01_map_forgot_roads/episode.yaml")


def test_build_runs_all_stages_in_order():
    result = build_final(EXAMPLE_EP, dry_run=True)
    assert result.success is True
    expected = [
        "validate", "plan", "generate", "timeline", "render_frames",
        "audio_mix", "assemble_video", "qc_check", "provenance_bundle"
    ]
    assert result.stages_completed == expected


def test_build_skip_validation():
    result = build_final(EXAMPLE_EP, dry_run=True, skip_validation=True)
    assert result.success is True
    assert "validate" not in result.stages_completed
    assert "validate: skipped (disabled)" in result.warnings


def test_validation_failure_stops_pipeline():
    with patch("wayfinders_cli.build.validate_episode") as mock_val:
        mock_val.return_value = ValidationResult(
            ok=False,
            errors=["Test validation error"],
            missing_files=[],
        )
        result = build_final(EXAMPLE_EP, skip_validation=False)
        assert result.success is False
        assert "validate" not in result.stages_completed
        assert any("validate" in e and "Test validation error" in e for e in result.errors)


def test_dry_run_shows_stages_without_executing():
    result = build_final(EXAMPLE_EP, dry_run=True)
    assert result.success is True
    assert len(result.stage_results) == 0
    assert len(result.stages_completed) == 9


def test_force_flag_passed_to_generate():
    with patch("wayfinders_cli.build.validate_episode") as mock_val, \
         patch("wayfinders_cli.build.build_plan") as mock_plan, \
         patch("wayfinders_cli.build.generate_episode_assets") as mock_gen, \
         patch("wayfinders_cli.build.write_timeline") as mock_timeline, \
         patch("wayfinders_cli.build.ffmpeg_exists", return_value=False), \
         patch("wayfinders_cli.build.create_provenance_bundle") as mock_prov, \
         patch("wayfinders_cli.build.QCChecker") as mock_qc:

        mock_val.return_value = ValidationResult(ok=True, errors=[], missing_files=[])
        mock_plan.return_value = {}
        mock_gen.return_value = MagicMock(generated=[], skipped=[], errors=[])
        mock_timeline.return_value = Path("logs/timeline.json")
        mock_prov.return_value = Path("logs/provenance.zip")
        mock_qc_instance = MagicMock()
        mock_qc_instance.run.return_value = MagicMock(passed=True, errors=[], warnings=[])
        mock_qc.return_value = mock_qc_instance

        build_final(EXAMPLE_EP, force=True)
        mock_gen.assert_called_once()
        _, kwargs = mock_gen.call_args
        assert kwargs.get("force") is True


def test_build_result_dataclass():
    result = BuildResult(
        success=True,
        stages_completed=["validate", "plan"],
        output_path=Path("renders/final.mp4"),
        errors=[],
        warnings=["test warning"],
    )
    assert result.success is True
    assert result.output_path == Path("renders/final.mp4")
    assert len(result.stages_completed) == 2
    assert "test warning" in result.warnings


def test_ffmpeg_warning_in_dry_run():
    with patch("wayfinders_cli.build.ffmpeg_exists", return_value=False):
        result = build_final(EXAMPLE_EP, dry_run=True)
        assert any("ffmpeg" in w for w in result.warnings)


def test_partial_build_on_generate_error():
    with patch("wayfinders_cli.build.validate_episode") as mock_val, \
         patch("wayfinders_cli.build.build_plan") as mock_plan, \
         patch("wayfinders_cli.build.generate_episode_assets") as mock_gen:

        mock_val.return_value = ValidationResult(ok=True, errors=[], missing_files=[])
        mock_plan.return_value = {}
        mock_gen.return_value = MagicMock(
            generated=[],
            skipped=[],
            errors=[("asset1", "generation failed")],
        )

        result = build_final(EXAMPLE_EP)
        assert result.success is False
        assert "validate" in result.stages_completed
        assert "plan" in result.stages_completed
        assert "generate" not in result.stages_completed
        assert any("generate" in e for e in result.errors)

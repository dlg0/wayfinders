from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .validate import validate_episode
from .plan import build_plan
from .gen.generate import generate_episode_assets
from .render.timeline import write_timeline
from .render.animatic_stub import build_animatic_from_placeholders
from .render.ffmpeg import ffmpeg_exists
from .qc.checker import QCChecker
from .qc.report import generate_qc_report, generate_cost_report
from .render.audio import mix_episode_audio
from .reproducibility import set_random_seed
from .provenance.bundle import create_provenance_bundle


@dataclass
class StageResult:
    name: str
    success: bool
    duration_sec: float
    message: str = ""


@dataclass
class BuildResult:
    success: bool
    stages_completed: list[str] = field(default_factory=list)
    output_path: Optional[Path] = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    stage_results: list[StageResult] = field(default_factory=list)


def _run_stage(name: str, func, result: BuildResult) -> bool:
    start = time.monotonic()
    try:
        success, msg = func()
        duration = time.monotonic() - start
        result.stage_results.append(StageResult(name, success, duration, msg))
        if success:
            result.stages_completed.append(name)
        else:
            result.errors.append(f"{name}: {msg}")
        return success
    except Exception as e:
        duration = time.monotonic() - start
        result.stage_results.append(StageResult(name, False, duration, str(e)))
        result.errors.append(f"{name}: {e}")
        return False


def build_final(
    episode_yaml: Path,
    force: bool = False,
    skip_validation: bool = False,
    skip_qc: bool = False,
    dry_run: bool = False,
    seed: Optional[int] = None,
) -> BuildResult:
    result = BuildResult(success=False)
    episode_dir = episode_yaml.parent
    logs_dir = episode_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    if seed is not None:
        set_random_seed(seed)

    stages = [
        ("validate", not skip_validation),
        ("plan", True),
        ("generate", True),
        ("timeline", True),
        ("render_frames", True),
        ("audio_mix", True),
        ("assemble_video", True),
        ("qc_check", not skip_qc),
        ("provenance_bundle", True),
    ]

    if dry_run:
        for stage_name, enabled in stages:
            if enabled:
                result.stages_completed.append(stage_name)
            else:
                result.warnings.append(f"{stage_name}: skipped (disabled)")

        if not ffmpeg_exists():
            result.warnings.append("assemble_video: ffmpeg not available, would skip")

        result.success = True
        return result

    def stage_validate():
        res = validate_episode(episode_yaml, allow_missing_assets=True)
        if not res.ok:
            return False, "; ".join(res.errors)
        if res.missing_files:
            pass
        return True, f"valid ({len(res.missing_files)} missing assets)"

    def stage_plan():
        payload = build_plan(episode_yaml)
        (logs_dir / "plan.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return True, "plan written"

    def stage_generate():
        gen_result = generate_episode_assets(episode_yaml, force=force)
        if gen_result.errors:
            err_msgs = [f"{aid}: {msg}" for aid, msg in gen_result.errors]
            return False, "; ".join(err_msgs)
        msg = f"{len(gen_result.generated)} generated, {len(gen_result.skipped)} cached"
        return True, msg

    def stage_timeline():
        out = write_timeline(episode_yaml)
        return True, f"timeline written to {out}"

    def stage_render_frames():
        try:
            import importlib.util
            if importlib.util.find_spec("PIL") is None:
                result.warnings.append("render_frames: Pillow not available, skipping")
                return True, "skipped (Pillow not available)"
        except ImportError:
            result.warnings.append("render_frames: Pillow not available, skipping")
            return True, "skipped (Pillow not available)"
        return True, "compositor not implemented, skipping"

    audio_mix_path: Optional[Path] = None

    def stage_audio_mix():
        nonlocal audio_mix_path
        if not ffmpeg_exists():
            result.warnings.append("audio_mix: ffmpeg not available, skipping")
            return True, "skipped (ffmpeg not available)"

        mix_result = mix_episode_audio(episode_yaml)
        if not mix_result.success:
            if "no audio tracks" in mix_result.message:
                result.warnings.append(f"audio_mix: {mix_result.message}")
                return True, mix_result.message
            return False, mix_result.message

        if mix_result.tracks_missing:
            result.warnings.append(
                f"audio_mix: {len(mix_result.tracks_missing)} missing audio assets"
            )

        audio_mix_path = mix_result.output_path
        return True, mix_result.message

    def stage_assemble_video():
        if not ffmpeg_exists():
            result.warnings.append("assemble_video: ffmpeg not available, skipping")
            return True, "skipped (ffmpeg not available)"

        try:
            out = build_animatic_from_placeholders(episode_yaml)
            result.output_path = out
            return True, f"video written to {out}"
        except Exception as e:
            return False, str(e)

    def stage_provenance_bundle():
        try:
            bundle_path = create_provenance_bundle(episode_yaml)
            return True, f"bundle written to {bundle_path}"
        except Exception as e:
            return False, str(e)

    def stage_qc_check():
        import yaml
        checker = QCChecker()
        qc_result = checker.run(episode_yaml)

        ep_data = yaml.safe_load(episode_yaml.read_text(encoding="utf-8"))
        episode_id = ep_data.get("id", "unknown")

        generate_qc_report(qc_result, logs_dir, episode_id)
        generate_cost_report(logs_dir, logs_dir)

        if not qc_result.passed:
            err_summary = "; ".join(qc_result.errors[:3])
            if len(qc_result.errors) > 3:
                err_summary += f" (+{len(qc_result.errors) - 3} more)"
            return False, f"QC failed: {err_summary}"

        warn_count = len(qc_result.warnings)
        return True, f"QC passed ({warn_count} warnings)"

    stage_funcs = {
        "validate": stage_validate,
        "plan": stage_plan,
        "generate": stage_generate,
        "timeline": stage_timeline,
        "render_frames": stage_render_frames,
        "audio_mix": stage_audio_mix,
        "assemble_video": stage_assemble_video,
        "qc_check": stage_qc_check,
        "provenance_bundle": stage_provenance_bundle,
    }

    for stage_name, enabled in stages:
        if not enabled:
            result.warnings.append(f"{stage_name}: skipped (disabled)")
            continue

        func = stage_funcs[stage_name]
        if not _run_stage(stage_name, func, result):
            _write_build_log(result, logs_dir)
            return result

    result.success = True
    _write_build_log(result, logs_dir)
    return result


def _write_build_log(result: BuildResult, logs_dir: Path) -> Path:
    log_path = logs_dir / "build.log"
    lines = [
        f"Build {'SUCCESS' if result.success else 'FAILED'}",
        f"Stages completed: {', '.join(result.stages_completed)}",
        "",
        "Stage Details:",
    ]
    for sr in result.stage_results:
        status = "✓" if sr.success else "✗"
        lines.append(f"  {status} {sr.name}: {sr.duration_sec:.2f}s - {sr.message}")

    if result.warnings:
        lines.append("")
        lines.append("Warnings:")
        for w in result.warnings:
            lines.append(f"  - {w}")

    if result.errors:
        lines.append("")
        lines.append("Errors:")
        for e in result.errors:
            lines.append(f"  - {e}")

    if result.output_path:
        lines.append("")
        lines.append(f"Output: {result.output_path}")

    log_path.write_text("\n".join(lines), encoding="utf-8")
    return log_path

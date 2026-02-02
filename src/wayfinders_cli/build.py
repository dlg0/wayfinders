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
    dry_run: bool = False,
) -> BuildResult:
    result = BuildResult(success=False)
    episode_dir = episode_yaml.parent
    logs_dir = episode_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    stages = [
        ("validate", not skip_validation),
        ("plan", True),
        ("generate", True),
        ("timeline", True),
        ("render_frames", True),
        ("assemble_video", True),
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

    stage_funcs = {
        "validate": stage_validate,
        "plan": stage_plan,
        "generate": stage_generate,
        "timeline": stage_timeline,
        "render_frames": stage_render_frames,
        "assemble_video": stage_assemble_video,
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
    _write_provenance_bundle(result, episode_yaml, logs_dir)
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


def _write_provenance_bundle(result: BuildResult, episode_yaml: Path, logs_dir: Path) -> Path:
    episode_dir = episode_yaml.parent
    provenance_path = logs_dir / "provenance.json"

    sidecars = []
    assets_dir = episode_dir / "assets"
    for sidecar_path in assets_dir.rglob("*.json"):
        try:
            data = json.loads(sidecar_path.read_text(encoding="utf-8"))
            sidecars.append(data)
        except (json.JSONDecodeError, OSError):
            pass

    bundle = {
        "success": result.success,
        "stages_completed": result.stages_completed,
        "output_path": str(result.output_path) if result.output_path else None,
        "assets": sidecars,
    }
    provenance_path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    return provenance_path

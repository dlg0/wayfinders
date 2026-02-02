from __future__ import annotations

import hashlib
import json
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .manifest import create_manifest, Manifest


@dataclass
class ProvenanceBundle:
    manifest: Manifest
    episode_yaml: str
    shotlist_yaml: Optional[str]
    sidecars: list[dict] = field(default_factory=list)
    plan_json: Optional[dict] = None
    timeline_json: Optional[dict] = None
    gen_runs: list[dict] = field(default_factory=list)
    qc_report: Optional[dict] = None
    checksums: dict[str, str] = field(default_factory=dict)
    render_settings: Optional[dict] = None


def compute_file_checksum(file_path: Path) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def collect_sidecars(assets_dir: Path) -> list[dict]:
    sidecars = []
    if not assets_dir.exists():
        return sidecars

    for sidecar_path in assets_dir.rglob("*.json"):
        try:
            data = json.loads(sidecar_path.read_text(encoding="utf-8"))
            data["_sidecar_path"] = str(sidecar_path.name)
            sidecars.append(data)
        except (json.JSONDecodeError, OSError):
            pass
    return sidecars


def read_jsonl(file_path: Path) -> list[dict]:
    entries = []
    if not file_path.exists():
        return entries

    with open(file_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return entries


def read_json_file(file_path: Path) -> Optional[dict]:
    if not file_path.exists():
        return None
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def create_provenance_bundle(
    episode_yaml: Path,
    output_path: Optional[Path] = None,
    include_prompts_dir: Optional[Path] = None,
) -> Path:
    episode_dir = episode_yaml.parent
    logs_dir = episode_dir / "logs"
    assets_dir = episode_dir / "assets"
    renders_dir = episode_dir / "renders"
    renders_dir.mkdir(parents=True, exist_ok=True)

    if output_path is None:
        output_path = renders_dir / "provenance_bundle.zip"

    episode_content = episode_yaml.read_text(encoding="utf-8")

    shotlist_path = episode_dir / "shotlist.yaml"
    shotlist_content = None
    if shotlist_path.exists():
        shotlist_content = shotlist_path.read_text(encoding="utf-8")

    sidecars = collect_sidecars(assets_dir)
    plan_json = read_json_file(logs_dir / "plan.json")
    timeline_json = read_json_file(logs_dir / "timeline.json")
    gen_runs = read_jsonl(logs_dir / "gen_runs.jsonl")
    qc_report = read_json_file(logs_dir / "qc_report.json")
    render_settings = read_json_file(episode_dir / "render_settings.json")

    checksums: dict[str, str] = {}
    for mp4_path in renders_dir.glob("*.mp4"):
        checksums[mp4_path.name] = compute_file_checksum(mp4_path)

    episode_id = episode_dir.name
    files_in_bundle: list[str] = ["manifest.json", "episode.yaml"]
    if shotlist_content:
        files_in_bundle.append("shotlist.yaml")
    if plan_json:
        files_in_bundle.append("logs/plan.json")
    if timeline_json:
        files_in_bundle.append("logs/timeline.json")
    if gen_runs:
        files_in_bundle.append("logs/gen_runs.jsonl")
    if qc_report:
        files_in_bundle.append("logs/qc_report.json")
    for sidecar in sidecars:
        sidecar_name = sidecar.get("_sidecar_path", "unknown.json")
        files_in_bundle.append(f"sidecars/{sidecar_name}")

    manifest = create_manifest(
        episode_id=episode_id,
        files=files_in_bundle,
        checksums=checksums,
        output_path=output_path,
    )

    bundle = ProvenanceBundle(
        manifest=manifest,
        episode_yaml=episode_content,
        shotlist_yaml=shotlist_content,
        sidecars=sidecars,
        plan_json=plan_json,
        timeline_json=timeline_json,
        gen_runs=gen_runs,
        qc_report=qc_report,
        checksums=checksums,
        render_settings=render_settings,
    )

    _write_bundle_zip(bundle, output_path, include_prompts_dir)
    return output_path


def _write_bundle_zip(
    bundle: ProvenanceBundle,
    output_path: Path,
    include_prompts_dir: Optional[Path] = None,
) -> None:
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", bundle.manifest.to_json())
        zf.writestr("episode.yaml", bundle.episode_yaml)

        if bundle.shotlist_yaml:
            zf.writestr("shotlist.yaml", bundle.shotlist_yaml)

        if bundle.plan_json:
            zf.writestr("logs/plan.json", json.dumps(bundle.plan_json, indent=2))

        if bundle.timeline_json:
            zf.writestr("logs/timeline.json", json.dumps(bundle.timeline_json, indent=2))

        if bundle.gen_runs:
            gen_runs_content = "\n".join(json.dumps(entry) for entry in bundle.gen_runs)
            zf.writestr("logs/gen_runs.jsonl", gen_runs_content)

        if bundle.qc_report:
            zf.writestr("logs/qc_report.json", json.dumps(bundle.qc_report, indent=2))

        for sidecar in bundle.sidecars:
            sidecar_name = sidecar.pop("_sidecar_path", "unknown.json")
            zf.writestr(f"sidecars/{sidecar_name}", json.dumps(sidecar, indent=2))

        zf.writestr("checksums.json", json.dumps(bundle.checksums, indent=2))

        if bundle.render_settings:
            zf.writestr("render_settings.json", json.dumps(bundle.render_settings, indent=2))

        if include_prompts_dir and include_prompts_dir.exists():
            for prompt_file in include_prompts_dir.rglob("*"):
                if prompt_file.is_file():
                    rel_path = prompt_file.relative_to(include_prompts_dir)
                    zf.write(prompt_file, f"prompts/{rel_path}")

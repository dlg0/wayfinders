from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from wayfinders_cli.provenance.bundle import (
    ProvenanceBundle,
    create_provenance_bundle,
    compute_file_checksum,
    collect_sidecars,
    read_jsonl,
    read_json_file,
)
from wayfinders_cli.provenance.manifest import create_manifest


@pytest.fixture
def temp_episode_dir(tmp_path: Path) -> Path:
    ep_dir = tmp_path / "s01e01_test"
    ep_dir.mkdir(parents=True)

    episode_yaml = ep_dir / "episode.yaml"
    episode_yaml.write_text("title: Test Episode\n", encoding="utf-8")

    shotlist_yaml = ep_dir / "shotlist.yaml"
    shotlist_yaml.write_text("shots:\n  - id: shot1\n", encoding="utf-8")

    logs_dir = ep_dir / "logs"
    logs_dir.mkdir()
    (logs_dir / "plan.json").write_text('{"stages": ["plan"]}', encoding="utf-8")
    (logs_dir / "timeline.json").write_text('{"tracks": []}', encoding="utf-8")
    (logs_dir / "gen_runs.jsonl").write_text(
        '{"run_id": "1"}\n{"run_id": "2"}\n', encoding="utf-8"
    )

    assets_dir = ep_dir / "assets"
    assets_dir.mkdir()
    (assets_dir / "asset1.json").write_text(
        '{"cache_key": "abc123", "provider_id": "test"}', encoding="utf-8"
    )
    (assets_dir / "asset2.json").write_text(
        '{"cache_key": "def456", "provider_id": "test"}', encoding="utf-8"
    )

    renders_dir = ep_dir / "renders"
    renders_dir.mkdir()
    mp4_content = b"fake mp4 content"
    (renders_dir / "final.mp4").write_bytes(mp4_content)

    return ep_dir


def test_compute_file_checksum(tmp_path: Path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello world", encoding="utf-8")

    checksum = compute_file_checksum(test_file)

    assert len(checksum) == 64
    assert checksum == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"


def test_collect_sidecars(temp_episode_dir: Path):
    assets_dir = temp_episode_dir / "assets"

    sidecars = collect_sidecars(assets_dir)

    assert len(sidecars) == 2
    cache_keys = {s["cache_key"] for s in sidecars}
    assert cache_keys == {"abc123", "def456"}
    for sidecar in sidecars:
        assert "_sidecar_path" in sidecar


def test_collect_sidecars_nonexistent_dir(tmp_path: Path):
    sidecars = collect_sidecars(tmp_path / "nonexistent")
    assert sidecars == []


def test_read_jsonl(temp_episode_dir: Path):
    logs_dir = temp_episode_dir / "logs"

    entries = read_jsonl(logs_dir / "gen_runs.jsonl")

    assert len(entries) == 2
    assert entries[0] == {"run_id": "1"}
    assert entries[1] == {"run_id": "2"}


def test_read_jsonl_nonexistent():
    entries = read_jsonl(Path("/nonexistent/file.jsonl"))
    assert entries == []


def test_read_json_file(temp_episode_dir: Path):
    logs_dir = temp_episode_dir / "logs"

    data = read_json_file(logs_dir / "plan.json")

    assert data == {"stages": ["plan"]}


def test_read_json_file_nonexistent():
    data = read_json_file(Path("/nonexistent/file.json"))
    assert data is None


def test_create_manifest():
    manifest = create_manifest(
        episode_id="s01e01_test",
        files=["manifest.json", "episode.yaml"],
        checksums={"final.mp4": "abc123"},
        output_path=Path("/some/path.zip"),
    )

    assert manifest.version == "1.0"
    assert manifest.episode_id == "s01e01_test"
    assert manifest.files == ["manifest.json", "episode.yaml"]
    assert manifest.checksums == {"final.mp4": "abc123"}
    assert manifest.output_path == "/some/path.zip"
    assert manifest.build_timestamp is not None
    assert manifest.pipeline_version is not None


def test_manifest_to_json():
    manifest = create_manifest(
        episode_id="s01e01_test",
        files=["manifest.json"],
        checksums={},
    )

    json_str = manifest.to_json()
    data = json.loads(json_str)

    assert data["version"] == "1.0"
    assert data["episode_id"] == "s01e01_test"


def test_create_provenance_bundle(temp_episode_dir: Path):
    episode_yaml = temp_episode_dir / "episode.yaml"

    bundle_path = create_provenance_bundle(episode_yaml)

    assert bundle_path.exists()
    assert bundle_path.name == "provenance_bundle.zip"
    assert bundle_path.parent == temp_episode_dir / "renders"


def test_bundle_zip_structure(temp_episode_dir: Path):
    episode_yaml = temp_episode_dir / "episode.yaml"

    bundle_path = create_provenance_bundle(episode_yaml)

    with zipfile.ZipFile(bundle_path, "r") as zf:
        names = zf.namelist()

        assert "manifest.json" in names
        assert "episode.yaml" in names
        assert "shotlist.yaml" in names
        assert "logs/plan.json" in names
        assert "logs/timeline.json" in names
        assert "logs/gen_runs.jsonl" in names
        assert "checksums.json" in names
        assert any(n.startswith("sidecars/") for n in names)


def test_bundle_manifest_content(temp_episode_dir: Path):
    episode_yaml = temp_episode_dir / "episode.yaml"

    bundle_path = create_provenance_bundle(episode_yaml)

    with zipfile.ZipFile(bundle_path, "r") as zf:
        manifest_data = json.loads(zf.read("manifest.json"))

        assert manifest_data["version"] == "1.0"
        assert manifest_data["episode_id"] == temp_episode_dir.name
        assert "episode.yaml" in manifest_data["files"]


def test_bundle_checksums(temp_episode_dir: Path):
    episode_yaml = temp_episode_dir / "episode.yaml"

    bundle_path = create_provenance_bundle(episode_yaml)

    with zipfile.ZipFile(bundle_path, "r") as zf:
        checksums_data = json.loads(zf.read("checksums.json"))

        assert "final.mp4" in checksums_data
        assert len(checksums_data["final.mp4"]) == 64


def test_bundle_custom_output_path(temp_episode_dir: Path, tmp_path: Path):
    episode_yaml = temp_episode_dir / "episode.yaml"
    custom_output = tmp_path / "custom_bundle.zip"

    bundle_path = create_provenance_bundle(episode_yaml, output_path=custom_output)

    assert bundle_path == custom_output
    assert bundle_path.exists()


def test_bundle_with_qc_report(temp_episode_dir: Path):
    logs_dir = temp_episode_dir / "logs"
    (logs_dir / "qc_report.json").write_text('{"passed": true}', encoding="utf-8")
    episode_yaml = temp_episode_dir / "episode.yaml"

    bundle_path = create_provenance_bundle(episode_yaml)

    with zipfile.ZipFile(bundle_path, "r") as zf:
        assert "logs/qc_report.json" in zf.namelist()
        qc_data = json.loads(zf.read("logs/qc_report.json"))
        assert qc_data == {"passed": True}


def test_bundle_with_render_settings(temp_episode_dir: Path):
    (temp_episode_dir / "render_settings.json").write_text(
        '{"resolution": "1080p"}', encoding="utf-8"
    )
    episode_yaml = temp_episode_dir / "episode.yaml"

    bundle_path = create_provenance_bundle(episode_yaml)

    with zipfile.ZipFile(bundle_path, "r") as zf:
        assert "render_settings.json" in zf.namelist()
        settings = json.loads(zf.read("render_settings.json"))
        assert settings == {"resolution": "1080p"}


def test_bundle_include_prompts_dir(temp_episode_dir: Path, tmp_path: Path):
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "char1.txt").write_text("prompt for char1", encoding="utf-8")
    subdir = prompts_dir / "subdir"
    subdir.mkdir()
    (subdir / "char2.txt").write_text("prompt for char2", encoding="utf-8")

    episode_yaml = temp_episode_dir / "episode.yaml"

    bundle_path = create_provenance_bundle(
        episode_yaml, include_prompts_dir=prompts_dir
    )

    with zipfile.ZipFile(bundle_path, "r") as zf:
        names = zf.namelist()
        assert "prompts/char1.txt" in names
        assert "prompts/subdir/char2.txt" in names


def test_bundle_without_shotlist(temp_episode_dir: Path):
    (temp_episode_dir / "shotlist.yaml").unlink()
    episode_yaml = temp_episode_dir / "episode.yaml"

    bundle_path = create_provenance_bundle(episode_yaml)

    with zipfile.ZipFile(bundle_path, "r") as zf:
        assert "shotlist.yaml" not in zf.namelist()


def test_bundle_empty_assets_dir(tmp_path: Path):
    ep_dir = tmp_path / "s01e02_empty"
    ep_dir.mkdir()
    episode_yaml = ep_dir / "episode.yaml"
    episode_yaml.write_text("title: Empty Test\n", encoding="utf-8")

    bundle_path = create_provenance_bundle(episode_yaml)

    assert bundle_path.exists()
    with zipfile.ZipFile(bundle_path, "r") as zf:
        assert "episode.yaml" in zf.namelist()
        assert not any(n.startswith("sidecars/") for n in zf.namelist())


def test_provenance_bundle_dataclass():
    manifest = create_manifest("test_ep", [], {})
    bundle = ProvenanceBundle(
        manifest=manifest,
        episode_yaml="title: Test\n",
        shotlist_yaml="shots: []\n",
        sidecars=[{"cache_key": "abc"}],
        plan_json={"stages": []},
        timeline_json={"tracks": []},
        gen_runs=[{"run_id": "1"}],
        checksums={"final.mp4": "abc123"},
    )

    assert bundle.episode_yaml == "title: Test\n"
    assert len(bundle.sidecars) == 1
    assert bundle.checksums["final.mp4"] == "abc123"

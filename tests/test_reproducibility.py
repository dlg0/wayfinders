from __future__ import annotations

import json
import random
from pathlib import Path

from wayfinders_cli.reproducibility import (
    get_pipeline_version,
    set_random_seed,
    stamp_version,
)


class TestGetPipelineVersion:
    def test_returns_string(self):
        version = get_pipeline_version()
        assert isinstance(version, str)
        assert len(version) > 0

    def test_version_not_unknown_in_repo(self):
        version = get_pipeline_version()
        assert version != "unknown" or version.startswith("0.")


class TestSetRandomSeed:
    def test_deterministic_random(self):
        set_random_seed(42)
        first_sequence = [random.random() for _ in range(10)]

        set_random_seed(42)
        second_sequence = [random.random() for _ in range(10)]

        assert first_sequence == second_sequence

    def test_different_seeds_produce_different_sequences(self):
        set_random_seed(42)
        first_sequence = [random.random() for _ in range(10)]

        set_random_seed(123)
        second_sequence = [random.random() for _ in range(10)]

        assert first_sequence != second_sequence


class TestStampVersion:
    def test_creates_sidecar_file(self, tmp_path: Path):
        output_file = tmp_path / "output.mp4"
        output_file.touch()

        sidecar = stamp_version(output_file)

        assert sidecar.exists()
        assert sidecar.name == "output.mp4.version.json"

    def test_sidecar_contains_required_fields(self, tmp_path: Path):
        output_file = tmp_path / "output.mp4"
        output_file.touch()

        sidecar = stamp_version(output_file)
        data = json.loads(sidecar.read_text())

        assert "pipeline_version" in data
        assert "timestamp" in data
        assert "output_file" in data
        assert data["output_file"] == "output.mp4"

    def test_includes_extra_metadata(self, tmp_path: Path):
        output_file = tmp_path / "output.mp4"
        output_file.touch()

        extra = {"seed": 42, "episode": "s01e01"}
        sidecar = stamp_version(output_file, extra_metadata=extra)
        data = json.loads(sidecar.read_text())

        assert "metadata" in data
        assert data["metadata"]["seed"] == 42
        assert data["metadata"]["episode"] == "s01e01"

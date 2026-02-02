from __future__ import annotations

import json
from pathlib import Path

from wayfinders_cli.cache import check_cache, compute_cache_key
from wayfinders_cli.gen.provenance import log_generation_run, write_asset_sidecar
from wayfinders_cli.gen.types import GeneratedAsset, ImageGenRequest


def make_request(
    template_name: str = "character_standing",
    resolved_prompt: str = "A cartoon fox standing",
    params: dict | None = None,
    width: int = 512,
    height: int = 512,
    provider_id: str = "placeholder",
    model_id: str | None = None,
    out_path: Path | None = None,
) -> ImageGenRequest:
    return ImageGenRequest(
        asset_type="character",
        asset_id="fox_standing",
        template_name=template_name,
        resolved_prompt=resolved_prompt,
        params=params or {"style": "cartoon"},
        width=width,
        height=height,
        out_path=out_path or Path("/tmp/test.png"),
        provider_id=provider_id,
        model_id=model_id,
    )


def make_asset(out_path: Path, cache_key: str) -> GeneratedAsset:
    return GeneratedAsset(
        out_path=out_path,
        output_hash="abc123",
        cache_key=cache_key,
        provider_id="placeholder",
        model_id=None,
    )


class TestComputeCacheKey:
    def test_same_inputs_produce_same_key(self) -> None:
        req1 = make_request()
        req2 = make_request()
        assert compute_cache_key(req1) == compute_cache_key(req2)

    def test_different_prompt_produces_different_key(self) -> None:
        req1 = make_request(resolved_prompt="A cartoon fox")
        req2 = make_request(resolved_prompt="A cartoon bear")
        assert compute_cache_key(req1) != compute_cache_key(req2)

    def test_different_dimensions_produce_different_key(self) -> None:
        req1 = make_request(width=512, height=512)
        req2 = make_request(width=1024, height=1024)
        assert compute_cache_key(req1) != compute_cache_key(req2)

    def test_different_params_produce_different_key(self) -> None:
        req1 = make_request(params={"style": "cartoon"})
        req2 = make_request(params={"style": "realistic"})
        assert compute_cache_key(req1) != compute_cache_key(req2)

    def test_different_provider_produces_different_key(self) -> None:
        req1 = make_request(provider_id="placeholder")
        req2 = make_request(provider_id="openai")
        assert compute_cache_key(req1) != compute_cache_key(req2)

    def test_cache_key_is_sha256_hex(self) -> None:
        req = make_request()
        key = compute_cache_key(req)
        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)


class TestWriteAssetSidecar:
    def test_sidecar_is_written_with_all_fields(self, tmp_path: Path) -> None:
        out_path = tmp_path / "asset.png"
        out_path.write_bytes(b"fake image")
        request = make_request(out_path=out_path)
        cache_key = compute_cache_key(request)
        asset = make_asset(out_path, cache_key)

        sidecar_path = write_asset_sidecar(asset, request)

        assert sidecar_path.exists()
        data = json.loads(sidecar_path.read_text())
        assert data["cache_key"] == cache_key
        assert data["provider_id"] == "placeholder"
        assert data["model_id"] is None
        assert data["template_name"] == "character_standing"
        assert data["resolved_prompt"] == "A cartoon fox standing"
        assert data["params"] == {"style": "cartoon"}
        assert "created_at" in data
        assert data["output_hash"] == "abc123"


class TestCheckCache:
    def test_returns_false_if_file_missing(self, tmp_path: Path) -> None:
        out_path = tmp_path / "missing.png"
        assert check_cache("somekey", out_path) is False

    def test_returns_false_if_sidecar_missing(self, tmp_path: Path) -> None:
        out_path = tmp_path / "asset.png"
        out_path.write_bytes(b"fake image")
        assert check_cache("somekey", out_path) is False

    def test_returns_false_if_key_mismatch(self, tmp_path: Path) -> None:
        out_path = tmp_path / "asset.png"
        out_path.write_bytes(b"fake image")
        sidecar = out_path.with_suffix(".png.json")
        sidecar.write_text(json.dumps({"cache_key": "otherkey"}))
        assert check_cache("somekey", out_path) is False

    def test_returns_true_if_key_matches(self, tmp_path: Path) -> None:
        out_path = tmp_path / "asset.png"
        out_path.write_bytes(b"fake image")
        sidecar = out_path.with_suffix(".png.json")
        sidecar.write_text(json.dumps({"cache_key": "mykey"}))
        assert check_cache("mykey", out_path) is True

    def test_cache_lookup_finds_existing_asset(self, tmp_path: Path) -> None:
        out_path = tmp_path / "asset.png"
        out_path.write_bytes(b"fake image")
        request = make_request(out_path=out_path)
        cache_key = compute_cache_key(request)
        asset = make_asset(out_path, cache_key)
        write_asset_sidecar(asset, request)

        assert check_cache(cache_key, out_path) is True


class TestLogGenerationRun:
    def test_appends_to_jsonl(self, tmp_path: Path) -> None:
        episode_dir = tmp_path / "ep01"
        episode_dir.mkdir()
        out_path = episode_dir / "assets" / "fox.png"
        out_path.parent.mkdir(parents=True)
        out_path.write_bytes(b"fake")

        request = make_request(out_path=out_path)
        cache_key = compute_cache_key(request)
        asset = make_asset(out_path, cache_key)

        log_generation_run(episode_dir, request, asset, cache_hit=False)

        log_path = episode_dir / "logs" / "gen_runs.jsonl"
        assert log_path.exists()
        lines = log_path.read_text().strip().split("\n")
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["asset_id"] == "fox_standing"
        assert data["cache_key"] == cache_key
        assert data["cache_hit"] is False
        assert data["provider_id"] == "placeholder"
        assert "timestamp" in data
        assert data["output_path"] == str(out_path)

    def test_appends_multiple_runs(self, tmp_path: Path) -> None:
        episode_dir = tmp_path / "ep01"
        episode_dir.mkdir()
        out_path = episode_dir / "assets" / "fox.png"
        out_path.parent.mkdir(parents=True)
        out_path.write_bytes(b"fake")

        request = make_request(out_path=out_path)
        cache_key = compute_cache_key(request)
        asset = make_asset(out_path, cache_key)

        log_generation_run(episode_dir, request, asset, cache_hit=False)
        log_generation_run(episode_dir, request, asset, cache_hit=True)

        log_path = episode_dir / "logs" / "gen_runs.jsonl"
        lines = log_path.read_text().strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0])["cache_hit"] is False
        assert json.loads(lines[1])["cache_hit"] is True

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

from .config import ConfigError
from .prompting import PromptResolutionError, PromptResolver, log_resolved_prompt
from .provenance import now_utc_iso, write_sidecar, append_jsonl
from .registry import ProviderRegistry
from .types import ImageGenRequest


@dataclass
class GenerationResult:
    generated: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    errors: list[tuple[str, str]] = field(default_factory=list)


@dataclass(frozen=True)
class AssetSpec:
    asset_type: str
    asset_id: str
    template_name: str
    params: dict[str, Any]
    width: int
    height: int
    out_path: Path


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _load_canon_characters(show_dir: Path) -> dict[str, dict[str, Any]]:
    path = show_dir / "canon" / "characters.yaml"
    if not path.exists():
        return {}
    data = _load_yaml(path)
    return {c["id"]: c for c in data.get("characters", [])}


def _load_canon_biomes(show_dir: Path) -> dict[str, dict[str, Any]]:
    path = show_dir / "canon" / "biomes.yaml"
    if not path.exists():
        return {}
    data = _load_yaml(path)
    return {b["id"]: b for b in data.get("biomes", [])}


def _compute_cache_key(
    asset_type: str,
    asset_id: str,
    resolved_prompt: str,
    width: int,
    height: int,
    provider_id: str,
) -> str:
    key_data = f"{asset_type}:{asset_id}:{width}x{height}:{provider_id}:{resolved_prompt}"
    return hashlib.sha256(key_data.encode()).hexdigest()[:16]


def _read_sidecar_cache_key(out_path: Path) -> Optional[str]:
    sidecar = out_path.with_suffix(out_path.suffix + ".json")
    if not sidecar.exists():
        return None
    try:
        data = json.loads(sidecar.read_text(encoding="utf-8"))
        return data.get("cache_key")
    except (json.JSONDecodeError, OSError):
        return None


def discover_assets(
    episode_yaml: Path,
    show_dir: Path,
) -> list[AssetSpec]:
    episode_dir = episode_yaml.parent
    episode_data = _load_yaml(episode_yaml)
    
    shotlist_path = episode_dir / "shotlist.yaml"
    if not shotlist_path.exists():
        return []
    shotlist_data = _load_yaml(shotlist_path)
    
    characters = _load_canon_characters(show_dir)
    biomes = _load_canon_biomes(show_dir)
    
    style_profile = episode_data.get("style_profile", "comic_low_fps_v1")
    episode_biome = episode_data.get("biome", "")
    
    assets: list[AssetSpec] = []
    seen_bg_ids: set[str] = set()
    seen_cutout_ids: set[str] = set()
    
    for shot in shotlist_data.get("shots", []):
        bg_id = shot.get("bg")
        if bg_id and bg_id not in seen_bg_ids:
            seen_bg_ids.add(bg_id)
            
            biome_id = episode_biome
            biome_label = biomes.get(biome_id, {}).get("label", biome_id)
            
            assets.append(AssetSpec(
                asset_type="background",
                asset_id=bg_id,
                template_name="background.j2",
                params={
                    "biome_id": biome_id,
                    "biome_label": biome_label,
                    "style_profile": style_profile,
                    "bg_id": bg_id,
                },
                width=1920,
                height=1080,
                out_path=episode_dir / "assets" / "bg" / f"{bg_id}.png",
            ))
        
        for actor in shot.get("actors", []):
            char_id = actor.get("character")
            pose = actor.get("pose", "idle")
            expression = actor.get("expression", "neutral")
            
            if not char_id:
                continue
            
            cutout_id = f"{char_id}_{pose}"
            if cutout_id in seen_cutout_ids:
                continue
            seen_cutout_ids.add(cutout_id)
            
            char_data = characters.get(char_id, {})
            char_label = char_data.get("label", char_id)
            char_role = char_data.get("role", "")
            
            assets.append(AssetSpec(
                asset_type="cutout",
                asset_id=cutout_id,
                template_name="cutout.j2",
                params={
                    "character_id": char_id,
                    "character_label": char_label,
                    "character_role": char_role,
                    "pose_id": pose,
                    "expression_id": expression,
                    "style_profile": style_profile,
                },
                width=1536,
                height=1536,
                out_path=episode_dir / "assets" / "cutouts" / f"{cutout_id}.png",
            ))
    
    return assets


def generate_episode_assets(
    episode_yaml: Path,
    force: bool = False,
    changed_only: bool = False,
    provider_override: Optional[str] = None,
) -> GenerationResult:
    result = GenerationResult()
    
    episode_dir = episode_yaml.parent
    show_dir = episode_yaml.parent.parent.parent / "show"
    if not show_dir.exists():
        show_dir = Path("show")
    
    try:
        registry = ProviderRegistry.from_config_file()
    except ConfigError as e:
        result.errors.append(("config", str(e)))
        return result
    
    provider_name = provider_override or registry.config.default_provider
    try:
        provider = registry.get_provider(provider_name)
    except ConfigError as e:
        result.errors.append(("provider", str(e)))
        return result
    
    prompts_dir = show_dir / "prompts"
    if not prompts_dir.exists():
        result.errors.append(("prompts", f"Prompts directory not found: {prompts_dir}"))
        return result
    
    prompt_resolver = PromptResolver(prompts_dir)
    
    assets = discover_assets(episode_yaml, show_dir)
    
    gen_log_path = episode_dir / "logs" / "gen.jsonl"
    
    for spec in assets:
        try:
            resolved = prompt_resolver.resolve(spec.template_name, spec.params)
        except PromptResolutionError as e:
            result.errors.append((spec.asset_id, str(e)))
            continue
        
        cache_key = _compute_cache_key(
            spec.asset_type,
            spec.asset_id,
            resolved.resolved_text,
            spec.width,
            spec.height,
            provider.provider_id,
        )
        
        if not force and spec.out_path.exists():
            existing_cache_key = _read_sidecar_cache_key(spec.out_path)
            if existing_cache_key == cache_key:
                result.skipped.append(spec.asset_id)
                continue
            elif not changed_only:
                pass
            else:
                if existing_cache_key == cache_key:
                    result.skipped.append(spec.asset_id)
                    continue
        
        request = ImageGenRequest(
            asset_type=spec.asset_type,
            asset_id=spec.asset_id,
            template_name=spec.template_name,
            resolved_prompt=resolved.resolved_text,
            params=spec.params,
            width=spec.width,
            height=spec.height,
            out_path=spec.out_path,
            provider_id=provider.provider_id,
        )
        
        try:
            generated = provider.generate(request)
        except Exception as e:
            result.errors.append((spec.asset_id, str(e)))
            continue
        
        log_resolved_prompt(episode_dir, spec.asset_id, resolved)
        
        sidecar_payload = {
            "asset_id": spec.asset_id,
            "asset_type": spec.asset_type,
            "cache_key": cache_key,
            "output_hash": generated.output_hash,
            "provider_id": generated.provider_id,
            "model_id": generated.model_id,
            "template_name": spec.template_name,
            "params": spec.params,
            "resolved_prompt": resolved.resolved_text,
            "timestamp": now_utc_iso(),
        }
        write_sidecar(spec.out_path, sidecar_payload)
        
        log_entry = {
            "event": "asset_generated",
            "asset_id": spec.asset_id,
            "asset_type": spec.asset_type,
            "provider_id": generated.provider_id,
            "cache_key": cache_key,
            "output_hash": generated.output_hash,
            "out_path": str(spec.out_path),
            "timestamp": now_utc_iso(),
        }
        append_jsonl(gen_log_path, log_entry)
        
        result.generated.append(spec.asset_id)
    
    return result

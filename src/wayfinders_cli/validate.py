from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from .canon import load_canon
from .io import load_model
from .schema import Episode, ShotList


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str]
    missing_files: list[str]


def repo_root_from(path: Path) -> Path:
    p = path.resolve()
    for parent in [p] + list(p.parents):
        if (parent / "pyproject.toml").exists():
            return parent
    return p.parent


def validate_episode(episode_path: Path, allow_missing_assets: bool = False) -> ValidationResult:
    errors: list[str] = []
    missing: list[str] = []

    root = repo_root_from(episode_path)
    canon = load_canon(root)

    try:
        ep = load_model(Episode, episode_path)
    except ValidationError as e:
        return ValidationResult(False, [str(e)], [])
    except Exception as e:
        return ValidationResult(False, [f"Failed reading episode.yaml: {e}"], [])

    shotlist_path = episode_path.parent / "shotlist.yaml"
    try:
        sl = load_model(ShotList, shotlist_path)
    except ValidationError as e:
        return ValidationResult(False, [f"{shotlist_path}: {e}"], [])
    except Exception as e:
        return ValidationResult(False, [f"Failed reading shotlist.yaml: {e}"], [])

    for c in ep.cast:
        if c not in canon.characters:
            errors.append(f"Unknown character id in episode.cast: {c}")
    if ep.biome not in canon.biomes:
        errors.append(f"Unknown biome id: {ep.biome}")

    for sh in sl.shots:
        for a in sh.actors:
            if a.character not in canon.characters:
                errors.append(f"{sh.id}: unknown actor character '{a.character}'")
        for ov in sh.overlays:
            if ov.id not in canon.overlays:
                errors.append(f"{sh.id}: unknown overlay '{ov.id}'")
        for fx in sh.fx:
            if fx not in canon.fx:
                errors.append(f"{sh.id}: unknown fx '{fx}'")

    assets_dir = episode_path.parent / "assets"
    for sh in sl.shots:
        bg_file = assets_dir / "bgs" / f"{sh.bg}.png"
        if not bg_file.exists():
            missing.append(str(bg_file))
        for a in sh.actors:
            ch_file = assets_dir / "chars" / a.character / f"{a.pose}_{a.expression}.png"
            if not ch_file.exists():
                missing.append(str(ch_file))

    if allow_missing_assets:
        return ValidationResult(len(errors) == 0, errors, missing)

    ok = (len(errors) == 0) and (len(missing) == 0)
    return ValidationResult(ok, errors, missing)

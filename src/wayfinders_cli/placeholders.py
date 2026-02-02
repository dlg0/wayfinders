from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .io import load_model
from .schema import Episode, ShotList

try:
    from PIL import Image, ImageDraw
except Exception:
    Image = None  # type: ignore
    ImageDraw = None  # type: ignore


@dataclass
class PlaceholderResult:
    created: list[str]
    skipped: list[str]


def _require_pillow():
    if Image is None:
        raise RuntimeError(
            "Pillow is required. Install with: uv pip install -e '.[placeholders]'"
        )


def create_placeholders(episode_path: Path, force: bool = False) -> PlaceholderResult:
    _require_pillow()
    ep = load_model(Episode, episode_path)
    sl = load_model(ShotList, episode_path.parent / "shotlist.yaml")

    assets_dir = episode_path.parent / "assets"
    created: list[str] = []
    skipped: list[str] = []

    # backgrounds
    for sh in sl.shots:
        out = assets_dir / "bgs" / f"{sh.bg}.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.exists() and not force:
            skipped.append(str(out))
            continue
        img = Image.new("RGBA", ep.render.resolution, (240, 240, 240, 255))
        d = ImageDraw.Draw(img)
        d.text((24, 24), f"BG: {sh.bg}\nShot: {sh.id}\nBiome: {ep.biome}", fill=(0, 0, 0, 255))
        img.save(out)
        created.append(str(out))

    # cutouts
    for sh in sl.shots:
        for a in sh.actors:
            out = assets_dir / "chars" / a.character / f"{a.pose}_{a.expression}.png"
            out.parent.mkdir(parents=True, exist_ok=True)
            if out.exists() and not force:
                skipped.append(str(out))
                continue
            img = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            d.rectangle([64, 64, 960, 960], outline=(0, 0, 0, 255), width=6)
            d.text((90, 90), f"{a.character}\n{a.pose}\n{a.expression}", fill=(0, 0, 0, 255))
            img.save(out)
            created.append(str(out))

    # endcard paper helper
    end = assets_dir / "bgs" / "bg_endcard_paper.png"
    if (not end.exists()) or force:
        img = Image.new("RGBA", ep.render.resolution, (250, 245, 235, 255))
        d = ImageDraw.Draw(img)
        d.text((24, 24), "ENDCARD PAPER", fill=(0, 0, 0, 255))
        end.parent.mkdir(parents=True, exist_ok=True)
        img.save(end)
        created.append(str(end))

    return PlaceholderResult(created, skipped)

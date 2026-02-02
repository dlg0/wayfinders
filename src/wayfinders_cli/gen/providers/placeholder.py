from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from ..provider import ImageProvider
from ..types import GeneratedAsset, ImageGenRequest

if TYPE_CHECKING:
    from ..config import PlaceholderProviderConfig

try:
    from PIL import Image, ImageDraw
except ImportError:
    Image = None  # type: ignore
    ImageDraw = None  # type: ignore


def _require_pillow() -> None:
    if Image is None:
        raise RuntimeError(
            "Pillow is required for placeholder generation. "
            "Install with: uv pip install -e '.[placeholders]'"
        )


ASSET_TYPE_COLORS = {
    "background": (240, 240, 240, 255),
    "cutout": (200, 220, 255, 255),
    "prop": (220, 255, 220, 255),
}


class PlaceholderProvider(ImageProvider):
    def __init__(self, config: "PlaceholderProviderConfig | None" = None):
        self._config = config

    @property
    def provider_id(self) -> str:
        return "placeholder"

    def generate(self, req: ImageGenRequest) -> GeneratedAsset:
        _require_pillow()

        color = ASSET_TYPE_COLORS.get(req.asset_type, (230, 230, 230, 255))
        if req.asset_type == "cutout":
            img = Image.new("RGBA", (req.width, req.height), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            margin = min(req.width, req.height) // 16
            d.rectangle(
                [margin, margin, req.width - margin, req.height - margin],
                fill=color,
                outline=(0, 0, 0, 255),
                width=4,
            )
        else:
            img = Image.new("RGBA", (req.width, req.height), color)
            d = ImageDraw.Draw(img)

        label_lines = [
            f"Type: {req.asset_type}",
            f"ID: {req.asset_id}",
            f"Template: {req.template_name}",
            f"Size: {req.width}x{req.height}",
        ]
        label = "\n".join(label_lines)
        d.text((24, 24), label, fill=(0, 0, 0, 255))

        req.out_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(req.out_path)

        file_bytes = req.out_path.read_bytes()
        output_hash = hashlib.sha256(file_bytes).hexdigest()[:16]
        cache_key = self._compute_cache_key(req)

        return GeneratedAsset(
            out_path=req.out_path,
            output_hash=output_hash,
            cache_key=cache_key,
            provider_id=self.provider_id,
            model_id=None,
        )

    def _compute_cache_key(self, req: ImageGenRequest) -> str:
        key_data = f"{req.asset_type}:{req.asset_id}:{req.width}x{req.height}:{req.resolved_prompt}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]

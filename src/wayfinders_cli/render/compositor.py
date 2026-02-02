from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

try:
    from PIL import Image
except Exception:
    Image = None  # type: ignore

if TYPE_CHECKING:
    from PIL.Image import Image as PILImage

from .ir import ShotIR, CameraMoveIR


class CompositorError(Exception):
    pass


class MissingAssetError(CompositorError):
    def __init__(self, asset_type: str, asset_id: str, path: Path):
        self.asset_type = asset_type
        self.asset_id = asset_id
        self.path = path
        super().__init__(f"Missing {asset_type} asset: {asset_id} (expected at {path})")


def _require_pillow():
    if Image is None:
        raise RuntimeError(
            "Pillow required. Install: uv pip install -e '.[placeholders]'"
        )


class Compositor:
    def __init__(self, assets_dir: Path, resolution: tuple[int, int] = (1920, 1080)):
        _require_pillow()
        self.assets_dir = assets_dir
        self.resolution = resolution
        self._bg_cache: dict[str, PILImage] = {}
        self._cutout_cache: dict[str, PILImage] = {}

    def render_frame(
        self,
        shot: ShotIR,
        frame_in_shot: int = 0,
    ) -> "PILImage":
        w, h = self.resolution

        bg_img = self._load_bg(shot.bg)
        canvas = bg_img.copy()

        if shot.camera.move != "none":
            canvas = self._apply_camera(canvas, shot.camera, frame_in_shot, shot.frame_count)

        for idx, actor in enumerate(shot.actors):
            cutout = self._load_cutout(actor.character, actor.pose, actor.expression)
            x, y, scale = self._resolve_actor_position(actor, idx, len(shot.actors))
            cutout = self._scale_cutout(cutout, scale)
            canvas = self._composite_cutout(canvas, cutout, x, y)

        for overlay in shot.overlays:
            canvas = self._apply_overlay(canvas, overlay)

        return canvas

    def _load_bg(self, bg_id: str) -> "PILImage":
        if bg_id in self._bg_cache:
            return self._bg_cache[bg_id]

        bg_path = self.assets_dir / "bg" / f"{bg_id}.png"
        if not bg_path.exists():
            raise MissingAssetError("background", bg_id, bg_path)

        img = Image.open(bg_path).convert("RGBA")
        if img.size != self.resolution:
            img = img.resize(self.resolution, Image.Resampling.LANCZOS)
        self._bg_cache[bg_id] = img
        return img

    def _load_cutout(self, character: str, pose: str, expression: str) -> "PILImage":
        cutout_id = f"{character}_{pose}_{expression}"
        if cutout_id in self._cutout_cache:
            return self._cutout_cache[cutout_id]

        cutout_path = self.assets_dir / "cutouts" / f"{cutout_id}.png"
        if not cutout_path.exists():
            fallback_id = f"{character}_{pose}"
            cutout_path = self.assets_dir / "cutouts" / f"{fallback_id}.png"
            if not cutout_path.exists():
                raise MissingAssetError("cutout", cutout_id, cutout_path)

        img = Image.open(cutout_path).convert("RGBA")
        self._cutout_cache[cutout_id] = img
        return img

    def _resolve_actor_position(
        self, actor, idx: int, total_actors: int
    ) -> tuple[float, float, float]:
        w, h = self.resolution

        if actor.x is not None:
            x = actor.x
        else:
            if total_actors == 1:
                x = 0.5
            else:
                spacing = 0.6 / max(total_actors - 1, 1)
                x = 0.2 + idx * spacing

        if actor.y is not None:
            y = actor.y
        else:
            y = 0.7

        scale = actor.scale if actor.scale is not None else 0.5

        return x, y, scale

    def _scale_cutout(self, cutout: "PILImage", scale: float) -> "PILImage":
        target_h = int(self.resolution[1] * scale)
        aspect = cutout.width / cutout.height
        target_w = int(target_h * aspect)
        return cutout.resize((target_w, target_h), Image.Resampling.LANCZOS)

    def _composite_cutout(
        self, canvas: "PILImage", cutout: "PILImage", x: float, y: float
    ) -> "PILImage":
        w, h = self.resolution
        cx = int(x * w - cutout.width / 2)
        cy = int(y * h - cutout.height)
        canvas.paste(cutout, (cx, cy), cutout)
        return canvas

    def _apply_camera(
        self,
        img: "PILImage",
        camera: CameraMoveIR,
        frame_idx: int,
        total_frames: int,
    ) -> "PILImage":
        if total_frames <= 1:
            t = 0.0
        else:
            t = frame_idx / (total_frames - 1)

        pan_x = camera.x0 + (camera.x1 - camera.x0) * t
        pan_y = camera.y0 + (camera.y1 - camera.y0) * t
        zoom = camera.z0 + (camera.z1 - camera.z0) * t

        w, h = self.resolution
        orig_w, orig_h = img.size

        if camera.move == "shake" and camera.strength > 0:
            import math
            pan_x += camera.strength * 0.01 * math.sin(frame_idx * 0.5)
            pan_y += camera.strength * 0.01 * math.cos(frame_idx * 0.7)

        if zoom != 1.0:
            new_w = int(orig_w * zoom)
            new_h = int(orig_h * zoom)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        offset_x = int(pan_x * w)
        offset_y = int(pan_y * h)

        result = Image.new("RGBA", (w, h), (0, 0, 0, 255))

        paste_x = (w - img.width) // 2 - offset_x
        paste_y = (h - img.height) // 2 - offset_y
        result.paste(img, (paste_x, paste_y))

        return result

    def _apply_overlay(self, canvas: "PILImage", overlay) -> "PILImage":
        from PIL import ImageDraw, ImageFont

        if overlay.text:
            d = ImageDraw.Draw(canvas)
            w, h = self.resolution
            x = overlay.x if overlay.x is not None else 0.5
            y = overlay.y if overlay.y is not None else 0.9
            text_x = int(x * w)
            text_y = int(y * h)
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 48)
            except Exception:
                font = ImageFont.load_default()
            bbox = d.textbbox((0, 0), overlay.text, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            d.text((text_x - tw // 2, text_y - th // 2), overlay.text, fill=(0, 0, 0, 255), font=font)
        return canvas

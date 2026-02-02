from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field, model_validator


class RenderSettings(BaseModel):
    fps: int = 24
    resolution: tuple[int, int] = (1920, 1080)


class EpisodeAssets(BaseModel):
    pose_packs: list[str] = Field(default_factory=list)
    bg_pack: str
    overlay_pack: str


class EpisodeNotes(BaseModel):
    rule_of_day: str
    logline: str


class Episode(BaseModel):
    id: str = Field(pattern=r"^s\d{2}e\d{2}$")
    title: str
    runtime_target_sec: int = Field(ge=60, le=3600)
    biome: str
    cast: list[str] = Field(min_length=1)
    style_profile: str = "comic_low_fps_v1"
    render: RenderSettings = RenderSettings()
    assets: EpisodeAssets
    notes: EpisodeNotes


CameraMoveType = Literal["none", "pan", "slowpush", "shake"]


class CameraMove(BaseModel):
    move: CameraMoveType = "none"
    x0: float = 0.0
    x1: float = 0.0
    y0: float = 0.0
    y1: float = 0.0
    z0: float = 1.0
    z1: float = 1.0
    strength: float = 0.0


class ActorRef(BaseModel):
    character: str
    pose: str
    expression: str = "neutral"
    mouth_track: Optional[str] = None


class OverlayRef(BaseModel):
    id: str
    text: Optional[str] = None


class AudioLevels(BaseModel):
    dialogue: float = Field(default=1.0, ge=0.0, le=1.0)
    sfx: float = Field(default=0.8, ge=0.0, le=1.0)
    music: float = Field(default=0.3, ge=0.0, le=1.0)


class AudioRef(BaseModel):
    dialogue: list[str] = Field(default_factory=list)
    sfx: list[str] = Field(default_factory=list)
    music_bed: Optional[str] = None
    levels: Optional[AudioLevels] = None


class Shot(BaseModel):
    id: str
    dur_sec: float = Field(gt=0.0, le=60.0)
    bg: str
    camera: CameraMove = CameraMove()
    actors: list[ActorRef] = Field(default_factory=list)
    overlays: list[OverlayRef] = Field(default_factory=list)
    fx: list[str] = Field(default_factory=list)
    audio: AudioRef = AudioRef()

    @model_validator(mode="after")
    def _no_dupe_chars(self):
        chars = [a.character for a in self.actors]
        if len(chars) != len(set(chars)):
            raise ValueError(f"Shot {self.id}: duplicate character")
        return self


class ShotList(BaseModel):
    version: int = 1
    shots: list[Shot] = Field(default_factory=list)

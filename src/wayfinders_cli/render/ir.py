from __future__ import annotations

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field

CameraMoveType = Literal["none", "pan", "slowpush", "shake"]

class CameraMoveIR(BaseModel):
    move: CameraMoveType = "none"
    x0: float = 0.0
    x1: float = 0.0
    y0: float = 0.0
    y1: float = 0.0
    z0: float = 1.0
    z1: float = 1.0
    strength: float = 0.0

class ActorIR(BaseModel):
    character: str
    pose: str
    expression: str = "neutral"
    mouth_track: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None
    scale: Optional[float] = None
    rotation_deg: Optional[float] = None

class OverlayIR(BaseModel):
    id: str
    text: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None

class AudioIR(BaseModel):
    dialogue: list[str] = Field(default_factory=list)
    sfx: list[str] = Field(default_factory=list)
    music: Optional[str] = None

class ShotIR(BaseModel):
    id: str
    dur_sec: float = Field(gt=0.0, le=60.0)
    frame_count: int = Field(ge=1)
    bg: str
    bg_layers: Optional[dict[str, str]] = None
    camera: CameraMoveIR = CameraMoveIR()
    actors: list[ActorIR] = Field(default_factory=list)
    overlays: list[OverlayIR] = Field(default_factory=list)
    fx: list[str] = Field(default_factory=list)
    audio: AudioIR = AudioIR()
    notes: Optional[dict[str, Any]] = None

class TimelineIR(BaseModel):
    schema_version: int = 1
    episode_id: str
    fps: int = 24
    resolution: tuple[int, int] = (1920, 1080)
    shots: list[ShotIR] = Field(default_factory=list)

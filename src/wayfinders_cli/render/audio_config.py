from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class FadeSettings(BaseModel):
    fade_in_sec: float = Field(default=0.0, ge=0.0)
    fade_out_sec: float = Field(default=0.0, ge=0.0)


class TrackLevels(BaseModel):
    dialogue: float = Field(default=1.0, ge=0.0, le=1.0)
    sfx: float = Field(default=0.8, ge=0.0, le=1.0)
    music: float = Field(default=0.3, ge=0.0, le=1.0)


class AudioSpec(BaseModel):
    """Per-shot audio configuration."""

    shot_id: str
    start_sec: float
    duration_sec: float
    dialogue_files: list[str] = Field(default_factory=list)
    sfx_files: list[str] = Field(default_factory=list)
    levels: TrackLevels = TrackLevels()
    fade: FadeSettings = FadeSettings()


class EpisodeAudioConfig(BaseModel):
    """Episode-level audio configuration."""

    music_bed: Optional[str] = None
    master_levels: TrackLevels = TrackLevels()
    fade_in_sec: float = Field(default=1.0, ge=0.0)
    fade_out_sec: float = Field(default=2.0, ge=0.0)
    shots: list[AudioSpec] = Field(default_factory=list)

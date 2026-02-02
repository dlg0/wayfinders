from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from .ir import TimelineIR


class Renderer(ABC):
    """Render outputs from a Timeline IR."""

    @abstractmethod
    def build_frames(self, timeline: TimelineIR, episode_dir: Path) -> Path: ...

    @abstractmethod
    def build_animatic(self, timeline: TimelineIR, episode_dir: Path) -> Path: ...

    @abstractmethod
    def build_final(self, timeline: TimelineIR, episode_dir: Path) -> Path: ...

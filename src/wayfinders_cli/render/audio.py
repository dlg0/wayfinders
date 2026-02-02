from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .ffmpeg import check_ffmpeg, run_ffmpeg
from .audio_config import AudioSpec, EpisodeAudioConfig, TrackLevels, FadeSettings

logger = logging.getLogger(__name__)


@dataclass
class AudioTrack:
    path: Path
    start_sec: float
    duration_sec: Optional[float] = None
    volume: float = 1.0
    fade_in_sec: float = 0.0
    fade_out_sec: float = 0.0


@dataclass
class MixResult:
    success: bool
    output_path: Optional[Path] = None
    tracks_used: int = 0
    tracks_missing: list[str] = field(default_factory=list)
    message: str = ""


class AudioMixerError(RuntimeError):
    """Raised when audio mixing fails."""


class AudioMixer:
    """Mixes dialogue, sfx, and music tracks for an episode."""

    def __init__(
        self,
        episode_dir: Path,
        config: EpisodeAudioConfig,
    ):
        self.episode_dir = episode_dir
        self.config = config
        self.audio_dir = episode_dir / "assets" / "audio"
        self.output_dir = episode_dir / "renders"

    def _resolve_audio_path(self, filename: str) -> Optional[Path]:
        for ext in ["", ".wav", ".mp3", ".aac", ".ogg"]:
            candidate = self.audio_dir / f"{filename}{ext}"
            if candidate.exists():
                return candidate
        path = self.audio_dir / filename
        if path.exists():
            return path
        return None

    def _collect_tracks(self) -> tuple[list[AudioTrack], list[str]]:
        tracks: list[AudioTrack] = []
        missing: list[str] = []

        if self.config.music_bed:
            music_path = self._resolve_audio_path(self.config.music_bed)
            if music_path:
                tracks.append(
                    AudioTrack(
                        path=music_path,
                        start_sec=0.0,
                        volume=self.config.master_levels.music,
                        fade_in_sec=self.config.fade_in_sec,
                        fade_out_sec=self.config.fade_out_sec,
                    )
                )
            else:
                missing.append(f"music_bed:{self.config.music_bed}")

        for shot in self.config.shots:
            for dialogue_file in shot.dialogue_files:
                path = self._resolve_audio_path(dialogue_file)
                if path:
                    tracks.append(
                        AudioTrack(
                            path=path,
                            start_sec=shot.start_sec,
                            volume=shot.levels.dialogue * self.config.master_levels.dialogue,
                            fade_in_sec=shot.fade.fade_in_sec,
                            fade_out_sec=shot.fade.fade_out_sec,
                        )
                    )
                else:
                    missing.append(f"{shot.shot_id}:dialogue:{dialogue_file}")

            for sfx_file in shot.sfx_files:
                path = self._resolve_audio_path(sfx_file)
                if path:
                    tracks.append(
                        AudioTrack(
                            path=path,
                            start_sec=shot.start_sec,
                            volume=shot.levels.sfx * self.config.master_levels.sfx,
                            fade_in_sec=shot.fade.fade_in_sec,
                            fade_out_sec=shot.fade.fade_out_sec,
                        )
                    )
                else:
                    missing.append(f"{shot.shot_id}:sfx:{sfx_file}")

        return tracks, missing

    def _build_ffmpeg_filter(self, tracks: list[AudioTrack], total_duration: float) -> str:
        if not tracks:
            return ""

        filter_parts = []
        track_labels = []

        for i, track in enumerate(tracks):
            label = f"a{i}"
            filters = []

            if track.volume != 1.0:
                filters.append(f"volume={track.volume}")

            if track.fade_in_sec > 0:
                filters.append(f"afade=t=in:st=0:d={track.fade_in_sec}")

            if track.fade_out_sec > 0:
                fade_start = total_duration - track.fade_out_sec
                if fade_start > 0:
                    filters.append(f"afade=t=out:st={fade_start}:d={track.fade_out_sec}")

            if track.start_sec > 0:
                filters.append(f"adelay={int(track.start_sec * 1000)}|{int(track.start_sec * 1000)}")

            if filters:
                filter_chain = ",".join(filters)
                filter_parts.append(f"[{i}:a]{filter_chain}[{label}]")
            else:
                filter_parts.append(f"[{i}:a]acopy[{label}]")

            track_labels.append(f"[{label}]")

        mix_inputs = "".join(track_labels)
        filter_parts.append(f"{mix_inputs}amix=inputs={len(tracks)}:duration=longest:normalize=0[out]")

        return ";".join(filter_parts)

    def mix(self, output_filename: str = "audio_mix.wav") -> MixResult:
        if not check_ffmpeg():
            logger.warning("ffmpeg not available, skipping audio mix")
            return MixResult(
                success=False,
                message="ffmpeg not available",
            )

        tracks, missing = self._collect_tracks()

        if missing:
            for m in missing:
                logger.warning(f"Missing audio asset: {m}")

        if not tracks:
            logger.warning("No audio tracks found, skipping mix")
            return MixResult(
                success=True,
                tracks_used=0,
                tracks_missing=missing,
                message="no audio tracks available",
            )

        self.output_dir.mkdir(parents=True, exist_ok=True)
        output_path = self.output_dir / output_filename

        total_duration = 0.0
        for shot in self.config.shots:
            shot_end = shot.start_sec + shot.duration_sec
            if shot_end > total_duration:
                total_duration = shot_end

        if total_duration == 0:
            total_duration = 60.0

        cmd = ["ffmpeg", "-y"]

        for track in tracks:
            cmd.extend(["-i", str(track.path)])

        filter_complex = self._build_ffmpeg_filter(tracks, total_duration)
        cmd.extend(["-filter_complex", filter_complex])
        cmd.extend(["-map", "[out]"])
        cmd.extend(["-t", str(total_duration)])
        cmd.append(str(output_path))

        try:
            run_ffmpeg(cmd)
            return MixResult(
                success=True,
                output_path=output_path,
                tracks_used=len(tracks),
                tracks_missing=missing,
                message=f"mixed {len(tracks)} tracks",
            )
        except Exception as e:
            logger.error(f"Audio mix failed: {e}")
            return MixResult(
                success=False,
                tracks_missing=missing,
                message=str(e),
            )


def build_audio_config_from_shotlist(
    shots: list,
    music_bed: Optional[str] = None,
    levels: Optional[dict] = None,
) -> EpisodeAudioConfig:
    """Build EpisodeAudioConfig from a list of Shot objects."""
    audio_specs = []
    current_time = 0.0

    default_levels = TrackLevels()
    if levels:
        default_levels = TrackLevels(
            dialogue=levels.get("dialogue", 1.0),
            sfx=levels.get("sfx", 0.8),
            music=levels.get("music", 0.3),
        )

    for shot in shots:
        dialogue_files = []
        for d in shot.audio.dialogue:
            if ":" in d:
                filename = d.split(":", 1)[1].strip()
                dialogue_files.append(filename.replace(" ", "_").lower())
            else:
                dialogue_files.append(d)

        audio_specs.append(
            AudioSpec(
                shot_id=shot.id,
                start_sec=current_time,
                duration_sec=shot.dur_sec,
                dialogue_files=dialogue_files,
                sfx_files=list(shot.audio.sfx),
                levels=default_levels,
                fade=FadeSettings(),
            )
        )
        current_time += shot.dur_sec

    return EpisodeAudioConfig(
        music_bed=music_bed,
        master_levels=default_levels,
        shots=audio_specs,
    )


def mix_episode_audio(
    episode_yaml: Path,
    music_bed: Optional[str] = None,
    levels: Optional[dict] = None,
) -> MixResult:
    """High-level function to mix audio for an episode."""
    import yaml
    from ..schema import ShotList

    episode_dir = episode_yaml.parent
    shotlist_path = episode_dir / "shotlist.yaml"

    if not shotlist_path.exists():
        return MixResult(
            success=False,
            message=f"shotlist.yaml not found at {shotlist_path}",
        )

    with open(shotlist_path, "r", encoding="utf-8") as f:
        shotlist_data = yaml.safe_load(f)

    shotlist = ShotList.model_validate(shotlist_data)
    config = build_audio_config_from_shotlist(
        shotlist.shots,
        music_bed=music_bed,
        levels=levels,
    )

    mixer = AudioMixer(episode_dir, config)
    return mixer.mix()

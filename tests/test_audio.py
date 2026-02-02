from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import patch

from wayfinders_cli.render.audio import (
    AudioMixer,
    AudioTrack,
    build_audio_config_from_shotlist,
    mix_episode_audio,
)
from wayfinders_cli.render.audio_config import (
    AudioSpec,
    EpisodeAudioConfig,
    FadeSettings,
    TrackLevels,
)
from wayfinders_cli.schema import Shot, AudioRef, CameraMove


class TestAudioSpec:
    def test_default_values(self):
        spec = AudioSpec(shot_id="S01", start_sec=0.0, duration_sec=5.0)
        assert spec.dialogue_files == []
        assert spec.sfx_files == []
        assert spec.levels.dialogue == 1.0
        assert spec.levels.sfx == 0.8
        assert spec.levels.music == 0.3

    def test_with_files(self):
        spec = AudioSpec(
            shot_id="S01",
            start_sec=0.0,
            duration_sec=5.0,
            dialogue_files=["spencer_line1.wav"],
            sfx_files=["footsteps.wav", "wind.wav"],
        )
        assert len(spec.dialogue_files) == 1
        assert len(spec.sfx_files) == 2


class TestEpisodeAudioConfig:
    def test_default_values(self):
        config = EpisodeAudioConfig()
        assert config.music_bed is None
        assert config.fade_in_sec == 1.0
        assert config.fade_out_sec == 2.0
        assert config.shots == []

    def test_with_music_bed(self):
        config = EpisodeAudioConfig(music_bed="episode_theme.wav")
        assert config.music_bed == "episode_theme.wav"


class TestFadeSettings:
    def test_default_values(self):
        fade = FadeSettings()
        assert fade.fade_in_sec == 0.0
        assert fade.fade_out_sec == 0.0

    def test_custom_values(self):
        fade = FadeSettings(fade_in_sec=0.5, fade_out_sec=1.5)
        assert fade.fade_in_sec == 0.5
        assert fade.fade_out_sec == 1.5


class TestTrackLevels:
    def test_default_values(self):
        levels = TrackLevels()
        assert levels.dialogue == 1.0
        assert levels.sfx == 0.8
        assert levels.music == 0.3

    def test_validation_bounds(self):
        with pytest.raises(ValueError):
            TrackLevels(dialogue=1.5)
        with pytest.raises(ValueError):
            TrackLevels(sfx=-0.1)


class TestAudioTrack:
    def test_creation(self, tmp_path: Path):
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio")

        track = AudioTrack(
            path=audio_file,
            start_sec=5.0,
            volume=0.8,
            fade_in_sec=0.5,
        )
        assert track.path == audio_file
        assert track.start_sec == 5.0
        assert track.volume == 0.8
        assert track.fade_in_sec == 0.5
        assert track.fade_out_sec == 0.0


class TestAudioMixer:
    def test_init(self, tmp_path: Path):
        episode_dir = tmp_path / "episode"
        episode_dir.mkdir()
        config = EpisodeAudioConfig()

        mixer = AudioMixer(episode_dir, config)
        assert mixer.episode_dir == episode_dir
        assert mixer.audio_dir == episode_dir / "assets" / "audio"
        assert mixer.output_dir == episode_dir / "renders"

    def test_resolve_audio_path_finds_file(self, tmp_path: Path):
        episode_dir = tmp_path / "episode"
        audio_dir = episode_dir / "assets" / "audio"
        audio_dir.mkdir(parents=True)
        (audio_dir / "test.wav").write_bytes(b"audio")

        mixer = AudioMixer(episode_dir, EpisodeAudioConfig())
        path = mixer._resolve_audio_path("test.wav")
        assert path is not None
        assert path.name == "test.wav"

    def test_resolve_audio_path_finds_without_extension(self, tmp_path: Path):
        episode_dir = tmp_path / "episode"
        audio_dir = episode_dir / "assets" / "audio"
        audio_dir.mkdir(parents=True)
        (audio_dir / "test.wav").write_bytes(b"audio")

        mixer = AudioMixer(episode_dir, EpisodeAudioConfig())
        path = mixer._resolve_audio_path("test")
        assert path is not None
        assert path.name == "test.wav"

    def test_resolve_audio_path_returns_none_for_missing(self, tmp_path: Path):
        episode_dir = tmp_path / "episode"
        mixer = AudioMixer(episode_dir, EpisodeAudioConfig())
        path = mixer._resolve_audio_path("nonexistent")
        assert path is None

    def test_mix_skips_when_no_ffmpeg(self, tmp_path: Path):
        episode_dir = tmp_path / "episode"
        mixer = AudioMixer(episode_dir, EpisodeAudioConfig())

        with patch("wayfinders_cli.render.audio.check_ffmpeg", return_value=False):
            result = mixer.mix()
            assert not result.success
            assert "ffmpeg not available" in result.message

    def test_mix_with_no_tracks(self, tmp_path: Path):
        episode_dir = tmp_path / "episode"
        mixer = AudioMixer(episode_dir, EpisodeAudioConfig())

        with patch("wayfinders_cli.render.audio.check_ffmpeg", return_value=True):
            result = mixer.mix()
            assert result.success
            assert result.tracks_used == 0
            assert "no audio tracks" in result.message

    def test_collect_tracks_reports_missing(self, tmp_path: Path):
        episode_dir = tmp_path / "episode"
        config = EpisodeAudioConfig(
            music_bed="missing_music.wav",
            shots=[
                AudioSpec(
                    shot_id="S01",
                    start_sec=0.0,
                    duration_sec=5.0,
                    dialogue_files=["missing_dialogue.wav"],
                    sfx_files=["missing_sfx.wav"],
                )
            ],
        )
        mixer = AudioMixer(episode_dir, config)
        tracks, missing = mixer._collect_tracks()

        assert len(tracks) == 0
        assert len(missing) == 3
        assert "music_bed:missing_music.wav" in missing
        assert "S01:dialogue:missing_dialogue.wav" in missing
        assert "S01:sfx:missing_sfx.wav" in missing

    def test_collect_tracks_finds_existing(self, tmp_path: Path):
        episode_dir = tmp_path / "episode"
        audio_dir = episode_dir / "assets" / "audio"
        audio_dir.mkdir(parents=True)
        (audio_dir / "music.wav").write_bytes(b"music")
        (audio_dir / "dialogue.wav").write_bytes(b"dialogue")
        (audio_dir / "sfx.wav").write_bytes(b"sfx")

        config = EpisodeAudioConfig(
            music_bed="music.wav",
            shots=[
                AudioSpec(
                    shot_id="S01",
                    start_sec=0.0,
                    duration_sec=5.0,
                    dialogue_files=["dialogue.wav"],
                    sfx_files=["sfx.wav"],
                )
            ],
        )
        mixer = AudioMixer(episode_dir, config)
        tracks, missing = mixer._collect_tracks()

        assert len(tracks) == 3
        assert len(missing) == 0

    def test_build_ffmpeg_filter_single_track(self, tmp_path: Path):
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"audio")

        mixer = AudioMixer(tmp_path, EpisodeAudioConfig())
        tracks = [AudioTrack(path=audio_file, start_sec=0.0, volume=1.0)]
        filter_str = mixer._build_ffmpeg_filter(tracks, 10.0)

        assert "[0:a]" in filter_str
        assert "amix=inputs=1" in filter_str
        assert "[out]" in filter_str

    def test_build_ffmpeg_filter_with_volume(self, tmp_path: Path):
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"audio")

        mixer = AudioMixer(tmp_path, EpisodeAudioConfig())
        tracks = [AudioTrack(path=audio_file, start_sec=0.0, volume=0.5)]
        filter_str = mixer._build_ffmpeg_filter(tracks, 10.0)

        assert "volume=0.5" in filter_str

    def test_build_ffmpeg_filter_with_delay(self, tmp_path: Path):
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"audio")

        mixer = AudioMixer(tmp_path, EpisodeAudioConfig())
        tracks = [AudioTrack(path=audio_file, start_sec=5.0, volume=1.0)]
        filter_str = mixer._build_ffmpeg_filter(tracks, 10.0)

        assert "adelay=5000|5000" in filter_str

    def test_build_ffmpeg_filter_with_fades(self, tmp_path: Path):
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"audio")

        mixer = AudioMixer(tmp_path, EpisodeAudioConfig())
        tracks = [
            AudioTrack(
                path=audio_file,
                start_sec=0.0,
                volume=1.0,
                fade_in_sec=1.0,
                fade_out_sec=2.0,
            )
        ]
        filter_str = mixer._build_ffmpeg_filter(tracks, 10.0)

        assert "afade=t=in:st=0:d=1.0" in filter_str
        assert "afade=t=out:st=8.0:d=2.0" in filter_str

    def test_mix_with_real_tracks(self, tmp_path: Path):
        episode_dir = tmp_path / "episode"
        audio_dir = episode_dir / "assets" / "audio"
        audio_dir.mkdir(parents=True)
        renders_dir = episode_dir / "renders"
        renders_dir.mkdir(parents=True)

        (audio_dir / "music.wav").write_bytes(b"music")
        (audio_dir / "dialogue.wav").write_bytes(b"dialogue")

        config = EpisodeAudioConfig(
            music_bed="music.wav",
            shots=[
                AudioSpec(
                    shot_id="S01",
                    start_sec=0.0,
                    duration_sec=5.0,
                    dialogue_files=["dialogue.wav"],
                )
            ],
        )
        mixer = AudioMixer(episode_dir, config)

        with patch("wayfinders_cli.render.audio.check_ffmpeg", return_value=True):
            with patch("wayfinders_cli.render.audio.run_ffmpeg") as mock_run:
                result = mixer.mix()

                assert result.success
                assert result.tracks_used == 2
                mock_run.assert_called_once()

                cmd = mock_run.call_args[0][0]
                assert "ffmpeg" in cmd
                assert "-filter_complex" in cmd


class TestBuildAudioConfigFromShotlist:
    def test_builds_config_from_shots(self):
        shots = [
            Shot(
                id="S01",
                dur_sec=5.0,
                bg="bg_test",
                camera=CameraMove(),
                audio=AudioRef(
                    dialogue=["Spencer: Hello!"],
                    sfx=["footsteps"],
                ),
            ),
            Shot(
                id="S02",
                dur_sec=3.0,
                bg="bg_test",
                camera=CameraMove(),
                audio=AudioRef(
                    dialogue=[],
                    sfx=["wind"],
                ),
            ),
        ]

        config = build_audio_config_from_shotlist(shots)

        assert len(config.shots) == 2
        assert config.shots[0].shot_id == "S01"
        assert config.shots[0].start_sec == 0.0
        assert config.shots[0].duration_sec == 5.0
        assert "hello!" in config.shots[0].dialogue_files[0]
        assert "footsteps" in config.shots[0].sfx_files

        assert config.shots[1].shot_id == "S02"
        assert config.shots[1].start_sec == 5.0
        assert config.shots[1].duration_sec == 3.0

    def test_builds_config_with_music_bed(self):
        shots = []
        config = build_audio_config_from_shotlist(shots, music_bed="theme.wav")
        assert config.music_bed == "theme.wav"

    def test_builds_config_with_custom_levels(self):
        shots = []
        config = build_audio_config_from_shotlist(
            shots,
            levels={"dialogue": 0.9, "sfx": 0.7, "music": 0.2},
        )
        assert config.master_levels.dialogue == 0.9
        assert config.master_levels.sfx == 0.7
        assert config.master_levels.music == 0.2

    def test_timeline_alignment(self):
        shots = [
            Shot(id="S01", dur_sec=5.0, bg="bg", camera=CameraMove(), audio=AudioRef()),
            Shot(id="S02", dur_sec=10.0, bg="bg", camera=CameraMove(), audio=AudioRef()),
            Shot(id="S03", dur_sec=3.0, bg="bg", camera=CameraMove(), audio=AudioRef()),
        ]

        config = build_audio_config_from_shotlist(shots)

        assert config.shots[0].start_sec == 0.0
        assert config.shots[1].start_sec == 5.0
        assert config.shots[2].start_sec == 15.0


class TestMixEpisodeAudio:
    def test_missing_shotlist(self, tmp_path: Path):
        episode_yaml = tmp_path / "episode.yaml"
        episode_yaml.write_text("id: test")

        result = mix_episode_audio(episode_yaml)
        assert not result.success
        assert "shotlist.yaml not found" in result.message

    def test_with_valid_shotlist(self, tmp_path: Path):
        episode_dir = tmp_path / "episode"
        episode_dir.mkdir()

        shotlist_content = """
version: 1
shots:
  - id: S01
    dur_sec: 5
    bg: bg_test
    camera: { move: none }
    actors: []
    overlays: []
    fx: []
    audio: { dialogue: [], sfx: [] }
"""
        (episode_dir / "shotlist.yaml").write_text(shotlist_content)
        episode_yaml = episode_dir / "episode.yaml"
        episode_yaml.write_text("id: test")

        with patch("wayfinders_cli.render.audio.check_ffmpeg", return_value=True):
            result = mix_episode_audio(episode_yaml)
            assert result.success
            assert result.tracks_used == 0

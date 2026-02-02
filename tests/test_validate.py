from pathlib import Path
from wayfinders_cli.validate import validate_episode

def test_validate_example_episode_allows_missing_assets():
    ep = Path("episodes/s01e01_map_forgot_roads/episode.yaml")
    res = validate_episode(ep, allow_missing_assets=True)
    assert res.errors == []
    assert res.ok is True

def test_validate_example_episode_requires_assets_fails_before_placeholders():
    ep = Path("episodes/s01e01_map_forgot_roads/episode.yaml")
    res = validate_episode(ep, allow_missing_assets=False)
    assert res.ok is False
    assert len(res.missing_files) > 0

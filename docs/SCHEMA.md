# Schema overview

## `episode.yaml`
Metadata + settings:
- id, title, runtime_target_sec, biome, cast
- render settings (fps/resolution)
- required asset packs (pose packs, bg pack, overlay pack)

## `shotlist.yaml`
Ordered list of shots:
- background id
- camera move params
- actor cutouts (character, pose, expression)
- overlays, fx, audio cues

Models:
- `src/wayfinders_cli/schema.py`

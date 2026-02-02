# CLI specification (wf)

This is the developer contract for the Wayfinders CLI.

All CLI commands should be run via `uv run wf ...` so the project environment is managed by uv.

## Commands (v1)

### `wf validate <episode.yaml>`
- Loads `episode.yaml` + sibling `shotlist.yaml`
- Schema validation (Pydantic)
- Canon validation (IDs exist in `show/canon/*.yaml`)
- File checks for referenced assets (unless `--allow-missing-assets`)

Exit codes:
- 0: valid
- 2: schema/semantic errors
- 3: missing files

### `wf plan <episode.yaml>`
- Produces a build plan JSON (referenced assets, missing assets)
- Writes `episodes/<ep>/logs/plan.json`

### `wf placeholders <episode.yaml> [--force]`
- Generates placeholder PNGs for all referenced bgs and cutouts (PIL only)

### `wf new-episode <season> <episode> --title ... --biome ...`
- Scaffolds a new episode folder with template YAML and keepfiles

### `wf build-timeline <episode.yaml>`
- Writes Timeline IR to `episodes/<ep>/logs/timeline.json`

### `wf build-animatic <episode.yaml>`
- Renders frames from placeholder BGs (stub) and assembles animatic MP4 if ffmpeg is present.

### `wf canon export-jsonschema`
- Exports JSON schema for the Episode model to `docs/jsonschema/episode.schema.json`

### `wf render export-jsonschema`
- Exports JSON schema for the Timeline IR to `docs/jsonschema/timeline.schema.json`

## Provider interfaces (planned)
- `gen/provider.py`: ImageProvider interface
- `render/renderer.py`: Renderer interface

See `docs/ROADMAP.md` for the full buildout plan.

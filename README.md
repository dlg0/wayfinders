# Wayfinders (show pipeline repo scaffold)

This repository is a **developer handoff scaffold** for a complete production tool to create a
stylized, low-frame kids adventure series using **rigged cutouts** (Option B).

## What "complete" means (Definition of Done)
Once the items in `docs/ROADMAP.md` are implemented, the tool supports:
- declarative episodes (YAML) + canonical show data (YAML)
- caching + provenance for asset generation
- building a Timeline IR and rendering an animatic/final MP4
- reporting (costs, reused vs new, provenance bundles)

## Quickstart
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,placeholders]"
```

Validate the example episode:
```bash
wf validate episodes/s01e01_map_forgot_roads/episode.yaml --allow-missing-assets
```

Generate placeholder assets:
```bash
wf placeholders episodes/s01e01_map_forgot_roads/episode.yaml
```

Create a build plan:
```bash
wf plan episodes/s01e01_map_forgot_roads/episode.yaml
```

Build timeline + animatic stub:
```bash
wf build-timeline episodes/s01e01_map_forgot_roads/episode.yaml
wf build-animatic episodes/s01e01_map_forgot_roads/episode.yaml
```

Export JSON schemas for editor tooling:
```bash
wf canon export-jsonschema
wf render export-jsonschema
```

## Key docs
- `docs/ARCHITECTURE.md`
- `docs/ROADMAP.md`
- `docs/RENDER_SPEC.md`
- `docs/TIMELINE_IR.md`
- `docs/PROVENANCE.md`

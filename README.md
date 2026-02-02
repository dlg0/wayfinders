# Wayfinders (show pipeline repo scaffold)

[![CI](https://github.com/dlg0/wayfinders/actions/workflows/ci.yml/badge.svg)](https://github.com/dlg0/wayfinders/actions/workflows/ci.yml)
[![Installation](https://img.shields.io/badge/docs-INSTALL.md-blue)](docs/INSTALL.md)

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
uv venv
source .venv/bin/activate
uv pip install -e ".[dev,placeholders]"
```

Validate the example episode:
```bash
uv run wf validate episodes/s01e01_map_forgot_roads/episode.yaml --allow-missing-assets
```

Generate placeholder assets:
```bash
uv run wf placeholders episodes/s01e01_map_forgot_roads/episode.yaml
```

Create a build plan:
```bash
uv run wf plan episodes/s01e01_map_forgot_roads/episode.yaml
```

Build timeline + animatic stub:
```bash
uv run wf build-timeline episodes/s01e01_map_forgot_roads/episode.yaml
uv run wf build-animatic episodes/s01e01_map_forgot_roads/episode.yaml
```

Export JSON schemas for editor tooling:
```bash
uv run wf canon export-jsonschema
uv run wf render export-jsonschema
```

## Key docs
- `docs/ARCHITECTURE.md`
- `docs/ROADMAP.md`
- `docs/RENDER_SPEC.md`
- `docs/TIMELINE_IR.md`
- `docs/PROVENANCE.md`

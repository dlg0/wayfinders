# Timeline IR (internal representation)

Stable contract between shotlist YAML and renderers/preview tools.

Location:
- episodes/<ep>/logs/timeline.json

Models:
- src/wayfinders_cli/render/ir.py

JSON Schema:
- docs/jsonschema/timeline.schema.json (via `wf render export-jsonschema`)

Semantics:
- frame_count authoritative
- bg_layers optional for parallax
- actor transforms optional (x,y,scale,rotation_deg)
- overlays and audio are structured and extensible

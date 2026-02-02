# Provenance & reproducibility

Each generated asset should have a sidecar JSON (same filename + .json) with:
- cache_key
- provider_id/model_id
- template_name
- resolved_prompt
- params
- created_at
- output_hash (sha256)

Per-episode JSONL:
- episodes/<ep>/logs/gen_runs.jsonl

Provenance bundle zip should include:
- all sidecars + gen_runs.jsonl
- plan.json + timeline.json
- output checksums (mp4 sha256)

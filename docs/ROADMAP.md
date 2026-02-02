# Roadmap to "complete production tool"

M0 (in repo now)
- schemas + validation + plan
- placeholder generation
- timeline IR builder + schema export
- animatic stub + ffmpeg wrapper

M1 Episode scaffolding
- robust templated scaffolding using Jinja templates (episode + shotlist)
- CLI: `wf new-episode ... --template ...`

M2 Generation infrastructure
- provider registry + config (`wf.toml`)
- prompt resolver (Jinja) + resolved prompt logging
- cache keys + sidecars + gen_runs.jsonl
- CLI: `wf gen assets --episode ... --changed/--force`

M3 Rendering engine (cutouts)
- compositor: parallax, camera moves, actor staging, overlays, simple fx
- frames output + MP4 assembly

M4 Audio mix + Final
- dialogue track support, sfx, music bed, final mix

M5 QC + Reporting + Packaging
- QC gates (kids rules + IP checklist reminders)
- cost and reuse reporting
- provenance bundle zip

Definition of Done
- `wf build final <episode.yaml>` produces `renders/final.mp4` and a provenance bundle
